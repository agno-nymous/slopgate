import json
import os
import re
import subprocess
import tempfile
from time import sleep

from slopgate import llm, trace
from slopgate.config import PRICES, ULTRA

SUMMARY_PROMPT = """Write a summary of at most two sentences for the author of a pull request. Slopgate reviewed the pull request and proved each accepted rewrite with characterization tests in a sandbox. Use plain words, no headings, no lists.

Results:

{results}"""


def run(*args, stdin=None, **options) -> str:
    done = subprocess.run(args, input=stdin, capture_output=True, text=True, **options)
    if done.returncode:
        raise RuntimeError(f"{' '.join(args[:3])} failed: {done.stderr.strip()}")
    return done.stdout.strip()


def gh(*args, stdin=None) -> str:
    for attempt in range(3):
        try:
            return run("gh", *args, stdin=stdin)
        except RuntimeError as error:
            if attempt == 2 or not re.search(r"HTTP 5\d\d", str(error)):
                raise
            sleep(10 * (attempt + 1))


def duration(seconds: float) -> str:
    minutes, rest = divmod(round(seconds), 60)
    return f"{minutes} min {rest} s" if minutes else f"{rest} s"


def plural(n: int, word: str) -> str:
    return f"{n} {word}" + ("" if n == 1 else "s")


def cost() -> str:
    dollars = sum(PRICES[model][0] * sent + PRICES[model][1] * received for model, sent, received in llm.usage) / 1e6
    tokens = sum(sent + received for _, sent, received in llm.usage)
    return f"Token cost: ${dollars:.4f} ({tokens:,} tokens)."


def open_followup(repo, followups, pr, target, files) -> str:
    branch = f"slopgate/{pr['head']['ref']}"
    author = {"GIT_AUTHOR_NAME": "slopgate", "GIT_AUTHOR_EMAIL": "slopgate@users.noreply.github.com"}
    with tempfile.TemporaryDirectory() as tmp:
        env = {**os.environ, **author, "GIT_COMMITTER_NAME": "slopgate", "GIT_COMMITTER_EMAIL": author["GIT_AUTHOR_EMAIL"], "GIT_INDEX_FILE": f"{tmp}/index"}

        def git(*args, stdin=None):
            return run("git", *args, stdin=stdin, cwd=repo, env=env)

        git("read-tree", pr["head"]["sha"])
        for path, text in files.items():
            git("update-index", "--add", "--cacheinfo", f"100644,{git('hash-object', '-w', '--stdin', stdin=text)},{path}")
        commit = git("commit-tree", git("write-tree"), "-p", pr["head"]["sha"], "-m", "refactor: apply Slopgate follow-up changes")
        # the branch belongs to Slopgate; each review replaces it with a commit on the current head
        git("push", "--force", "origin", f"{commit}:refs/heads/{branch}")
    body = "\n\n".join(f"**{f['kind']}**: {f['reason']}" for f in followups)
    try:
        url = gh("pr", "list", "--repo", target, "--head", branch, "--state", "open", "--json", "url", "--jq", ".[0].url") or gh(
            "pr", "create", "--repo", target, "--base", pr["head"]["ref"], "--head", branch,
            "--title", f"Slopgate follow-up for #{pr['number']}", "--body", body,
        )
    except RuntimeError as error:
        return f"not opened as a pull request ({error}); the changes are on https://github.com/{target}/compare/{pr['head']['ref']}...{branch}"
    return f"in {url}"


def summary(result, followup_line, seconds) -> str:
    try:
        with trace.span("gate.summary", prompt="SUMMARY_PROMPT"):
            text = llm.complete(ULTRA, SUMMARY_PROMPT.format(results=json.dumps(result, indent=1)[:20000])).strip() + "\n\n"
    except Exception:
        text = ""
    rejected = result["rejected"]
    lines = [
        f"Accepted: {plural(len(result['suggestions']), 'inline suggestion')}, {followup_line}. Rejected: {len(rejected)}."
        + (f" Notes on test files: {len(result['notes'])}." if result["notes"] else ""),
        f"{cost()} Time: {duration(seconds)}.",
    ]
    if rejected:
        reasons = "\n".join(f"- `{r['function']}` in {r['path']}: {r['reason']}" for r in rejected)
        lines.append(f"<details><summary>Rejected</summary>\n\n{reasons}\n\n</details>")
    return text + "\n\n".join(lines)


def pull_request(repo, number) -> dict:
    target = run("gh", "repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner", cwd=repo)
    pr = json.loads(gh("api", f"repos/{target}/pulls/{number}"))
    run("git", "fetch", "-q", "origin", pr["base"]["sha"], f"pull/{number}/head", cwd=repo)
    return {"pull_request": pr, "repository": {"full_name": target}}


def publish(repo, result, event, seconds) -> None:
    if not any(result.values()):
        return
    pr, target = event["pull_request"], event["repository"]["full_name"]
    number = str(pr["number"])
    notice = next((r["reason"] for r in result["rejected"] if "function" not in r), None)
    if notice:
        output = notice.split("\n", 1)[1]
        body = f"Slopgate could not build the test environment, so it proved nothing.\n\n```\n{output}\n```"
    else:
        followups = result["followup"]
        if not followups:
            followup_line = "0 follow-up changes"
        elif pr["head"]["repo"]["full_name"] != target:
            followup_line = f"{plural(len(followups), 'follow-up change')} not opened: the pull request comes from a fork"
        else:
            # each follow-up holds whole files proven against head on their own, so two that edit one file cannot both apply
            kept, files = [], {}
            for followup in followups:
                if not files.keys() & followup["files"].keys():
                    kept.append(followup)
                    files |= followup["files"]
            try:
                where = open_followup(repo, kept, pr, target, files)
            except RuntimeError as error:
                where = f"not pushed ({error})"
            followup_line = f"{plural(len(kept), 'follow-up change')} {where}"
            if len(kept) < len(followups):
                followup_line += f" ({len(followups) - len(kept)} skipped: it edits a file that an earlier follow-up edits)"
        body = summary(result, followup_line, seconds)
    comments = result["suggestions"] + [{"path": n["path"], "line": n["line"], "side": "RIGHT", "body": n["body"]} for n in result["notes"]]
    if comments:
        review = {"commit_id": pr["head"]["sha"], "event": "COMMENT", "body": body, "comments": comments}
        gh("api", "--method", "POST", f"repos/{target}/pulls/{number}/reviews", "--input", "-", stdin=json.dumps(review))
    else:
        gh("pr", "comment", number, "--repo", target, "--body", body)
