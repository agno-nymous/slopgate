import ast
import json
import re
import shlex
import subprocess
import sys
import textwrap
import threading
import time
from types import SimpleNamespace

import pytest
from contree_sdk.sdk.exceptions import NotFoundError

from slopgate import kinds, llm, sandbox
from slopgate import review as gate
from slopgate.cli import main
from slopgate.config import AGENT_SECONDS, AGENT_STEPS, AGENT_TOKENS, SUPER, ULTRA
from slopgate.functions import dedent, is_test_file, parse, pytest_patterns, structure_hash
from slopgate.kinds import KINDS, classify, flattenable, has_dead_code, leftover, problems, repeated_checks
from slopgate.review import COVERAGE, EXECUTE, NO_ENVIRONMENT, REJECTED, characterize, same_code, strip_fence
from slopgate.sandbox import Contree, ContreeSession, Local, LocalSession

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
    return bool(user_active and is_owner and not locked and not archived)
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

VIEW = NESTED.replace("can_edit", "can_view")
FLAT_VIEW = FLAT.replace("can_edit", "can_view")
ALL_SET = "def all_set(a, b, c, d, e, f): unused = a; return (a and b) and (c and d) and (e and f)\n"
SIGNATURE = "def can_edit(user_active, is_owner, locked, archived):\n"
DROPS_LOCKED = "def can_edit(user_active, is_owner, locked, archived):\n    return bool(user_active and is_owner and not archived)\n"


def review(capsys, repo, sandbox="local"):
    assert main(["review", "--repo", repo, "--base", "HEAD~1", "--head", "HEAD", "--dry-run", "--sandbox", sandbox]) is None
    out, err = capsys.readouterr()
    assert err == ""
    return json.loads(out)


def fenced(code):
    return "```python\n" + code + "```"


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
        "```python\n" + TESTS.format(name="can_edit", call="can_edit") + "```",
        "Here is the rewrite:\n```python\n" + FLAT + "```",
    ]

    result = review(capsys, repo)

    assert result["followup"] == [] and result["rejected"] == []
    assert models(fake_llm) == [SUPER, SUPER, SUPER]
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
        fenced(TESTS.format(name="Policy", call="Policy.can_edit")),
        fenced("@staticmethod\n" + FLAT),
    ]

    [suggestion] = review(capsys, repo)["suggestions"]

    assert "Policy.can_edit" in suggestion["body"]
    assert suggestion["start_line"] == 4
    assert suggestion["line"] == 18
    code = suggested_code(suggestion["body"])
    assert code == textwrap.indent("@staticmethod\n" + FLAT, "    ")
    lines = method.splitlines(keepends=True)
    ast.parse("".join(lines[: suggestion["start_line"] - 1]) + code + "".join(lines[suggestion["line"] :]))


def test_one_line_function_has_no_start_line(make_repo, fake_llm, capsys):
    repo = make_repo({"app/__init__.py": ""}, {"app/flags.py": ALL_SET})
    fake_llm.replies += [
        fenced(
            "from app.flags import all_set\n\n\n"
            + "".join(
                f"def test_false_at_{i}():\n    args = [True] * 6\n    args[{i}] = False\n    assert all_set(*args) is False\n\n\n"
                for i in range(6)
            )
            + "def test_all_true():\n    assert all_set(*[True] * 6) is True\n"
        ),
        fenced("def all_set(a, b, c, d, e, f): return all((a, b, c, d, e, f))\n"),
    ]

    [suggestion] = review(capsys, repo)["suggestions"]

    assert suggestion["line"] == 1
    assert "start_line" not in suggestion and "start_side" not in suggestion
    assert "complexity 6 -> 1" in suggestion["body"]


REJECTED_NOTE = {
    "path": "app/perms.py",
    "function": "can_edit",
    "kinds": ["nesting"],
    "line": 14,
    "body": f"**nesting** (not rewritten): `can_edit`: {KINDS['nesting']} Slopgate could not prove a rewrite of this function, "
    "so it changed nothing.",
}


def test_rewrite_that_changes_behavior_is_rejected(make_repo, fake_llm, capsys):
    repo = make_repo({"app/__init__.py": ""}, {"app/perms.py": NESTED})
    fake_llm.replies += [fenced(TESTS.format(name="can_edit", call="can_edit")), fenced(DROPS_LOCKED), fenced(DROPS_LOCKED)]

    result = review(capsys, repo)

    assert result["suggestions"] == [] and result["followup"] == []
    [rejected] = result["rejected"]
    assert (rejected["function"], rejected["path"]) == ("can_edit", "app/perms.py")
    assert rejected["reason"].startswith("rewrite fails characterization tests")
    assert "test_locked_cannot_edit" in rejected["reason"]
    assert models(fake_llm) == [SUPER, SUPER, SUPER, ULTRA]
    assert result["notes"] == [REJECTED_NOTE]


def test_failed_rewrite_gets_one_ultra_retry(make_repo, fake_llm, capsys):
    repo = make_repo({"app/__init__.py": ""}, {"app/perms.py": NESTED})
    fake_llm.replies += [fenced(TESTS.format(name="can_edit", call="can_edit")), fenced(DROPS_LOCKED), fenced(FLAT)]

    result = review(capsys, repo)

    assert result["rejected"] == []
    [suggestion] = result["suggestions"]
    assert suggested_code(suggestion["body"]) == FLAT
    assert models(fake_llm) == [SUPER, SUPER, SUPER, ULTRA]


def test_non_python_change_prints_empty_result_without_llm(make_repo, fake_llm, capsys):
    repo = make_repo({"app/perms.py": NESTED, "README.md": "# Demo\n"}, {"README.md": "# Demo\n\nSome *text*.\n"})

    assert review(capsys, repo) == {"suggestions": [], "followup": [], "rejected": [], "notes": []}
    assert fake_llm.calls == []


CHECK_FILES = {"pyproject.toml": '[tool.pytest.ini_options]\npython_files = ["check_*.py"]\n'}
HELPER_FILES = {"pytest.ini": "[pytest]\npython_files = check_*.py helpers.py\n"}


@pytest.mark.parametrize(
    ("config", "path", "expected"),
    [
        ({}, "test/test_api.py", True),
        ({}, "checks/api_test.py", True),
        ({}, "src/conftest.py", True),
        ({}, "tests/helpers.py", False),
        (CHECK_FILES, "check_api.py", True),
        (CHECK_FILES, "test_api.py", False),
        (CHECK_FILES, "src/conftest.py", True),
        (HELPER_FILES, "tests/helpers.py", True),
        (HELPER_FILES, "test_api.py", False),
    ],
)
def test_test_files_are_found_by_file_name_and_pytest_config(config, path, expected):
    assert is_test_file(path, pytest_patterns(config.get)) is expected


def test_slop_in_a_test_file_gets_a_note_and_no_proof(make_repo, fake_llm, capsys):
    repo = make_repo({"app/__init__.py": ""}, {"tests/conftest.py": "import pytest\n\n\n" + NESTED + "\n\n" + SIMPLE})

    result = review(capsys, repo)

    assert fake_llm.calls == []
    body = f"**nesting** (not rewritten): `can_edit`: {KINDS['nesting']} Slopgate does not change test files."
    assert result == {
        "suggestions": [],
        "followup": [],
        "rejected": [],
        "notes": [{"path": "tests/conftest.py", "function": "can_edit", "kinds": ["nesting"], "line": 17, "body": body}],
    }


def two_nested_functions(make_repo, slopgate_toml):
    return make_repo(
        {"app/__init__.py": ""},
        {"app/perms.py": NESTED + "\n\n" + VIEW, ".slopgate.toml": "[sandbox]\n" + slopgate_toml},
    )


def test_repo_installs_once_per_review(make_repo, fake_llm, capsys, tmp_path_factory):
    installs = tmp_path_factory.mktemp("log") / "installs"
    repo = two_nested_functions(make_repo, f"setup = 'echo x >> {installs}'\n")
    fake_llm.replies += [
        fenced(TESTS.format(name="can_edit", call="can_edit")),
        fenced(FLAT),
        fenced(TESTS.format(name="can_view", call="can_view")),
        fenced(FLAT_VIEW),
    ]

    result = review(capsys, repo)

    assert len(result["suggestions"]) == 2
    assert installs.read_text().splitlines() == ["x"]


