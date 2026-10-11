import json
import subprocess
import sys

import pytest
from test_review import FLAT, NESTED, SIMPLE, TESTS, fenced, models, review

from slopgate import embed
from slopgate.cli import main
from slopgate.config import SUPER
from slopgate.review import SameJob
from slopgate.index import build, search

SLUGIFY = '''\
def slugify(title):
    if title is None:
        raise ValueError("title is required")
    words = title.lower().split()
    return "-".join(words)
'''

RENAMED_COPY = '''\
def make_slug(heading):
    if heading is None:
        raise ValueError("title is required")
    parts = heading.lower().split()
    return "-".join(parts)
'''

POST_PATH = '''

def post_path(heading):
    return "posts/" + make_slug(heading) + ".html"
'''

VIEWS = '''\
from app.posts import make_slug


def url_for(heading):
    return "/posts/" + make_slug(heading)
'''

VIEW_TESTS = '''\
from app.posts import post_path
from app.views import url_for


def test_url_for():
    assert url_for("Hello World") == "/posts/hello-world"


def test_post_path():
    assert post_path("Hello World") == "posts/hello-world.html"
'''

TYPE_ERROR_COPY = '''\
def make_slug(title):
    if title is None:
        raise TypeError("title is required")
    return "-".join(title.lower().split())
'''

SLUG_TESTS = '''\
import pytest

from app.posts import make_slug


def test_none():
    with pytest.raises(TypeError):
        make_slug(None)


def test_words():
    assert make_slug("Hello Big World") == "hello-big-world"
'''

EMPTY = {"suggestions": [], "followup": [], "rejected": [], "notes": []}
OTHER_JOB = SameJob(difference="", same_job=False)


def index(capsys, repo):
    assert main(["index", "--repo", repo, "--ref", "HEAD"]) is None
    return json.loads(capsys.readouterr().out)


def test_index_is_written_once_and_loaded_after(make_repo, fake_embed, capsys, tmp_path):
    repo = make_repo({"app/text.py": SLUGIFY}, {"app/ship.py": SIMPLE})
    sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True).stdout.strip()

    first = index(capsys, repo)

    path = tmp_path / ".slopgate" / f"{sha}.json"
    assert first == {"ref": sha, "functions": 2, "path": str(path)}
    written = path.read_bytes()
    fake_embed.calls.clear()
    sentinel = [{"source": "def sentinel(): pass\n"}]
    path.write_text(json.dumps(sentinel))
    assert build(repo, "HEAD") == sentinel
    path.write_bytes(written)
    assert fake_embed.calls == []
    assert all("vector" not in record for record in json.loads(written))


def test_renamed_exact_copy_is_replaced_by_the_helper_without_llm(make_repo, fake_llm, capsys, tmp_path_factory):
    ran = tmp_path_factory.mktemp("log") / "ran"
    repo = make_repo(
        {"app/__init__.py": "", "app/text.py": SLUGIFY},
        {
            "app/posts.py": RENAMED_COPY + POST_PATH,
            "app/views.py": VIEWS,
            "tests/test_views.py": VIEW_TESTS,
            ".slopgate.toml": f"[sandbox]\ntest = 'python -m pytest -q tests/test_views.py && echo ok >> {ran}'\n",
        },
    )

    result = review(capsys, repo)

    assert fake_llm.calls == []
    assert result["suggestions"] == [] and result["rejected"] == []
    [followup] = result["followup"]
    assert followup["function"] == "make_slug" and followup["kinds"] == ["duplicate"]
    assert "`slugify` in app/text.py" in followup["reason"]
    assert followup["files"] == {
        "app/posts.py": 'from app.text import slugify\ndef post_path(heading):\n    return "posts/" + slugify(heading) + ".html"\n',
        "app/views.py": VIEWS.replace("from app.posts import make_slug", "from app.text import slugify").replace(
            "make_slug(", "slugify("
        ),
    }
    assert ran.read_text() == "ok\n"


@pytest.mark.parametrize(
    ("difference", "outcome"),
    [("raises TypeError instead of ValueError on None", "followup"), ("", "rejected")],
    ids=["stated", "unstated"],
)
def test_copy_with_other_error_on_none(make_repo, fake_llm, capsys, difference, outcome):
    repo = make_repo({"app/__init__.py": "", "app/text.py": SLUGIFY}, {"app/posts.py": TYPE_ERROR_COPY})
    fake_llm.replies += [SameJob(difference=difference, same_job=True), fenced(SLUG_TESTS)]

    result = review(capsys, repo)

    assert models(fake_llm) == [SUPER, SUPER, SUPER]
    [entry] = result[outcome]
    if outcome == "followup":
        assert "`slugify` in app/text.py" in entry["reason"]
        assert difference in entry["reason"] and "test_none" in entry["reason"]
        assert entry["files"] == {"app/posts.py": ""}
    else:
        assert entry["reason"].startswith("differential tests fail on helper")
        assert result["followup"] == []


