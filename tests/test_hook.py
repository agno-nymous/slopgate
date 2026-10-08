import importlib.util
import io
import json
from array import array
from pathlib import Path

import numpy
import pytest
from test_duplicates import RENAMED_COPY, SLUGIFY

from slopgate import embed
from slopgate.cli import main
from slopgate.config import LIGHTNING
from slopgate.live import rows, store

SLUG_COPY = '''\
def make_slug(heading):
    if heading is None:
        raise ValueError("title is required")
    return "-".join(heading.lower().split())
'''

UNIQUE = "def shipping_band(weight):\n    return 'heavy' if weight > 20 else 'light'\n"


def note(new, new_at, helper, helper_at, confidence):
    context = (
        f"slopgate: `{new}` ({new_at}) duplicates existing `{helper}` ({helper_at}), confidence {confidence}. "
        f"Call `{helper}` instead of keeping `{new}`, unless the behavior must differ."
    )
    return json.dumps({"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": context}}) + "\n"


def payload(repo, rel, content, tool="Write"):
    if tool == "Write":
        tool_input = {"file_path": f"{repo}/{rel}", "content": content}
    else:
        tool_input = {"file_path": f"{repo}/{rel}", "old_string": "", "new_string": content, "replace_all": False}
    return json.dumps({
        "session_id": "abc123",
        "transcript_path": "/home/me/.claude/projects/shop/abc123.jsonl",
        "cwd": repo,
        "permission_mode": "default",
        "hook_event_name": "PostToolUse",
        "tool_name": tool,
        "tool_input": tool_input,
        "tool_response": {"filePath": f"{repo}/{rel}", "success": True},
        "tool_use_id": "toolu_01ABC",
    })


def run(monkeypatch, capsys, stdin):
    monkeypatch.setattr("sys.stdin", io.StringIO(stdin))
    assert main(["hook"]) is None
    return capsys.readouterr()


def write(monkeypatch, capsys, repo, rel, content, tool="Write"):
    (Path(repo) / rel).parent.mkdir(parents=True, exist_ok=True)
    (Path(repo) / rel).write_text(content)
    return run(monkeypatch, capsys, payload(repo, rel, content, tool))


def indexed(make_repo, capsys, files):
    repo = make_repo({"app/__init__.py": "", **files}, {"README.md": "demo\n"})
    assert main(["index", "--repo", repo, "--ref", "HEAD"]) is None
    capsys.readouterr()
    return repo


@pytest.mark.parametrize("tool", ["Write", "Edit"])
def test_duplicate_write_prints_note_naming_helper_file_and_confidence(make_repo, fake_llm, monkeypatch, capsys, tool):
    repo = indexed(make_repo, capsys, {"app/text.py": SLUGIFY})
    fake_llm.replies += [0.97]

    result = write(monkeypatch, capsys, repo, "app/posts.py", SLUG_COPY, tool)

    assert result.out == note("make_slug", "app/posts.py:1", "slugify", "app/text.py:1", "0.97")
    [(model, prompt)] = fake_llm.calls
    assert model == LIGHTNING
    assert prompt.index(SLUGIFY) < prompt.index(SLUG_COPY)


def test_unique_write_prints_nothing_and_calls_no_llm(make_repo, fake_llm, monkeypatch, capsys):
    repo = indexed(make_repo, capsys, {"app/text.py": SLUGIFY})

    result = write(monkeypatch, capsys, repo, "app/ship.py", UNIQUE)

    assert (result.out, result.err) == ("", "")
    assert fake_llm.calls == []


def test_function_written_earlier_in_session_is_found(make_repo, fake_llm, monkeypatch, capsys):
    repo = indexed(make_repo, capsys, {})
    assert write(monkeypatch, capsys, repo, "app/text.py", SLUGIFY).out == ""
    assert fake_llm.calls == []
    fake_llm.replies += [0.95]

    result = write(monkeypatch, capsys, repo, "app/posts.py", SLUG_COPY)

    assert result.out == note("make_slug", "app/posts.py:1", "slugify", "app/text.py:1", "0.95")


@pytest.mark.parametrize(("confidence", "flagged"), [(0.8, True), (0.79, False)])
def test_confidence_below_flag_prints_nothing(make_repo, fake_llm, monkeypatch, capsys, confidence, flagged):
    repo = indexed(make_repo, capsys, {"app/text.py": SLUGIFY})
    fake_llm.replies += [confidence]

    result = write(monkeypatch, capsys, repo, "app/posts.py", SLUG_COPY)

    assert result.out == (note("make_slug", "app/posts.py:1", "slugify", "app/text.py:1", "0.80") if flagged else "")
    assert len(fake_llm.calls) == 1


def test_exact_structural_copy_is_flagged_without_llm(make_repo, fake_llm, monkeypatch, capsys):
    repo = indexed(make_repo, capsys, {"app/text.py": SLUGIFY})

    result = write(monkeypatch, capsys, repo, "app/posts.py", "import re\n\n\n" + RENAMED_COPY)

    assert result.out == note("make_slug", "app/posts.py:4", "slugify", "app/text.py:1", "1.00")
    assert fake_llm.calls == []


def test_syntax_error_exits_zero_with_no_output(make_repo, fake_llm, monkeypatch, capsys):
    repo = indexed(make_repo, capsys, {"app/text.py": SLUGIFY})

    result = write(monkeypatch, capsys, repo, "app/posts.py", "def broken(:\n")

    assert result.out == ""
    assert result.err.startswith("slopgate: ")


