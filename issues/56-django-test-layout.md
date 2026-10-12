# 56 — The test-file rule misses `tests.py`, and django tests do not run under pytest

## Summary

- **Goal:** Treat a test module as a test file when its name is `tests.py` or when it is under a `tests/` folder. Example: on django#21736, the gate tried to rewrite `EmailValidatorDeprecationTests.test_call_override_using_stock_validate_domain_part_warns` in `tests/validators/tests.py`. A test file must get a note only (ticket 17).
- **Checkable finish condition:** `is_test_file("tests/validators/tests.py", patterns)` is true in an offline test. A dry run on django#21736 gives a note for that method, and no agent run.
- **Evidence:** Before: ticket 49 (2026-10-11), trace `1ce129a1`. The agent ran 15 steps (94,000 tokens, 60 s), and the judge failed with "settings are not configured". After: the test and the dry run.
- **Constraints:** Keep the pytest patterns of the repository as the first rule. Do not add a django test runner in this ticket.

**Blocked by:** —

**Status:** ready-for-agent

## Context

`is_test_file` and `pytest_patterns` in `slopgate/functions.py` use the `python_files` patterns of the repository, or the pytest default (`test_*.py`, `*_test.py`). Django names its test modules `tests.py` and runs them with `tests/runtests.py`, not with pytest. So the gate does not see these files as test files.

A django function outside the tests also needs a settings module to run. That is a second problem. It belongs to the environment of the repository (`.slopgate.toml`), or to a later ticket.

## Design

In `is_test_file`, also return true for a file named `tests.py`, and for a file under a folder named `tests` or `test`.

## Acceptance

- [ ] The offline test passes.
- [ ] A dry run on django#21736 gives a note for the test method.
- [ ] `uv run pytest -q` passes.

## Comments
