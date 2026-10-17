import json
import re
import subprocess
import sys

import pytest
from test_duplicates import OTHER_JOB
from test_review import DROPS_LOCKED, FLAT, NESTED, TESTS, fenced
from test_wrappers import COMPUTE_TAX, INVOICE_TESTS, INVOICE_TOTAL, TAX_FOR

from slopgate.cli import main
from slopgate.github import duration
from slopgate.config import ULTRA
from slopgate.kinds import KINDS
from slopgate.review import REJECTED

SUMMARY = "One function got flatter."
PR_URL = "https://github.com/acme/shop/pull/8"

FAKE_GH = f'''\
#!{sys.executable}
import json, os, sys
args = sys.argv[1:]
with open(os.environ["GH_LOG"], "a") as log:
    log.write(json.dumps({{"args": args, "stdin": sys.stdin.read() if "-" in args else None}}) + "\\n")
outages = os.environ.get("GH_OUTAGES")
left = int(open(outages).read()) if outages else 0
if left:
    open(outages, "w").write(str(left - 1))
    sys.exit("HTTP 503: No server is currently available to service your request.")
if args[:2] == ["pr", "list"]:
    print(os.environ.get("GH_EXISTING_PR", ""))
elif args[:2] == ["repo", "view"]:
    print("acme/shop")
elif args[0] == "api" and args[1].endswith("/comments"):
    print(os.environ.get("GH_COMMENTS", ""))
elif args[0] == "api" and "--method" not in args:
    print(open(os.environ["GH_PR"]).read())
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
    fake_llm.replies += [fenced(TESTS.format(name="can_edit", call="can_edit")), fenced(FLAT), SUMMARY]

    post(repo)

    read, call = calls()
    assert read["args"][:2] == ["api", "repos/acme/shop/pulls/7/comments"]
    assert call["args"] == ["api", "--method", "POST", "repos/acme/shop/pulls/7/reviews", "--input", "-"]
    review = json.loads(call["stdin"])
    assert review["event"] == "COMMENT"
    assert review["commit_id"] == json.load(open(__import__("os").environ["GITHUB_EVENT_PATH"]))["pull_request"]["head"]["sha"]
    [comment] = review["comments"]
    assert "```suggestion\n" + FLAT in comment["body"]
    assert review["body"].startswith(SUMMARY)
    assert "Accepted: 1 inline suggestion, 0 follow-up changes." in review["body"]
    # fake usage is 1000 prompt + 100 completion tokens per call: Super twice (agent), Super (rewrite), Ultra
    assert re.search(r"Token cost: \$0\.0025 \(4,400 tokens\)\. Time: \d+ s\.", review["body"])
    assert fake_llm.calls[-1][0] == ULTRA


def test_pr_flag_fetches_the_pull_request_reviews_it_and_posts_to_it(github, fake_llm, capsys, monkeypatch, tmp_path_factory):
    make, calls = github
    repo, origin = make({"app/__init__.py": ""}, {"app/perms.py": NESTED})

    def git(*args, cwd=repo):
        return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()

    base, head = git("rev-parse", "HEAD~1"), git("rev-parse", "HEAD")
    git("push", "-q", "origin", f"{base}:refs/heads/main", f"{head}:refs/pull/7/head")
    clone = str(tmp_path_factory.mktemp("clone"))
    git("clone", "-q", "--no-local", str(origin), clone, cwd=None)
    pr = json.load(open(__import__("os").environ["GITHUB_EVENT_PATH"]))["pull_request"] | {"base": {"sha": base}}
    pr_file = tmp_path_factory.mktemp("pr") / "pr.json"
    pr_file.write_text(json.dumps(pr))
    monkeypatch.setenv("GH_PR", str(pr_file))
    monkeypatch.delenv("GITHUB_EVENT_PATH")
    fake_llm.replies += [fenced(TESTS.format(name="can_edit", call="can_edit")), fenced(FLAT), SUMMARY]

    assert main(["review", "--repo", clone, "--pr", "7", "--sandbox", "local"]) is None

    viewed, read, _, posted = calls()
    assert viewed["args"][:2] == ["repo", "view"]
    assert read["args"] == ["api", "repos/acme/shop/pulls/7"]
    assert posted["args"] == ["api", "--method", "POST", "repos/acme/shop/pulls/7/reviews", "--input", "-"]
    review = json.loads(posted["stdin"])
    assert review["commit_id"] == head
    assert "```suggestion\n" + FLAT in review["comments"][0]["body"]


def test_review_needs_pr_or_base_and_head(capsys):
    with pytest.raises(SystemExit):
        main(["review", "--base", "HEAD~1"])
    assert "give --pr, or both --base and --head" in capsys.readouterr().err


WRAPPER_BASE = {"app/__init__.py": "", "app/billing.py": COMPUTE_TAX}
WRAPPER_HEAD = {"app/billing.py": COMPUTE_TAX + TAX_FOR + INVOICE_TOTAL}


def test_followup_changes_open_one_pull_request_on_the_author_branch(github, fake_llm, capsys):
    make, calls = github
    repo, origin = make(WRAPPER_BASE, WRAPPER_HEAD)
    fake_llm.replies += [OTHER_JOB, fenced(INVOICE_TESTS), SUMMARY]

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
    assert f"Accepted: 0 inline suggestions, 1 follow-up change in {PR_URL}." in body


def test_existing_followup_pull_request_is_updated_not_duplicated(github, fake_llm, capsys, monkeypatch):
    make, calls = github
    repo, origin = make(WRAPPER_BASE, WRAPPER_HEAD)
    monkeypatch.setenv("GH_EXISTING_PR", "https://github.com/acme/shop/pull/5")
    subprocess.run(["git", "commit", "-q", "--allow-empty", "-m", "earlier review"], cwd=repo, check=True)
    subprocess.run(["git", "push", "-q", "origin", "HEAD:refs/heads/slopgate/feature"], cwd=repo, check=True)
    subprocess.run(["git", "reset", "-q", "--hard", "HEAD~1"], cwd=repo, check=True)
    fake_llm.replies += [OTHER_JOB, fenced(INVOICE_TESTS), SUMMARY]

    post(repo)

    assert [c["args"][:2] for c in calls()] == [["pr", "list"], ["pr", "comment"]]
    assert "1 follow-up change in https://github.com/acme/shop/pull/5" in calls()[-1]["args"][-1]
    assert branch_file(origin, "app/billing.py") == COMPUTE_TAX + INVOICE_TOTAL.replace("tax_for(", "compute_tax(")


def test_fork_pull_request_gets_no_followup_branch(github, fake_llm, capsys):
    make, calls = github
    repo, origin = make(WRAPPER_BASE, WRAPPER_HEAD, fork=True)
    fake_llm.replies += [OTHER_JOB, fenced(INVOICE_TESTS), SUMMARY]

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


def test_note_on_a_test_file_is_posted_as_a_review_comment_without_a_suggestion(github, fake_llm, capsys):
    make, calls = github
    repo, _ = make({"app/__init__.py": ""}, {"tests/conftest.py": NESTED})
    fake_llm.replies += [SUMMARY]

    post(repo)

    _, call = calls()
    assert call["args"] == ["api", "--method", "POST", "repos/acme/shop/pulls/7/reviews", "--input", "-"]
    review = json.loads(call["stdin"])
    assert "Accepted: 0 inline suggestions, 0 follow-up changes. Notes: 1." in review["body"]
    [comment] = review["comments"]
    body = f"**nesting** (not rewritten): `can_edit`: {KINDS['nesting']} Slopgate does not change test files."
    assert comment == {"path": "tests/conftest.py", "line": 14, "side": "RIGHT", "body": body}


def test_comment_that_already_exists_on_the_pull_request_is_not_posted_again(github, fake_llm, capsys, monkeypatch):
    make, calls = github
    repo, _ = make({"app/__init__.py": ""}, {"tests/conftest.py": NESTED, "tests/test_perms.py": NESTED.replace("can_edit", "check_edit")})
    first_line = f"**nesting** (not rewritten): `can_edit`: {KINDS['nesting']} Slopgate does not change test files."
    monkeypatch.setenv("GH_COMMENTS", json.dumps(["tests/conftest.py", first_line]) + "\n" + json.dumps(["tests/other.py", "**dead**"]))
    fake_llm.replies += [SUMMARY]

    post(repo)

    read, call = calls()
    assert read["args"] == ["api", "repos/acme/shop/pulls/7/comments", "--paginate", "--jq", '.[] | [.path, (.body | split("\\n")[0])] | @json']
    [comment] = json.loads(call["stdin"])["comments"]
    assert comment["path"] == "tests/test_perms.py"


def test_review_with_only_existing_comments_posts_the_summary_alone(github, fake_llm, capsys, monkeypatch):
    make, calls = github
    repo, _ = make({"app/__init__.py": ""}, {"tests/conftest.py": NESTED})
    first_line = f"**nesting** (not rewritten): `can_edit`: {KINDS['nesting']} Slopgate does not change test files."
    monkeypatch.setenv("GH_COMMENTS", json.dumps(["tests/conftest.py", first_line]))
    fake_llm.replies += [SUMMARY]

    post(repo)

    _, commented = calls()
    assert commented["args"][:2] == ["pr", "comment"]
    assert "Notes: 1." in commented["args"][-1]


def test_suggestion_with_a_new_pass_count_is_not_posted_again(github, fake_llm, capsys, monkeypatch):
    make, calls = github
    repo, _ = make({"app/__init__.py": ""}, {"app/perms.py": NESTED})
    tests = TESTS.format(name="can_edit", call="can_edit")
    fake_llm.replies += [fenced(tests), fenced(FLAT), SUMMARY]
    post(repo)
    [first] = json.loads(calls()[-1]["stdin"])["comments"]
    first_line, second_line = first["body"].split("\n")[:2]
    assert first_line == "Slopgate (`nesting`) rewrite of `can_edit`."
    assert "5 characterization tests passed" in second_line

    monkeypatch.setenv("GH_COMMENTS", json.dumps([first["path"], first_line]))
    more_tests = tests + "\n\ndef test_owner_can_edit_again():\n    assert can_edit(True, True, False, False) is True\n"
    fake_llm.replies += [fenced(more_tests), fenced(FLAT), SUMMARY]
    post(repo)

    commented = calls()[-1]
    assert commented["args"][:2] == ["pr", "comment"]
    assert "Accepted: 1 inline suggestion" in commented["args"][-1]


def test_install_failure_posts_one_notice_and_a_note_per_candidate_without_a_summary_call(github, fake_llm, capsys):
    make, calls = github
    repo, _ = make(
        {"app/__init__.py": ""},
        {"app/perms.py": NESTED, "app/views.py": NESTED.replace("can_edit", "can_view"), ".slopgate.toml": "[sandbox]\nsetup = 'echo broken; exit 1'\n"},
    )

    post(repo)

    _, call = calls()
    review = json.loads(call["stdin"])
    assert review["body"] == "Slopgate could not build the test environment, so it proved nothing.\n\n```\nbroken\n```"
    why = "Slopgate could not build the test environment, so it could not prove a rewrite and changed nothing."
    assert review["comments"] == [
        {"path": "app/perms.py", "line": 14, "side": "RIGHT", "body": f"**nesting** (not rewritten): `can_edit`: {KINDS['nesting']} {why}"},
        {"path": "app/views.py", "line": 14, "side": "RIGHT", "body": f"**nesting** (not rewritten): `can_view`: {KINDS['nesting']} {why}"},
    ]
    assert fake_llm.calls == []


def test_install_failure_still_posts_the_notes_as_a_review(github, fake_llm, capsys):
    make, calls = github
    repo, _ = make({"app/__init__.py": ""}, {"app/perms.py": NESTED, "tests/conftest.py": NESTED, ".slopgate.toml": "[sandbox]\nsetup = 'echo broken; exit 1'\n"})

    post(repo)

    _, call = calls()
    assert call["args"] == ["api", "--method", "POST", "repos/acme/shop/pulls/7/reviews", "--input", "-"]
    review = json.loads(call["stdin"])
    assert review["body"] == "Slopgate could not build the test environment, so it proved nothing.\n\n```\nbroken\n```"
    assert [c["path"] for c in review["comments"]] == ["tests/conftest.py", "app/perms.py"]
    assert ULTRA not in [model for model, _ in fake_llm.calls]


def test_rejections_show_only_the_inline_note(github, fake_llm, capsys):
    make, calls = github
    repo, _ = make({"app/__init__.py": ""}, {"app/perms.py": NESTED})
    fake_llm.replies += [fenced(TESTS.format(name="can_edit", call="can_edit")), fenced(DROPS_LOCKED), fenced(DROPS_LOCKED), SUMMARY]

    post(repo)

    _, call = calls()
    review = json.loads(call["stdin"])
    assert "Accepted: 0 inline suggestions, 0 follow-up changes. Notes: 1." in review["body"]
    assert "Rejected" not in review["body"]
    assert "test_locked_cannot_edit" not in call["stdin"] and "```" not in review["body"]
    model, summary_prompt = fake_llm.calls[-1]
    assert model == ULTRA and summary_prompt.startswith("Write a summary")
    assert "test_locked_cannot_edit" not in summary_prompt and "can_edit" in summary_prompt
    [comment] = review["comments"]
    assert (comment["path"], comment["line"]) == ("app/perms.py", 14)
    assert comment["body"] == f"**nesting** (not rewritten): `can_edit`: {KINDS['nesting']} {REJECTED}"


def test_summary_failure_still_posts_the_results(github, fake_llm, capsys):
    make, calls = github
    repo, _ = make({"app/__init__.py": ""}, {"app/perms.py": NESTED})
    fake_llm.replies += [fenced(TESTS.format(name="can_edit", call="can_edit")), fenced(FLAT)]

    post(repo)

    _, call = calls()
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
    fake_llm.replies += [OTHER_JOB, OTHER_JOB, fenced(INVOICE_TESTS), fenced(fee_tests), SUMMARY]

    post(repo)

    assert "def tax_for" not in branch_file(origin, "app/billing.py")
    assert "def fee_for" in branch_file(origin, "app/billing.py")
    body = calls()[-1]["args"][-1]
    assert f"1 follow-up change in {PR_URL} (1 skipped: it edits a file that an earlier follow-up edits)" in body


def test_followup_pull_request_failure_still_posts_the_review(github, fake_llm, capsys, monkeypatch):
    make, calls = github
    repo, origin = make(WRAPPER_BASE, {"app/billing.py": COMPUTE_TAX + TAX_FOR + INVOICE_TOTAL, "app/perms.py": NESTED})
    monkeypatch.setenv("GH_CREATE_ERROR", "GitHub Actions is not permitted to create or approve pull requests")
    fake_llm.replies += [OTHER_JOB, fenced(INVOICE_TESTS), fenced(TESTS.format(name="can_edit", call="can_edit")), fenced(FLAT), SUMMARY]

    post(repo)

    assert capsys.readouterr().err == ""
    assert [c["args"][:2] for c in calls()].count(["pr", "create"]) == 1
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
    fake_llm.replies += [OTHER_JOB, fenced(INVOICE_TESTS), SUMMARY]

    post(repo)

    [commented] = calls()
    assert commented["args"][:2] == ["pr", "comment"]
    assert "1 follow-up change not pushed (git push --force failed: " in commented["args"][-1]
    assert "compare" not in commented["args"][-1]


@pytest.fixture
def outages(tmp_path, monkeypatch):
    def set_count(n):
        counter = tmp_path / "outages"
        counter.write_text(str(n))
        monkeypatch.setenv("GH_OUTAGES", str(counter))

    sleeps = []
    monkeypatch.setattr("slopgate.github.sleep", sleeps.append)
    return set_count, sleeps


def test_github_server_errors_are_retried(github, fake_llm, capsys, outages):
    make, calls = github
    set_count, sleeps = outages
    repo, _ = make({"app/__init__.py": ""}, {"app/perms.py": NESTED})
    set_count(2)
    fake_llm.replies += [fenced(TESTS.format(name="can_edit", call="can_edit")), fenced(FLAT), SUMMARY]

    post(repo)

    assert capsys.readouterr().err == ""
    assert len(calls()) == 4
    assert json.loads(calls()[-1]["stdin"])["event"] == "COMMENT"
    assert len(sleeps) == 2


def test_github_server_errors_give_up_after_three_tries(github, fake_llm, capsys, outages):
    make, calls = github
    set_count, _ = outages
    repo, _ = make({"app/__init__.py": ""}, {"app/perms.py": NESTED})
    set_count(3)
    fake_llm.replies += [fenced(TESTS.format(name="can_edit", call="can_edit")), fenced(FLAT), SUMMARY]

    with pytest.raises(SystemExit) as exit:
        post(repo)

    assert exit.value.code == 1
    assert "HTTP 503" in capsys.readouterr().err
    assert len(calls()) == 3


@pytest.mark.parametrize(("seconds", "text"), [(42.4, "42 s"), (103.2, "1 min 43 s"), (3600, "60 min 0 s")])
def test_review_time_reads_in_minutes_and_seconds(seconds, text):
    assert duration(seconds) == text
