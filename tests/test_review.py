import ast
import json
import re
import textwrap
from types import SimpleNamespace

import pytest

from slopgate import kinds, llm
from slopgate.cli import main
from slopgate.config import LIGHTNING, SUPER, ULTRA
from slopgate.functions import is_test_file, parse, pytest_patterns
from slopgate.kinds import KINDS, Check, has_dead_code
from slopgate.review import MISSED_RETRY, NOT_PYTHON_RETRY, RECORDER_PATH, Calls, parse_tests_reply, same_code, strip_fence
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

NO_LINES = Check(reason="No line matches the rule.", lines=[])
VIEW = NESTED.replace("can_edit", "can_view")
FLAT_VIEW = FLAT.replace("can_edit", "can_view")
ALL_SET_LINE = "def all_set(a, b, c, d, e, f): return (a and b) and (c and d) and (e and f)"
ALL_SET = ALL_SET_LINE + "\n"
ALL_SET_CHECK = Check(reason="The groups repeat the and chain.", lines=[ALL_SET_LINE])
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
        NO_LINES,
        NO_LINES,
        "```python\n" + TESTS.format(name="can_edit", call="can_edit") + "```",
        "Here is the rewrite:\n```python\n" + FLAT + "```",
    ]

    result = review(capsys, repo)

    assert result["followup"] == [] and result["rejected"] == []
    assert models(fake_llm) == [LIGHTNING, LIGHTNING, SUPER, SUPER]
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
        NO_LINES,
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
        ALL_SET_CHECK,
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


def test_rewrite_that_changes_behavior_is_rejected(make_repo, fake_llm, capsys):
    repo = make_repo({"app/__init__.py": ""}, {"app/perms.py": NESTED})
    fake_llm.replies += [NO_LINES, fenced(TESTS.format(name="can_edit", call="can_edit")), fenced(DROPS_LOCKED), fenced(DROPS_LOCKED)]

    result = review(capsys, repo)

    assert result["suggestions"] == [] and result["followup"] == []
    [rejected] = result["rejected"]
    assert (rejected["function"], rejected["path"]) == ("can_edit", "app/perms.py")
    assert rejected["reason"].startswith("rewrite fails characterization tests")
    assert "test_locked_cannot_edit" in rejected["reason"]
    assert models(fake_llm) == [LIGHTNING, SUPER, SUPER, ULTRA]


def test_failed_rewrite_gets_one_ultra_retry(make_repo, fake_llm, capsys):
    repo = make_repo({"app/__init__.py": ""}, {"app/perms.py": NESTED})
    fake_llm.replies += [NO_LINES, fenced(TESTS.format(name="can_edit", call="can_edit")), fenced(DROPS_LOCKED), fenced(FLAT)]

    result = review(capsys, repo)

    assert result["rejected"] == []
    [suggestion] = result["suggestions"]
    assert suggested_code(suggestion["body"]) == FLAT
    assert models(fake_llm) == [LIGHTNING, SUPER, SUPER, ULTRA]


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
    fake_llm.replies += [NO_LINES, NO_LINES]

    result = review(capsys, repo)

    assert models(fake_llm) == [LIGHTNING, LIGHTNING]
    body = f"**nesting** (not proven): `can_edit`: {KINDS['nesting']} Not proven: Slopgate does not change test files."
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
        NO_LINES,
        NO_LINES,
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
        NO_LINES,
        NO_LINES,
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
    fake_llm.replies += [NO_LINES, fenced(TESTS.format(name="can_edit", call="can_edit")), fenced(FLAT), fenced(FLAT)]

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
    fake_llm.replies += [NO_LINES, fenced(TESTS.format(name="can_edit", call="can_edit")), fenced(FLAT)]

    result = review(capsys, repo)

    assert result["rejected"] == []
    [suggestion] = result["suggestions"]
    assert suggested_code(suggestion["body"]) == FLAT


