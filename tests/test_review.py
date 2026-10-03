import ast
import json
import re
import textwrap

import pytest

from slopgate.cli import main
from slopgate.config import LIGHTNING, SUPER, ULTRA
from slopgate.sandbox import Local

NESTED = '''\
def can_edit(user_active, is_owner, locked, archived):
    if user_active:
        if is_owner:
            if not locked:
                if not archived:
                    return True
                else:
                    return False
            else:
                return False
        else:
            return False
    else:
        return False
'''

SIMPLE = '''\
def shipping_band(weight):
    if weight < 1:
        return "small"
    elif weight < 5:
        return "medium"
    elif weight < 20:
        return "large"
    elif weight < 100:
        return "freight"
    return "quote"
'''

FLAT = '''\
def can_edit(user_active, is_owner, locked, archived):
    return user_active and is_owner and not locked and not archived
'''

TESTS = '''\
from app.perms import {name}


def test_inactive_user_cannot_edit():
    assert {call}(False, True, False, False) is False


def test_non_owner_cannot_edit():
    assert {call}(True, False, False, False) is False


def test_locked_cannot_edit():
    assert {call}(True, True, True, False) is False


def test_archived_cannot_edit():
    assert {call}(True, True, False, True) is False


def test_active_owner_can_edit_open_item():
    assert {call}(True, True, False, False) is True
'''

IS_NESTING = '{"kind": "nesting"}'
VIEW = NESTED.replace("can_edit", "can_view")
FLAT_VIEW = FLAT.replace("can_edit", "can_view")
DROPS_LOCKED = "def can_edit(user_active, is_owner, locked, archived):\n    return user_active and is_owner and not archived\n"


def review(capsys, repo, sandbox="local"):
    assert main(["review", "--repo", repo, "--base", "HEAD~1", "--head", "HEAD", "--dry-run", "--sandbox", sandbox]) is None
    out, err = capsys.readouterr()
    assert err == ""
    return json.loads(out)


def suggested_code(body):
    return re.search(r"```suggestion\n(.*?)```", body, re.S)[1]


def models(fake_llm):
    return [model for model, _ in fake_llm.calls]


def test_nested_function_gets_one_proven_suggestion(make_repo, fake_llm, capsys):
    repo = make_repo(
        {"app/__init__.py": "", "README.md": "demo\n"},
        {"app/perms.py": NESTED + "\n\n" + SIMPLE},
    )
    fake_llm.replies += [
        IS_NESTING,
        "```python\n" + TESTS.format(name="can_edit", call="can_edit") + "```",
        "Here is the rewrite:\n```python\n" + FLAT + "```",
    ]

    result = review(capsys, repo)

    assert result["followup"] == [] and result["rejected"] == []
    assert len(fake_llm.calls) == 3
    [suggestion] = result["suggestions"]
    assert suggestion["path"] == "app/perms.py"
    assert suggestion["side"] == "RIGHT"
    assert (suggestion["start_line"], suggestion["line"]) == (1, 14)
    assert suggestion["start_side"] == "RIGHT"
    body = suggestion["body"]
    assert "can_edit" in body and "shipping_band" not in body
    nest_before, nest_after = map(int, re.search(r"nesting (\d+) -> (\d+)", body).groups())
    assert nest_before == 4 and nest_after <= 2
    cc_before, cc_after = map(int, re.search(r"complexity (\d+) -> (\d+)", body).groups())
    assert cc_after < cc_before
    assert "5 characterization tests passed in sandbox" in body
    assert suggested_code(body) == FLAT


def test_method_keeps_qualname_decorator_line_and_indentation(make_repo, fake_llm, capsys):
    method = "class Policy:\n    VERSION = 1\n\n" + textwrap.indent("@staticmethod\n" + NESTED, "    ")
    repo = make_repo({"app/__init__.py": ""}, {"app/perms.py": method})
    fake_llm.replies += [
        IS_NESTING,
        TESTS.format(name="Policy", call="Policy.can_edit"),
        "@staticmethod\n" + FLAT,
    ]

    [suggestion] = review(capsys, repo)["suggestions"]

    assert "Policy.can_edit" in suggestion["body"]
    assert suggestion["start_line"] == 4
    assert suggestion["line"] == 18
    code = suggested_code(suggestion["body"])
    assert code == textwrap.indent("@staticmethod\n" + FLAT, "    ")
    lines = method.splitlines(keepends=True)
    ast.parse("".join(lines[: suggestion["start_line"] - 1]) + code + "".join(lines[suggestion["line"] :]))


