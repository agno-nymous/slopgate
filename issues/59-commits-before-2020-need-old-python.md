# 59 — A commit from before 2020 needs an older Python than 3.10

## Summary

- **Goal:** Build a test environment for a commit from 2019 or earlier. Example: `pydata/xarray` at 2019-10-12 depends on `pandas 0.25.1`. That version has no wheel for Python 3.10, and its source build fails with `No module named 'pkg_resources'`.
- **Checkable finish condition:** A dry run on a commit of `pydata/xarray` from 2019 builds an environment in which `import xarray` works.
- **Evidence:** Before: ticket 53, 2026-10-12. The pinned install failed, the fallback `pip install -e .` installed numpy 2, and the test agent stopped with `np.unicode_` removed in `xarray/core/dtypes.py` (trace `e8404751`, project `slopgate-gate`). After: the dry run.
- **Constraints:** Commits from 2020 to 2023-10 keep `python:3.10-slim`. `.slopgate.toml` still wins. (Changed on 2026-10-19 by the user: every old commit gets the Python of its date. See Comments.)

**Blocked by:** —

**Status:** done

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

- [x] The Comments give the result of each option on 3 commits.
- [x] A dry run on xarray at 2019-10-12 gives an environment in which `import xarray` works.
- [x] `uv run pytest -q` passes.

### 2026-10-12 — count from ticket 44

An injected-slop run on SWE-bench Lite commits (dry run, `slopgate review --repo <checkout> --base <commit> --head HEAD --dry-run`) failed to build or run a test environment on 3 of 3 repos at commits from before 2020:

| Repo | Commit date | Error |
|---|---|---|
| `sympy/sympy` | 2016-07-16 | `from UserDict import DictMixin as MappingMixin` in `_pytest/main.py` (an old `pytest`, installed on Python 3.10) |
| `django/django` | 2019-02-08 | `py/_path/local.py` in `pyimport` (`__import__(modname)` failed; 4 functions) |
| `psf/requests` | 2014-03-12 | import error in `requests/packages/urllib3/__init__.py` (`could not build test environment`) |

The pinned install takes the dependency versions of the commit date. For these dates, the versions of `pytest` and `py` are too old for Python 3.10. The ticket text names only `pydata/xarray` and `pandas`: the fix must also cover `pytest` and `py`. Count: 6 of 6 injected functions on these three repos got no rewrite (the 7th run, `sympy` `ZeroMatrix.__pow__`, ended with a sandbox timeout: ticket 60). The benchmark of ticket 10 can choose newer SWE-bench commits for these repos (2020 or later) instead.

## Comments

### 2026-10-19 — done

**What was built.** An old commit (merge-base before 2023-10-02) now builds on the Python of its date, not always on `python:3.10-slim`. `old_python` in `slopgate/sandbox.py` takes the newest Python minor that was released 90 days or more before the merge-base date. The floor is 3.6. `PYTHONS` and `PYTHON_LAG_DAYS` in `slopgate/config.py` hold the release dates and the lag. Four more changes make the install work on these Pythons:

- `pip install -q --ignore-requires-python uv`. The uv package declares Python 3.8 or later, but its binary installs into 3.6 and 3.7.
- `--reinstall` replaces `--reinstall-package pytest`. The image installs the newest pytest first. Its new `py` and `pluggy` satisfy the version ranges of an old pytest, so the old option kept them: pytest 2.9.2 ran with py 1.11.0, and pytest 4.4.1 ran with pluggy 1.2.0.
- On Python 3.6, uv installs the project without `-e`, and then `pip install -q --no-deps -e .` makes it editable. The newest setuptools for 3.6 (59.6) has no `build_editable`, so uv cannot make an editable install there.
- `Contree.prepare` gets its image with `images.oci`. This call imports a tag that the account does not have from Docker Hub. The account had `python:3.9-slim` to `3.14-slim`, but not 3.6 to 3.8. One import took 11 s.

**Scope change (user decision, 2026-10-19).** The ticket said that commits from 2020 to 2023-10 keep `python:3.10-slim`. The measurement below shows that sphinx-7975, sphinx-8506, sphinx-8627 (2020-07 to 2020-12), and pytest-5227 and pytest-7220 (2019 to 2020) fail on 3.10 with `TypeError: required field "lineno" missing from alias`. They pass on 3.7 or 3.8. The user chose to give every old commit the Python of its date.

**Why 3.6 is the floor.** On `python:3.5-slim`, uv stops at its interpreter probe: the probe uses an f-string. On `python:3.4-slim`, pip finds no uv wheel. Python 3.7 is not a floor that works: django at 2017-06 fails on 3.7 with `SyntaxError: Generator expression must be parenthesized`.

**Why a lag of 90 days.** A new Python gets wheels of the C packages some days or weeks after its release. With no lag, xarray at 2019-10-14 got Python 3.8. numpy 1.17.2 had no wheel for 3.8, the build failed (`Broken toolchain`), and the fallback ran. With a lag of 90 or 180 days, the commit gets 3.7 and its tests pass. Both lags pass on all 6 commits whose image they change (run of 2026-10-19). 90 days is the smaller change.

**Worked example.** xarray at `863e4906` (2019-10-12) with one added function (`first_key` with a broad `except`), dry run `slopgate review --repo <clone> --base 863e4906 --head HEAD --dry-run`:

