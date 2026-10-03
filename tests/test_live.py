import os

import pytest
from openai import OpenAI
from test_review import FLAT, IS_NESTING, NESTED, SIMPLE, TESTS, review

from slopgate import config

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
    fake_llm.replies += [IS_NESTING, TESTS.format(name="can_edit", call="can_edit"), FLAT]

    result = review(capsys, repo, "contree")

    assert result["rejected"] == []
    assert len(result["suggestions"]) == 1