def test_one_line_function_flagged_by_complexity_has_no_start_line(make_repo, fake_llm, capsys):
    repo = make_repo(
        {"app/__init__.py": ""},
        {"app/flags.py": "def all_set(a, b, c, d, e, f): return a and b and c and d and e and f\n"},
    )
    fake_llm.replies += [
        IS_NESTING,
        "from app.flags import all_set\n\n\n"
        + "".join(
            f"def test_false_at_{i}():\n    args = [True] * 6\n    args[{i}] = False\n    assert all_set(*args) is False\n\n\n"
            for i in range(6)
        )
        + "def test_all_true():\n    assert all_set(*[True] * 6) is True\n",
        "def all_set(a, b, c, d, e, f): return all((a, b, c, d, e, f))\n",
    ]

    [suggestion] = review(capsys, repo)["suggestions"]

    assert suggestion["line"] == 1
    assert "start_line" not in suggestion and "start_side" not in suggestion
    assert "complexity 6 -> 1" in suggestion["body"]


def test_rewrite_that_changes_behavior_is_rejected(make_repo, fake_llm, capsys):
    repo = make_repo({"app/__init__.py": ""}, {"app/perms.py": NESTED})
    fake_llm.replies += [IS_NESTING, TESTS.format(name="can_edit", call="can_edit"), DROPS_LOCKED, DROPS_LOCKED]

    result = review(capsys, repo)

    assert result["suggestions"] == [] and result["followup"] == []
    [rejected] = result["rejected"]
    assert (rejected["function"], rejected["path"]) == ("can_edit", "app/perms.py")
    assert rejected["reason"].startswith("rewrite fails characterization tests")
    assert "test_locked_cannot_edit" in rejected["reason"]
    assert models(fake_llm) == [LIGHTNING, SUPER, SUPER, ULTRA]


def test_failed_rewrite_gets_one_ultra_retry(make_repo, fake_llm, capsys):
    repo = make_repo({"app/__init__.py": ""}, {"app/perms.py": NESTED})
    fake_llm.replies += [IS_NESTING, TESTS.format(name="can_edit", call="can_edit"), DROPS_LOCKED, FLAT]

    result = review(capsys, repo)

    assert result["rejected"] == []
    [suggestion] = result["suggestions"]
    assert suggested_code(suggestion["body"]) == FLAT
    assert models(fake_llm) == [LIGHTNING, SUPER, SUPER, ULTRA]


def test_non_python_change_prints_empty_result_without_llm(make_repo, fake_llm, capsys):
    repo = make_repo({"app/perms.py": NESTED, "README.md": "# Demo\n"}, {"README.md": "# Demo\n\nSome *text*.\n"})

    assert review(capsys, repo) == {"suggestions": [], "followup": [], "rejected": []}
    assert fake_llm.calls == []


def two_nested_functions(make_repo, slopgate_toml):
    return make_repo(
        {"app/__init__.py": ""},
        {"app/perms.py": NESTED + "\n\n" + VIEW, ".slopgate.toml": "[sandbox]\n" + slopgate_toml},
    )


def test_repo_installs_once_per_review(make_repo, fake_llm, capsys, tmp_path_factory):
    installs = tmp_path_factory.mktemp("log") / "installs"
    repo = two_nested_functions(make_repo, f"setup = 'echo x >> {installs}'\n")
    fake_llm.replies += [
        IS_NESTING,
        IS_NESTING,
        TESTS.format(name="can_edit", call="can_edit"),
        FLAT,
        TESTS.format(name="can_view", call="can_view"),
        FLAT_VIEW,
    ]

    result = review(capsys, repo)

    assert len(result["suggestions"]) == 2
    assert installs.read_text().splitlines() == ["x"]