def test_install_failure_is_one_notice_with_last_20_lines(make_repo, fake_llm, capsys):
    setup = "echo boom; for i in $(seq 1 30); do echo line$i; done; exit 1"
    repo = make_repo({"app/__init__.py": ""}, {"app/perms.py": NESTED, ".slopgate.toml": f"[sandbox]\nsetup = '{setup}'\n"})
    fake_llm.replies += [NO_LINES]

    result = review(capsys, repo)

    tail = "\n".join(f"line{i}" for i in range(11, 31))
    assert result == {
        "suggestions": [],
        "followup": [],
        "rejected": [{"reason": f"could not build test environment\n{tail}"}],
        "notes": [],
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
    redundant = Check(reason="The inner check repeats the outer one.", lines=["if price is not None and price > 0:"])
    filler = Check(reason="The comments restate the code.", lines=["# create the result list", "# loop over the values"])
    fake_llm.replies += [NO_LINES, redundant, NO_LINES, NO_LINES, {"redundant_check": NO_LINES, "filler_comment": filler}]
    fake_llm.replies += [fenced(reply) for _, tests, rewrite in KIND_CASES for reply in (tests, rewrite)]

    result = review(capsys, repo)

    assert result["rejected"] == []
    named = [re.match(r"Slopgate \((.*?)\) rewrite", suggestion["body"])[1] for suggestion in result["suggestions"]]
    assert named == ["`nesting`", "`nesting`, `redundant_check`", "`swallowed_error`", "`lookup_table`", "`filler_comment`", "`dead`"]
    assert models(fake_llm).count(LIGHTNING) == 6
    total_prompt = next(prompt for _, prompt in fake_llm.calls if prompt.startswith("Rewrite") and "def total" in prompt)
    assert f"1. {KINDS['nesting']}\n2. {KINDS['redundant_check']} These lines:\n   if price is not None and price > 0:\n" in total_prompt


COMMENTED = NESTED.replace("    if user_active:\n", "    # check the user\n    if user_active:\n", 1)
FILLER = Check(reason="The comment restates the next line.", lines=["# check the user"])


def test_nesting_and_filler_comment_get_one_rewrite_with_a_numbered_list(make_repo, fake_llm, capsys):
    repo = make_repo({"app/__init__.py": ""}, {"app/perms.py": COMMENTED})
    fake_llm.replies += [{"redundant_check": NO_LINES, "filler_comment": FILLER}, fenced(TESTS.format(name="can_edit", call="can_edit")), fenced(FLAT)]

    result = review(capsys, repo)

    [suggestion] = result["suggestions"]
    assert suggestion["body"].startswith("Slopgate (`nesting`, `filler_comment`) rewrite of `can_edit`")
    [rewrite_prompt] = [prompt for _, prompt in fake_llm.calls if prompt.startswith("Rewrite")]
    problems = f"Fix these problems:\n\n1. {KINDS['nesting']}\n2. {KINDS['filler_comment']} These lines:\n   # check the user\n\nRules:"
    assert problems in rewrite_prompt


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
        (NESTED, [NO_LINES], TESTS.format(name="can_edit", call="can_edit"), STILL_NESTED, "nesting"),
        (
            COMMENTED,
            [{"redundant_check": NO_LINES, "filler_comment": FILLER}],
            TESTS.format(name="can_edit", call="can_edit"),
            SIGNATURE + "    # check the user\n    return bool(user_active and is_owner and not locked and not archived)\n",
            "filler_comment",
        ),
        (PARSE_INT, [], PARSE_INT_TESTS, PARSE_INT.replace("except Exception", "except BaseException"), "swallowed_error"),
    ],
    ids=["detector", "evidence-line", "ruff"],
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


GUARDED_TOTAL = "def total(prices):\n    if prices is None:\n        return 0\n    if prices is None or len(prices) == 0:\n        return 0\n    return sum(prices)\n"


def test_redundant_check_rewrite_that_keeps_only_the_guard_line_is_accepted(make_repo, fake_llm, capsys):
    repo = make_repo({"app/__init__.py": ""}, {"app/perms.py": GUARDED_TOTAL})
    evidence = Check(reason="The second check repeats the first.", lines=["if prices is None:", "if prices is None or len(prices) == 0:"])
    tests = (
        "from app.perms import total\n\n\ndef test_none():\n    assert total(None) == 0\n\n\n"
        "def test_empty():\n    assert total([]) == 0\n\n\ndef test_sum():\n    assert total([1, 2]) == 3\n"
    )
    rewrite = GUARDED_TOTAL.replace("prices is None or len(prices) == 0", "len(prices) == 0")
    fake_llm.replies += [evidence, fenced(tests), fenced(rewrite)]

    result = review(capsys, repo)

    assert result["rejected"] == []
    [suggestion] = result["suggestions"]
    assert suggestion["body"].startswith("Slopgate (`redundant_check`) rewrite of `total`.\n")
    assert suggested_code(suggestion["body"]) == rewrite


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
    fake_llm.replies += [NO_LINES, fenced(TESTS.format(name="can_edit", call="can_edit")), fenced(rewrite)]

    result = review(capsys, repo)

    assert result["suggestions"] == []
    assert result["rejected"] == [{"function": "can_edit", "path": "app/perms.py", "kinds": ["nesting"], "reason": f"rule: {rule}"}]
    assert len(trials) == 2
    assert models(fake_llm) == [LIGHTNING, SUPER, SUPER]


def test_function_using_random_is_rejected_as_nondeterministic(make_repo, fake_llm, capsys):
    line = "return random.random() if a and b and c and d and e and f else 0"
    source = f"import random\n\n\ndef roll(a, b, c, d, e, f):\n    {line}\n"
    repo = make_repo({"app/__init__.py": ""}, {"app/dice.py": source})
    fake_llm.replies += [Check(reason="a is tested twice.", lines=[line])]

    result = review(capsys, repo)

    assert result["suggestions"] == []
    [rejected] = result["rejected"]
    assert rejected["function"] == "roll"
    assert "nondeterministic" in rejected["reason"]
    assert models(fake_llm) == [LIGHTNING]


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
    fake_llm.replies += [NO_LINES, fenced(TESTS.format(name="can_edit", call="can_edit")), fenced(FLAT)]

    result = review(capsys, repo)

    assert result["rejected"] == []
    assert len(result["suggestions"]) == 1