def test_candidate_without_a_verdict_is_skipped(make_repo, fake_llm, capsys):
    repo = make_repo({"app/__init__.py": "", "app/a.py": SLUGIFY, "app/b.py": SLUGIFY}, {"app/posts.py": TYPE_ERROR_COPY})
    fake_llm.replies += [None, SameJob(difference="raises TypeError", same_job=True), fenced(SLUG_TESTS)]

    result = review(capsys, repo)

    assert models(fake_llm) == [SUPER] * 4
    [helper] = [path for path in ("app/a.py", "app/b.py") if f"Existing helper, in {path}:" in fake_llm.calls[1][1]]
    [entry] = result["followup"]
    assert f"`slugify` in {helper}" in entry["reason"] and "raises TypeError" in entry["reason"]


def test_unrelated_helper_below_floor_costs_no_llm_call(make_repo, fake_llm, fake_embed, capsys):
    repo = make_repo({"app/text.py": SLUGIFY}, {"app/ship.py": FLAT})

    assert review(capsys, repo) == EMPTY
    assert fake_llm.calls == []
    assert fake_embed.calls == []


def test_copy_is_found_when_the_embedding_model_fails(make_repo, fake_llm, capsys, monkeypatch):
    def encode(texts, query=False):
        raise RuntimeError("no embedding model")

    monkeypatch.setattr(embed, "encode", encode)
    repo = make_repo({"app/__init__.py": "", "app/text.py": SLUGIFY}, {"app/posts.py": TYPE_ERROR_COPY})
    fake_llm.replies += [SameJob(difference="raises TypeError instead of ValueError on None", same_job=True), fenced(SLUG_TESTS)]

    result = review(capsys, repo)

    [followup] = result["followup"]
    assert "`slugify` in app/text.py" in followup["reason"]
    assert followup["files"] == {"app/posts.py": ""}


@pytest.mark.parametrize(
    ("base", "head"),
    [
        (SLUGIFY, "class Posts:\n" + "".join("    " + line for line in RENAMED_COPY.splitlines(keepends=True))),
        ("class Text:\n" + "".join("    " + line for line in SLUGIFY.splitlines(keepends=True)), RENAMED_COPY),
    ],
    ids=["head-method", "base-method"],
)
def test_methods_are_never_duplicates(make_repo, fake_llm, capsys, base, head):
    repo = make_repo({"app/text.py": base}, {"app/posts.py": head, "app/ship.py": FLAT})

    assert review(capsys, repo) == EMPTY
    assert fake_llm.calls == []


def test_partly_changed_function_lands_in_followup_with_full_file(make_repo, fake_llm, capsys):
    repo = make_repo({"app/__init__.py": "", "app/perms.py": NESTED}, {"app/perms.py": NESTED.replace("return True", "return bool(1)")})
    fake_llm.replies += [fenced(TESTS.format(name="can_edit", call="can_edit")), fenced(FLAT)]

    result = review(capsys, repo)

    assert result["suggestions"] == [] and result["rejected"] == []
    [followup] = result["followup"]
    assert (followup["function"], followup["kinds"]) == ("can_edit", ["nesting"])
    assert "nesting 4 -> 0" in followup["reason"]
    assert followup["files"] == {"app/perms.py": FLAT}


RESTRUCTURED = '''\
def make_slug(title):
    if title is None:
        return ""
    lowered = title.lower()
    words = lowered.split()
    return "-".join(words)
'''

PLAIN_SLUGIFY = '''\
def slugify(title):
    words = title.lower().split()
    return "-".join(words)
'''

RESTRUCTURED_TESTS = '''\
from app.posts import make_slug


def test_none():
    assert make_slug(None) == ""


def test_words():
    assert make_slug("Hello Big World") == "hello-big-world"
'''