def test_broken_trial_does_not_affect_the_next(make_repo, fake_llm, capsys):
    repo = two_nested_functions(make_repo, "")
    crashes = "def can_edit(user_active, is_owner, locked, archived):\n    return undefined_name\n"
    fake_llm.replies += [
        IS_NESTING,
        IS_NESTING,
        TESTS.format(name="can_edit", call="can_edit"),
        crashes,
        crashes,
        TESTS.format(name="can_view", call="can_view"),
        FLAT_VIEW,
    ]

    result = review(capsys, repo)

    [rejected] = result["rejected"]
    assert rejected["function"] == "can_edit"
    assert rejected["reason"].startswith("rewrite fails characterization tests")
    [suggestion] = result["suggestions"]
    assert suggested_code(suggestion["body"]) == FLAT_VIEW


def test_failing_test_override_rejects_rewrite(make_repo, fake_llm, capsys):
    repo = make_repo({"app/__init__.py": ""}, {"app/perms.py": NESTED, ".slopgate.toml": "[sandbox]\ntest = 'exit 1'\n"})
    fake_llm.replies += [IS_NESTING, TESTS.format(name="can_edit", call="can_edit"), FLAT, FLAT]

    result = review(capsys, repo)

    assert result["suggestions"] == [] and result["followup"] == []
    [rejected] = result["rejected"]
    assert (rejected["function"], rejected["path"]) == ("can_edit", "app/perms.py")
    assert rejected["reason"].startswith("rewrite fails repo tests")


def test_passing_test_override_replaces_red_repo_suite(make_repo, fake_llm, capsys):
    repo = make_repo(
        {"app/__init__.py": "", "tests/test_suite.py": "def test_suite_is_red():\n    assert False\n"},
        {"app/perms.py": NESTED, ".slopgate.toml": "[sandbox]\ntest = 'true'\n"},
    )
    fake_llm.replies += [IS_NESTING, TESTS.format(name="can_edit", call="can_edit"), FLAT]

    result = review(capsys, repo)

    assert result["rejected"] == []
    [suggestion] = result["suggestions"]
    assert suggested_code(suggestion["body"]) == FLAT


def test_install_failure_is_one_notice_with_last_20_lines(make_repo, fake_llm, capsys):
    setup = "echo boom; for i in $(seq 1 30); do echo line$i; done; exit 1"
    repo = make_repo({"app/__init__.py": ""}, {"app/perms.py": NESTED, ".slopgate.toml": f"[sandbox]\nsetup = '{setup}'\n"})
    fake_llm.replies += [IS_NESTING]

    result = review(capsys, repo)

    tail = "\n".join(f"line{i}" for i in range(11, 31))
    assert result == {
        "suggestions": [],
        "followup": [],
        "rejected": [{"reason": f"could not build test environment\n{tail}"}],
    }
    assert [model for model, _ in fake_llm.calls] == [LIGHTNING]


KINDS_SOURCE = NESTED + '''

def total(prices):
    if prices is None:
        return 0
    if len(prices) == 0:
        return 0
    subtotal = 0
    for price in prices:
        if price is not None:
            if price is not None and price > 0:
                subtotal += price
    return subtotal


def parse_port(value):
    try:
        if value is None:
            return 8080
        if isinstance(value, bool):
            return 8080
        port = int(value)
        if port < 1:
            return 8080
        if port > 65535:
            return 8080
        return port
    except Exception:
        return 8080


def http_reason(code):
    if code == 200:
        return "OK"
    elif code == 201:
        return "Created"
    elif code == 204:
        return "No Content"
    elif code == 400:
        return "Bad Request"
    elif code == 404:
        return "Not Found"
    elif code == 500:
        return "Server Error"
    return "Unknown"


def clamp_all(values, low, high):
    # return empty list for None
    if values is None:
        return []
    # check the bounds
    if low > high:
        raise ValueError("low > high")
    # create the result list
    result = []
    # loop over the values
    for value in values:
        # check if value is too low
        if value < low:
            result.append(low)
        # check if value is too high
        elif value > high:
            result.append(high)
        else:
            result.append(value)
    # return the result
    return result


def describe(n):
    label = "n"
    return f"value {n}"
    print("done")
'''