def test_tests_that_miss_a_branch_are_rejected_with_the_count(make_repo, fake_llm, capsys):
    repo = make_repo({"app/__init__.py": ""}, {"app/perms.py": NESTED})
    weak = fenced(TESTS.format(name="can_edit", call="can_edit")).replace(
        "def test_locked_cannot_edit():\n    assert can_edit(True, True, True, False) is False\n", ""
    )
    fake_llm.replies += [NO_LINES, weak]

    result = review(capsys, repo)

    assert result["suggestions"] == []
    assert result["rejected"] == [
        {"function": "can_edit", "path": "app/perms.py", "kinds": ["nesting"], "reason": "characterization tests miss branches: 1"}
    ]
    assert models(fake_llm) == [LIGHTNING, SUPER]


@pytest.mark.parametrize(
    "reply",
    [
        None,
        NO_LINES,
        Check(reason="made up", lines=["if weight < 3:"]),
        Check(reason="not a condition", lines=['return "small"']),
    ],
    ids=["no-reply", "no-lines", "line-not-in-function", "line-without-a-condition"],
)
def test_check_without_a_grounded_line_drops_the_function_silently(make_repo, fake_llm, capsys, reply):
    repo = make_repo({"app/__init__.py": ""}, {"app/ship.py": SIMPLE})
    fake_llm.replies += [reply]

    assert review(capsys, repo) == {"suggestions": [], "followup": [], "rejected": [], "notes": []}
    assert models(fake_llm) == [LIGHTNING]


LABEL = 'def label(n, wide):\n    # use the wide form if wide and n is set\n    if (n and\n            wide):\n        return "#" * n\n    return "#"\n'


@pytest.mark.parametrize(
    ("kind", "line"),
    [("redundant_check", "# use the wide form if wide and n is set"), ("redundant_check", "if (n and"), ("filler_comment", 'return "#"')],
    ids=["comment-as-condition", "unclosed-bracket", "hash-in-string-as-comment"],
)
def test_evidence_line_without_the_syntax_of_its_kind_is_not_grounded(make_repo, fake_llm, capsys, kind, line):
    repo = make_repo({"app/__init__.py": ""}, {"app/labels.py": LABEL})
    fake_llm.replies += [{"redundant_check": NO_LINES, "filler_comment": NO_LINES} | {kind: Check(reason="It matches.", lines=[line])}]

    assert review(capsys, repo) == {"suggestions": [], "followup": [], "rejected": [], "notes": []}
    assert models(fake_llm) == [LIGHTNING, LIGHTNING]


def test_two_while_loops_are_checked_for_redundant_check(make_repo, fake_llm, capsys):
    source = "def drain(queue, limit):\n    while queue:\n        queue.pop()\n    while limit > 0:\n        limit -= 1\n    return limit\n"
    repo = make_repo({"app/__init__.py": ""}, {"app/queue.py": source})
    fake_llm.replies += [NO_LINES]

    assert review(capsys, repo) == {"suggestions": [], "followup": [], "rejected": [], "notes": []}
    [(model, prompt)] = fake_llm.calls
    assert model == LIGHTNING and prompt.startswith("Check the Python function below for one kind of slop: redundant_check.")


def test_failed_check_keeps_the_measured_kinds(make_repo, fake_llm, monkeypatch, capsys):
    repo = make_repo({"app/__init__.py": ""}, {"app/perms.py": COMMENTED})
    fake_llm.replies += [{"redundant_check": NO_LINES}, fenced(TESTS.format(name="can_edit", call="can_edit")), fenced(FLAT)]
    decide = llm.decide

    def broken_filler_check(model, prompt, schema):
        if "one kind of slop: filler_comment" in prompt:
            raise RuntimeError("boom")
        return decide(model, prompt, schema)

    monkeypatch.setattr(llm, "decide", broken_filler_check)

    result = review(capsys, repo)

    assert result["rejected"] == []
    [suggestion] = result["suggestions"]
    assert suggestion["body"].startswith("Slopgate (`nesting`) rewrite of `can_edit`.\n")


def test_ruff_failure_rejects_the_function_and_the_review_goes_on(make_repo, fake_llm, monkeypatch, capsys):
    repo = make_repo({"app/__init__.py": ""}, {"app/broken.py": "def one():\n    return 1\n", "app/perms.py": NESTED})
    fake_llm.replies += [NO_LINES, fenced(TESTS.format(name="can_edit", call="can_edit")), fenced(FLAT)]
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
    [suggestion] = result["suggestions"]
    assert suggestion["path"] == "app/perms.py"


def test_tests_that_differ_across_two_runs_are_rejected(make_repo, fake_llm, capsys):
    repo = make_repo({"app/__init__.py": ""}, {"app/perms.py": NESTED})
    # hash("b") is odd under PYTHONHASHSEED=1 and even under PYTHONHASHSEED=2
    flaky = fenced(TESTS.format(name="can_edit", call="can_edit") + '\n\ndef test_hash_order():\n    assert hash("b") % 2 == 1\n')
    fake_llm.replies += [NO_LINES, flaky]

    result = review(capsys, repo)

    assert models(fake_llm) == [LIGHTNING, SUPER]

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


