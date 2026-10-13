# 59 — A commit from before 2020 needs an older Python than 3.10

## Summary

- **Goal:** Build a test environment for a commit from 2019 or earlier. Example: `pydata/xarray` at 2019-10-12 depends on `pandas 0.25.1`. That version has no wheel for Python 3.10, and its source build fails with `No module named 'pkg_resources'`.
- **Checkable finish condition:** A dry run on a commit of `pydata/xarray` from 2019 builds an environment in which `import xarray` works.
- **Evidence:** Before: ticket 53, 2026-10-12. The pinned install failed, the fallback `pip install -e .` installed numpy 2, and the test agent stopped with `np.unicode_` removed in `xarray/core/dtypes.py` (trace `e8404751`, project `slopgate-gate`). After: the dry run.
- **Constraints:** Commits from 2020 to 2023-10 keep `python:3.10-slim`. `.slopgate.toml` still wins.

**Blocked by:** —

**Status:** ready-for-agent

**Type:** bug.

## Context

Ticket 53 runs a commit from before 2023-10-02 on `python:3.10-slim` with the dependency versions of the commit date. A package from 2019 has wheels for Python 3.7 only (`pandas 0.25.1`, `numpy 1.17`). Python 3.10 must build them from source, and the build fails.

`uv` is a Python package for Python 3.8 and later. So `pip install uv` fails on `python:3.7-slim`.

## Design

Measure 2 options on 3 commits from 2018 and 2019 (for example xarray, matplotlib, and scikit-learn):

1. **Older image.** Use `python:3.7-slim` for commits before 2020. Install `uv` in a separate step with another Python, and install into the 3.7 environment with `uv pip install --python <path>`.
2. **Skip the date limit for these commits.** Install the newest versions of the dependencies that still work with a constraint on the numpy version (`numpy<2`).

Choose by the count of commits that build and pass a small test run.

## Acceptance

- [ ] The Comments give the result of each option on 3 commits.
- [ ] A dry run on xarray at 2019-10-12 gives an environment in which `import xarray` works.
- [ ] `uv run pytest -q` passes.

### 2026-10-12 — count from ticket 44

An injected-slop run on SWE-bench Lite commits (dry run, `slopgate review --repo <checkout> --base <commit> --head HEAD --dry-run`) failed to build or run a test environment on 3 of 3 repos at commits from before 2020:

| Repo | Commit date | Error |
|---|---|---|
| `sympy/sympy` | 2016-07-16 | `from UserDict import DictMixin as MappingMixin` in `_pytest/main.py` (an old `pytest`, installed on Python 3.10) |
| `django/django` | 2019-02-08 | `py/_path/local.py` in `pyimport` (`__import__(modname)` failed; 4 functions) |
| `psf/requests` | 2014-03-12 | import error in `requests/packages/urllib3/__init__.py` (`could not build test environment`) |

The pinned install takes the dependency versions of the commit date. For these dates, the versions of `pytest` and `py` are too old for Python 3.10. The ticket text names only `pydata/xarray` and `pandas`: the fix must also cover `pytest` and `py`. Count: 6 of 6 injected functions on these three repos got no rewrite (the 7th run, `sympy` `ZeroMatrix.__pow__`, ended with a sandbox timeout: ticket 60). The benchmark of ticket 10 can choose newer SWE-bench commits for these repos (2020 or later) instead.