KIND_CASES = [
    ("nesting", TESTS.format(name="can_edit", call="can_edit"), FLAT),
    (
        "redundant_check",
        "from app.perms import total\n\n\n"
        "def test_none():\n    assert total(None) == 0\n\n\n"
        "def test_empty():\n    assert total([]) == 0\n\n\n"
        "def test_mixed():\n    assert total([None, -1, 2, 3]) == 5\n",
        "def total(prices):\n    if prices is None:\n        return 0\n"
        "    return sum(price for price in prices if price is not None and price > 0)\n",
    ),
    (
        "swallowed_error",
        "from app.perms import parse_port\n\n\n"
        + "".join(
            f"def test_{name}():\n    assert parse_port({arg}) == {want}\n\n\n"
            for name, arg, want in [
                ("none", None, 8080),
                ("bool", True, 8080),
                ("low", '"0"', 8080),
                ("high", '"70000"', 8080),
                ("garbage", '"abc"', 8080),
                ("valid", '"443"', 443),
            ]
        ),
        "def parse_port(value):\n    if value is None or isinstance(value, bool):\n        return 8080\n"
        "    try:\n        port = int(value)\n    except (TypeError, ValueError):\n        return 8080\n"
        "    return port if 1 <= port <= 65535 else 8080\n",
    ),
    (
        "lookup_table",
        "from app.perms import http_reason\n\n\n"
        + "".join(
            f"def test_{code}():\n    assert http_reason({code}) == {reason!r}\n\n\n"
            for code, reason in [
                (200, "OK"),
                (201, "Created"),
                (204, "No Content"),
                (400, "Bad Request"),
                (404, "Not Found"),
                (500, "Server Error"),
                (999, "Unknown"),
            ]
        ),
        "def http_reason(code):\n    return {200: 'OK', 201: 'Created', 204: 'No Content', 400: 'Bad Request', "
        "404: 'Not Found', 500: 'Server Error'}.get(code, 'Unknown')\n",
    ),
    (
        "filler_comment",
        "import pytest\n\nfrom app.perms import clamp_all\n\n\n"
        "def test_none():\n    assert clamp_all(None, 0, 1) == []\n\n\n"
        "def test_bad_bounds():\n    with pytest.raises(ValueError):\n        clamp_all([1], 2, 1)\n\n\n"
        "def test_clamps():\n    assert clamp_all([0, 5, 10], 1, 9) == [1, 5, 9]\n",
        "def clamp_all(values, low, high):\n    if values is None:\n        return []\n"
        "    if low > high:\n        raise ValueError('low > high')\n    result = []\n"
        "    for value in values:\n        if value < low:\n            result.append(low)\n"
        "        elif value > high:\n            result.append(high)\n        else:\n            result.append(value)\n"
        "    return result\n",
    ),
    (
        "dead",
        "from app.perms import describe\n\n\ndef test_describe():\n    assert describe(3) == 'value 3'\n",
        "def describe(n):\n    return f'value {n}'\n",
    ),
]


def test_each_in_place_kind_gets_a_suggestion_naming_it(make_repo, fake_llm, capsys):
    repo = make_repo({"app/__init__.py": ""}, {"app/perms.py": KINDS_SOURCE})
    fake_llm.replies += [json.dumps({"kind": kind}) for kind, _, _ in KIND_CASES if kind != "dead"]
    fake_llm.replies += [reply for _, tests, rewrite in KIND_CASES for reply in (tests, rewrite)]

    result = review(capsys, repo)

    assert result["rejected"] == []
    assert len(result["suggestions"]) == 6
    for (kind, _, _), suggestion in zip(KIND_CASES, result["suggestions"]):
        assert f"Slopgate (`{kind}`)" in suggestion["body"]
    assert models(fake_llm).count(LIGHTNING) == 5


@pytest.fixture
def trials(monkeypatch):
    commands = []
    run = Local.run

    def spy(self, checkpoint, files, cmd):
        commands.append(cmd)
        return run(self, checkpoint, files, cmd)

    monkeypatch.setattr(Local, "run", spy)
    return commands


SIGNATURE = "def can_edit(user_active, is_owner, locked, archived):\n"


