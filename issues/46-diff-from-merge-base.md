# 46 — Find the changed functions from the merge-base, not from the base tip

## Summary

- **Goal:** The gate finds the changed functions with the same diff that GitHub shows for the pull request. It uses the merge-base of the base and the head.
- **Checkable finish condition:** A test makes a repo where the base branch gets a commit after the pull request branch starts. The gate then finds only the functions that the pull request changes. Each inline comment is on a line of the pull request diff. `uv run pytest -q` passes.
- **Evidence:** Found by the code review of ticket 34 on 2026-10-10, from the code only. Not reproduced on GitHub yet.
- **Constraints:** Do not change the `--base` and `--head` options of `slopgate review`.

**Blocked by:** None — can start immediately.

**Status:** ready-for-agent

## Context

`changed_functions` in `slopgate/diff.py` runs `git diff --unified=0 --diff-filter=AM <base> <head>`. This is a two-dot diff. The workflow and `slopgate review --pr` give `pull_request.base.sha` as the base. That is the tip of the base branch, not the point where the pull request branch starts.

When `main` gets a commit after the pull request branch starts, the two-dot diff also shows the lines of that commit (in reverse). The gate then treats functions that the pull request did not change as changed functions.

GitHub builds the pull request diff from the merge-base. An inline review comment must be on a line of that diff. A comment on another line makes GitHub reject the whole review with HTTP 422, with the valid suggestions. `gh()` does not retry a 4xx error, and the review is lost.

Ticket 34 makes this more frequent: each function with slop and no rewrite now gets an inline note. Before ticket 34, only accepted suggestions were inline comments.

## Design

1. In `changed_functions`, diff from the merge-base: `git diff ... <base>...<head>` (three dots).
2. Check whether `index.build(repo, base)` in `slopgate/review.py` must also use the merge-base. The duplicate search uses the base index as the known functions.

## Acceptance

- [ ] A test with a base branch that moved ahead finds only the functions of the pull request.
- [ ] The inline comments of that test are on lines of the merge-base diff.
- [ ] `uv run pytest -q` passes.

## Comments
