# 17 — Test files get review notes only

**What to build:** The gate makes no code changes in test files. For a function in a test file, the gate posts a review note that names the finding and how to fix it. The note has no suggested change, no sandbox proof, and no follow-up pull request. The hook uses the same rule to find test files.

**Blocked by:** None — can start immediately.

**Status:** done

## Context

The gate (`slopgate review`, in `slopgate/review.py`) examines every changed function, test functions included. On PR #9 this caused two problems:

1. The gate examined `fake_llm`, a pytest fixture in `tests/conftest.py`. Super cannot write a test that calls a fixture directly, so Super replied in prose. The gate saved the prose as a test file, and pytest failed with `SyntaxError: invalid character '’'`.
2. A rewrite of test code changes the code that proves other rewrites. A characterization test cannot prove a change to a test.

The hook (`slopgate hook`, in `slopgate/live.py`) already keeps test functions out of its search pool. The function that decides this (`pooled` in `slopgate/live.py`) checks for a folder named `tests` and a name that starts with `test_`. A repo can keep its tests in a folder with a different name, for example `test/`, `testing/`, or next to the code. So the folder name is not a correct rule.

## The rule: a test file is found by its file name

1. A file is a test file when its file name (not its folder) matches one of these patterns: `test_*.py`, `*_test.py`, `conftest.py`. These are the pytest default discovery patterns, plus the fixture file.
2. If the repo sets `python_files` in its pytest config, use those patterns in place of the first two. Read `[tool.pytest.ini_options]` in `pyproject.toml` and `[pytest]` in `pytest.ini`. Keep `conftest.py` in all cases.
3. Match the file name with `fnmatch`.
4. The gate reads the config at the pull request head (`git show <head>:pyproject.toml`). The hook reads the config from the working tree.

Put the rule in one function that the gate and the hook both call. Do not copy it.

## What the gate does for a function in a test file

