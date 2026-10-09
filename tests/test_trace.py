import http.server
import json
import os
import socket
import subprocess
import sys
import threading
import time

import pytest

from slopgate import trace

SENTINEL = "sk-sentinel-4711"

OFF_CODE = """
import sys
from slopgate.cli import main
main(sys.argv[1:])
from slopgate import trace
with trace.span("x", a=1):
    trace.output("y")
trace.bind(print)
leaked = {name.partition(".")[0] for name in sys.modules} & {"opentelemetry", "phoenix", "openinference"}
assert not leaked, sorted(leaked)
"""

TRACED_CODE = """
import sys
from concurrent.futures import ThreadPoolExecutor
from slopgate import llm, trace
from slopgate.sandbox import Local
llm.BASE_URL = sys.argv[1] + "/v1/"
trace.start("slopgate-tests")
with trace.span("test.run"):
    with ThreadPoolExecutor() as threads:
        list(threads.map(trace.bind(lambda prompt: llm.complete("m", prompt)), ["hello from the test"]))
    Local().run(sys.argv[2], {}, "env")
"""

CLOSED_CODE = """
from slopgate import trace
trace.start("p")
with trace.span("x"):
    pass
"""

CHAT_REPLY = {
    "id": "x",
    "object": "chat.completion",
    "created": 0,
    "model": "m",
    "choices": [{"index": 0, "message": {"role": "assistant", "content": "ok"}, "finish_reason": "stop"}],
    "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
}


def git_rev(repo, ref):
    return subprocess.run(["git", "rev-parse", ref], cwd=repo, capture_output=True, text=True, check=True).stdout.strip()


def test_tracing_off_imports_no_opentelemetry(make_repo):
    repo = make_repo({"app.py": "def f():\n    return 1\n"}, {"app.py": "def f():\n    return 2\n"})
    env = {key: value for key, value in os.environ.items() if key != "PHOENIX_COLLECTOR_ENDPOINT"}
    run = subprocess.run(
        [
            sys.executable,
            "-c",
            OFF_CODE,
            "review",
            "--repo",
            repo,
            "--base",
            git_rev(repo, "HEAD~1"),
            "--head",
            git_rev(repo, "HEAD"),
            "--dry-run",
            "--sandbox",
            "local",
        ],
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert run.returncode == 0, run.stderr


def test_no_span_holds_the_api_key(tmp_path):
    pytest.importorskip("phoenix.otel")
    from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import ExportTraceServiceRequest

    trace_bodies = []

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_POST(self):
            body = self.rfile.read(int(self.headers["Content-Length"]))
            if self.path == "/v1/chat/completions":
                payload = json.dumps(CHAT_REPLY).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
            else:
                trace_bodies.append(body)
                payload = b""
                self.send_response(200)
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, *args):
            pass

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        url = f"http://127.0.0.1:{server.server_port}"
        env = {
            **os.environ,
            "NEBIUS_API_KEY": SENTINEL,
            "PHOENIX_COLLECTOR_ENDPOINT": url,
        }
        run = subprocess.run(
            [sys.executable, "-c", TRACED_CODE, url, str(tmp_path)],
            env=env,
            capture_output=True,
            text=True,
            timeout=120,
        )
    finally:
        server.shutdown()

    assert run.returncode == 0, run.stderr
    spans = []
    for body in trace_bodies:
        request = ExportTraceServiceRequest()
        request.ParseFromString(body)
        for resource in request.resource_spans:
            for scope in resource.scope_spans:
                spans.extend(scope.spans)
    names = {span.name for span in spans}
    assert {"test.run", "ChatCompletion", "sandbox.run"} <= names, names
    roots = [span for span in spans if span.parent_span_id == b""]
    assert len(roots) == 1, [span.name for span in roots]
    joined = b"".join(trace_bodies)
    assert b"hello from the test" in joined
    assert SENTINEL.encode() not in joined


def test_exit_is_quick_when_phoenix_is_down(tmp_path):
    pytest.importorskip("phoenix.otel")
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    env = {key: value for key, value in os.environ.items() if key != "OTEL_EXPORTER_OTLP_TRACES_TIMEOUT"}
    env["PHOENIX_COLLECTOR_ENDPOINT"] = f"http://127.0.0.1:{port}"
    started = time.monotonic()
    run = subprocess.run([sys.executable, "-c", CLOSED_CODE], env=env, capture_output=True, text=True, timeout=120)
    elapsed = time.monotonic() - started
    assert run.returncode == 0, run.stderr
    assert elapsed < 4.0


def test_start_refuses_a_remote_endpoint(monkeypatch, capsys):
    monkeypatch.setattr(trace, "_project", None)
    monkeypatch.setenv("PHOENIX_COLLECTOR_ENDPOINT", "https://app.phoenix.arize.com")
    trace.start("p")
    assert trace._project is None
    assert "not a local Phoenix" in capsys.readouterr().err


def test_traced_review_matches_untraced_review(make_repo, fake_llm, capsys, monkeypatch):
    pytest.importorskip("phoenix.otel")
    from openinference.instrumentation import OITracer, TraceConfig
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
    from test_review import FLAT, IS_NESTING, NESTED, TESTS, fenced, review

    repo = make_repo({"app/__init__.py": ""}, {"app/perms.py": NESTED})
    replies = [IS_NESTING, fenced(TESTS.format(name="can_edit", call="can_edit")), fenced(FLAT)]
    fake_llm.replies += replies
    untraced = review(capsys, repo)
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    monkeypatch.setattr(trace, "_project", "slopgate-tests")
    monkeypatch.setattr(trace, "_tracer", OITracer(provider.get_tracer("test"), config=TraceConfig()))
    fake_llm.replies += replies

    assert review(capsys, repo) == untraced
    function = next(span for span in exporter.get_finished_spans() if span.name == "gate.function")
    assert json.loads(function.attributes["metadata"])["slop_kind"] == "nesting"