- Before: `python:3.10-slim`. The pinned install failed, the fallback `pip install -e .` installed numpy 2, and `import xarray` failed: `` `np.unicode_` was removed in the NumPy 2.0 release ``.
- After: `commands` gives `python:3.7-slim` and `pip install -q --ignore-requires-python uv && uv pip install ... --exclude-newer 2019-10-12T17:33:33-04:00 --exclude-newer-package setuptools=2100-01-01 -e . pytest --reinstall && ...`. The environment has numpy 1.17.2 and pandas 0.25.1. Trace `d650de97` (project `slopgate-gate`): `sandbox.prepare` 14.7 s with no error. The repo suite baseline ran (33 s, exit 0). The test agent wrote its file in 10 steps, and its tests passed on the original code (`3 passed`). The gate then rejected the rewrite of `first_key`: it changed the result for an object whose `__iter__` raises `RuntimeError`. A second dry run on the final code (trace `9d6c2b33`): `sandbox.prepare` 12.1 s with no error.

**Measured results (ConTree, 2026-10-19).** Each row builds with the gate's own `commands()` and `Contree.prepare()`, and then runs a small test file of the repo (for example `xarray/tests/test_utils.py`, `tests/test_util_inspect.py` for sphinx). "fallback" means that the pinned install failed and `pip install -e .` ran.

The 3 options of the design, on 14 commits:

| Option | Builds and passes the small test |
|---|---|
| Today: `python:3.10-slim` | 4 of 14 (django 2019-02, flask, seaborn, pylint) |
| 1. Python of the commit date, first version (no lag, no 3.6 fix) | 11 of 14 |
| 1. Python of the commit date, final code | 12 of 14 |
| 2. No date limit, `numpy<2`, on 3.10 | 2 of 14 (django 2019-02, pylint). The newest jinja2, werkzeug, and pandas break old sphinx, flask, and xarray. |

The final code, on 18 commits (the 14 above and 4 more xarray and django commits): 13 build with the pinned install and pass all tests of the small test file. 1 builds pinned and has 1 failed test of 90 (pytest-7220). 2 pass only through the fallback (django 2017-06, pytest-5227). 2 fail (sympy 2016-07, requests 2014-03).

Each commit of the final run:

| Commit | Date | Python | Fallback | Small test |
|---|---|---|---|---|
| xarray | 2019-10-12 | 3.7 | no | 25 passed |
| xarray | 2019-10-14 | 3.7 | no | 25 passed |
| xarray | 2019-10-21 | 3.7 | no | 25 passed |
| xarray | 2020-01-14 | 3.8 | no | 33 passed |
| xarray v0.16.0 | 2020-07-11 | 3.8 | no | 34 passed |
| django | 2017-06-15 | 3.6 | yes | `utils_tests.test_text` OK |
| django | 2019-02-08 | 3.7 | no | `utils_tests.test_text` OK |
| sympy | 2016-07-16 | 3.6 | no | collection error: `cannot import name 'raises'` |
| requests | 2014-03-12 | 3.6 | yes | `importlib._bootstrap` has no `SourceFileLoader` |
| requests-3362 | 2016-06-28 | 3.6 | no | 20 passed |
| sphinx-7975 | 2020-07-18 | 3.8 | no | 36 passed |
| sphinx-8506 | 2020-11-28 | 3.8 | no | 37 passed |
| sphinx-8627 | 2020-12-31 | 3.8 | no | 37 passed |
| pytest-5227 | 2019-05-07 | 3.7 | yes | 73 passed |
| pytest-7220 | 2020-05-30 | 3.8 | no | 89 passed, 1 failed |
| flask-4992 | 2023-02-23 | 3.11 | no | 18 passed |
| seaborn-3190 | 2022-12-27 | 3.10 | no | 45 passed |
| pylint-5859 | 2022-03-02 | 3.10 | no | 34 passed |

- All 4 ticket 10 instances of the ROADMAP row (sphinx-7975, sphinx-8506, sphinx-8627, requests-3362) now build and pass the small test.
- A build takes 11 s to 21 s, the same as on 3.10.
- Offline tests: 7 new or changed tests in `tests/test_review.py`. `uv run pytest -q`: 452 passed.
- The commits are pure-Python repos. matplotlib and scikit-learn of 2018 and 2019 compile C code, and a slim image has no compiler, so they cannot show the effect of the Python version (ticket 67 handles compilers).

**Code review (Opus, thermo-nuclear).**

1. The release date alone gives a Python without wheels for a commit soon after the release. Applied: the 90-day lag above, measured.
2. `prepare` copied the lookup and import that `images.oci` does already. Applied: one `oci` call.
3. The ticket text did not match the code. Applied: this entry and the Constraints line.
4. Two checks of `python == "3.6"`. Applied: one check.
5. Merge `OLD_COMMIT_BEFORE` into `PYTHONS`. Rejected: `OLD_COMMIT_BEFORE` decides the date limit of the dependencies (ticket 53), and `PYTHONS` decides the image. With the lag in the boundary, commits from 2023-10 to 2023-12 would get a date limit that nobody measured.

**Known limits.**

- Commits from before 2018 work on 3.6 only in part (ticket 69): sympy 2016-07 and requests 2014-03 fail, and django 2017-06 passes only through the fallback.
- pytest-5227 uses the fallback: PyPI now has only `atomicwrites` 1.4.1 (2022), so the date limit leaves no version (ticket 68).
- On 3.8, the pinned install of pytest-7220 worked. The `pkg_resources` failure of ticket 68 did not occur: the newest setuptools for 3.8 still has `pkg_resources`. Ticket 68 has the details.
- The images of Python 3.6 to 3.8 are end-of-life. Docker Hub still serves them.
