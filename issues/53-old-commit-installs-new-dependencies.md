# 53 — An old commit installs today's versions of its dependencies

## Summary

- **Goal:** Build a test environment that works for an old commit. Example: `pallets/flask#4646` (June 2022) asks for `Werkzeug >= 2.2.0` with no upper limit. `pip install -e .` installs Werkzeug 3, which removed `werkzeug.urls.url_quote`. So `import flask` fails, and the test agent cannot run one test.
- **Checkable finish condition:** A dry run on `pallets/flask#4646` builds an environment in which `import flask` works, and the test agent writes tests that run.
- **Evidence:** Before: ticket 49, trace `c76dc0c3` (2026-10-11): `ImportError: cannot import name 'url_quote' from 'werkzeug.urls'`. The agent used 168,818 tokens and stopped at the token limit. After: the dry run.
- **Constraints:** Do not change the install for a pull request on current code, except for a repo that has `uv.lock` (see the Comments of 2026-10-11): it installs its lock. Keep `.slopgate.toml` as the override that wins.

**Blocked by:** —

**Status:** done

## Context

`commands` in `slopgate/sandbox.py` gives `pip install -e .` for a repo with `pyproject.toml` or `setup.py` (ticket 49 added `setup.py`). pip resolves each dependency to the newest version that the package allows. For a pull request on current code, that is correct. For a commit from the past, a newer major version can break the import.

This matters for the SWE-bench benchmark (ticket 10), where every commit is from the past. It does not matter for a live pull request on a maintained repo.

## Design

Measure 2 options on flask#4646 and on 3 other SWE-bench commits from before 2023:

1. **Date limit.** Install with `uv pip install --exclude-newer <commit date>`, so that each dependency resolves to a version from before the commit. This needs `uv` in the sandbox image.
2. **Repo pins.** When the repo has `requirements/tests.txt` or a similar pinned file, install it too.

Apply the chosen option only when the commit is older than a set age, or only in the benchmark.

## Acceptance

- [x] The Comments give the result of each option on the 4 commits.
- [x] A dry run on flask#4646 gives tests that run.
- [x] `uv run pytest -q` passes.

## Comments

### 2026-10-11 — external count from ticket 49

The cause is not only old commits. It also occurs on current code, because the gate ignores the pins of the repository.

- **flask#5818 (2025):** flask pins its test tools in `uv.lock` and in `[dependency-groups]`. `commands` gives `pip install -e .`, and the checkpoint then gets the newest `pytest`. Flask's `tests/conftest.py` uses `monkeypatch.notset`, which the newest `pytest` does not have. So each test of the agent failed in the fixture, before it reached the function. Count: 4 of 4 candidates on this pull request (traces `b7843283`).
- **flask#4646 (2022):** the newest Werkzeug has no `werkzeug.urls.url_quote` (see the Summary). Count: 1 candidate.

Total: 5 of the 7 external candidate runs in ticket 49.

Add a third option to the Design: **the repository lock.** When the repository has `uv.lock`, install with `uv sync --frozen` (or `uv export --frozen` into `pip install -r`), and install the `dev` or `test` dependency group too. Measure it on flask#5818 first.

### 2026-10-12 — done

**What was built.** `commands(repo, ref, since)` in `slopgate/sandbox.py` now chooses the install. `since` is the commit date of the merge-base of the pull request (`fork` in `review`). It returns `(setup, test, image)`.

1. The repo has `uv.lock` and `pyproject.toml`: export the lock (`uv export --frozen --all-groups --no-hashes --no-emit-project`), install it, then install the project.
2. The merge-base is older than 2023-10-02 (`OLD_COMMIT_BEFORE` in `config.py`, the release of Python 3.12): `uv pip install --exclude-newer <date>` with `pytest` and `setuptools` of that date, on `python:3.10-slim` (`OLD_COMMIT_IMAGE`).
3. Any other repo: `pip install -e .`, as before.

Each pinned install ends with `|| pip install -e .`. If the pinned install fails, the sandbox falls back to the plain install. A `setup` line in `.slopgate.toml` replaces the install and the image.

Design changes from the code review (an Opus subagent, 8 findings):

- **Date from the merge-base, not from the head.** The head of a benchmark case is a new commit on old code. Its committer date is today. (Finding 3, applied.)
- **Only `Contree` pins** (`Contree.pins`). The `Local` sandbox installs into the venv of the gate, and the pinned install would replace the versions of this venv. (Finding 1, applied.)
- **The image is chosen once**, in `commands`, and a `setup` override resets it. (Finding 2, applied.)
- Finding 4 (the Constraint line): applied, the line names the `uv.lock` case.
- Finding 6 (tests): applied. The new tests check the shell syntax with `sh -n`, the override, the image, and the merge-base date.
- Findings 5, 7, and 8 (a marker for a fallback, a pin for `uv`, `--all-extras`): rejected for now. See the limits.

**Measured results: install options.** Each cell shows `import <package>` and a small pytest run in ConTree. "Plain" is the old `pip install -e .`.

