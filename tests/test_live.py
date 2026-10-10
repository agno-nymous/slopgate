import inspect
import os
import subprocess
import time
from pathlib import Path

import pytest
from openai import OpenAI
from test_duplicates import SLUGIFY
from test_hook import SLUG_COPY, UNIQUE, indexed, write
from test_review import FLAT, NESTED, SIMPLE, TESTS, fenced, review
from test_wrappers import APPLY_DISCOUNT

from slopgate import config, embed, live, llm
from slopgate.functions import parse
from slopgate.kinds import classify
from slopgate.review import SAME_JOB_PROMPT, SameJob, characterize
from slopgate.sandbox import Contree, Local

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
    fake_llm.replies += [fenced(TESTS.format(name="can_edit", call="can_edit")), fenced(FLAT)]

    result = review(capsys, repo, "contree")

    assert result["rejected"] == []
    assert len(result["suggestions"]) == 1


@needs_sandbox
def test_contree_session_hides_the_api_key_and_ends_a_hung_command(make_repo):
    repo = make_repo({"README.md": "demo\n"}, {"app/__init__.py": ""})
    box = Contree()
    session = box.session(box.prepare(repo, "HEAD", None))

    code, output = session.execute("env", 60)
    start = time.perf_counter()
    hung = session.execute("echo started; sleep 30", 3)
    seconds = time.perf_counter() - start
    print(f"hung command: {hung!r} after {seconds:.1f} s")

    assert code == 0 and "PATH=" in output and "NEBIUS_" not in output
    assert hung == (124, "started\n") and seconds < 20
    assert session.read("missing.txt") is None


@needs_sandbox
def test_contree_run_stops_a_sleep_at_the_time_limit(make_repo, monkeypatch):
    repo = make_repo({"README.md": "demo\n"}, {"app/__init__.py": ""})
    box = Contree()
    checkpoint = box.prepare(repo, "HEAD", None)
    monkeypatch.setattr("slopgate.sandbox.SANDBOX_TIMEOUT", 5)

    start = time.perf_counter()
    assert box.run(checkpoint, {}, "true")[0] == 0
    overhead = time.perf_counter() - start
    start = time.perf_counter()
    code, output = box.run(checkpoint, {}, "sleep 10")
    seconds = time.perf_counter() - start
    print(f"true: {overhead:.1f} s, sleep 10: {code} {output!r} after {seconds:.1f} s")

    assert code == 124 and output.endswith("timed out after 5 s")
    assert seconds < 5 + overhead + 3


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


@pytest.mark.parametrize("model", [config.SUPER, config.LIGHTNING], ids=["super", "lightning"])
def test_decide_finds_a_renamed_copy_of_apply_discount(model):
    copy = APPLY_DISCOUNT.replace("apply_discount", "discounted_price")
    prompt = SAME_JOB_PROMPT.format(path="shop/cart.py", source=copy, helper_path="shop/pricing.py", helper_source=APPLY_DISCOUNT)

    start = time.perf_counter()
    verdict = llm.decide(model, prompt, SameJob)
    print(f"{model}: {time.perf_counter() - start:.2f} s, {verdict!r}")

    assert verdict is not None and verdict.same_job, verdict


@pytest.mark.parametrize(
    ("path", "qualname"),
    [("app/pricing.py", "apply_discount"), ("slopgate/review.py", "broken_rule")],
    ids=["apply_discount", "broken_rule"],
)
def test_agent_proves_characterization_tests(make_repo, monkeypatch, path, qualname):
    root = Path(__file__).parent.parent
    package = {f"slopgate/{p.name}": p.read_text() for p in (root / "slopgate").glob("*.py")}
    head = {"app/__init__.py": "", "app/pricing.py": APPLY_DISCOUNT, **package}
    repo = make_repo({"README.md": "demo\n"}, head)
    [function] = [f for f in parse(path, head[path]) if f.qualname == qualname]
    replies = []
    step = llm.step
    monkeypatch.setattr(llm, "step", lambda model, messages, tools: replies.append(step(model, messages, tools)) or replies[-1])
    sandbox = Local()
    test_path = "tests/test_slopgate_0.py"

    start = time.perf_counter()
    tests, failure = characterize(sandbox, sandbox.prepare(repo, "HEAD", None), function, test_path, f"python -m coverage run --branch -m pytest -q {test_path}")
    print(f"{qualname}: {time.perf_counter() - start:.1f} s, {len(replies)} steps, failure {failure!r}")
    for reply in replies:
        print(reply.content, [call.function.arguments for call in reply.tool_calls or []])

    assert failure is None and tests, failure


PR_20_HEAD = "70c27da340aeaadec60bfb22a711c84acdb0cabd"
PR_20_NOTES = {
    "tests/test_duplicates.py": ["test_copy_with_other_error_on_none"],
    "tests/test_github.py": [
        "test_inline_suggestions_are_posted_as_one_comment_review",
        "test_pr_flag_fetches_the_pull_request_reviews_it_and_posts_to_it",
        "test_followup_changes_open_one_pull_request_on_the_author_branch",
        "test_followup_pull_request_failure_still_posts_the_review",
    ],
    "tests/test_live.py": ["test_super_tests_reply_is_proven_or_cannot_test"],
    "tests/test_review.py": [
        "test_rewrite_that_changes_behavior_is_rejected",
        "test_each_in_place_kind_gets_a_suggestion_naming_it",
        "test_tests_that_fail_on_original_get_one_retry_with_the_failure",
        "test_calls_that_do_not_evaluate_get_one_retry_with_the_error",
        "test_empty_block_gets_one_retry_that_names_the_error",
        "test_method_prompt_has_no_calls_form_and_bare_calls_run_as_a_test_file",
    ],
}


def test_classify_finds_no_kind_in_the_pr_20_test_functions():
    root = Path(__file__).parent.parent
    found = {}
    for path, names in PR_20_NOTES.items():
        text = subprocess.run(["git", "show", f"{PR_20_HEAD}:{path}"], cwd=root, check=True, capture_output=True, text=True).stdout
        found |= {function.qualname: classify(function, text) for function in parse(path, text) if function.qualname in names}

    assert len(found) == 12
    assert found == dict.fromkeys(found, {}), found


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