def test_broken_trial_does_not_affect_the_next(make_repo, fake_llm, capsys):
    repo = two_nested_functions(make_repo, "")
    crashes = "def can_edit(user_active, is_owner, locked, archived):\n    return bool(undefined_name)\n"
    fake_llm.replies += [
        fenced(TESTS.format(name="can_edit", call="can_edit")),
        fenced(crashes),
        fenced(crashes),
        fenced(TESTS.format(name="can_view", call="can_view")),
        fenced(FLAT_VIEW),
    ]

    result = review(capsys, repo)

    [rejected] = result["rejected"]
    assert rejected["function"] == "can_edit"
    assert rejected["reason"].startswith("rewrite fails characterization tests")
    [suggestion] = result["suggestions"]
    assert suggested_code(suggestion["body"]) == FLAT_VIEW


def test_failing_test_override_rejects_rewrite(make_repo, fake_llm, capsys):
    repo = make_repo({"app/__init__.py": ""}, {"app/perms.py": NESTED, ".slopgate.toml": "[sandbox]\ntest = 'exit 1'\n"})
    fake_llm.replies += [fenced(TESTS.format(name="can_edit", call="can_edit")), fenced(FLAT)]

    result = review(capsys, repo)

    assert result["suggestions"] == [] and result["followup"] == []
    [rejected] = result["rejected"]
    assert (rejected["function"], rejected["path"]) == ("can_edit", "app/perms.py")
    assert rejected["reason"].startswith("rewrite fails repo tests")
    assert models(fake_llm) == [SUPER, SUPER, SUPER]


def test_passing_test_override_replaces_red_repo_suite(make_repo, fake_llm, capsys):
    repo = make_repo(
        {"app/__init__.py": "", "tests/test_suite.py": "def test_suite_is_red():\n    assert False\n"},
        {"app/perms.py": NESTED, ".slopgate.toml": "[sandbox]\ntest = 'true'\n"},
    )
    fake_llm.replies += [fenced(TESTS.format(name="can_edit", call="can_edit")), fenced(FLAT)]

    result = review(capsys, repo)

    assert result["rejected"] == []
    [suggestion] = result["suggestions"]
    assert suggested_code(suggestion["body"]) == FLAT


def test_install_failure_is_one_notice_with_last_20_lines(make_repo, fake_llm, capsys):
    setup = "echo boom; for i in $(seq 1 30); do echo line$i; done; exit 1"
    repo = make_repo({"app/__init__.py": ""}, {"app/perms.py": NESTED, ".slopgate.toml": f"[sandbox]\nsetup = '{setup}'\n"})

    result = review(capsys, repo)

    tail = "\n".join(f"line{i}" for i in range(11, 31))
    assert result == {
        "suggestions": [],
        "followup": [],
        "rejected": [{"reason": f"could not build test environment\n{tail}"}],
        "notes": [{**REJECTED_NOTE, "body": REJECTED_NOTE["body"].replace(REJECTED, NO_ENVIRONMENT)}],
    }
    assert NO_ENVIRONMENT in result["notes"][0]["body"]
    assert fake_llm.calls == []


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
        "nesting",
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
        "dead",
        "from app.perms import describe\n\n\ndef test_describe():\n    assert describe(3) == 'value 3'\n",
        "def describe(n):\n    return f'value {n}'\n",
    ),
]


def test_each_in_place_kind_gets_a_suggestion_naming_it(make_repo, fake_llm, capsys):
    repo = make_repo({"app/__init__.py": ""}, {"app/perms.py": KINDS_SOURCE})
    fake_llm.replies += [fenced(reply) for _, tests, rewrite in KIND_CASES for reply in (tests, rewrite)]

    result = review(capsys, repo)

    assert result["rejected"] == []
    named = [re.match(r"Slopgate \((.*?)\) rewrite", suggestion["body"])[1] for suggestion in result["suggestions"]]
    assert named == ["`nesting`", "`nesting`", "`swallowed_error`", "`lookup_table`", "`dead`"]
    assert models(fake_llm) == [SUPER] * 15


REPEATED = SIGNATURE + """\
    if not user_active:
        return False
    if user_active:
        if is_owner:
            if not locked:
                return not archived
    return False
"""


def test_nesting_and_redundant_check_give_one_numbered_list_with_the_repeated_line():
    [function] = parse("app/perms.py", REPEATED)

    found = classify(function, REPEATED)

    assert found == {"nesting": [], "redundant_check": ["if user_active:"]}
    assert problems(found) == f"1. {KINDS['nesting']}\n2. {KINDS['redundant_check']} These lines:\n   if user_active:"


FIRST = "def first(items):\n    if not items:\n        return None\n    if not items:\n        return 1\n    return items[0]\n"


def test_rewrite_leaves_the_slop_only_while_a_check_still_repeats():
    [function] = parse("app/first.py", FIRST)
    found = classify(function, FIRST)
    guard_only = "def first(items):\n    if not items:\n        return None\n    return items[0]\n"
    other_repeat = "def first(items):\n    if not items:\n        return None\n    if items:\n        return items[0]\n    return 1\n"

    assert found == {"redundant_check": ["if not items:"]}
    assert leftover(found, function, guard_only, guard_only) is None
    assert leftover(found, function, other_repeat, other_repeat) == "rewrite leaves the slop: redundant_check"


@pytest.mark.parametrize(
    ("handler", "kinds"),
    [("except Exception:\n        return None", [["swallowed_error"]]), ("except Exception as error:\n        return str(error)", [])],
    ids=["error-dropped", "error-used"],
)
def test_broad_except_is_swallowed_only_when_the_handler_drops_the_error(make_repo, fake_llm, capsys, handler, kinds):
    source = f"def parse_int(value):\n    try:\n        return int(value)\n    {handler}\n"
    repo = make_repo({"app/__init__.py": ""}, {"tests/conftest.py": source})

    result = review(capsys, repo)

    assert [n["kinds"] for n in result["notes"]] == kinds
    assert fake_llm.calls == []


@pytest.mark.parametrize("source", [FLAT, 'def label(n):\n    return f"#{n}"\n'], ids=["one-condition", "hash-in-string"])
def test_function_with_no_kind_makes_no_model_call(make_repo, fake_llm, capsys, source):
    repo = make_repo({"app/__init__.py": ""}, {"app/perms.py": source})

    assert review(capsys, repo) == {"suggestions": [], "followup": [], "rejected": [], "notes": []}
    assert fake_llm.calls == []


STILL_NESTED = SIGNATURE + "    if user_active:\n        if is_owner:\n            if not locked:\n                return not archived\n    return False\n"
PARSE_INT = "def parse_int(value):\n    try:\n        return int(value)\n    except Exception:\n        return None\n"
PARSE_INT_TESTS = (
    "from app.perms import parse_int\n\n\ndef test_number():\n    assert parse_int('3') == 3\n\n\n"
    "def test_text():\n    assert parse_int('x') is None\n"
)


@pytest.mark.parametrize(
    ("source", "checks", "tests", "rewrite", "kind"),
    [
        (NESTED, [], TESTS.format(name="can_edit", call="can_edit"), STILL_NESTED, "nesting"),
        (PARSE_INT, [], PARSE_INT_TESTS, PARSE_INT.replace("except Exception", "except BaseException"), "swallowed_error"),
    ],
    ids=["detector", "ruff"],
)
def test_rewrite_that_leaves_the_slop_is_rejected_after_one_retry(make_repo, fake_llm, capsys, trials, source, checks, tests, rewrite, kind):
    repo = make_repo({"app/__init__.py": ""}, {"app/perms.py": source})
    fake_llm.replies += [*checks, fenced(tests), fenced(rewrite), fenced(rewrite)]

    result = review(capsys, repo)

    assert result["suggestions"] == []
    [rejected] = result["rejected"]
    assert rejected["reason"] == f"rewrite leaves the slop: {kind}"
    assert models(fake_llm)[-3:] == [SUPER, SUPER, ULTRA]
    assert f"Failure:\n\nrewrite leaves the slop: {kind}" in fake_llm.calls[-1][1]
    assert len(trials) == 2


