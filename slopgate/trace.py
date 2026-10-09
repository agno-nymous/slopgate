import contextlib
import contextvars
import json
import os
import sys
from urllib.parse import urlparse

ENDPOINT = "PHOENIX_COLLECTOR_ENDPOINT"
LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}

_project = None
_tracer = None


def start(project: str) -> None:
    global _project
    endpoint = os.environ.get(ENDPOINT)
    if _project or not endpoint:
        return
    try:
        host = urlparse(endpoint).hostname
    except ValueError:
        host = None
    if host not in LOCAL_HOSTS:
        print(f"slopgate: tracing off: {ENDPOINT} is not a local Phoenix", file=sys.stderr)
        return
    _project = project


def span(name: str, input=None, session: str | None = None, **metadata):
    if _project is None:
        return contextlib.nullcontext()
    return _span(name, input, session, metadata)


def output(value) -> None:
    if _tracer is None:
        return
    from opentelemetry import trace

    trace.get_current_span().set_attributes(_payload("output", value))


def bind(fn):
    if _tracer is None:
        return fn
    context = contextvars.copy_context()
    # A Context cannot be entered by two threads at once, so each task runs in its own copy.
    return lambda *args: context.copy().run(fn, *args)


@contextlib.contextmanager
def _span(name, input, session, metadata):
    tracer = _setup()
    if tracer is None:
        yield
        return
    from openinference.instrumentation import get_attributes_from_context, using_metadata, using_session

    inherited = json.loads(dict(get_attributes_from_context()).get("metadata", "{}"))
    merged = inherited | {key: value for key, value in metadata.items() if value is not None}
    with (
        using_session(session) if session else contextlib.nullcontext(),
        using_metadata(merged),
        tracer.start_as_current_span(name, openinference_span_kind="tool" if name.startswith("sandbox.") else "chain") as current,
    ):
        if input is not None:
            current.set_attributes(_payload("input", input))
        yield


def _setup():
    global _project, _tracer
    if _tracer is None:
        # With the default 10 s timeout the exporter retries for 6-7 s at exit when Phoenix is down.
        os.environ.setdefault("OTEL_EXPORTER_OTLP_TRACES_TIMEOUT", "1")
        try:
            from phoenix.otel import register

            # gRPC (the default) replaces the URL's port with 4317; HTTP keeps the URL.
            provider = register(project_name=_project, protocol="http/protobuf", batch=True, auto_instrument=True, verbose=False)
        except Exception as error:
            print(f"slopgate: tracing off: {error!r}", file=sys.stderr)
            _project = None
            return None
        _tracer = provider.get_tracer("slopgate")
    return _tracer


def _payload(prefix: str, value) -> dict:
    if isinstance(value, str):
        return {f"{prefix}.value": value, f"{prefix}.mime_type": "text/plain"}
    return {f"{prefix}.value": json.dumps(value, default=str), f"{prefix}.mime_type": "application/json"}
