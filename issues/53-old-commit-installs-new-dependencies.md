# 53 — An old commit installs today's versions of its dependencies

## Summary

- **Goal:** Build a test environment that works for an old commit. Example: `pallets/flask#4646` (June 2022) asks for `Werkzeug >= 2.2.0` with no upper limit. `pip install -e .` installs Werkzeug 3, which removed `werkzeug.urls.url_quote`. So `import flask` fails, and the test agent cannot run one test.
- **Checkable finish condition:** A dry run on `pallets/flask#4646` builds an environment in which `import flask` works, and the test agent writes tests that run.
- **Evidence:** Before: ticket 49, trace `c76dc0c3` (2026-10-11): `ImportError: cannot import name 'url_quote' from 'werkzeug.urls'`. The agent used 168,818 tokens and stopped at the token limit. After: the dry run.
- **Constraints:** Do not change the install for a pull request on current code. Keep `.slopgate.toml` as the override that wins.

**Blocked by:** —

**Status:** ready-for-agent

## Context

`commands` in `slopgate/sandbox.py` gives `pip install -e .` for a repo with `pyproject.toml` or `setup.py` (ticket 49 added `setup.py`). pip resolves each dependency to the newest version that the package allows. For a pull request on current code, that is correct. For a commit from the past, a newer major version can break the import.

This matters for the SWE-bench benchmark (ticket 10), where every commit is from the past. It does not matter for a live pull request on a maintained repo.

## Design

Measure 2 options on flask#4646 and on 3 other SWE-bench commits from before 2023:

1. **Date limit.** Install with `uv pip install --exclude-newer <commit date>`, so that each dependency resolves to a version from before the commit. This needs `uv` in the sandbox image.
2. **Repo pins.** When the repo has `requirements/tests.txt` or a similar pinned file, install it too.

Apply the chosen option only when the commit is older than a set age, or only in the benchmark.

## Acceptance

- [ ] The Comments give the result of each option on the 4 commits.
- [ ] A dry run on flask#4646 gives tests that run.
- [ ] `uv run pytest -q` passes.

## Comments

### 2026-10-11 — external count from ticket 49

The cause is not only old commits. It also occurs on current code, because the gate ignores the pins of the repository.

- **flask#5818 (2025):** flask pins its test tools in `uv.lock` and in `[dependency-groups]`. `commands` gives `pip install -e .`, and the checkpoint then gets the newest `pytest`. Flask's `tests/conftest.py` uses `monkeypatch.notset`, which the newest `pytest` does not have. So each test of the agent failed in the fixture, before it reached the function. Count: 4 of 4 candidates on this pull request (traces `b7843283`).
- **flask#4646 (2022):** the newest Werkzeug has no `werkzeug.urls.url_quote` (see the Summary). Count: 1 candidate.

Total: 5 of the 7 external candidate runs in ticket 49.

Add a third option to the Design: **the repository lock.** When the repository has `uv.lock`, install with `uv sync --frozen` (or `uv export --frozen` into `pip install -r`), and install the `dev` or `test` dependency group too. Measure it on flask#5818 first.