@pytest.fixture
def trials(monkeypatch):
    commands = []
    run = Local.run

    def spy(self, checkpoint, files, cmd):
        commands.append(cmd)
        return run(self, checkpoint, files, cmd)

    monkeypatch.setattr(Local, "run", spy)
    return commands


@pytest.mark.parametrize(
    ("rewrite", "rule"),
    [
        ("def can_edit(user_active, is_owner, locked):\n    return user_active and is_owner and not locked\n", "signature changed"),
        (SIGNATURE + "    class Box:\n        pass\n    return user_active and is_owner and not locked and not archived\n", "adds a class"),
        (SIGNATURE + "    def check():\n        return not archived\n    return user_active and is_owner and not locked and check()\n", "adds a function"),
        ("def can_edit(user_active, is_owner, locked, archived:\n    return True\n", "does not parse"),
        (
            SIGNATURE + "    return user_active and is_owner and not locked and not archived\n",
            "returns a non-bool value where the original returns only bools",
        ),
        (SIGNATURE + "    return False if locked else user_active\n", "returns a non-bool value where the original returns only bools"),
        (SIGNATURE + "    return min(user_active, is_owner)\n", "returns a non-bool value where the original returns only bools"),
    ],
)
def test_rule_breaking_rewrite_is_rejected_without_a_trial(make_repo, fake_llm, capsys, trials, rewrite, rule):
    repo = make_repo({"app/__init__.py": ""}, {"app/perms.py": NESTED})
    fake_llm.replies += [fenced(TESTS.format(name="can_edit", call="can_edit")), fenced(rewrite)]

    result = review(capsys, repo)

    assert result["suggestions"] == []
    assert result["rejected"] == [{"function": "can_edit", "path": "app/perms.py", "kinds": ["nesting"], "reason": f"rule: {rule}"}]
    assert len(trials) == 2
    assert models(fake_llm) == [SUPER, SUPER, SUPER]


def test_function_using_random_is_rejected_as_nondeterministic(make_repo, fake_llm, capsys):
    line = "return random.random() if a and b and c and d and e and f else 0"
    source = f"import random\n\n\ndef roll(a, b, c, d, e, f):\n    unused = a\n    {line}\n"
    repo = make_repo({"app/__init__.py": ""}, {"app/dice.py": source})

    result = review(capsys, repo)

    assert result["suggestions"] == []
    [rejected] = result["rejected"]
    assert rejected["function"] == "roll"
    assert "nondeterministic" in rejected["reason"]
    assert fake_llm.calls == []


def test_review_survives_a_sandbox_that_cuts_output_at_65535_characters(make_repo, fake_llm, capsys, monkeypatch):
    run = Local.run

    def cut(self, checkpoint, files, cmd):
        code, output = run(self, checkpoint, files, cmd)
        return code, output[:65535]

    monkeypatch.setattr(Local, "run", cut)
    big = "".join(f"VALUE_{i} = {i}\n" for i in range(6000))
    repo = make_repo(
        {"app/__init__.py": "", "app/big.py": big},
        {"app/perms.py": "from app import big\n\n\n" + NESTED},
    )
    fake_llm.replies += [fenced(TESTS.format(name="can_edit", call="can_edit")), fenced(FLAT)]

    result = review(capsys, repo)

    assert result["rejected"] == []
    assert len(result["suggestions"]) == 1


def test_tests_that_miss_a_branch_are_rejected_with_the_count(make_repo, fake_llm, capsys):
    repo = make_repo({"app/__init__.py": ""}, {"app/perms.py": NESTED})
    weak = fenced(TESTS.format(name="can_edit", call="can_edit")).replace(
        "def test_locked_cannot_edit():\n    assert can_edit(True, True, True, False) is False\n", ""
    )
    fake_llm.replies += [weak]

    result = review(capsys, repo)

    assert result["suggestions"] == []
    assert result["rejected"] == [
        {"function": "can_edit", "path": "app/perms.py", "kinds": ["nesting"], "reason": "characterization tests miss branches: 1"}
    ]
    assert models(fake_llm) == [SUPER, SUPER]


def test_ruff_failure_rejects_the_function_and_the_review_goes_on(make_repo, fake_llm, monkeypatch, capsys):
    repo = make_repo({"app/__init__.py": ""}, {"app/broken.py": "def one():\n    return 1\n", "app/perms.py": NESTED})
    fake_llm.replies += [fenced(TESTS.format(name="can_edit", call="can_edit")), fenced(FLAT)]
    ruff = kinds.ruff

    def broken_ruff(path, text):
        if path == "app/broken.py":
            raise RuntimeError("ruff failed on app/broken.py")
        return ruff(path, text)

    monkeypatch.setattr(kinds, "ruff", broken_ruff)

    result = review(capsys, repo)

    assert result["rejected"] == [
        {"function": "one", "path": "app/broken.py", "kinds": [], "reason": "internal error: RuntimeError('ruff failed on app/broken.py')"}
    ]
    assert result["notes"] == []
    [suggestion] = result["suggestions"]
    assert suggestion["path"] == "app/perms.py"


def test_tests_that_differ_across_two_runs_are_rejected(make_repo, fake_llm, capsys):
    repo = make_repo({"app/__init__.py": ""}, {"app/perms.py": NESTED})
    # hash("b") is odd under PYTHONHASHSEED=1 and even under PYTHONHASHSEED=2
    flaky = fenced(TESTS.format(name="can_edit", call="can_edit") + '\n\ndef test_hash_order():\n    assert hash("b") % 2 == 1\n')
    fake_llm.replies += [flaky]

    result = review(capsys, repo)

    assert models(fake_llm) == [SUPER, SUPER]
    assert result["suggestions"] == []
    assert result["rejected"] == [
        {
            "function": "can_edit",
            "path": "app/perms.py",
            "kinds": ["nesting"],
            "reason": "nondeterministic: characterization tests differ across two runs",
        }
    ]


def test_unused_argument_is_not_dead_code(make_repo, fake_llm, capsys):
    repo = make_repo({"app/__init__.py": ""}, {"app/labels.py": 'def label(n, style):\n    return f"#{n}"\n'})

    assert review(capsys, repo) == {"suggestions": [], "followup": [], "rejected": [], "notes": []}
    assert fake_llm.calls == []


@pytest.mark.parametrize(
    "source, expected",
    [
        ("def encoder():\n    return lambda texts, unused: texts\n", False),
        ("def outer():\n    def inner(a, unused):\n        return a\n    return inner\n", False),
        ("def setup():\n    x = 1\n    return 2\n", True),
        ("def stop():\n    return 1\n    print('done')\n", True),
    ],
)
def test_dead_code_ignores_nested_parameters_only(source, expected):
    (function,) = parse("app/mod.py", source)

    assert has_dead_code(function, source) is expected


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        (
            'def isatty(file):\n    if hasattr(file, "isatty"):\n        return file.isatty()\n    if not hasattr(file, "isatty"):\n        return False\n    return True\n',
            ['if not hasattr(file, "isatty"):'],
        ),
        ("def intersection(a, b, x):\n    if a <= b:\n        return x\n    if a > b:\n        return None\n    return x\n", ["if a > b:"]),
        ("def sign(x):\n    if x is None:\n        return 0\n    elif x is not None:\n        return 1\n    return 2\n", ["elif x is not None:"]),
        ("def f(x, seen):\n    if x in seen:\n        y = x\n        if x in seen:\n            return y\n    return 0\n", ["if x in seen:"]),
        ("def f(x):\n    if x > 0:\n        return 1\n    elif x > 0:\n        return 2\n    return 0\n", ["elif x > 0:"]),
        ("def f(x):\n    if x is None:\n        return 0\n    if x is not None:\n        return 1\n    return 2\n", ["if x is not None:"]),
        ("def f(x, items):\n    if not x:\n        return 0\n    ys = [x for x in items]\n    if x:\n        return ys\n    return 1\n", ["if x:"]),
        ("def f(x):\n    if x is None:\n        return 0\n    x = load()\n    if x is None:\n        return 1\n    return x\n", []),
        ("def f(x):\n    if x is None:\n        log(x)\n    if x is None:\n        return 1\n    return x\n", []),
        ("def f(x, items):\n    if x is None:\n        return 0\n    for item in items:\n        if x is None:\n            return 1\n        x = item\n    return x\n", []),
        ("def f(x):\n    if x is None:\n        return 0\n\n    def inner(x):\n        if x is None:\n            return 1\n        return x\n\n    return inner\n", []),
        ("def make(path):\n    if not path.exists():\n        try:\n            path.mkdir()\n        except OSError:\n            if not path.exists():\n                raise\n    return path\n", []),
    ],
    ids=[
        "astropy-isatty",
        "sympy-intersection",
        "elif-negates-if",
        "if-inside-same-if",
        "elif-repeats-if",
        "not-none-after-none-guard",
        "comprehension-name",
        "reassigned",
        "guard-does-not-exit",
        "loop-body",
        "nested-def",
        "race-recheck-in-handler",
    ],
)
def test_repeated_checks_find_a_condition_an_earlier_check_decides(source, expected):
    assert repeated_checks(source) == expected


