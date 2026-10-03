import json
import re
import textwrap

from slopgate.cli import main

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

VIEW = NESTED.replace("can_edit", "can_view")
FLAT_VIEW = FLAT.replace("can_edit", "can_view")


def review(capsys, repo, sandbox="local"):
    assert main(["review", "--repo", repo, "--base", "HEAD~1", "--head", "HEAD", "--dry-run", "--sandbox", sandbox]) is None
    out, err = capsys.readouterr()
    assert err == ""
    return json.loads(out)


def suggested_code(body):
    return re.search(r"```suggestion\n(.*?)```", body, re.S)[1]


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
    assert len(fake_llm.calls) == 2
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
        TESTS.format(name="Policy", call="Policy.can_edit"),
        "@staticmethod\n" + FLAT,
    ]

    [suggestion] = review(capsys, repo)["suggestions"]

    assert "Policy.can_edit" in suggestion["body"]
    assert suggestion["start_line"] == 4
    assert suggestion["line"] == 18
    assert suggested_code(suggestion["body"]) == textwrap.indent("@staticmethod\n" + FLAT, "    ")


def test_one_line_function_flagged_by_complexity_has_no_start_line(make_repo, fake_llm, capsys):
    repo = make_repo(
        {"app/__init__.py": ""},
        {"app/flags.py": "def all_set(a, b, c, d, e, f): return a and b and c and d and e and f\n"},
    )
    fake_llm.replies += [
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
    fake_llm.replies += [
        TESTS.format(name="can_edit", call="can_edit"),
        "def can_edit(user_active, is_owner, locked, archived):\n    return user_active and is_owner and not archived\n",
    ]

    result = review(capsys, repo)

    assert result["suggestions"] == [] and result["followup"] == []
    [rejected] = result["rejected"]
    assert (rejected["function"], rejected["path"]) == ("can_edit", "app/perms.py")
    assert rejected["reason"].startswith("rewrite fails characterization tests")
    assert "test_locked_cannot_edit" in rejected["reason"]


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
    fake_llm.replies += [
        TESTS.format(name="can_edit", call="can_edit"),
        "def can_edit(:\n    return\n",
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
    fake_llm.replies += [TESTS.format(name="can_edit", call="can_edit"), FLAT]

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
    fake_llm.replies += [TESTS.format(name="can_edit", call="can_edit"), FLAT]

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
    }
    assert fake_llm.calls == []