def test_tests_prompt_without_repo_callees_has_no_context_section(make_repo, fake_llm, capsys):
    repo = make_repo({"app/__init__.py": ""}, {"app/perms.py": NESTED})
    fake_llm.replies += [NO_LINES, fenced(TESTS.format(name="can_edit", call="can_edit")), fenced(FLAT)]

    review(capsys, repo)

    tests_prompt = fake_llm.calls[1][1]
    assert tests_prompt.endswith("```python\n" + NESTED + "\n```")
    assert "Code it calls" not in tests_prompt


WRONG_TESTS = TESTS.format(name="can_edit", call="can_edit").replace(
    "assert can_edit(True, True, False, True) is False", "assert can_edit(True, True, False, True) is True"
)


def test_tests_that_fail_on_original_get_one_retry_with_the_failure(make_repo, fake_llm, capsys):
    repo = make_repo({"app/__init__.py": ""}, {"app/perms.py": NESTED})
    fake_llm.replies += [NO_LINES, fenced(WRONG_TESTS), fenced(TESTS.format(name="can_edit", call="can_edit")), fenced(FLAT)]

    result = review(capsys, repo)

    assert result["rejected"] == []
    [suggestion] = result["suggestions"]
    assert "5 characterization tests passed" in suggestion["body"]
    assert models(fake_llm) == [LIGHTNING, SUPER, SUPER, SUPER]
    retry_prompt = fake_llm.calls[2][1]
    assert "Earlier test file:\n\n```python\n" + WRONG_TESTS + "\n```" in retry_prompt
    assert "assert False is True" in retry_prompt


def test_tests_that_fail_on_original_twice_are_rejected(make_repo, fake_llm, capsys):
    repo = make_repo({"app/__init__.py": ""}, {"app/perms.py": NESTED})
    fake_llm.replies += [NO_LINES, fenced(WRONG_TESTS), fenced(WRONG_TESTS)]

    result = review(capsys, repo)

    [rejected] = result["rejected"]
    assert rejected["reason"].startswith("characterization tests fail on original")
    assert models(fake_llm) == [LIGHTNING, SUPER, SUPER]


EDIT_CALLS = fenced(
    "can_edit(False, True, False, False)\n"
    "can_edit(True, False, False, False)\n"
    "can_edit(True, True, True, False)\n"
    "can_edit(True, True, False, True)\n"
    "can_edit(True, True, False, False)\n"
)


def test_proposed_calls_are_recorded_on_the_original(make_repo, fake_llm, capsys):
    repo = make_repo({"app/__init__.py": ""}, {"app/perms.py": NESTED})
    fake_llm.replies += [NO_LINES, EDIT_CALLS, fenced(FLAT)]

    result = review(capsys, repo)

    assert result["rejected"] == []
    [suggestion] = result["suggestions"]
    assert "5 characterization tests passed" in suggestion["body"]
    assert models(fake_llm) == [LIGHTNING, SUPER, SUPER]


@pytest.mark.parametrize(
    ("rewrite", "failing"),
    [
        (DROPS_LOCKED, "capture(True, True, True, False)"),
    ],
    ids=["value"],
)
def test_recorded_calls_reject_a_rewrite_that_changes_the_result(make_repo, fake_llm, capsys, rewrite, failing):
    repo = make_repo({"app/__init__.py": ""}, {"app/perms.py": NESTED})
    fake_llm.replies += [NO_LINES, EDIT_CALLS, fenced(rewrite), fenced(rewrite)]

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
    calls = fenced("grade(70)\ngrade(10)\ngrade(-1)\ngrade(None)\n")
    fake_llm.replies += [NO_LINES, calls, fenced(rewrite), fenced(rewrite)]

    result = review(capsys, repo)

    assert len(result["suggestions"]) == accepted
    assert len(result["rejected"]) == (not accepted)


BARE_NAME_CALLS = fenced("can_edit(*1)\n")


def test_calls_that_do_not_evaluate_get_one_retry_with_the_error(make_repo, fake_llm, capsys):
    repo = make_repo({"app/__init__.py": ""}, {"app/perms.py": NESTED})
    fake_llm.replies += [NO_LINES, BARE_NAME_CALLS, EDIT_CALLS, fenced(FLAT)]

    result = review(capsys, repo)

    assert result["rejected"] == []
    [suggestion] = result["suggestions"]
    assert "5 characterization tests passed" in suggestion["body"]
    assert models(fake_llm) == [LIGHTNING, SUPER, SUPER, SUPER]
    retry_prompt = fake_llm.calls[2][1]
    assert retry_prompt.startswith(fake_llm.calls[1][1])
    assert "Earlier calls:\n\n```python\ncan_edit(*1)\n```" in retry_prompt
    assert "must be an iterable, not int" in retry_prompt