@pytest.mark.parametrize(
    "source",
    [
        "def f(items):\n    if not items:\n        return None\n    items.clear()\n    if not items:\n        return 1\n",
        "def f(self):\n    if self.closed:\n        return\n    self.close()\n    if self.closed:\n        return 1\n",
        "def f():\n    if CACHE is None:\n        return\n    reset()\n    if CACHE is None:\n        return 1\n",
        "def f(x):\n    def reset():\n        nonlocal x\n        x = None\n\n    if x is None:\n        return\n    reset()\n    if x is None:\n        return 1\n",
        "def f(it):\n    if next(it) is None:\n        return\n    if next(it) is None:\n        return 1\n",
        "def f(self, v):\n    if self.a.b is None:\n        return\n    self.a.b = v\n    if self.a.b is None:\n        return 1\n",
        "def f(d, k, v):\n    if d[k] is None:\n        return\n    d[k] = v\n    if d[k] is None:\n        return 1\n",
        "def f(d, k):\n    if d[k] > 0:\n        return\n    d[k] += 5\n    if d[k] > 0:\n        return 1\n",
        'def f(self):\n    if not hasattr(self, "x"):\n        return\n    del self.x\n    if not hasattr(self, "x"):\n        return 1\n',
        "def f(conn, other):\n    if conn is None:\n        return\n    try:\n        conn = other\n    except OSError:\n        return\n    else:\n        if conn is None:\n            return 1\n",
        "def f(x, other):\n    if x is None:\n        return\n    try:\n        x = other\n    finally:\n        if x is None:\n            x = 0\n",
        "def f(lock, ctx):\n    if lock is None:\n        return\n    with ctx as lock:\n        if lock is None:\n            return 1\n",
        "def f(xs, y):\n    if y is None:\n        return\n    _ = [x for x in xs if (y := x)]\n    if y is None:\n        return 1\n",
        "def f(xs, x, other):\n    for _ in xs:\n        if x is None:\n            break\n        x = other\n        if x is None:\n            return 1\n",
        "def f(val, s):\n    if val is None:\n        return\n    match s:\n        case [val]:\n            pass\n    if val is None:\n        return 1\n",
        "def f(os):\n    if os is None:\n        return\n    import os\n    if os is None:\n        return 1\n",
        "def f(e, z):\n    if e is None:\n        return\n    try:\n        y = 1 / z\n    except ZeroDivisionError as e:\n        y = e\n    if e is None:\n        return y\n",
    ],
    ids=[
        "method-call-mutates-argument",
        "method-call-mutates-self",
        "call-changes-global",
        "call-changes-nonlocal",
        "impure-test",
        "nested-attribute-store",
        "subscript-store",
        "subscript-augassign",
        "del-attribute",
        "try-else-after-store",
        "finally-after-store",
        "with-as-rebinds",
        "walrus-in-comprehension-if",
        "loop-break-guard-then-store",
        "match-capture",
        "import-rebinds",
        "except-as-rebinds",
    ],
)
def test_repeated_checks_drop_a_fact_that_may_no_longer_hold(source):
    assert repeated_checks(source) == []


@pytest.mark.parametrize(
    "source",
    [
        "def f(x, items):\n    if x:\n        return 0\n    else:\n        for item in items:\n            if item:\n                print(item)\n",
        "def f(items):\n    for item in items:\n        if item:\n            with item:\n                if item.ok:\n                    print(item)\n",
        "def f(a, b, items):\n    for item in items:\n        if a:\n            if b:\n                print(item)\n    return items\n",
        "def f(a, items):\n    for item in items:\n        if a:\n            with a:\n                print(item)\n        else:\n            pass\n    return items\n",
    ],
    ids=["S1-else-after-exit", "S2-last-if-in-loop", "S3-if-holds-only-if", "S4-else-pass"],
)
def test_deep_if_that_guard_clauses_can_flatten_is_nesting(source):
    (function,) = parse("app/mod.py", source)

    assert flattenable(source)
    assert classify(function, source) == {"nesting": []}


@pytest.mark.parametrize(
    "source",
    [
        "def check(cursor, tables):\n    with cursor:\n        for table in tables:\n            for row in table.rows:\n                if bad(row):\n                    report(row)\n",
        "def check(cursor, tables, errors):\n    with cursor:\n        for table in tables:\n            for row in table.rows:\n                check(row)\n    if errors:\n        for e in errors:\n            log(e)\n",
        "def f(x):\n    try:\n        for a in x:\n            with a:\n                g()\n    except ValueError:\n        if x:\n            return 1\n        else:\n            pass\n",
    ],
    ids=["loops-do-real-work", "trailing-if-off-the-deep-chain", "handler-if-off-the-deep-chain"],
)
def test_deep_loops_that_do_real_work_are_not_nesting(source):
    (function,) = parse("app/mod.py", source)

    assert not flattenable(source)
    assert classify(function, source) == {}


PROBER = """class Prober:
    def get_name(self):
        if not self.best:
            self.get_confidence()
#            self.best = None
        return self.best.name
"""


def test_method_with_a_comment_at_column_0_is_classified_and_hashed():
    (function,) = parse("app/prober.py", PROBER)
    (uncommented,) = parse("app/prober.py", PROBER.replace("#            self.best = None\n", ""))

    assert classify(function, PROBER) == {}
    assert structure_hash(function.source) == structure_hash(uncommented.source)


def test_dedent_leaves_less_indented_string_lines_unchanged():
    (function,) = parse("app/report.py", 'class Report:\n    def render(self):\n        text = """head\nbody\n"""\n        return text\n')

    source = dedent(function.source)

    assert source == 'def render(self):\n    text = """head\nbody\n"""\n    return text\n'
    assert ast.parse(source).body[0].body[0].value.value == "head\nbody\n"


def test_parse_keeps_a_backslash_continuation_into_a_comment_with_its_function():
    text = (
        "def test_guess_rational_cv():\n"
        "    assert guess_solve_strategy( (sqrt(x) + 1)/(x**Rational(1, 3) + sqrt(x) + 1), x ) \\\n"
        "        #==GS_RATIONAL_CV_1\n"
        "\n\n"
        "def test_guess_transcendental():\n"
        "    pass\n"
    )

    first, _ = parse("t.py", text)

    assert first.end == 3
    assert first.source.endswith("        #==GS_RATIONAL_CV_1\n")


def test_parse_ends_a_function_at_a_comment_that_ends_in_a_backslash():
    (kept,) = parse("t.py", "def f():\n    x = 1  # C:\\\n")

    assert kept.end == 2


