import json
import subprocess
import sys
import textwrap

import pytest
from test_review import FLAT, IS_NESTING, NESTED, TESTS
from test_wrappers import COMPUTE_TAX, INVOICE_TESTS, INVOICE_TOTAL, TAX_FOR

from slopgate.cli import main
from slopgate.config import ULTRA

SUMMARY = "One function got flatter."
PR_URL = "https://github.com/acme/shop/pull/8"

FAKE_GH = f'''\
#!{sys.executable}
import json, os, sys
args = sys.argv[1:]
with open(os.environ["GH_LOG"], "a") as log:
    log.write(json.dumps({{"args": args, "stdin": sys.stdin.read() if "-" in args else None}}) + "\\n")
if args[:2] == ["pr", "list"]:
    print(os.environ.get("GH_EXISTING_PR", ""))
elif args[:2] == ["pr", "create"] and os.environ.get("GH_CREATE_ERROR"):
    sys.exit(os.environ["GH_CREATE_ERROR"])
elif args[:2] == ["pr", "create"]:
    print("{PR_URL}")
'''


@pytest.fixture
def github(make_repo, tmp_path_factory, monkeypatch):
    tools = tmp_path_factory.mktemp("tools")
    (tools / "gh").write_text(FAKE_GH)
    (tools / "gh").chmod(0o755)
    log = tools / "log.jsonl"
    monkeypatch.setenv("PATH", f"{tools}:{__import__('os').environ['PATH']}")
    monkeypatch.setenv("GH_LOG", str(log))

    def make(base, head, fork=False):
        repo = make_repo(base, head)
        origin = tmp_path_factory.mktemp("origin")
        subprocess.run(["git", "init", "-q", "--bare", str(origin)], check=True)
        subprocess.run(["git", "remote", "add", "origin", str(origin)], cwd=repo, check=True)
        sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo, check=True, capture_output=True, text=True).stdout.strip()
        event = {
            "repository": {"full_name": "acme/shop"},
            "pull_request": {
                "number": 7,
                "head": {"ref": "feature", "sha": sha, "repo": {"full_name": "someone/shop" if fork else "acme/shop"}},
            },
        }
        path = tools / "event.json"
        path.write_text(json.dumps(event))
        monkeypatch.setenv("GITHUB_EVENT_PATH", str(path))
        return repo, origin

    def calls():
        return [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []

    return make, calls


def post(repo):
    assert main(["review", "--repo", repo, "--base", "HEAD~1", "--head", "HEAD", "--sandbox", "local"]) is None


def branch_file(origin, path):
    return subprocess.run(["git", "show", f"slopgate/feature:{path}"], cwd=origin, capture_output=True, text=True).stdout


def test_inline_suggestions_are_posted_as_one_comment_review(github, fake_llm, capsys):
    make, calls = github
    repo, _ = make({"app/__init__.py": ""}, {"app/perms.py": NESTED})
    fake_llm.replies += [IS_NESTING, TESTS.format(name="can_edit", call="can_edit"), FLAT, SUMMARY]

    post(repo)

    [call] = calls()
    assert call["args"] == ["api", "--method", "POST", "repos/acme/shop/pulls/7/reviews", "--input", "-"]
    review = json.loads(call["stdin"])
    assert review["event"] == "COMMENT"
    assert review["commit_id"] == json.load(open(__import__("os").environ["GITHUB_EVENT_PATH"]))["pull_request"]["head"]["sha"]
    [comment] = review["comments"]
    assert "```suggestion\n" + FLAT in comment["body"]
    assert review["body"].startswith(SUMMARY)
    assert "Accepted: 1 inline suggestion, 0 follow-up changes. Rejected: 0." in review["body"]
    # fake usage is 1000 prompt + 100 completion tokens per call: Lightning, Super, Super, Ultra
    assert "Token cost: $0.0022 (4,400 tokens)." in review["body"]
    assert fake_llm.calls[-1][0] == ULTRA


WRAPPER_BASE = {"app/__init__.py": "", "app/billing.py": COMPUTE_TAX}
WRAPPER_HEAD = {"app/billing.py": COMPUTE_TAX + TAX_FOR + INVOICE_TOTAL}


def test_followup_changes_open_one_pull_request_on_the_author_branch(github, fake_llm, capsys):
    make, calls = github
    repo, origin = make(WRAPPER_BASE, WRAPPER_HEAD)
    fake_llm.replies += [INVOICE_TESTS, SUMMARY]

    post(repo)

    assert branch_file(origin, "app/billing.py") == COMPUTE_TAX + INVOICE_TOTAL.replace("tax_for(", "compute_tax(")
    parent = subprocess.run(["git", "rev-parse", "slopgate/feature~1"], cwd=origin, capture_output=True, text=True).stdout.strip()
    assert parent == json.load(open(__import__("os").environ["GITHUB_EVENT_PATH"]))["pull_request"]["head"]["sha"]
    listed, created, commented = calls()
    assert listed["args"][:2] == ["pr", "list"]
    assert created["args"][:2] == ["pr", "create"]
    assert created["args"][created["args"].index("--base") + 1] == "feature"
    assert created["args"][created["args"].index("--head") + 1] == "slopgate/feature"
    assert "`tax_for` only forwards to `compute_tax`" in created["args"][created["args"].index("--body") + 1]
    assert commented["args"][:4] == ["pr", "comment", "7", "--repo"]
    body = commented["args"][commented["args"].index("--body") + 1]
    assert f"Accepted: 0 inline suggestions, 1 follow-up change in {PR_URL}. Rejected: 0." in body


def test_existing_followup_pull_request_is_updated_not_duplicated(github, fake_llm, capsys, monkeypatch):
    make, calls = github
    repo, origin = make(WRAPPER_BASE, WRAPPER_HEAD)
    monkeypatch.setenv("GH_EXISTING_PR", "https://github.com/acme/shop/pull/5")
    subprocess.run(["git", "commit", "-q", "--allow-empty", "-m", "earlier review"], cwd=repo, check=True)
    subprocess.run(["git", "push", "-q", "origin", "HEAD:refs/heads/slopgate/feature"], cwd=repo, check=True)
    subprocess.run(["git", "reset", "-q", "--hard", "HEAD~1"], cwd=repo, check=True)
    fake_llm.replies += [INVOICE_TESTS, SUMMARY]

    post(repo)

    assert [c["args"][:2] for c in calls()] == [["pr", "list"], ["pr", "comment"]]
    assert "1 follow-up change in https://github.com/acme/shop/pull/5" in calls()[-1]["args"][-1]
    assert branch_file(origin, "app/billing.py") == COMPUTE_TAX + INVOICE_TOTAL.replace("tax_for(", "compute_tax(")


def test_fork_pull_request_gets_no_followup_branch(github, fake_llm, capsys):
    make, calls = github
    repo, origin = make(WRAPPER_BASE, WRAPPER_HEAD, fork=True)
    fake_llm.replies += [INVOICE_TESTS, SUMMARY]

    post(repo)

    [commented] = calls()
    assert commented["args"][:2] == ["pr", "comment"]
    assert "1 follow-up change not opened: the pull request comes from a fork." in commented["args"][-1]
    assert branch_file(origin, "app/billing.py") == ""


def test_no_findings_post_nothing(github, fake_llm, capsys):
    make, calls = github
    repo, _ = make({"app/perms.py": NESTED, "README.md": "# Demo\n"}, {"README.md": "# Demo\n\nMore.\n"})

    post(repo)

    assert calls() == []
    assert fake_llm.calls == []


def test_install_failure_posts_one_notice_without_a_summary_call(github, fake_llm, capsys):
    make, calls = github
    repo, _ = make({"app/__init__.py": ""}, {"app/perms.py": NESTED, ".slopgate.toml": "[sandbox]\nsetup = 'echo broken; exit 1'\n"})
    fake_llm.replies += [IS_NESTING]

    post(repo)

    [commented] = calls()
    assert commented["args"][:2] == ["pr", "comment"]
    assert commented["args"][-1] == "Slopgate could not build the test environment, so it proved nothing.\n\n```\nbroken\n```"
    assert [model for model, _ in fake_llm.calls] != [] and ULTRA not in [model for model, _ in fake_llm.calls]


def test_rejections_are_listed_under_the_summary(github, fake_llm, capsys):
    make, calls = github
    repo, _ = make({"app/__init__.py": ""}, {"app/perms.py": NESTED})
    weak = TESTS.format(name="can_edit", call="can_edit").replace(
        "def test_locked_cannot_edit():\n    assert can_edit(True, True, True, False) is False\n", ""
    )
    fake_llm.replies += [IS_NESTING, weak, SUMMARY]

    post(repo)

    body = calls()[0]["args"][-1]
    assert "Accepted: 0 inline suggestions, 0 follow-up changes. Rejected: 1." in body
    assert "- `can_edit` in app/perms.py: characterization tests miss branches: 1" in body


def test_summary_failure_still_posts_the_results(github, fake_llm, capsys):
    make, calls = github
    repo, _ = make({"app/__init__.py": ""}, {"app/perms.py": NESTED})
    fake_llm.replies += [IS_NESTING, TESTS.format(name="can_edit", call="can_edit"), FLAT]

    post(repo)

    [call] = calls()
    review = json.loads(call["stdin"])
    assert len(review["comments"]) == 1
    assert review["body"].startswith("Accepted: 1 inline suggestion")


FEE_FOR = '''

def fee_for(amount, rate):
    return compute_tax(amount, rate)


def fee_total(amount):
    return amount + fee_for(amount, 0.1)
'''


def test_followups_that_edit_the_same_file_open_only_the_first(github, fake_llm, capsys):
    make, calls = github
    repo, origin = make(WRAPPER_BASE, {"app/billing.py": COMPUTE_TAX + TAX_FOR + INVOICE_TOTAL + FEE_FOR})
    fee_tests = "from app.billing import fee_total\n\n\ndef test_fee():\n    assert fee_total(100) == 110.0\n"
    fake_llm.replies += ['{"same_job": false}', INVOICE_TESTS, fee_tests, SUMMARY]

    post(repo)

    assert "def tax_for" not in branch_file(origin, "app/billing.py")
    assert "def fee_for" in branch_file(origin, "app/billing.py")
    body = calls()[-1]["args"][-1]
    assert f"1 follow-up change in {PR_URL} (1 skipped: it edits a file that an earlier follow-up edits)" in body


def test_followup_pull_request_failure_still_posts_the_review(github, fake_llm, capsys, monkeypatch):
    make, calls = github
    repo, origin = make(WRAPPER_BASE, {"app/billing.py": COMPUTE_TAX + TAX_FOR + INVOICE_TOTAL, "app/perms.py": NESTED})
    monkeypatch.setenv("GH_CREATE_ERROR", "GitHub Actions is not permitted to create or approve pull requests")
    fake_llm.replies += [IS_NESTING, INVOICE_TESTS, TESTS.format(name="can_edit", call="can_edit"), FLAT, SUMMARY]

    post(repo)

    assert capsys.readouterr().err == ""
    review = json.loads(calls()[-1]["stdin"])
    assert len(review["comments"]) == 1
    assert (
        "1 follow-up change not opened as a pull request (gh pr create failed: GitHub Actions is not permitted to create or approve pull requests); "
        "the changes are on https://github.com/acme/shop/compare/feature...slopgate/feature" in review["body"]
    )
    assert branch_file(origin, "app/billing.py")


def test_followup_push_failure_still_posts_the_review(github, fake_llm, capsys):
    make, calls = github
    repo, _ = make(WRAPPER_BASE, WRAPPER_HEAD)
    subprocess.run(["git", "remote", "set-url", "origin", "/nonexistent/origin.git"], cwd=repo, check=True)
    fake_llm.replies += [INVOICE_TESTS, SUMMARY]

    post(repo)

    [commented] = calls()
    assert commented["args"][:2] == ["pr", "comment"]
    assert "1 follow-up change not pushed (git push --force failed: " in commented["args"][-1]
    assert "compare" not in commented["args"][-1]