def test_empty_block_gets_one_retry_that_names_the_error(make_repo, fake_llm, capsys, trials):
    repo = make_repo({"app/__init__.py": ""}, {"app/perms.py": NESTED})
    fake_llm.replies += [NO_LINES, fenced(""), fenced(TESTS.format(name="can_edit", call="can_edit")), fenced(FLAT)]

    result = review(capsys, repo)

    assert result["rejected"] == []
    [suggestion] = result["suggestions"]
    assert "5 characterization tests passed" in suggestion["body"]
    assert models(fake_llm) == [LIGHTNING, SUPER, SUPER, SUPER]
    assert fake_llm.calls[2][1] == fake_llm.calls[1][1] + NOT_PYTHON_RETRY.format(error="the block holds no call to `can_edit` with plain-value arguments")
    assert not any(RECORDER_PATH in cmd for cmd in trials)


def test_empty_block_twice_is_rejected_without_a_sandbox_run(make_repo, fake_llm, capsys, trials):
    repo = make_repo({"app/__init__.py": ""}, {"app/perms.py": NESTED})
    fake_llm.replies += [NO_LINES, fenced(""), fenced("")]

    result = review(capsys, repo)

    assert result["rejected"] == [{"function": "can_edit", "path": "app/perms.py", "kinds": ["nesting"], "reason": "tests reply is not python"}]
    assert models(fake_llm) == [LIGHTNING, SUPER, SUPER]
    assert trials == []


def test_recorder_that_ends_without_results_twice_is_rejected(make_repo, fake_llm, capsys):
    repo = make_repo({"app/__init__.py": ""}, {"app/perms.py": NESTED})
    fake_llm.replies += [NO_LINES, fenced("can_edit(*1)\n"), BARE_NAME_CALLS]

    [rejected] = review(capsys, repo)["rejected"]

    assert rejected["reason"].startswith("could not record calls")
    assert "TypeError" in rejected["reason"]
    assert models(fake_llm) == [LIGHTNING, SUPER, SUPER]


@pytest.mark.parametrize(
    ("first", "second", "reason"),
    [
        (BARE_NAME_CALLS, fenced(WRONG_TESTS), "characterization tests fail on original"),
        (fenced(WRONG_TESTS), BARE_NAME_CALLS, "could not record calls"),
    ],
    ids=["calls-then-tests", "tests-then-calls"],
)
def test_one_retry_covers_either_failure(make_repo, fake_llm, capsys, first, second, reason):
    repo = make_repo({"app/__init__.py": ""}, {"app/perms.py": NESTED})
    fake_llm.replies += [NO_LINES, first, second]

    [rejected] = review(capsys, repo)["rejected"]

    assert rejected["reason"].startswith(reason)
    assert models(fake_llm) == [LIGHTNING, SUPER, SUPER]


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
def test_recorded_calls_check_the_arguments_after_the_call(make_repo, fake_llm, capsys, rewrite, accepted):
    repo = make_repo({"app/__init__.py": ""}, {"app/tags.py": ADD_TAG})
    calls = fenced('add_tag(["a"], "")\nadd_tag(["a"], "a")\nadd_tag(["a", "b", "c"], "d")\nadd_tag(["a"], "b")\n')
    fake_llm.replies += [NO_LINES, calls, fenced(rewrite), fenced(rewrite)]

    result = review(capsys, repo)

    assert len(result["suggestions"]) == accepted
    assert len(result["rejected"]) == (not accepted)


def test_method_prompt_has_no_calls_form_and_bare_calls_run_as_a_test_file(make_repo, fake_llm, capsys, trials):
    method = "class Policy:\n" + textwrap.indent("@staticmethod\n" + NESTED, "    ")
    repo = make_repo({"app/__init__.py": ""}, {"app/perms.py": NESTED + "\n\n" + method})
    fake_llm.replies += [NO_LINES, NO_LINES, fenced(TESTS.format(name="can_edit", call="can_edit")), fenced(FLAT)]
    bare_calls = fenced("Policy.can_edit(True, True, False, False)\nPolicy.can_edit(False, True, False, False)\n")
    fake_llm.replies += [bare_calls, fenced(TESTS.format(name="Policy", call="Policy.can_edit")), fenced("@staticmethod\n" + FLAT)]

    result = review(capsys, repo)

    function_prompt, method_prompt, method_retry = [prompt for _, prompt in fake_llm.calls if prompt.startswith("Write characterization")]
    assert "\n1. Calls. " in function_prompt and "\n2. Test file. " in function_prompt and "\n3. Cannot test. " in function_prompt
    assert "Calls." not in method_prompt
    assert "\n1. Test file. " in method_prompt and "\n2. Cannot test. " in method_prompt
    assert "Your earlier test file failed on the unchanged code above" in method_retry
    assert not any(RECORDER_PATH in cmd for cmd in trials)
    assert result["rejected"] == [] and len(result["suggestions"]) == 2


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

LOG_CALLS = fenced("log_value([], 5)\nlog_value([], 50)\nlog_value([], -1)\nlog_value([], None)\n")


def test_recorded_calls_check_the_arguments_after_an_exception(make_repo, fake_llm, capsys):
    repo = make_repo({"app/__init__.py": ""}, {"app/log.py": LOG_VALUE})
    fake_llm.replies += [NO_LINES, LOG_CALLS, fenced(CHECKS_FIRST), fenced(CHECKS_FIRST)]

    [rejected] = review(capsys, repo)["rejected"]

    assert rejected["reason"].startswith("rewrite fails characterization tests")
    assert "test_call_1" in rejected["reason"]


