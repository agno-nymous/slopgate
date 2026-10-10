import math
import re
import subprocess
import threading
import time
import zlib
from types import SimpleNamespace

import pytest

from slopgate import embed, llm, trace

STARTED = time.strftime("%Y-%m-%d %H:%M:%S")
trace.start("slopgate-tests")


@pytest.fixture(autouse=True)
def traced(request):
    with trace.span("test.run", session=f"{request.node.originalname} {STARTED}", input=request.node.nodeid, test=request.node.nodeid):
        yield


@pytest.fixture
def make_repo(tmp_path):
    def make(base: dict[str, str], head: dict[str, str]):
        def git(*args):
            subprocess.run(["git", *args], cwd=tmp_path, check=True, capture_output=True)

        def commit(files, message):
            for rel, content in files.items():
                if content is None:
                    (tmp_path / rel).unlink()
                    continue
                (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
                (tmp_path / rel).write_text(content)
            git("add", "-A")
            git("commit", "-q", "-m", message)

        git("init", "-q", "-b", "main")
        git("config", "user.name", "Slopgate Test")
        git("config", "user.email", "test@example.com")
        git("config", "commit.gpgsign", "false")
        commit(base, "base")
        commit(head, "head")
        return str(tmp_path)

    return make


@pytest.fixture
def fake_llm(monkeypatch):
    fake = SimpleNamespace(replies=[], calls=[])

    def complete(model, prompt):
        fake.calls.append((model, prompt))
        llm.usage.append((model, 1000, 100))
        return fake.replies.pop(0)

    def yes_probability(model, prompt):
        fake.calls.append((model, prompt))
        return fake.replies.pop(0)

    lock = threading.Lock()

    def decide(model, prompt, schema):
        with lock:
            fake.calls.append((model, prompt))
            llm.usage.append((model, 1000, 100))
            return fake.replies.pop(0)

    monkeypatch.setattr(llm, "complete", complete)
    monkeypatch.setattr(llm, "decide", decide)
    monkeypatch.setattr(llm, "yes_probability", yes_probability)
    monkeypatch.setattr(llm, "usage", [])
    return fake


@pytest.fixture(autouse=True)
def fake_embed(request, monkeypatch):
    fake = SimpleNamespace(calls=[], real=embed.encode)
    if request.node.get_closest_marker("live"):
        return fake

    def vector(text):
        counts = [0] * 1024
        for token in re.findall(r"[A-Za-z_]\w*", text):
            counts[zlib.crc32(token.encode()) % 1024] += 1
        norm = math.sqrt(sum(c * c for c in counts)) or 1
        return [c / norm for c in counts]

    def encode(texts, query=False):
        fake.calls.append((texts, query))
        return [vector(text) for text in texts]

    monkeypatch.setattr(embed, "encode", encode)
    monkeypatch.setattr(embed, "compile_model", lambda: True)
    monkeypatch.setattr(embed, "preload", lambda: None)
    return fake