def test_method_with_a_string_line_left_of_the_def_is_rejected_without_a_model_call(make_repo, fake_llm, capsys):
    method = "class Policy:\n" + textwrap.indent(NESTED, "    ").replace(
        "        if user_active:\n", '        print("""head\nbody\n""")\n        if user_active:\n', 1
    )
    repo = make_repo({"app/__init__.py": ""}, {"app/perms.py": method})

    result = review(capsys, repo)

    assert fake_llm.calls == []
    [rejected] = result["rejected"]
    assert (rejected["function"], rejected["reason"]) == ("Policy.can_edit", "a line is left of the def, so the gate cannot re-indent a rewrite")


def test_method_with_only_a_comment_left_of_the_def_gets_a_rewrite(make_repo, fake_llm, capsys):
    method = "class Policy:\n    VERSION = 1\n\n" + textwrap.indent("@staticmethod\n" + NESTED, "    ").replace(
        "        if user_active:\n", "#        note\n        if user_active:\n", 1
    )
    repo = make_repo({"app/__init__.py": ""}, {"app/perms.py": method})
    fake_llm.replies += [fenced(TESTS.format(name="Policy", call="Policy.can_edit")), fenced("@staticmethod\n" + FLAT)]

    result = review(capsys, repo)

    assert result["rejected"] == []
    assert suggested_code(result["suggestions"][0]["body"]) == textwrap.indent("@staticmethod\n" + FLAT, "    ")


def test_rewrite_prompt_states_the_bool_rule(make_repo, fake_llm, capsys):
    repo = make_repo({"app/__init__.py": ""}, {"app/perms.py": NESTED})
    fake_llm.replies += [fenced(TESTS.format(name="can_edit", call="can_edit")), fenced(FLAT)]

    review(capsys, repo)

    assert "If every return gives True or False, keep it that way" in fake_llm.calls[-1][1]


@pytest.mark.parametrize(
    "returned",
    [
        "not locked and (not archived or user_active == 1)",
        "True if user_active else is_owner > 0",
        "isinstance(user_active, bool) or all((is_owner, locked))",
    ],
)
def test_bool_expressions_pass_the_bool_rule(make_repo, fake_llm, capsys, trials, returned):
    repo = make_repo({"app/__init__.py": ""}, {"app/perms.py": NESTED})
    fake_llm.replies += [fenced(TESTS.format(name="can_edit", call="can_edit")), fenced(SIGNATURE + f"    return {returned}\n")]
    fake_llm.replies += [fenced(FLAT)]

    result = review(capsys, repo)

    assert not any(r["reason"].startswith("rule:") for r in result["rejected"])
    assert len(trials) > 2


WRONG_TESTS = TESTS.format(name="can_edit", call="can_edit").replace(
    "assert can_edit(True, True, False, True) is False", "assert can_edit(True, True, False, True) is True"
)
TEST_PATH = "tests/test_slopgate_0.py"
CMD = f"python -m coverage run --branch -m pytest -q {TEST_PATH}"


def test_tests_that_fail_on_original_are_rejected(make_repo, fake_llm, capsys):
    repo = make_repo({"app/__init__.py": ""}, {"app/perms.py": NESTED})
    fake_llm.replies += [fenced(WRONG_TESTS)]

    result = review(capsys, repo)
    [rejected] = result["rejected"]

    assert rejected["reason"].startswith("characterization tests fail on original")
    assert "assert False is True" in rejected["reason"]
    assert models(fake_llm) == [SUPER, SUPER]
    assert result["notes"] == [REJECTED_NOTE]


def tool_call(arguments):
    return SimpleNamespace(id="call_0", function=SimpleNamespace(name="execute", arguments=arguments))


def agent_reply(*calls):
    return SimpleNamespace(content="", tool_calls=list(calls) or None)


def write_command(path, text):
    return json.dumps({"command": f"mkdir -p {path.rpartition('/')[0] or '.'} && printf %s {shlex.quote(text)} > {path}"})


def perms(make_repo):
    repo = make_repo({"app/__init__.py": ""}, {"app/perms.py": NESTED})
    [function] = parse("app/perms.py", NESTED)
    sandbox = Local()
    return sandbox, sandbox.prepare(repo, "HEAD", None), function


def test_agent_file_that_passes_the_check_is_returned(make_repo, fake_llm):
    sandbox, checkpoint, function = perms(make_repo)
    fake_llm.replies += [fenced(TESTS.format(name="can_edit", call="can_edit"))]

    assert characterize(sandbox, checkpoint, function, TEST_PATH, CMD) == (TESTS.format(name="can_edit", call="can_edit"), None)
    assert models(fake_llm) == [SUPER, SUPER]
    assert "Import the target with exactly this line: from app.perms import can_edit\n" in fake_llm.calls[0][1]


def test_agent_that_stops_without_a_file_is_rejected(make_repo, fake_llm):
    sandbox, checkpoint, function = perms(make_repo)
    fake_llm.replies += [agent_reply()]

    assert characterize(sandbox, checkpoint, function, TEST_PATH, CMD) == (None, "no test file: agent stopped (no tool call)")
    assert models(fake_llm) == [SUPER]


PASSING = TESTS.format(name="can_edit", call="can_edit")
WEAK = PASSING.replace("def test_locked_cannot_edit():\n    assert can_edit(True, True, True, False) is False\n", "")


def scripted(monkeypatch, replies) -> list[str]:
    steps = []

    def step(model, messages, tools):
        steps.append(model)
        llm.usage.append((model, 1000, 100))
        reply = replies[min(len(steps), len(replies)) - 1]
        return (reply() if callable(reply) else reply), 1000

    monkeypatch.setattr(llm, "step", step)
    monkeypatch.setattr(llm, "usage", [])
    return steps


def writes(text):
    return agent_reply(tool_call(write_command(TEST_PATH, text)))


def test_agent_stops_at_the_step_limit_and_the_check_judges_its_file(make_repo, monkeypatch):
    sandbox, checkpoint, function = perms(make_repo)
    steps = scripted(monkeypatch, [writes(WEAK)])

    assert characterize(sandbox, checkpoint, function, TEST_PATH, CMD) == (None, "step limit: characterization tests miss branches: 1")
    assert steps == [SUPER] * AGENT_STEPS