def test_rewrite_prompt_states_the_bool_rule(make_repo, fake_llm, capsys):
    repo = make_repo({"app/__init__.py": ""}, {"app/perms.py": NESTED})
    fake_llm.replies += [NO_LINES, fenced(TESTS.format(name="can_edit", call="can_edit")), fenced(FLAT)]

    review(capsys, repo)

    assert "If every return gives True or False, keep it that way" in fake_llm.calls[2][1]


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
    fake_llm.replies += [NO_LINES, fenced(TESTS.format(name="can_edit", call="can_edit")), fenced(SIGNATURE + f"    return {returned}\n")]
    fake_llm.replies += [fenced(FLAT)]

    result = review(capsys, repo)

    assert not any(r["reason"].startswith("rule:") for r in result["rejected"])
    assert len(trials) > 2


def test_recorded_calls_reject_a_changed_result_type(make_repo, fake_llm, capsys):
    repo = make_repo({"app/__init__.py": ""}, {"app/log.py": LOG_VALUE})
    as_float = (
        "def log_value(log, value):\n    log.append(value)\n"
        '    if value is None or not 0 <= value < 10:\n        raise ValueError("out of range")\n    return float(value)\n'
    )
    fake_llm.replies += [NO_LINES, LOG_CALLS, fenced(as_float), fenced(as_float)]

    [rejected] = review(capsys, repo)["rejected"]

    assert rejected["reason"].startswith("rewrite fails characterization tests")
    assert "5.0" in rejected["reason"]


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


def test_unexpected_error_in_one_candidate_keeps_the_others(make_repo, fake_llm, monkeypatch, capsys):
    repo = two_nested_functions(make_repo, "")
    fake_llm.replies += [NO_LINES, NO_LINES, fenced(TESTS.format(name="can_view", call="can_view")), fenced(FLAT_VIEW)]
    complete = llm.complete

    def broken_third_call(model, prompt):
        if len(fake_llm.calls) == 2:
            fake_llm.calls.append((model, prompt))
            raise RuntimeError("boom")
        return complete(model, prompt)

    monkeypatch.setattr(llm, "complete", broken_third_call)

    result = review(capsys, repo)

    assert result["rejected"] == [{"function": "can_edit", "path": "app/perms.py", "kinds": ["nesting"], "reason": "internal error: RuntimeError('boom')"}]
    [suggestion] = result["suggestions"]
    assert suggested_code(suggestion["body"]) == FLAT_VIEW


@pytest.mark.parametrize("cut", ["tests", "rewrite"])
def test_cut_off_reply_rejects_the_candidate_and_the_next_one_runs(make_repo, monkeypatch, capsys, cut):
    repo = two_nested_functions(make_repo, "")
    edit_tests = fenced(TESTS.format(name="can_edit", call="can_edit"))
    edit_replies = [("length", edit_tests[:40])] if cut == "tests" else [("stop", edit_tests), ("length", "```python\ndef")]
    view_replies = [("stop", fenced(TESTS.format(name="can_view", call="can_view"))), ("stop", fenced(FLAT_VIEW))]
    fake_client(monkeypatch, [("stop", NO_LINES.model_dump_json()), ("stop", NO_LINES.model_dump_json()), *edit_replies, *view_replies])

    result = review(capsys, repo)

    assert result["rejected"] == [{"function": "can_edit", "path": "app/perms.py", "kinds": ["nesting"], "reason": "reply cut off"}]
    [suggestion] = result["suggestions"]
    assert suggested_code(suggestion["body"]) == FLAT_VIEW


def test_cut_off_check_reply_gives_no_kind(make_repo, monkeypatch, capsys):
    repo = make_repo({"app/__init__.py": ""}, {"app/ship.py": SIMPLE})
    requests = fake_client(monkeypatch, [("length", '{"rea')])

    assert review(capsys, repo) == {"suggestions": [], "followup": [], "rejected": [], "notes": []}
    assert len(requests) == 1


def test_prose_rewrite_reply_is_rejected_without_a_trial(make_repo, fake_llm, capsys, trials):
    repo = make_repo({"app/__init__.py": ""}, {"app/perms.py": NESTED})
    fake_llm.replies += [NO_LINES, fenced(TESTS.format(name="can_edit", call="can_edit")), "Return one bool() of the four checks."]

    result = review(capsys, repo)

    assert result["rejected"] == [{"function": "can_edit", "path": "app/perms.py", "kinds": ["nesting"], "reason": "rewrite reply is not a python block"}]
    assert len(trials) == 2
    assert models(fake_llm) == [LIGHTNING, SUPER, SUPER]


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
    fake_llm.replies += [NO_LINES, fenced(TESTS.format(name="can_edit", call="can_edit")), fenced(blank_line_added)]

    result = review(capsys, repo)

    assert result["rejected"] == [{"function": "can_edit", "path": "app/perms.py", "kinds": ["nesting"], "reason": "rewrite makes no change"}]
    assert len(trials) == 2
    assert models(fake_llm) == [LIGHTNING, SUPER, SUPER]


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
    fake_llm.replies += [NO_LINES, fenced(TESTS.format(name="can_edit", call="can_edit")), fenced(DROPS_LOCKED), fenced(FLAT)]

    review(capsys, repo)

    rewrite_prompt, retry_prompt = fake_llm.calls[2][1], fake_llm.calls[3][1]
    assert "```python\n" + NESTED + "\n```" in rewrite_prompt
    assert retry_prompt.startswith(rewrite_prompt)
    assert "This earlier rewrite failed:\n\n```python\n" + DROPS_LOCKED + "\n```" in retry_prompt


