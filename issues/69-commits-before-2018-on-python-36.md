# 69 — Some commits from before 2018 do not build or test on Python 3.6

## Summary

- **Goal:** Build a working test environment for a commit from 2014 to 2017. Ticket 59 gives these commits `python:3.6-slim`, the oldest Python that uv can install into. 2 of 4 such commits still fail.
- **Checkable finish condition:** On sympy at 2016-07-16 and requests at 2014-03-12, the pinned install builds the environment without the fallback, and a small test file of the repo passes.
- **Evidence:** Before: the ticket 59 measurement (2026-10-19, see Context). After: the same measurement.
- **Constraints:** Do not change the install of commits from 2018 on. `.slopgate.toml` still wins.

**Blocked by:** 59

**Status:** ready-for-agent

**Type:** bug.

## Context

Ticket 59 measured 4 commits from before 2018 on `python:3.6-slim`, with the gate's own `commands()` and `Contree.prepare()`:

| Commit | Date | Fallback | Small test |
|---|---|---|---|
| requests-3362 | 2016-06-28 | no | 20 passed |
| django | 2017-06-15 | yes | `utils_tests.test_text` OK |
| sympy | 2016-07-16 | no | `sympy/core/tests/test_basic.py`: `ImportError: cannot import name 'raises'` from `sympy.utilities.pytest` |
| requests | 2014-03-12 | yes | `AttributeError: module 'importlib._bootstrap' has no attribute 'SourceFileLoader'` |

- requests 2014-03: the pinned install reinstalls setuptools with the date limit. A setuptools of 2014 imports `importlib._bootstrap.SourceFileLoader`, which Python 3.6 does not have. The fallback also fails at `python setup.py egg_info`.
- sympy 2016-07: the environment has pytest 2.9.2 and py 1.4.31 of the date. The cause of the `raises` import error is not known. sympy of that time ran its tests with `bin/test`, not with pytest.
- django 2017-06: the pinned install fails with `TypeError: expected str, bytes or os.PathLike object, not NoneType`. The full traceback was not read.

SWE-bench Lite has many instances from this time (most of requests, much of sympy and django), so this matters if ticket 10 or a later benchmark uses them.

## Design

1. Read the full traceback of each failure.
2. For the setuptools failure: limit setuptools to the newest release that runs on Python 3.6 (59.6), not to the release of the date.
3. For sympy: find whether the repo needs its own test runner. If yes, that is a `test` command, not an install fix.
4. Measure each change on the 4 commits above. Keep requests-3362 working.

## Acceptance

- [ ] The Comments give the cause of each failure.
- [ ] sympy 2016-07 and requests 2014-03 build without the fallback and pass a small test.
- [ ] requests-3362 still passes.
- [ ] `uv run pytest -q` passes.