1. The gate finds the kind of slop as it does now (duplicate, dead code, or a kind from Lightning).
2. The gate does not ask a model for a rewrite. It does not write characterization tests and does not start the sandbox for this function.
3. The gate adds one note to a new result list, `result["notes"]`. Each note has `path`, `function`, `kind`, and `body`.
4. The body states the finding, the fix instruction for the kind (the text in `KINDS` in `slopgate/review.py`), and the words "Not proven: Slopgate does not change test files." For a duplicate, the body names the existing function and its file.
5. `publish` in `slopgate/github.py` posts each note as an inline review comment on the last added line of the function. The comment has no ```` ```suggestion ```` block. When the function has no added line, the note goes into the summary under a "Notes on test files" list.
6. A pull request with only notes still gets a review. Today `publish` returns early when `suggestions`, `followup`, and `rejected` are all empty. Include `notes` in that check.

Example note:

> **duplicate** (not proven): `test_unique_write` does the same job as `test_non_python_change` in tests/test_hook.py. Consider one parametrized test. Not proven: Slopgate does not change test files.

## What the hook does

The hook keeps functions in test files out of its search pool, and it does not flag a new function in a test file. Replace the folder check in `pooled` with the shared rule. Keep the check that drops methods (a `.` in the qualified name).

## Acceptance

- [x] A function in `test/test_api.py`, `checks/api_test.py`, and `src/conftest.py` counts as a test file. A function in `tests/helpers.py` does not count, unless `python_files` matches it.
- [x] A repo with `python_files = ["check_*.py"]` in `[tool.pytest.ini_options]` makes `check_api.py` a test file and `test_api.py` a normal file.
- [x] A nested, slop-flagged function in a test file produces one entry in `result["notes"]` and no entry in `suggestions`, `followup`, or `rejected`. The fake LLM gets no rewrite request and no tests request for it.
- [x] A copy of an existing test function produces a note of kind `duplicate` that names the existing function.
- [x] `publish` posts a note as an inline comment without a suggestion block. A pull request with only notes gets a review.
- [x] The hook drops a function in `test/test_api.py` from its pool. It still keeps a function in `tests/helpers.py`.
- [x] `uv run pytest -q` passes.

## How to verify by hand

1. Run `uv run --env-file .env slopgate review --repo <demo clone> --base main --head <branch> --dry-run --sandbox local` on a branch that adds a nested function to `tests/conftest.py`.
2. Check that the printed result has the function in `notes` only.

## Comments

### 2026-10-08: done

**What was built.** The gate makes no code changes in test files. For a function in a test file, the gate posts a note: an inline review comment with no suggestion block. The gate does not write tests, ask for a rewrite, or start the sandbox for this function. If a pull request has only notes, the gate never prepares the sandbox.

- `slopgate/functions.py` holds the shared rule. `pytest_patterns(read)` reads `python_files` from `pytest.ini` (`[pytest]`), or else from `pyproject.toml` (`[tool.pytest.ini_options]`). With no value, the patterns are `test_*.py` and `*_test.py`. `is_test_file(path, patterns)` matches the file name with `fnmatch.fnmatchcase`. `conftest.py` is always a test file.
- `slopgate/review.py` reads the patterns at the head ref. Wrapper detection skips functions in test files. Kind detection does not change. A finding in a test file goes to `result["notes"]` as `{path, function, kind, line, body}`. `line` is the last added line of the function.
- `slopgate/github.py` posts each note as a review comment in the same review as the suggestions. A pull request with only notes gets a review. The summary line counts the notes when there are any ("Notes on test files: N."). If the sandbox install fails, the notes still post, with the install notice as the review body. A duplicate note says "Call it instead." when the existing function is not in a test file.
- `slopgate/live.py`: `pooled` uses the shared rule in place of the `tests` folder check. The hook reads the patterns from the working tree.

**Worked example.** This is a live dry run on a clone of this repo. One commit adds two functions:

- `reply_for` in `tests/conftest.py`, which has 5 levels of nested `if`.
- `test_no_store_means_no_output` in `tests/test_hook.py`, which is a renamed copy of `test_repo_without_store_exits_zero_silently`.

The command was `slopgate review --repo <clone> --base HEAD~1 --head HEAD --dry-run --sandbox local`. Its output was:

```json
{
  "suggestions": [],
  "followup": [],
  "rejected": [],
  "notes": [
    {"path": "tests/conftest.py", "function": "reply_for", "kind": "dead", "line": 96,
     "body": "**dead** (not proven): `reply_for`: It has unreachable code or unused variables. Remove them. Not proven: Slopgate does not change test files."},
    {"path": "tests/test_hook.py", "function": "test_no_store_means_no_output", "kind": "duplicate", "line": 254,
     "body": "**duplicate** (not proven): `test_no_store_means_no_output` does the same job as `test_repo_without_store_exits_zero_silently` in tests/test_hook.py. Consider one parametrized test. Not proven: Slopgate does not change test files."}
  ]
}
```

The gate wrote no tests, asked for no rewrite, and did not start the sandbox. Lightning named `reply_for` as `dead`. Vulture finds no dead code in it, so `nesting` is the correct kind. The classifier made this error, and it is not part of this ticket.

**Measured results.**

- `uv run pytest -q`: 201 passed, 12 deselected.
- Mutation check: with `is_test_file` forced to return `False`, 11 tests fail. With the old `tests` folder check back in `pooled`, the `tests/helpers.py` hook test fails.

**Known limits.**

- The gate's duplicate pool still contains functions in test files. A new production function can match a test helper, and the gate then proposes to call the test helper. This ticket does not change that behavior.
- `changed_functions` returns only functions that have an added line. Thus every note has a line, and the "no added line" fallback in the summary is not necessary.
- A `pyproject.toml` or `pytest.ini` that is not valid at head stops the review with an error. The hook prints that error to stderr and exits 0.
