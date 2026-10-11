# 46 — Find the changed functions from the merge-base, not from the base tip

## Summary

- **Goal:** The gate finds the changed functions with the same diff that GitHub shows for the pull request. It uses the merge-base of the base and the head.
- **Checkable finish condition:** A test makes a repo where the base branch gets a commit after the pull request branch starts. The gate then finds only the functions that the pull request changes. Each inline comment is on a line of the pull request diff. `uv run pytest -q` passes.
- **Evidence:** Found by the code review of ticket 34 on 2026-10-10, from the code only. Not reproduced on GitHub yet.
- **Constraints:** Do not change the `--base` and `--head` options of `slopgate review`.

**Blocked by:** None — can start immediately.

**Status:** done

## Context

`changed_functions` in `slopgate/diff.py` runs `git diff --unified=0 --diff-filter=AM <base> <head>`. This is a two-dot diff. The workflow and `slopgate review --pr` give `pull_request.base.sha` as the base. That is the tip of the base branch, not the point where the pull request branch starts.

When `main` gets a commit after the pull request branch starts, the two-dot diff also shows the lines of that commit (in reverse). The gate then treats functions that the pull request did not change as changed functions.

GitHub builds the pull request diff from the merge-base. An inline review comment must be on a line of that diff. A comment on another line makes GitHub reject the whole review with HTTP 422, with the valid suggestions. `gh()` does not retry a 4xx error, and the review is lost.

Ticket 34 makes this more frequent: each function with slop and no rewrite now gets an inline note. Before ticket 34, only accepted suggestions were inline comments.

## Design

1. In `changed_functions`, diff from the merge-base: `git diff ... <base>...<head>` (three dots).
2. Check whether `index.build(repo, base)` in `slopgate/review.py` must also use the merge-base. The duplicate search uses the base index as the known functions.
   Decision (2026-10-11): yes. A function is new when it is not in the code at the merge-base. The duplicate pool must not hold base-tip versions of functions that the pull request head does not have.
3. Change made after the code review: `review()` finds the merge-base once with `git merge-base`. It gives the merge-base to `changed_functions` and to `index.build`, so both steps use the same commit. `changed_functions` keeps its two-dot diff. Its `base` argument is now the commit where the pull request starts. With no merge-base (no common history, or a shallow clone), `review()` stops with a clear `RuntimeError`.

## Acceptance

- [x] A test with a base branch that moved ahead finds only the functions of the pull request.
- [x] The inline comments of that test are on lines of the merge-base diff.
- [x] `uv run pytest -q` passes.

## Comments

### 2026-10-11: done

**What was built.** `review()` in `slopgate/review.py` finds the merge-base of the base and the head. The gate finds the changed functions from the merge-base, and it builds the base index at the merge-base. This is the same diff that GitHub shows for the pull request. The trace input of `gate.review` now shows `base...head`.

**Worked example (test).** `test_base_branch_moved_ahead_finds_only_pull_request_functions` makes this history:

- At the merge-base, `tests/test_old.py` has the nested `can_edit` and the flat `can_view`.
- The pull request makes `can_view` nested. It adds `tests/test_new.py` with `can_new`, a copy of `can_edit`.
- `main` then gets a commit. It flattens `can_edit` and adds a flat `can_new`.

The gate gives these notes:

```
[("tests/test_new.py", "can_new", ["duplicate"], 14),
 ("tests/test_old.py", "can_view", ["nesting"], 30)]
```

Both lines are in the pull request diff. With the old base-tip diff, the test fails: the kind of `can_new` becomes `nesting` instead of `duplicate`, and `can_edit` gets a note too.

**Worked example (this repo).** Base `origin/main` (`8a6eb90`), head `af0d654` (an older commit that is already in `main`):

- The two-dot diff has 28 hunks. They are the changes of `main`, in reverse. The old gate treated them as changed functions.
- The three-dot diff has 0 hunks.
- `slopgate review --dry-run` gives an empty result, with no model call and no sandbox run.

**Measured results.**

- `uv run pytest -q`: 300 passed, 17 deselected.
- Mutation checks: with `changed_functions` from the base tip, or with `index.build` at the base tip, the new test fails on an assertion.
- `test_review_without_a_merge_base_names_the_cause`: an orphan head gives a `RuntimeError` that names the merge-base.

**Known limits.**

- Not reproduced on GitHub. The Slopgate workflow is still disabled.
- With more than one merge-base (criss-cross history), `git merge-base` picks one. GitHub can pick another one.
- A `--pr` run in a shallow clone stops with the `RuntimeError`. Run `git fetch --unshallow` first.