@pytest.mark.parametrize("stdin", ["not json", "{}", '{"tool_input": {}}'])
def test_bad_payload_exits_zero_with_no_output(monkeypatch, capsys, stdin):
    result = run(monkeypatch, capsys, stdin)

    assert result.out == ""
    assert result.err.startswith("slopgate: ")


def test_repo_without_store_exits_zero_silently(make_repo, fake_llm, monkeypatch, capsys):
    repo = make_repo({"app/text.py": SLUGIFY}, {"README.md": "demo\n"})

    result = write(monkeypatch, capsys, repo, "app/posts.py", RENAMED_COPY)

    assert (result.out, result.err) == ("", "")
    assert not (Path(repo) / ".slopgate").exists()


@pytest.mark.parametrize(
    "files",
    [{"tests/helpers.py": SLUGIFY}, {"app/text.py": SLUGIFY.replace("def slugify", "def test_slugify")}],
    ids=["under-tests", "named-test"],
)
def test_test_function_is_never_a_candidate(make_repo, fake_llm, monkeypatch, capsys, files):
    repo = indexed(make_repo, capsys, files)

    result = write(monkeypatch, capsys, repo, "app/posts.py", RENAMED_COPY)

    assert (result.out, result.err) == ("", "")
    assert fake_llm.calls == []


@pytest.mark.parametrize(
    ("rel", "content"),
    [("tests/test_posts.py", RENAMED_COPY), ("app/posts.py", RENAMED_COPY.replace("def make_slug", "def test_make_slug"))],
    ids=["under-tests", "named-test"],
)
def test_test_function_is_never_a_query(make_repo, fake_llm, monkeypatch, capsys, rel, content):
    repo = indexed(make_repo, capsys, {"app/text.py": SLUGIFY})

    result = write(monkeypatch, capsys, repo, rel, content)

    assert (result.out, result.err) == ("", "")
    assert fake_llm.calls == []


def test_renamed_function_is_not_flagged_against_its_old_name(make_repo, fake_llm, monkeypatch, capsys):
    repo = indexed(make_repo, capsys, {"app/text.py": SLUGIFY})

    result = write(monkeypatch, capsys, repo, "app/text.py", RENAMED_COPY)

    assert (result.out, result.err) == ("", "")
    assert fake_llm.calls == []


def test_editing_a_known_function_loads_no_model(make_repo, fake_llm, fake_embed, monkeypatch, capsys):
    repo = indexed(make_repo, capsys, {"app/text.py": SLUGIFY})
    fake_embed.calls.clear()

    result = write(monkeypatch, capsys, repo, "app/text.py", SLUGIFY.replace("title.lower()", "title.strip().lower()"), "Edit")

    assert (result.out, result.err) == ("", "")
    assert fake_embed.calls == []


def test_real_encode_prefixes_queries_only(make_repo, fake_llm, fake_embed, monkeypatch, capsys):
    texts = []

    class Model:
        def encode(self, batch, normalize_embeddings):
            assert normalize_embeddings
            texts.extend(batch)
            return numpy.full((len(batch), 4), 0.5)

    monkeypatch.setattr(embed, "model", Model())
    monkeypatch.setattr(embed, "encode", fake_embed.real)
    repo = indexed(make_repo, capsys, {"app/text.py": SLUGIFY})
    fake_llm.replies += [0.1]

    assert write(monkeypatch, capsys, repo, "app/ship.py", UNIQUE).out == ""
    assert texts == [SLUGIFY, embed.PREFIX + UNIQUE, UNIQUE]


def test_seed_stores_each_pooled_function_with_its_own_vector(make_repo, fake_embed, capsys):
    repo = indexed(make_repo, capsys, {"app/text.py": "class Box:\n    def open(self):\n        return 1\n\n\n" + SLUGIFY})

    assert fake_embed.calls[0][0] == [SLUGIFY]
    [row] = rows(store(Path(repo)), "app/text.py")
    assert (row.qualname, row.vector) == ("slugify", array("f", embed.encode([SLUGIFY])[0]).tobytes())


def test_new_function_is_stored_even_when_classifier_fails(make_repo, fake_llm, monkeypatch, capsys):
    repo = indexed(make_repo, capsys, {"app/text.py": SLUGIFY})
    failed = write(monkeypatch, capsys, repo, "app/posts.py", SLUG_COPY)
    assert failed.out == ""
    assert failed.err.startswith("slopgate: ")

    result = write(monkeypatch, capsys, repo, "app/views.py", SLUG_COPY.replace("make_slug(heading)", "to_slug(text)").replace("heading", "text"))

    assert result.out == note("to_slug", "app/views.py:1", "make_slug", "app/posts.py:1", "1.00")


@pytest.mark.parametrize("installed, expected", [(True, "onnx"), (False, "torch")])
def test_cached_onnx_model_is_used_only_when_onnxruntime_is_installed(tmp_path, monkeypatch, installed, expected):
    compiled = tmp_path / "coderank-int8.onnx"
    compiled.touch()
    find_spec = importlib.util.find_spec
    monkeypatch.setattr(importlib.util, "find_spec", lambda name, *a: (installed or None) if name == "onnxruntime" else find_spec(name, *a))
    monkeypatch.setattr(embed, "COMPILED", compiled)
    monkeypatch.setattr(embed, "model", None)
    monkeypatch.setattr(embed, "onnx_model", lambda: "onnx")
    monkeypatch.setattr(embed, "torch_model", lambda: "torch")
    embed.load()
    assert embed.model == expected