@pytest.mark.parametrize(
    ("rewrite", "rule"),
    [
        ("def can_edit(user_active, is_owner, locked):\n    return user_active and is_owner and not locked\n", "signature changed"),
        (SIGNATURE + "    class Box:\n        pass\n    return user_active and is_owner and not locked and not archived\n", "adds a class"),
        (SIGNATURE + "    def check():\n        return not archived\n    return user_active and is_owner and not locked and check()\n", "adds a function"),
        ("def can_edit(user_active, is_owner, locked, archived:\n    return True\n", "does not parse"),
    ],
)
def test_rule_breaking_rewrite_is_rejected_without_a_trial(make_repo, fake_llm, capsys, trials, rewrite, rule):
    repo = make_repo({"app/__init__.py": ""}, {"app/perms.py": NESTED})
    fake_llm.replies += [IS_NESTING, TESTS.format(name="can_edit", call="can_edit"), rewrite]

    result = review(capsys, repo)

    assert result["suggestions"] == []
    assert result["rejected"] == [{"function": "can_edit", "path": "app/perms.py", "reason": f"rule: {rule}"}]
    assert len(trials) == 2
    assert models(fake_llm) == [LIGHTNING, SUPER, SUPER]


def test_function_using_random_is_rejected_as_nondeterministic(make_repo, fake_llm, capsys):
    source = "import random\n\n\ndef roll(a, b, c, d, e, f):\n    return random.random() if a and b and c and d and e and f else 0\n"
    repo = make_repo({"app/__init__.py": ""}, {"app/dice.py": source})
    fake_llm.replies += [IS_NESTING]

    result = review(capsys, repo)

    assert result["suggestions"] == []
    [rejected] = result["rejected"]
    assert rejected["function"] == "roll"
    assert "nondeterministic" in rejected["reason"]
    assert models(fake_llm) == [LIGHTNING]


def test_tests_that_miss_a_branch_are_rejected_with_the_count(make_repo, fake_llm, capsys):
    repo = make_repo({"app/__init__.py": ""}, {"app/perms.py": NESTED})
    weak = TESTS.format(name="can_edit", call="can_edit").replace(
        "def test_locked_cannot_edit():\n    assert can_edit(True, True, True, False) is False\n", ""
    )
    fake_llm.replies += [IS_NESTING, weak]

    result = review(capsys, repo)

    assert result["suggestions"] == []
    assert result["rejected"] == [
        {"function": "can_edit", "path": "app/perms.py", "reason": "characterization tests miss branches: 1"}
    ]
    assert models(fake_llm) == [LIGHTNING, SUPER]


@pytest.mark.parametrize("reply", ['{"kind": "none"}', "not json", '{"kind": "wrapper"}', '{"type": "nesting"}', "[]"])
def test_classifier_none_or_garbage_drops_the_function_silently(make_repo, fake_llm, capsys, reply):
    repo = make_repo({"app/__init__.py": ""}, {"app/perms.py": NESTED})
    fake_llm.replies += [reply]

    assert review(capsys, repo) == {"suggestions": [], "followup": [], "rejected": []}
    assert models(fake_llm) == [LIGHTNING]


def test_tests_that_differ_across_two_runs_are_rejected(make_repo, fake_llm, capsys):
    repo = make_repo({"app/__init__.py": ""}, {"app/perms.py": NESTED})
    # hash("b") is odd under PYTHONHASHSEED=1 and even under PYTHONHASHSEED=2
    flaky = TESTS.format(name="can_edit", call="can_edit") + '\n\ndef test_hash_order():\n    assert hash("b") % 2 == 1\n'
    fake_llm.replies += [IS_NESTING, flaky]

    result = review(capsys, repo)

    assert models(fake_llm) == [LIGHTNING, SUPER]

    assert result["suggestions"] == []
    assert result["rejected"] == [
        {
            "function": "can_edit",
            "path": "app/perms.py",
            "reason": "nondeterministic: characterization tests differ across two runs",
        }
    ]


def test_unused_argument_is_not_dead_code(make_repo, fake_llm, capsys):
    repo = make_repo({"app/__init__.py": ""}, {"app/labels.py": 'def label(n, style):\n    return f"#{n}"\n'})

    assert review(capsys, repo) == {"suggestions": [], "followup": [], "rejected": []}
    assert fake_llm.calls == []