def test_agent_counts_the_tokens_of_its_own_replies_when_other_threads_add_usage(make_repo, monkeypatch):
    sandbox, checkpoint, function = perms(make_repo)
    steps = []

    def step(model, messages, tools):
        steps.append(model)
        llm.usage += [(model, AGENT_TOKENS // 2 + 1, 100), (model, 1, 1)]
        return writes(WEAK), AGENT_TOKENS // 2 + 1

    monkeypatch.setattr(llm, "step", step)
    monkeypatch.setattr(llm, "usage", [])

    assert characterize(sandbox, checkpoint, function, TEST_PATH, CMD) == (None, "token limit: characterization tests miss branches: 1")
    assert len(steps) == 2


def test_the_last_reply_before_the_step_limit_still_runs_its_tool_calls(make_repo, monkeypatch):
    sandbox, checkpoint, function = perms(make_repo)
    monkeypatch.setattr("slopgate.review.AGENT_STEPS", 2)
    steps = scripted(monkeypatch, [writes(WEAK), writes(PASSING)])

    assert characterize(sandbox, checkpoint, function, TEST_PATH, CMD) == (PASSING, None)
    assert len(steps) == 2


def test_agent_stops_before_a_command_when_the_time_budget_is_gone(make_repo, monkeypatch):
    sandbox, checkpoint, function = perms(make_repo)
    clock = [0.0]
    monkeypatch.setattr("slopgate.review.time", SimpleNamespace(perf_counter=lambda: clock[0]))
    timeouts = []
    execute = LocalSession.execute
    monkeypatch.setattr(LocalSession, "execute", lambda self, command, timeout: timeouts.append(timeout) or execute(self, command, timeout))

    def at(seconds, text):
        def reply():
            clock[0] = seconds
            return writes(text)

        return reply

    scripted(monkeypatch, [at(AGENT_SECONDS - 30.2, WEAK), at(AGENT_SECONDS + 1, PASSING)])

    assert characterize(sandbox, checkpoint, function, TEST_PATH, CMD) == (None, "time limit: characterization tests miss branches: 1")
    assert timeouts == [31]


def test_a_cut_off_reply_ends_the_agent_and_its_file_is_still_judged(make_repo, monkeypatch):
    sandbox, checkpoint, function = perms(make_repo)

    def cut_off():
        raise llm.CutOff("reply cut off")

    scripted(monkeypatch, [writes(PASSING), cut_off])

    assert characterize(sandbox, checkpoint, function, TEST_PATH, CMD) == (PASSING, None)


def test_a_failed_command_ends_the_agent_and_its_file_is_still_judged(make_repo, monkeypatch):
    sandbox, checkpoint, function = perms(make_repo)
    commands = []
    execute = LocalSession.execute

    def fails_second(self, command, timeout):
        commands.append(command)
        if len(commands) == 2:
            raise RuntimeError("session failed")
        return execute(self, command, timeout)

    monkeypatch.setattr(LocalSession, "execute", fails_second)
    scripted(monkeypatch, [writes(WEAK), writes(PASSING)])

    assert characterize(sandbox, checkpoint, function, TEST_PATH, CMD) == (
        None,
        "agent error: RuntimeError('session failed'): characterization tests miss branches: 1",
    )


def test_a_failed_read_rejects_the_function_with_the_stop_reason(make_repo, monkeypatch):
    sandbox, checkpoint, function = perms(make_repo)
    def fails(self, path):
        raise RuntimeError("session failed")

    monkeypatch.setattr(LocalSession, "read", fails)
    scripted(monkeypatch, [agent_reply()])

    assert characterize(sandbox, checkpoint, function, TEST_PATH, CMD) == (
        None,
        "no test file: agent stopped (no tool call), read failed: RuntimeError('session failed')",
    )


def test_tool_call_arguments_that_are_not_json_get_an_error_message(make_repo, monkeypatch):
    sandbox, checkpoint, function = perms(make_repo)
    seen = []

    def step(model, messages, tools):
        seen.append(messages[-1])
        llm.usage.append((model, 1000, 100))
        return (agent_reply(tool_call('{"command": "cat > t.py <<EOF')) if len(seen) == 1 else agent_reply()), 1000

    monkeypatch.setattr(llm, "step", step)
    monkeypatch.setattr(llm, "usage", [])

    assert characterize(sandbox, checkpoint, function, TEST_PATH, CMD) == (None, "no test file: agent stopped (no tool call)")
    assert seen[1]["role"] == "tool"
    assert seen[1]["content"].startswith("Error: invalid arguments for execute: JSONDecodeError(")


def test_check_runs_on_the_original_code_and_not_in_the_agent_session(make_repo, fake_llm, capsys):
    repo = make_repo({"app/__init__.py": ""}, {"app/perms.py": NESTED})
    breaks_target = json.loads(write_command("app/perms.py", SIGNATURE + "    return False\n"))["command"]
    writes_tests = json.loads(write_command(TEST_PATH, TESTS.format(name="can_edit", call="can_edit")))["command"]
    command = json.dumps({"command": f"{breaks_target} && {writes_tests}"})
    fake_llm.replies += [agent_reply(tool_call(command)), fenced(FLAT)]

    result = review(capsys, repo)

    assert result["rejected"] == []
    [suggestion] = result["suggestions"]
    assert "5 characterization tests passed in sandbox" in suggestion["body"]


def test_local_session_keeps_files_between_commands_and_leaves_the_checkpoint_alone(tmp_path):
    session = Local().session(tmp_path)

    assert session.execute("echo hi > a.txt", 10) == (0, "")
    assert session.execute("cat a.txt", 10) == (0, "hi\n")
    assert (session.read("a.txt"), session.read("b.txt")) == ("hi\n", None)
    assert list(tmp_path.iterdir()) == []


def test_local_session_kills_a_command_and_its_children_at_the_time_limit(tmp_path):
    session = Local().session(tmp_path)
    start = time.perf_counter()

    assert session.execute("echo started; sleep 30 & sleep 30", 1) == (124, "started\n\ntimed out after 1 s")
    assert time.perf_counter() - start < 10


def test_shell_returns_at_the_time_limit_when_a_child_left_the_process_group(tmp_path):
    start = time.perf_counter()

    escaped = 'python -c "import os, time; os.setsid(); time.sleep(8)" &'
    assert sandbox.shell(f"echo started; {escaped} sleep 30", tmp_path, 1) == (124, "started\n\ntimed out after 1 s")
    assert time.perf_counter() - start < 8


def test_local_run_gives_a_command_no_stdin(tmp_path):
    # pytest gives its own children /dev/null as stdin, so the run must happen in a process whose stdin stays open.
    code = f"from slopgate.sandbox import Local; print(Local().run({str(tmp_path)!r}, {{}}, 'python -c \\'input()\\''))"
    child = subprocess.Popen([sys.executable, "-c", code], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)

    child.wait(timeout=10)

    assert "EOFError" in child.stdout.read()
    child.stdin.close()


def test_local_run_stops_a_command_at_the_time_limit(tmp_path, monkeypatch):
    monkeypatch.setattr("slopgate.sandbox.SANDBOX_TIMEOUT", 1)
    start = time.perf_counter()

    code, output = Local().run(tmp_path, {}, 'python -c "while True: pass"')

    assert code == 124 and output.endswith("timed out after 1 s")
    assert time.perf_counter() - start < 10


def test_contree_run_bounds_the_command_and_reports_a_run_that_reached_the_time_limit(monkeypatch):
    monkeypatch.setattr("slopgate.sandbox.SANDBOX_TIMEOUT", 7)
    clock, runs = [0.0], []

    def run(exit_code, seconds):
        def start(**kwargs):
            runs.append(kwargs)
            clock[0] += seconds
            return SimpleNamespace(wait=lambda: SimpleNamespace(exit_code=exit_code, stdout="partial", stderr=""))

        return SimpleNamespace(run=start)

    monkeypatch.setattr("slopgate.sandbox.time", SimpleNamespace(monotonic=lambda: clock[0]))
    box = Contree.__new__(Contree)

    assert box.run(run(137, 12), {"tests/test_x.py": "x = 1\n"}, "pytest -q") == (124, "partial\ntimed out after 7 s")
    assert box.run(run(124, 1), {}, "exit 124") == (124, "partial")
    assert runs[0] == {"shell": "timeout -k 5 7 sh -c 'pytest -q'", "cwd": "/repo", "files": {"/repo/tests/test_x.py": b"x = 1\n"}, "timeout": 67}


LOOPS = TESTS.format(name="can_edit", call="can_edit").replace("assert can_edit(False, True, False, False) is False", "while True: pass")


def test_a_test_that_never_ends_rejects_the_function_and_the_review_goes_on(make_repo, fake_llm, monkeypatch, capsys):
    monkeypatch.setattr("slopgate.sandbox.SANDBOX_TIMEOUT", 1)
    repo = two_nested_functions(make_repo, "")
    fake_llm.replies += [fenced(LOOPS), fenced(TESTS.format(name="can_view", call="can_view")), fenced(FLAT_VIEW)]

    result = review(capsys, repo)

    [rejected] = result["rejected"]
    assert rejected["function"] == "can_edit"
    assert rejected["reason"].startswith("characterization tests time out:") and rejected["reason"].endswith("timed out after 1 s")
    [suggestion] = result["suggestions"]
    assert suggested_code(suggestion["body"]) == FLAT_VIEW


def test_contree_session_bounds_each_command_in_the_sandbox_and_reads_a_missing_file_as_none():
    runs, reads = [], []

    def run(**kwargs):
        runs.append(kwargs)
        return SimpleNamespace(wait=lambda: SimpleNamespace(exit_code=124, stdout="partial", stderr="", result=SimpleNamespace(truncated=True)))

    def read(path):
        reads.append(path)
        raise NotFoundError()

    session = ContreeSession(SimpleNamespace(session=lambda: SimpleNamespace(run=run, read=read)))

    assert session.execute("sleep 30", 3) == (124, "partial\n[Output was truncated due to size limits]")
    assert runs == [
        {"shell": "timeout -k 5 3 sh -c 'sleep 30'", "cwd": "/repo", "timeout": 63, "disposable": False, "truncate_output_at": 10 * 1024 * 1024}
    ]
    assert session.read("tests/test_x.py") is None
    assert reads == ["/repo/tests/test_x.py"]


def fake_client(monkeypatch, replies):
    requests = []

    def create(**kwargs):
        requests.append(kwargs)
        finish_reason, content = replies.pop(0)
        return SimpleNamespace(
            usage=SimpleNamespace(prompt_tokens=1, completion_tokens=1),
            choices=[
                SimpleNamespace(
                    finish_reason=finish_reason,
                    message=SimpleNamespace(content=content, tool_calls=[SimpleNamespace(function=SimpleNamespace(arguments=content))]),
                )
            ],
        )

    monkeypatch.setattr(llm, "client", lambda: SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create))))
    monkeypatch.setattr(llm, "usage", [])
    return requests


