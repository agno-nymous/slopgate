# 44 — The import line is wrong for a repo with a `src/` layout

## Summary

- **Goal:** Give the test writer the correct import line when the package is in `src/`. Example: for `src/flask/helpers.py`, the gate writes `from src.flask.helpers import get_load_dotenv`. The correct line is `from flask.helpers import get_load_dotenv`.
- **Checkable finish condition:** `module_of("src/flask/helpers.py")` gives `flask.helpers` in an offline test. `module_of("slopgate/review.py")` still gives `slopgate.review`. `uv run pytest -q` passes.
- **Evidence:** Before: in the ticket 41 benchmark (2026-10-10), all 6 functions of `pytest-dev/pytest` failed in designs A, B, and C. 3 of them gave "coverage has no data for src/_pytest/...". After: a run of `bench/characterize.py --only pytest-dev/pytest` with the fix.
- **Constraints:** Change only `module_of` in `slopgate/review.py`. Remove a leading `src/` only. Do not read `pyproject.toml` or `setup.cfg`.

**Blocked by:** —

**Status:** ready-for-agent

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

- [ ] `module_of("src/flask/helpers.py") == "flask.helpers"`.
- [ ] `module_of("slopgate/review.py") == "slopgate.review"`.
- [ ] `uv run pytest -q` passes.

## Comments