def test_tests_prompt_without_repo_callees_has_no_context_section(make_repo, fake_llm, capsys):
    repo = make_repo({"app/__init__.py": ""}, {"app/perms.py": NESTED})
    fake_llm.replies += [IS_NESTING, TESTS.format(name="can_edit", call="can_edit"), FLAT]

    review(capsys, repo)

    tests_prompt = fake_llm.calls[1][1]
    assert tests_prompt.rstrip().endswith(NESTED.rstrip())
    assert "Code it calls" not in tests_prompt


WRONG_TESTS = TESTS.format(name="can_edit", call="can_edit").replace(
    "assert can_edit(True, True, False, True) is False", "assert can_edit(True, True, False, True) is True"
)


def test_tests_that_fail_on_original_get_one_retry_with_the_failure(make_repo, fake_llm, capsys):
    repo = make_repo({"app/__init__.py": ""}, {"app/perms.py": NESTED})
    fake_llm.replies += [IS_NESTING, WRONG_TESTS, TESTS.format(name="can_edit", call="can_edit"), FLAT]

    result = review(capsys, repo)

    assert result["rejected"] == []
    [suggestion] = result["suggestions"]
    assert "5 characterization tests passed" in suggestion["body"]
    assert models(fake_llm) == [LIGHTNING, SUPER, SUPER, SUPER]
    retry_prompt = fake_llm.calls[2][1]
    assert WRONG_TESTS in retry_prompt
    assert "assert False is True" in retry_prompt


def test_tests_that_fail_on_original_twice_are_rejected(make_repo, fake_llm, capsys):
    repo = make_repo({"app/__init__.py": ""}, {"app/perms.py": NESTED})
    fake_llm.replies += [IS_NESTING, WRONG_TESTS, WRONG_TESTS]

    result = review(capsys, repo)

    [rejected] = result["rejected"]
    assert rejected["reason"].startswith("characterization tests fail on original")
    assert models(fake_llm) == [LIGHTNING, SUPER, SUPER]


EDIT_INPUTS = json.dumps(
    {
        "inputs": [
            "False, True, False, False",
            "True, False, False, False",
            "True, True, True, False",
            "True, True, False, True",
            "True, True, False, False",
        ]
    }
)


def test_proposed_inputs_are_recorded_on_the_original(make_repo, fake_llm, capsys):
    repo = make_repo({"app/__init__.py": ""}, {"app/perms.py": NESTED})
    fake_llm.replies += [IS_NESTING, EDIT_INPUTS, FLAT]

    result = review(capsys, repo)

    assert result["rejected"] == []
    [suggestion] = result["suggestions"]
    assert "5 characterization tests passed" in suggestion["body"]
    assert models(fake_llm) == [LIGHTNING, SUPER, SUPER]


@pytest.mark.parametrize(
    ("rewrite", "failing"),
    [
        (DROPS_LOCKED, "capture(True, True, True, False)"),
        (SIGNATURE + "    return int(user_active and is_owner and not locked and not archived)\n", "capture(True, True, False, False)"),
    ],
    ids=["value", "type"],
)
def test_recorded_calls_reject_a_rewrite_that_changes_the_result(make_repo, fake_llm, capsys, rewrite, failing):
    repo = make_repo({"app/__init__.py": ""}, {"app/perms.py": NESTED})
    fake_llm.replies += [IS_NESTING, EDIT_INPUTS, rewrite, rewrite]

    [rejected] = review(capsys, repo)["rejected"]

    assert rejected["reason"].startswith("rewrite fails characterization tests")
    assert failing in rejected["reason"]


GRADE = '''\
def grade(score):
    if score is not None:
        if score >= 0:
            if score >= 50:
                return "pass"
            return "fail"
    raise ValueError(f"bad score: {score}")
'''

GRADE_FLAT = '''\
def grade(score):
    if score is None or score < 0:
        raise {error}(f"bad {noun}: {{score}}")
    return "pass" if score >= 50 else "fail"
'''


