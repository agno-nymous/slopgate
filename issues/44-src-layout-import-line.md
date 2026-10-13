# 44 — The import line is wrong for a repo with a `src/` layout

## Summary

- **Goal:** Give the test writer the correct import line when the package is in `src/`. Example: for `src/flask/helpers.py`, the gate writes `from src.flask.helpers import get_load_dotenv`. The correct line is `from flask.helpers import get_load_dotenv`.
- **Checkable finish condition:** `module_of("src/flask/helpers.py")` gives `flask.helpers` in an offline test. `module_of("slopgate/review.py")` still gives `slopgate.review`. `uv run pytest -q` passes.
- **Evidence:** Before: in the ticket 41 benchmark (2026-10-10), all 6 functions of `pytest-dev/pytest` failed in designs A, B, and C. 3 of them gave "coverage has no data for src/_pytest/...". After: a run of `bench/characterize.py --only pytest-dev/pytest` with the fix.
- **Constraints:** Remove a leading `src/` only in `module_of`. Do not read `pyproject.toml` or `setup.cfg`.

**Blocked by:** —

**Status:** done

**Type:** bug.

## Context

`module_of` in `slopgate/review.py` makes the module name from the file path: `path.removesuffix(".py").replace("/", ".")`. Many repos keep the package in `src/` (the "src layout"). For these repos, the module name starts with `src.`, which is wrong.

The installed package and `src.<package>` are then two copies of the same module. A test that imports `src._pytest.fixtures` runs a copy that coverage does not measure under the right name. Classes and globals of the two copies are different objects.

Found by ticket 41. The benchmark used `src/` functions from `pallets/flask` and `pytest-dev/pytest`. The flask functions often passed, because the package code imports itself with relative imports. The pytest functions all failed.

`module_of` has 8 call sites in `slopgate/review.py`: `record`, `removal`, `replace_calls`, `characterize`, and `deduplicate`.

## Design

1. In `module_of`, remove a leading `src/` from the path before the conversion.
2. Add an offline test for both forms of path.

## Acceptance

- [x] `module_of("src/flask/helpers.py") == "flask.helpers"`.
- [x] `module_of("slopgate/review.py") == "slopgate.review"`.
- [x] `uv run pytest -q` passes.

## Comments

### 2026-10-11 — count from ticket 49

The traced dry run of `pallets/flask#4646` (trace `1d564d20`) gave the import line `from src.flask.cli import find_best_app`. That run also had no install step (fixed in ticket 49: `commands` now installs a `setup.py` repo). Count in the 10 traced runs of ticket 49: 1 of 15 candidates.

### 2026-10-11 — external count from ticket 49

flask#5818 has its package in `src/flask/`. In the 4 agent runs on this pull request, the agent first wrote `from src.flask.app import Flask`, or added `--source=src` to its command. Count: 4 of the 7 external candidate runs, plus flask#4646 above, so 5 of 7.

### 2026-10-12 — done

**Built.** Two changes in `slopgate/review.py`:
1. `module_of` removes a leading `src/`. A test in `tests/test_review.py` checks three paths.
2. The coverage commands run `python -m coverage combine -q >/dev/null 2>&1` before `coverage json` (`COMBINE`, used in `check` and in the agent's task text). The first benchmark run after change 1 proved 0 of 6 functions of `pytest-dev/pytest` ("coverage has no data"), so the benchmark could not show change 1. The cause: `.coveragerc` of `pytest-dev/pytest` sets `parallel = 1`. Then `coverage run` writes `.coverage.<host>.<pid>.<suffix>`, and `coverage json` of coverage 7.10.7 (the sandbox version) reads only `.coverage`. The text of this second change was not in the ticket design.

**Worked example.** Input: `src/flask/helpers.py`. Before: `src.flask.helpers`. After: `flask.helpers`. The gate writes `from flask.helpers import get_load_dotenv`. `slopgate/review.py` still gives `slopgate.review`. `pkg/src/mod.py` still gives `pkg.src.mod`: only a leading `src/` goes. In a ConTree sandbox of `pytest-dev/pytest`, `from _pytest.config import _get_directory` runs from `/repo/src/_pytest`, and `combine` turns the data file `.coverage.hostname.11.XbkmlzXx` into `.coverage` with `src/_pytest/config/__init__.py` in its files.

**Measured.** `python -m bench.characterize --only pytest-dev/pytest` (6 functions, commit `6995257c`):
- Before both changes (2026-10-10, ticket 41): 0 of 6 proved.
- After change 1 only: 0 of 6, 6 of 6 "coverage has no data".
- After both changes: 5 of 6 proved (83%), 1 step limit (`LFPluginCollSkipfiles.pytest_make_collect_report`). Median 59 s, 12 model calls on average, cost $0.152.
- After change 2 only (`module_of` reverted for the run): 5 of 6 proved (83%), 1 step limit (`LocalPath._ensuredirs`). Median 62 s, 13.5 calls, cost $0.170. So `module_of` changed no result on this benchmark: the agent already fixed a wrong `src.` import line itself (ticket 49 saw the same in 4 of 7 external runs), and the 0 of 6 of ticket 41 came from the coverage data, not from the import line. The `module_of` change is still correct for the first line of the task, and it saves agent steps, but this run does not measure that.

**Limits.** No offline test covers `COMBINE`: coverage 7.16.2 on this Mac combines the parallel files by itself in `coverage json`, so a local test passes without the fix. The benchmark is the proof. The benchmark runs the agent in worker processes without traces, so I read no Phoenix traces. I found the cause with direct probes in the sandbox. One function ended at the step limit: not looked at.