| Commit | Plain | Date limit, Python 3.12 | Repo pins (`requirements/*.txt`) | Date limit, Python 3.10 | Lock |
|---|---|---|---|---|---|
| flask#4646 (2022) | import fails (`url_quote`) | import ok, tests fail (`monkeypatch.notset`) | import fails | import ok, 35 passed | none |
| flask#5818 (2025) | import ok, tests fail (`monkeypatch.notset`) | same as plain | none | not tried | 35 passed |
| seaborn 2022-07 | import fails (`register_cmap`) | install fails (pillow 9.2 has no 3.12 wheel) | import fails | 18 passed | none |
| sympy 2022-07 | 22 passed | 22 passed | none | 22 passed | none |
| pylint 2022-07 | install fails on 3.12; 11 passed on 3.10 | install fails | install fails | install fails (`setuptools~=62.6` has no `build_editable`); the fallback gives 11 passed | none |

- The date limit alone fails on Python 3.12: `uv` builds the project with the setuptools of 2022, and that setuptools does not run on 3.12. An old pytest on 3.12 fails in its assertion rewriter (`ast.Str`). So old commits run on Python 3.10.
- The date limit must also apply to pytest. The sandbox installs the newest pytest first, and the newest pytest has no `monkeypatch.notset`.
- The repo pin files do not help. `requirements/tests.txt` of flask 2022 pins `pytest`, not `werkzeug`.
- setuptools: a version from before 2022 cannot build an editable install, so the build uses the newest setuptools. The sandbox then gets the setuptools of the date. Without this step, setuptools 79 stayed in the environment of flask 2021, its `pkg_resources` raised a `DeprecationWarning`, and flask's `filterwarnings = error` made every fixture fail (trace `b9e42ed4`).

**Measured results: 5 SWE-bench repos with injected slop** (`bench/detect.py` transform `nesting`; the injected commit has today's date; the base commit is old). One run per repo with the new code, traced in Phoenix (project `slopgate-gate`).

| Repo, base commit date | Environment | Result |
|---|---|---|
| pallets/flask, 2021-05 | built in 14 s | **proven**: nesting 4 -> 2, 4 characterization tests passed, 75 s (trace `c250855f`). The code of `main` failed here with `ImportError` in `conftest.py`. |
| mwaskom/seaborn, 2022-06 | built in 17 s | 2 runs: proven once (3 tests passed, 282 s), and once `step limit: characterization tests miss branches: 1` (trace `97c2341c`, 85 s). The agent varies. The code of `main` stopped with `token limit: coverage has no data`. |
| pylint-dev/pylint, 2022-03 | built in 15 s | `step limit: characterization tests fail on original` (trace `148b215d`). The code of `main` failed to build the environment (`wrapt`). |
| pydata/xarray, 2019-10 | pinned install failed, the fallback built it | `np.unicode_` removed: numpy 2 is too new (trace `e8404751`). The code of `main` failed to build the environment (`versioneer`). New ticket 59. |
| pytest-dev/pytest, 2023-07 | build fails in 16 s | `setuptools-scm was unable to detect version` (trace `42ff0bf2`). The code of `main` fails in the same way. New ticket 58. |

Result: 1 of 5 repos reaches a proven suggestion every time, and 1 more sometimes. With the code of `main`, 0 of 5 did. The environment is usable for 3 of 5 repos (flask, seaborn, pylint). With the code of `main` it was usable for 1 of 5 (seaborn).

**Trace findings.**

- All 5 traces show `sandbox.prepare` at 14 s to 25 s. The pinned install is cheap.
- 3 of 5 runs ended at the agent step limit (15 steps, 15 `sandbox.execute` spans each). One of them (pylint) shows that the agent cannot make its tests pass on the original code. This is ticket 45 and ticket 52.
- Failure causes that are not in this ticket: `setuptools-scm` (ticket 58), commits before 2020 (ticket 59).
- The traces showed a defect of this ticket that the unit tests did not: the setuptools 79 `DeprecationWarning` on flask 2021.

**Worked example.** `pallets/flask`, base `d8c37f43` (2021-05-13). I injected nesting into `Flask.try_trigger_before_first_request_functions`.

- Before (code of `main`): setup `pip install -e .` on `python:3.12-slim`. The agent stopped with `ImportError while loading conftest '/repo/tests/conftest.py'`.
- After: setup `pip install -q uv && uv pip install --python "$(command -v python)" -q --exclude-newer 2021-05-13T13:35:12-07:00 --exclude-newer-package setuptools=2100-01-01 -e . pytest --reinstall-package pytest && ... setuptools --reinstall-package setuptools || pip install -e .` on `python:3.10-slim`. The environment has pytest 6.2.4, Werkzeug 2.0.0, and setuptools 56.2.0. The gate proved a rewrite: nesting 4 -> 2, complexity 4 -> 4, 4 characterization tests passed.
- Also `pallets/flask#4646` (2022-06-15): `import flask` works, and `tests/test_helpers.py` gives `35 passed`. The real PR has no slop, so the gate made no sandbox. A local commit dated 2022-06-15 with a nested function `describe_size` gave one suggestion with 11 characterization tests (83 s).

**Known limits.**

- The age rule uses the committer date of the merge-base. A rebased old commit looks young.
- Python 3.10 is a fixed choice for every old commit. A commit before 2020 needs Python 3.7 (ticket 59). A commit that requires Python 3.11 or later fails to build, and the fallback fails too.
- A failed pinned install falls back to the plain install without a message. The environment is then the old one. The log shows it only when the fallback fails too.
- `--all-groups` installs the docs and typing groups too. `--all-extras` is not set, so a test dependency that a repo lists as an extra is missing.
- A repo that installs from `requirements*.txt` only keeps the plain install.
- `uv` is not pinned: `pip install uv` installs the newest one.