@pytest.mark.parametrize("parameter", ["title", "heading"])
def test_restructured_copy_is_found_by_keyword_search(make_repo, fake_llm, capsys, parameter):
    repo = make_repo(
        {"app/__init__.py": "", "app/text.py": PLAIN_SLUGIFY}, {"app/posts.py": RESTRUCTURED.replace("title", parameter)}
    )
    fake_llm.replies += [
        SameJob(difference="returns an empty string for None where the helper raises", same_job=True),
        fenced(RESTRUCTURED_TESTS),
    ]

    result = review(capsys, repo)

    [followup] = result["followup"]
    assert followup["files"] == {"app/posts.py": ""}
    assert models(fake_llm) == [SUPER, SUPER, SUPER]


ORIGINAL_TEST = '''\
def test_non_python_change(tmp_path):
    (tmp_path / "notes.md").write_text("draft")
    assert [p.name for p in tmp_path.iterdir()] == ["notes.md"]
'''

COPIED_TEST = '''\
def test_unique_write(folder):
    (folder / "notes.md").write_text("draft")
    assert [f.name for f in folder.iterdir()] == ["notes.md"]
'''


def test_copied_test_function_gets_a_duplicate_note(make_repo, fake_llm, capsys):
    repo = make_repo({"tests/test_hook.py": ORIGINAL_TEST}, {"tests/test_hook.py": ORIGINAL_TEST + "\n\n" + COPIED_TEST})

    result = review(capsys, repo)

    assert fake_llm.calls == []
    body = (
        "**duplicate** (not rewritten): `test_unique_write` does the same job as `test_non_python_change` in tests/test_hook.py. "
        "Consider one parametrized test. Slopgate does not change test files."
    )
    assert result == EMPTY | {"notes": [{"path": "tests/test_hook.py", "function": "test_unique_write", "kinds": ["duplicate"], "line": 8, "body": body}]}


def test_test_function_copying_a_production_function_says_to_call_it(make_repo, fake_llm, capsys):
    repo = make_repo({"app/__init__.py": "", "app/text.py": SLUGIFY}, {"tests/conftest.py": RENAMED_COPY})

    result = review(capsys, repo)

    assert fake_llm.calls == []
    body = (
        "**duplicate** (not rewritten): `make_slug` does the same job as `slugify` in app/text.py. "
        "Call it instead. Slopgate does not change test files."
    )
    assert result == EMPTY | {"notes": [{"path": "tests/conftest.py", "function": "make_slug", "kinds": ["duplicate"], "line": 5, "body": body}]}


def test_function_changed_in_the_same_pr_is_not_a_helper(make_repo, fake_llm, capsys):
    changed_helper = SLUGIFY.replace('"title is required"', '"a title is required"')
    repo = make_repo(
        {"app/__init__.py": "", "app/posts.py": SLUGIFY},
        {"app/posts.py": changed_helper + "\n\n" + RENAMED_COPY},
    )

    assert review(capsys, repo) == EMPTY
    assert fake_llm.calls == []


def test_helper_moved_in_the_same_pr_is_not_a_helper(make_repo, fake_llm, capsys):
    repo = make_repo(
        {"app/__init__.py": "", "app/text.py": SLUGIFY},
        {"app/text.py": None, "app/words.py": SLUGIFY + "\n\n" + FLAT},
    )

    assert review(capsys, repo) == EMPTY
    assert fake_llm.calls == []


def test_helper_deleted_in_the_same_pr_is_not_a_helper(make_repo, fake_llm, capsys):
    repo = make_repo(
        {"app/__init__.py": "", "app/text.py": SLUGIFY},
        {"app/text.py": None, "app/posts.py": RENAMED_COPY},
    )

    assert review(capsys, repo) == EMPTY
    assert fake_llm.calls == []


def test_gate_imports_no_hook_only_module():
    code = (
        "import slopgate.cli, slopgate.review, slopgate.index, slopgate.github, slopgate.sandbox, sys; "
        "bad = {'slopgate.embed', 'numpy', 'torch', 'onnxruntime', 'sentence_transformers'} & set(sys.modules); "
        "assert not bad, bad"
    )
    assert subprocess.run([sys.executable, "-c", code]).returncode == 0


def test_search_returns_best_top_above_floor():
    def record(extra):
        return {"source": f"a b c d e f g h i j {extra}"}

    query = "a b c d e f g h i j"
    close = [record(" ".join(f"x{i}" for i in range(n))) for n in range(7)]
    far = {"source": "a b c d e f g h i j " + " ".join(f"y{i}" for i in range(100))}

    found = search([far, *reversed(close)], query, 0.5, 5)

    assert [r for _, r in found] == close[:5]
    assert [round(score, 2) for score, _ in found] == [1.0, 0.91, 0.83, 0.77, 0.71]
    assert far not in [r for _, r in search([far, *close], query, 0.5, 20)]
