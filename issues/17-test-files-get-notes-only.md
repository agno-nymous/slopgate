# 17 — Test files get review notes only

**What to build:** The gate makes no code changes in test files. For a function in a test file, the gate posts a review note that names the finding and how to fix it. The note has no suggested change, no sandbox proof, and no follow-up pull request. The hook uses the same rule to find test files.

**Blocked by:** None — can start immediately.

**Status:** ready-for-agent

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

- [ ] A function in `test/test_api.py`, `checks/api_test.py`, and `src/conftest.py` counts as a test file. A function in `tests/helpers.py` does not count, unless `python_files` matches it.
- [ ] A repo with `python_files = ["check_*.py"]` in `[tool.pytest.ini_options]` makes `check_api.py` a test file and `test_api.py` a normal file.
- [ ] A nested, slop-flagged function in a test file produces one entry in `result["notes"]` and no entry in `suggestions`, `followup`, or `rejected`. The fake LLM gets no rewrite request and no tests request for it.
- [ ] A copy of an existing test function produces a note of kind `duplicate` that names the existing function.
- [ ] `publish` posts a note as an inline comment without a suggestion block. A pull request with only notes gets a review.
- [ ] The hook drops a function in `test/test_api.py` from its pool. It still keeps a function in `tests/helpers.py`.
- [ ] `uv run pytest -q` passes.

## How to verify by hand

1. Run `uv run --env-file .env slopgate review --repo <demo clone> --base main --head <branch> --dry-run --sandbox local` on a branch that adds a nested function to `tests/conftest.py`.
2. Check that the printed result has the function in `notes` only.

## Comments