def test_complete_turns_thinking_off(monkeypatch):
    requests = fake_client(monkeypatch, [("stop", "ok")])

    assert llm.complete(SUPER, "hi") == "ok"
    assert requests[0]["extra_body"] == {"chat_template_kwargs": {"enable_thinking": False}}
    assert requests[0]["max_tokens"] == 32768


def test_step_offers_the_tools_with_thinking_off(monkeypatch):
    requests = fake_client(monkeypatch, [("stop", "ok")])
    messages = [{"role": "user", "content": "task"}]

    message, sent = llm.step(SUPER, messages, [EXECUTE])
    assert (message.content, sent) == ("ok", 1)
    [request] = requests
    assert (request["messages"], request["tools"], request["tool_choice"]) == (messages, [EXECUTE], "auto")
    assert request["extra_body"] == {"chat_template_kwargs": {"enable_thinking": False}}
    assert request["max_tokens"] == 32768
    assert llm.usage == [(SUPER, 1, 1)]


@pytest.mark.parametrize("call", [lambda: llm.complete(SUPER, "hi"), lambda: llm.step(SUPER, [], [EXECUTE])], ids=["complete", "step"])
def test_reply_that_reaches_the_token_limit_raises_cut_off(monkeypatch, call):
    fake_client(monkeypatch, [("length", "```python\ndef")])

    with pytest.raises(llm.CutOff):
        call()


def test_unexpected_error_in_one_candidate_keeps_the_others(make_repo, fake_llm, monkeypatch, capsys):
    repo = two_nested_functions(make_repo, "")
    fake_llm.replies += [fenced(TESTS.format(name="can_edit", call="can_edit")), fenced(TESTS.format(name="can_view", call="can_view")), fenced(FLAT_VIEW)]
    calls, complete = [], llm.complete

    def broken_first_call(model, prompt):
        calls.append(prompt)
        if len(calls) == 1:
            raise RuntimeError("boom")
        return complete(model, prompt)

    monkeypatch.setattr(llm, "complete", broken_first_call)

    result = review(capsys, repo)

    assert result["rejected"] == [{"function": "can_edit", "path": "app/perms.py", "kinds": ["nesting"], "reason": "internal error: RuntimeError('boom')"}]
    [note] = result["notes"]
    assert (note["path"], note["function"]) == ("app/perms.py", "can_edit")
    assert note["body"].endswith(REJECTED)
    [suggestion] = result["suggestions"]
    assert suggested_code(suggestion["body"]) == FLAT_VIEW


@pytest.mark.parametrize("cut", ["step", "complete"], ids=["tests", "rewrite"])
def test_cut_off_reply_rejects_the_candidate_and_the_next_one_runs(make_repo, fake_llm, monkeypatch, capsys, cut):
    repo = two_nested_functions(make_repo, "")
    if cut == "complete":
        fake_llm.replies += [fenced(TESTS.format(name="can_edit", call="can_edit"))]
    fake_llm.replies += [fenced(TESTS.format(name="can_view", call="can_view")), fenced(FLAT_VIEW)]
    calls, call = [], getattr(llm, cut)

    def cut_first(*args):
        calls.append(args)
        if len(calls) == 1:
            raise llm.CutOff("reply cut off")
        return call(*args)

    monkeypatch.setattr(llm, cut, cut_first)

    result = review(capsys, repo)

    reason = "no test file: agent stopped (reply cut off)" if cut == "step" else "reply cut off"
    assert result["rejected"] == [{"function": "can_edit", "path": "app/perms.py", "kinds": ["nesting"], "reason": reason}]
    [suggestion] = result["suggestions"]
    assert suggested_code(suggestion["body"]) == FLAT_VIEW


def test_prose_rewrite_reply_is_rejected_without_a_trial(make_repo, fake_llm, capsys, trials):
    repo = make_repo({"app/__init__.py": ""}, {"app/perms.py": NESTED})
    fake_llm.replies += [fenced(TESTS.format(name="can_edit", call="can_edit")), "Return one bool() of the four checks."]

    result = review(capsys, repo)

    assert result["rejected"] == [{"function": "can_edit", "path": "app/perms.py", "kinds": ["nesting"], "reason": "rewrite reply is not a python block"}]
    assert len(trials) == 2
    assert models(fake_llm) == [SUPER, SUPER, SUPER]


FENCE_IN_STRING = '''\
def as_markdown(code):
    return "```python\\n" + code + "\\n```"
'''

FENCE_IN_DOCSTRING = '''\
def as_markdown(code):
    """Wrap code in a fence.

    ```
    """
'''


@pytest.mark.parametrize(
    ("reply", "code"),
    [
        (fenced(FENCE_IN_STRING), FENCE_IN_STRING),
        ("Here is the rewrite:\n\n" + fenced(FENCE_IN_STRING) + "\n\nIt keeps the behavior.\n", FENCE_IN_STRING),
        (fenced(FLAT) + "\n\nThese calls cover each branch.\n\n```json\n{\"inputs\": []}\n```\n", FLAT),
        (fenced(FENCE_IN_DOCSTRING), 'def as_markdown(code):\n    """Wrap code in a fence.\n\n'),
        ("Return one bool() of the four checks.", None),
        ("```\n" + FLAT + "```", None),
        ("```python\n" + FLAT, None),
    ],
    ids=["fence-in-string", "prose-around-block", "json-block-after", "docstring-fence-ends-block", "prose-only", "no-python-tag", "no-closing-line"],
)
def test_strip_fence_takes_the_python_block_whole(reply, code):
    assert strip_fence(reply) == code


def test_unchanged_rewrite_is_rejected_without_a_trial_or_ultra(make_repo, fake_llm, capsys, trials):
    repo = make_repo({"app/__init__.py": ""}, {"app/perms.py": NESTED})
    blank_line_added = NESTED.replace("\n", "\n\n", 1)
    fake_llm.replies += [fenced(TESTS.format(name="can_edit", call="can_edit")), fenced(blank_line_added)]

    result = review(capsys, repo)

    assert result["rejected"] == [{"function": "can_edit", "path": "app/perms.py", "kinds": ["nesting"], "reason": "rewrite makes no change"}]
    assert len(trials) == 2
    assert models(fake_llm) == [SUPER, SUPER, SUPER]


CLAMP = KINDS_SOURCE[KINDS_SOURCE.index("def clamp_all") : KINDS_SOURCE.index("def describe")].rstrip() + "\n"


@pytest.mark.parametrize(
    ("original", "rewrite", "same"),
    [
        (NESTED, NESTED, True),
        (NESTED, textwrap.indent(NESTED, "    "), True),
        (NESTED, NESTED.replace("return False", "return (False)"), True),
        (NESTED, FLAT, False),
        (CLAMP, CLAMP.replace("    # check the bounds\n", ""), False),
        (CLAMP, CLAMP.replace("# loop over the values", "# clamp each value"), False),
    ],
    ids=["identical", "indented", "parenthesized", "flattened", "comment-removed", "comment-changed"],
)
def test_same_code_compares_syntax_and_comments(original, rewrite, same):
    assert same_code(original, rewrite) is same


