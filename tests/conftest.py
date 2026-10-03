import subprocess
from types import SimpleNamespace

import pytest

from slopgate import llm


@pytest.fixture
def make_repo(tmp_path):
    def make(base: dict[str, str], head: dict[str, str]):
        def git(*args):
            subprocess.run(["git", *args], cwd=tmp_path, check=True, capture_output=True)

        def commit(files, message):
            for rel, content in files.items():
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

    def complete(model, prompt, json=False):
        fake.calls.append((model, prompt))
        return fake.replies.pop(0)

    monkeypatch.setattr(llm, "complete", complete)
    return fake
