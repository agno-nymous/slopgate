import inspect
import os

import pytest
from openai import OpenAI
from test_duplicates import SLUGIFY
from test_hook import SLUG_COPY, UNIQUE, indexed, write
from test_review import FLAT, IS_NESTING, NESTED, SIMPLE, TESTS, fenced, review

from slopgate import config, embed, live, llm

pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(not os.environ.get("NEBIUS_API_KEY"), reason="NEBIUS_API_KEY not set"),
]

needs_sandbox = pytest.mark.skipif(
    not (os.environ.get("NEBIUS_API_KEY") and os.environ.get("NEBIUS_PROJECT_ID")),
    reason="NEBIUS_API_KEY and NEBIUS_PROJECT_ID not both set",
)

PYPROJECT = """\
[build-system]
requires = ["setuptools"]
build-backend = "setuptools.build_meta"

[project]
name = "demo"
version = "0"
dependencies = ["attrs"]

[tool.setuptools]
packages = ["app"]
"""


def test_config_model_ids_exist_in_token_factory():
    available = {m.id for m in OpenAI(base_url=config.BASE_URL, api_key=os.environ["NEBIUS_API_KEY"]).models.list()}
    nemotron = sorted(i for i in available if "nemotron" in i.lower())
    for model in (config.LIGHTNING, config.SUPER, config.ULTRA):
        assert model in available, f"{model} not in Token Factory; nemotron models: {nemotron}"


@needs_sandbox
def test_nested_fixture_gives_same_json_in_contree_and_local(make_repo, fake_llm, capsys):
    repo = make_repo(
        {"app/__init__.py": "", "README.md": "demo\n"},
        {"app/perms.py": NESTED + "\n\n" + SIMPLE},
    )
    fake_llm.replies += 2 * [
        IS_NESTING,
        "```python\n" + TESTS.format(name="can_edit", call="can_edit") + "```",
        "Here is the rewrite:\n```python\n" + FLAT + "```",
    ]

    contree = review(capsys, repo, "contree")

    assert len(contree["suggestions"]) == 1
    assert contree == review(capsys, repo, "local")


@needs_sandbox
@pytest.mark.parametrize("manifest", [{"pyproject.toml": PYPROJECT}, {"requirements.txt": "attrs\n"}], ids=["pyproject", "requirements"])
def test_detected_install_provides_dependency(make_repo, fake_llm, capsys, manifest):
    repo = make_repo({"app/__init__.py": "", **manifest}, {"app/perms.py": "import attrs\n\n\n" + NESTED})
    fake_llm.replies += [IS_NESTING, TESTS.format(name="can_edit", call="can_edit"), fenced(FLAT)]

    result = review(capsys, repo, "contree")

    assert result["rejected"] == []
    assert len(result["suggestions"]) == 1


@pytest.mark.parametrize("model", [config.SUPER, config.ULTRA])
def test_complete_replies_without_reasoning(monkeypatch, model):
    openai = llm.client()
    create = openai.chat.completions.create
    replies = []
    monkeypatch.setattr(openai.chat.completions, "create", lambda **kwargs: replies.append(create(**kwargs)) or replies[-1])
    monkeypatch.setattr(llm, "client", lambda: openai)

    text = llm.complete(model, "Is 17 prime? Answer in one word.")

    [reply] = replies
    extra = reply.choices[0].message.model_extra
    assert text.strip()
    assert not extra.get("reasoning") and not extra.get("reasoning_content"), extra


def test_reuse_prompt_separates_copy_from_unique():
    copy = llm.yes_probability(config.LIGHTNING, live.question(SLUGIFY, SLUG_COPY))
    unique = llm.yes_probability(config.LIGHTNING, live.question(SLUGIFY, UNIQUE))

    assert copy >= config.FLAG and unique < 0.1, (copy, unique)


def test_int8_model_matches_torch():
    pytest.importorskip("onnxruntime")
    assert embed.compile_model()
    texts = [SLUGIFY, SLUG_COPY, UNIQUE, embed.PREFIX + SLUG_COPY, inspect.getsource(live.hook)]

    int8 = embed.onnx_model().encode(texts, normalize_embeddings=True)
    torch = embed.torch_model().encode(texts, normalize_embeddings=True)

    assert min((int8 * torch).sum(1)) >= 0.9


def test_hook_flags_copy_with_compiled_model_and_lightning(make_repo, monkeypatch, capsys):
    pytest.importorskip("onnxruntime")
    monkeypatch.setattr(embed, "model", None)
    repo = indexed(make_repo, capsys, {"app/text.py": SLUGIFY, "app/ship.py": SIMPLE})

    copy = write(monkeypatch, capsys, repo, "app/posts.py", SLUG_COPY)
    unique = write(monkeypatch, capsys, repo, "app/band.py", UNIQUE)

    assert "duplicates existing `slugify` (app/text.py:1)" in copy.out, copy.err
    assert (unique.out, unique.err) == ("", "")