def test_rewrite_and_retry_prompts_hold_code_in_python_blocks(make_repo, fake_llm, capsys):
    repo = make_repo({"app/__init__.py": ""}, {"app/perms.py": NESTED})
    fake_llm.replies += [fenced(TESTS.format(name="can_edit", call="can_edit")), fenced(DROPS_LOCKED), fenced(FLAT)]

    review(capsys, repo)

    rewrite_prompt, retry_prompt = fake_llm.calls[2][1], fake_llm.calls[3][1]
    assert "```python\n" + NESTED + "\n```" in rewrite_prompt
    assert retry_prompt.startswith(rewrite_prompt)
    assert "This earlier rewrite failed:\n\n```python\n" + DROPS_LOCKED + "\n```" in retry_prompt


def test_coverage_that_omits_the_file_is_not_called_nondeterministic(make_repo, fake_llm, capsys):
    repo = make_repo({"app/__init__.py": ""}, {"app/perms.py": NESTED, ".coveragerc": "[run]\nomit = app/perms.py\n"})
    fake_llm.replies += [fenced(TESTS.format(name="can_edit", call="can_edit"))]

    result = review(capsys, repo)

    assert result["rejected"] == [{"function": "can_edit", "path": "app/perms.py", "kinds": ["nesting"], "reason": "coverage has no data for app/perms.py"}]


def test_cut_off_duplicate_verdict_skips_the_helper_and_the_review_goes_on(make_repo, monkeypatch, capsys):
    from test_duplicates import SLUGIFY, TYPE_ERROR_COPY

    repo = make_repo({"app/__init__.py": "", "app/text.py": SLUGIFY}, {"app/posts.py": TYPE_ERROR_COPY})
    requests = fake_client(monkeypatch, [("length", '{"same_')])

    result = review(capsys, repo)

    assert result == {"suggestions": [], "followup": [], "rejected": [], "notes": []}
    assert len(requests) == 1


def nested(name):
    return NESTED.replace("can_edit", name)


def flat(name):
    return FLAT.replace("can_edit", name)


SUITE = "python -m pytest -q"


class SlowSandbox:
    def __init__(self, delay=lambda cmd: 0.25, suite=lambda code: True):
        self.delay, self.suite, self.suites = delay, suite, []
        self.lock, self.active, self.peak = threading.Lock(), 0, 0

    def busy(self, cmd):
        with self.lock:
            self.active += 1
            self.peak = max(self.peak, self.active)
        time.sleep(self.delay(cmd))
        with self.lock:
            self.active -= 1

    def prepare(self, repo, ref, setup):
        return None

    def session(self, checkpoint):
        return self

    def execute(self, command, timeout):
        self.busy(command)
        return 0, ""

    def read(self, path):
        return "def test_placeholder():\n    pass\n"

    def run(self, checkpoint, files, cmd):
        self.busy(cmd)
        if cmd != SUITE:
            return 0, f"5 passed\n{COVERAGE}\n[]"
        self.suites.append(files)
        return (0, "1 passed") if self.suite(files["app/perms.py"]) else (1, "FAILED tests/test_app.py::test_app")


@pytest.fixture
def gate_review(make_repo, monkeypatch):
    def step(model, messages, tools):
        llm.usage.append((model, 1000, 100))
        if messages[-1]["role"] == "tool":
            return SimpleNamespace(content="Done.", tool_calls=None), 1000
        call = SimpleNamespace(id="call_0", function=SimpleNamespace(name="execute", arguments=json.dumps({"command": "true"})))
        return SimpleNamespace(content="", tool_calls=[call]), 1000

    def complete(model, prompt):
        llm.usage.append((model, 1000, 100))
        name = re.search(r"def (\w+)\(", prompt)[1]
        return "I cannot rewrite this." if name in prose else fenced(flat(name))

    prose = set()
    monkeypatch.setattr(llm, "step", step)
    monkeypatch.setattr(llm, "complete", complete)
    monkeypatch.setattr(llm, "usage", [])
    repo = None

    def run(names, sandbox, workers=8, refuse=()):
        nonlocal repo
        repo = repo or make_repo({"app/__init__.py": ""}, {"app/perms.py": "\n\n".join(map(nested, names))})
        prose.update(refuse)
        monkeypatch.setattr(gate, "WORKERS", workers)
        return gate.review(repo, "HEAD~1", "HEAD", sandbox)

    return run


def rewritten(result):
    return [re.search(r"rewrite of `(\w+)`", s["body"])[1] for s in result["suggestions"]]


THREE = ["can_edit", "can_view", "can_delete"]


def test_candidates_run_in_parallel(gate_review):
    peaks, timings = {}, {}
    for workers in (1, 8):
        sandbox = SlowSandbox()
        began = time.perf_counter()
        result = gate_review(THREE, sandbox, workers)
        timings[workers] = time.perf_counter() - began
        peaks[workers] = sandbox.peak
        assert rewritten(result) == THREE

    assert peaks == {1: 1, 8: 3}
    assert timings[8] < timings[1] / 2, timings


def test_accepted_rewrites_share_one_repo_suite_run(gate_review):
    sandbox = SlowSandbox(delay=lambda cmd: 0)

    result = gate_review(THREE, sandbox)

    assert rewritten(result) == THREE and result["rejected"] == []
    assert sandbox.suites == [{"app/perms.py": "\n\n".join(map(flat, THREE))}]


def test_rewrite_that_breaks_the_repo_suite_alone_is_the_only_one_rejected(gate_review):
    sandbox = SlowSandbox(delay=lambda cmd: 0, suite=lambda code: flat("can_view") not in code)

    result = gate_review(THREE, sandbox)

    assert rewritten(result) == ["can_edit", "can_delete"]
    [rejected] = result["rejected"]
    assert (rejected["function"], rejected["path"], rejected["kinds"]) == ("can_view", "app/perms.py", ["nesting"])
    assert rejected["reason"] == "rewrite fails repo tests: FAILED tests/test_app.py::test_app"
    assert [note["function"] for note in result["notes"]] == ["can_view"]


def test_rewrites_that_pass_alone_but_fail_together_keep_the_first(gate_review):
    sandbox = SlowSandbox(delay=lambda cmd: 0, suite=lambda code: not (flat("can_edit") in code and flat("can_view") in code))

    result = gate_review(THREE, sandbox)

    assert rewritten(result) == ["can_edit", "can_delete"]
    assert result["rejected"] == [
        {"function": "can_view", "path": "app/perms.py", "kinds": ["nesting"], "reason": "rewrite conflicts with another rewrite"}
    ]


def test_parallel_results_keep_the_candidate_order(gate_review):
    def first_is_slowest(cmd):
        n = re.search(r"test_slopgate_(\d+)", cmd)
        return 0.1 * (4 - int(n[1])) if n else 0

    names = [*THREE, "can_move"]
    refuse = ["can_edit", "can_delete"]
    parallel = gate_review(names, SlowSandbox(delay=first_is_slowest), 8, refuse)
    serial = gate_review(names, SlowSandbox(delay=first_is_slowest), 1, refuse)

    assert rewritten(parallel) == ["can_view", "can_move"]
    assert [r["function"] for r in parallel["rejected"]] == refuse
    assert (parallel["suggestions"], parallel["rejected"]) == (serial["suggestions"], serial["rejected"])


def test_broken_repo_suite_run_rejects_the_accepted_rewrites_and_keeps_the_other_results(gate_review):
    def broken(code):
        raise RuntimeError("sandbox down")

    result = gate_review(THREE, SlowSandbox(delay=lambda cmd: 0, suite=broken), refuse=["can_view"])

    error = "internal error: RuntimeError('sandbox down')"
    assert result["suggestions"] == [] and result["followup"] == []
    assert [(r["function"], r["reason"]) for r in result["rejected"]] == [
        ("can_edit", error),
        ("can_view", "rewrite reply is not a python block"),
        ("can_delete", error),
    ]
    assert [note["function"] for note in result["notes"]] == THREE
