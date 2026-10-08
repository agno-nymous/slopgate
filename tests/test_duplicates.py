import json
import subprocess

import numpy
import pytest
from test_review import FLAT, IS_NESTING, NESTED, SIMPLE, TESTS, fenced, models, review

from slopgate import embed
from slopgate.cli import main
from slopgate.config import DUPLICATE_SCORE, SUPER

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

EMPTY = {"suggestions": [], "followup": [], "rejected": []}


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
    assert len(fake_embed.calls) == 1
    assert index(capsys, repo) == first
    assert path.read_bytes() == written
    assert len(fake_embed.calls) == 1


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
    assert followup["function"] == "make_slug" and followup["kind"] == "duplicate"
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
    fake_llm.replies += [json.dumps({"same_job": True, "difference": difference}), SLUG_TESTS]

    result = review(capsys, repo)

    assert models(fake_llm) == [SUPER, SUPER]
    [entry] = result[outcome]
    if outcome == "followup":
        assert "`slugify` in app/text.py" in entry["reason"]
        assert difference in entry["reason"] and "test_none" in entry["reason"]
        assert entry["files"] == {"app/posts.py": ""}
    else:
        assert entry["reason"].startswith("differential tests fail on helper")
        assert result["followup"] == []


def test_unrelated_helper_below_floor_costs_no_llm_call(make_repo, fake_llm, fake_embed, capsys):
    repo = make_repo({"app/text.py": SLUGIFY}, {"app/ship.py": SIMPLE})

    assert review(capsys, repo) == EMPTY
    assert fake_llm.calls == []
    assert fake_embed.calls == [([SLUGIFY], False), ([SIMPLE], True)]


@pytest.mark.parametrize(
    ("base", "head"),
    [
        (SLUGIFY, "class Posts:\n" + "".join("    " + line for line in RENAMED_COPY.splitlines(keepends=True))),
        ("class Text:\n" + "".join("    " + line for line in SLUGIFY.splitlines(keepends=True)), RENAMED_COPY),
    ],
    ids=["head-method", "base-method"],
)
def test_methods_are_never_duplicates(make_repo, fake_llm, capsys, base, head):
    repo = make_repo({"app/text.py": base}, {"app/posts.py": head, "app/ship.py": SIMPLE})

    assert review(capsys, repo) == EMPTY
    assert fake_llm.calls == []


def test_real_encode_prefixes_queries_only(make_repo, fake_llm, fake_embed, capsys, monkeypatch):
    texts = []

    class Model:
        def encode(self, batch, normalize_embeddings):
            assert normalize_embeddings
            texts.extend(batch)
            return numpy.full((len(batch), 4), 0.5)

    monkeypatch.setattr(embed, "model", Model())
    monkeypatch.setattr(embed, "encode", fake_embed.real)
    repo = make_repo({"app/text.py": SLUGIFY}, {"app/ship.py": SIMPLE})
    fake_llm.replies += ["not json"]

    assert review(capsys, repo) == EMPTY
    assert models(fake_llm) == [SUPER]
    assert texts == [SLUGIFY, "Represent this query for searching relevant code: " + SIMPLE]


def test_partly_changed_function_lands_in_followup_with_full_file(make_repo, fake_llm, capsys):
    repo = make_repo({"app/__init__.py": "", "app/perms.py": NESTED}, {"app/perms.py": NESTED.replace("return True", "return bool(1)")})
    fake_llm.replies += [IS_NESTING, TESTS.format(name="can_edit", call="can_edit"), fenced(FLAT)]

    result = review(capsys, repo)

    assert result["suggestions"] == [] and result["rejected"] == []
    [followup] = result["followup"]
    assert (followup["function"], followup["kind"]) == ("can_edit", "nesting")
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


@pytest.mark.live
@pytest.mark.parametrize("parameter", ["title", "heading"])
def test_restructured_copy_is_found_by_real_vector_search(make_repo, fake_llm, capsys, parameter):
    repo = make_repo(
        {"app/__init__.py": "", "app/text.py": PLAIN_SLUGIFY}, {"app/posts.py": RESTRUCTURED.replace("title", parameter)}
    )
    fake_llm.replies += [
        json.dumps({"same_job": True, "difference": "returns an empty string for None where the helper raises"}),
        RESTRUCTURED_TESTS,
    ]

    result = review(capsys, repo)

    [followup] = result["followup"]
    print(followup["reason"])
    score = float(followup["reason"].split("(score ")[1].split(")")[0])
    assert score >= DUPLICATE_SCORE
    assert followup["files"] == {"app/posts.py": ""}
    assert models(fake_llm) == [SUPER, SUPER]


def test_function_changed_in_the_same_pr_is_not_a_helper(make_repo, fake_llm, capsys):
    changed_helper = SLUGIFY.replace('"title is required"', '"a title is required"')
    repo = make_repo(
        {"app/__init__.py": "", "app/posts.py": SLUGIFY},
        {"app/posts.py": changed_helper + "\n\n" + RENAMED_COPY},
    )

    assert review(capsys, repo) == EMPTY
    assert fake_llm.calls == []