@pytest.mark.parametrize(
    ("error", "noun", "accepted"),
    [("ValueError", "score", True), ("ValueError", "value", False), ("TypeError", "score", False)],
    ids=["same", "message", "type"],
)
def test_recorded_exceptions_check_type_and_message(make_repo, fake_llm, capsys, error, noun, accepted):
    repo = make_repo({"app/__init__.py": ""}, {"app/grades.py": GRADE})
    rewrite = GRADE_FLAT.format(error=error, noun=noun)
    calls = json.dumps({"inputs": ["70", "10", "-1", "None"]})
    fake_llm.replies += [IS_NESTING, calls, rewrite, rewrite]

    result = review(capsys, repo)

    assert len(result["suggestions"]) == accepted
    assert len(result["rejected"]) == (not accepted)


def test_recorder_that_ends_without_results_is_rejected(make_repo, fake_llm, capsys):
    repo = make_repo({"app/__init__.py": ""}, {"app/perms.py": NESTED})
    fake_llm.replies += [IS_NESTING, json.dumps({"inputs": ["1,,"]})]

    [rejected] = review(capsys, repo)["rejected"]

    assert rejected["reason"].startswith("could not record calls")
    assert models(fake_llm) == [LIGHTNING, SUPER]


ADD_TAG = """\
def add_tag(tags, tag):
    if tag:
        if tag not in tags:
            if len(tags) < 3:
                tags.append(tag)
                return True
    return False
"""

ADD_TAG_FLAT = """\
def add_tag(tags, tag):
    if not tag or tag in tags or len(tags) >= 3:
        return False
    tags.append(tag)
    return True
"""


@pytest.mark.parametrize(
    ("rewrite", "accepted"),
    [(ADD_TAG_FLAT, True), (ADD_TAG_FLAT.replace("    tags.append(tag)\n", ""), False)],
    ids=["keeps-append", "drops-append"],
)
def test_recorded_inputs_check_the_arguments_after_the_call(make_repo, fake_llm, capsys, rewrite, accepted):
    repo = make_repo({"app/__init__.py": ""}, {"app/tags.py": ADD_TAG})
    inputs = json.dumps({"inputs": ['["a"], ""', '["a"], "a"', '["a", "b", "c"], "d"', '["a"], "b"']})
    fake_llm.replies += [IS_NESTING, inputs, rewrite, rewrite]

    result = review(capsys, repo)

    assert len(result["suggestions"]) == accepted
    assert len(result["rejected"]) == (not accepted)


def test_methods_are_not_offered_the_inputs_form(make_repo, fake_llm, capsys):
    method = "class Policy:\n" + textwrap.indent("@staticmethod\n" + NESTED, "    ")
    repo = make_repo({"app/__init__.py": ""}, {"app/perms.py": NESTED + "\n\n" + method})
    fake_llm.replies += [IS_NESTING, IS_NESTING, TESTS.format(name="can_edit", call="can_edit"), FLAT]
    fake_llm.replies += [TESTS.format(name="Policy", call="Policy.can_edit"), "@staticmethod\n" + FLAT]

    review(capsys, repo)

    function_prompt, method_prompt = [prompt for _, prompt in fake_llm.calls if prompt.startswith("Write characterization")]
    assert '{"inputs":' in function_prompt
    assert '{"inputs":' not in method_prompt


LOG_VALUE = '''\
def log_value(log, value):
    log.append(value)
    if value is not None:
        if value >= 0:
            if value < 10:
                return value
    raise ValueError("out of range")
'''

CHECKS_FIRST = '''\
def log_value(log, value):
    if value is None or not 0 <= value < 10:
        raise ValueError("out of range")
    log.append(value)
    return value
'''


def test_recorded_inputs_check_the_arguments_after_an_exception(make_repo, fake_llm, capsys):
    repo = make_repo({"app/__init__.py": ""}, {"app/log.py": LOG_VALUE})
    fake_llm.replies += [IS_NESTING, json.dumps({"inputs": ["[], 5", "[], 50", "[], -1", "[], None"]}), CHECKS_FIRST, CHECKS_FIRST]

    [rejected] = review(capsys, repo)["rejected"]

    assert rejected["reason"].startswith("rewrite fails characterization tests")
    assert "test_call_1" in rejected["reason"]