def test_coverage_that_omits_the_file_is_not_called_nondeterministic(make_repo, fake_llm, capsys):
    repo = make_repo({"app/__init__.py": ""}, {"app/perms.py": NESTED, ".coveragerc": "[run]\nomit = app/perms.py\n"})
    fake_llm.replies += [NO_LINES, fenced(TESTS.format(name="can_edit", call="can_edit"))]

    result = review(capsys, repo)

    assert result["rejected"] == [{"function": "can_edit", "path": "app/perms.py", "kinds": ["nesting"], "reason": "coverage has no data for app/perms.py"}]


def test_cut_off_duplicate_verdict_skips_the_helper_and_the_review_goes_on(make_repo, monkeypatch, capsys):
    from test_duplicates import SLUGIFY, TYPE_ERROR_COPY

    repo = make_repo({"app/__init__.py": "", "app/text.py": SLUGIFY}, {"app/posts.py": TYPE_ERROR_COPY})
    requests = fake_client(monkeypatch, [("length", '{"same_')])

    result = review(capsys, repo)

    assert result == {"suggestions": [], "followup": [], "rejected": [], "notes": []}
    assert len(requests) == 1


def test_prose_tests_reply_retries_once_and_is_rejected_without_a_sandbox_run(make_repo, fake_llm, capsys, trials):
    repo = make_repo({"app/__init__.py": ""}, {"app/perms.py": NESTED})
    prose = "I'm unable to write characterization tests without seeing the function’s helpers."
    fake_llm.replies += [NO_LINES, prose, prose]

    result = review(capsys, repo)

    assert result["rejected"] == [{"function": "can_edit", "path": "app/perms.py", "kinds": ["nesting"], "reason": "tests reply is not python"}]
    assert models(fake_llm) == [LIGHTNING, SUPER, SUPER]
    assert fake_llm.calls[2][1] == fake_llm.calls[1][1] + NOT_PYTHON_RETRY.format(error="no ```python block")
    assert trials == []


def test_block_that_does_not_parse_retries_with_the_syntax_error(make_repo, fake_llm, capsys):
    repo = make_repo({"app/__init__.py": ""}, {"app/perms.py": NESTED})
    fake_llm.replies += [NO_LINES, fenced("can_edit(True, True, False, False]\n"), EDIT_CALLS, fenced(FLAT)]

    result = review(capsys, repo)

    assert result["rejected"] == []
    assert "closing parenthesis ']' does not match opening parenthesis '('" in fake_llm.calls[2][1]
    assert models(fake_llm) == [LIGHTNING, SUPER, SUPER, SUPER]


def test_cannot_test_reply_is_rejected_with_its_reason_and_no_retry(make_repo, fake_llm, capsys, trials):
    repo = make_repo({"app/__init__.py": ""}, {"app/perms.py": NESTED})
    fake_llm.replies += [NO_LINES, "CANNOT_TEST: fixture\n"]

    result = review(capsys, repo)

    assert result["rejected"] == [{"function": "can_edit", "path": "app/perms.py", "kinds": ["nesting"], "reason": "model cannot test: fixture"}]
    assert models(fake_llm) == [LIGHTNING, SUPER]
    assert trials == []




def test_block_of_three_calls_records_three_tests_with_the_argument_text(make_repo, fake_llm, capsys):
    repo = make_repo({"app/__init__.py": ""}, {"app/flags.py": ALL_SET})
    calls = fenced("all_set(True, True, True, True, True, True)\nall_set(True, False, True, True, True, True)\nall_set(\n    0, 1, 1, 1, 1, f=1\n)\n")
    as_bool = fenced("def all_set(a, b, c, d, e, f): return all((a, b, c, d, e, f))\n")
    fake_llm.replies += [ALL_SET_CHECK, calls, as_bool, as_bool]

    [rejected] = review(capsys, repo)["rejected"]

    assert rejected["reason"].startswith("rewrite fails characterization tests")
    assert "FAILED tests/test_slopgate_0.py::test_call_2" in rejected["reason"]
    assert "1 failed, 2 passed" in rejected["reason"]
    assert models(fake_llm) == [LIGHTNING, SUPER, SUPER, ULTRA]


def test_script_reply_is_recorded_as_calls_whatever_values_it_predicts(make_repo, fake_llm, capsys, trials):
    repo = make_repo({"app/__init__.py": ""}, {"app/perms.py": NESTED})
    script = fenced(
        "from app.perms import can_edit\n\n"
        "assert can_edit(True, True, False, False) == 'wrong guess'\n"
        "assert can_edit(False, True, False, False) == 'wrong guess'\n"
        "assert can_edit(True, False, False, False) == 'wrong guess'\n"
        "try:\n    can_edit(True, True, True, False)\nexcept ValueError:\n    pass\n"
        "print(can_edit(True, True, False, True))\n"
    )
    fake_llm.replies += [NO_LINES, script, fenced(FLAT)]

    result = review(capsys, repo)

    [suggestion] = result["suggestions"]
    assert "5 characterization tests passed" in suggestion["body"]
    assert any(RECORDER_PATH in cmd for cmd in trials)


def test_block_with_test_functions_is_used_as_the_test_file(make_repo, fake_llm, capsys, trials):
    repo = make_repo({"app/__init__.py": ""}, {"app/perms.py": NESTED})
    fake_llm.replies += [NO_LINES, fenced(TESTS.format(name="can_edit", call="can_edit")), fenced(FLAT)]

    result = review(capsys, repo)

    [suggestion] = result["suggestions"]
    assert "5 characterization tests passed" in suggestion["body"]
    assert not any(RECORDER_PATH in cmd for cmd in trials)


GRADE_TESTS = '''\
import pytest

from app.grades import grade


def test_pass():
    assert grade(70) == "pass"


def test_fail():
    assert grade(10) == "fail"


@pytest.mark.parametrize("score", [-1, None])
def test_bad_score(score):
    with pytest.raises(ValueError):
        grade(score)
'''

GRADE_CALLS_WITHOUT_NONE = fenced("grade(70)\ngrade(10)\ngrade(-1)\n")


def test_calls_that_miss_a_branch_get_one_retry_for_a_test_file(make_repo, fake_llm, capsys):
    repo = make_repo({"app/__init__.py": ""}, {"app/grades.py": GRADE})
    rewrite = fenced(GRADE_FLAT.format(error="ValueError", noun="score"))
    fake_llm.replies += [NO_LINES, GRADE_CALLS_WITHOUT_NONE, fenced(GRADE_TESTS), rewrite]

    result = review(capsys, repo)

    assert result["rejected"] == []
    [suggestion] = result["suggestions"]
    assert "4 characterization tests passed" in suggestion["body"]
    assert models(fake_llm) == [LIGHTNING, SUPER, SUPER, SUPER]
    assert fake_llm.calls[2][1] == fake_llm.calls[1][1] + MISSED_RETRY.format(missed=1, module="app.grades", name="grade")


def test_calls_that_miss_a_branch_twice_are_rejected_with_the_count(make_repo, fake_llm, capsys):
    repo = make_repo({"app/__init__.py": ""}, {"app/grades.py": GRADE})
    fake_llm.replies += [NO_LINES, GRADE_CALLS_WITHOUT_NONE, GRADE_CALLS_WITHOUT_NONE]

    result = review(capsys, repo)

    assert result["rejected"] == [{"function": "grade", "path": "app/grades.py", "kinds": ["nesting"], "reason": "characterization tests miss branches: 1"}]
    assert models(fake_llm) == [LIGHTNING, SUPER, SUPER]


def test_tests_prompt_says_helpers_and_imports_are_not_needed(make_repo, fake_llm, capsys):
    repo = make_repo({"app/__init__.py": ""}, {"app/perms.py": NESTED})
    fake_llm.replies += [NO_LINES, fenced(TESTS.format(name="can_edit", call="can_edit")), fenced(FLAT)]

    review(capsys, repo)

    assert "The tests run the real code, so you do not need to see helpers or imports." in fake_llm.calls[1][1]


PARSE_SOURCE = "def f(a, b=0):\n    return a\n"


@pytest.mark.parametrize(
    "block, expected",
    [
        ("f (1, 2)", ["1, 2"]),
        ("f(\n    1,\n    b=2,\n)", ["1, b=2"]),
        ("f(*[1, 2], **{'b': 3})", ["*[1, 2], **{'b': 3}"]),
        ("f(1,)", ["1"]),
        ("(f)(1)", ["1"]),
        ("x = 5\nf(x)\nf(2)", ["2"]),
        ("f(f(1))", ["f(1)", "1"]),
    ],
)
def test_parse_tests_reply_takes_argument_text_from_the_call_nodes(block, expected):
    [function] = parse("app/m.py", PARSE_SOURCE)

    reply = parse_tests_reply(f"```python\n{block}\n```", function, True)

    assert reply == Calls(form="calls", calls=expected)


def test_parse_tests_reply_reads_a_def_block_as_a_test_file():
    [function] = parse("app/m.py", PARSE_SOURCE)

    reply = parse_tests_reply("```python\ndef test_a():\n    f(1)\n```", function, True)

    assert reply.form == "test_file"


def test_parse_tests_reply_rejects_a_script_whose_calls_use_script_names():
    [function] = parse("app/m.py", PARSE_SOURCE)

    with pytest.raises(ValueError, match="no call to `f` with plain-value arguments"):
        parse_tests_reply("```python\nx = 5\nf(x)\n```", function, True)
