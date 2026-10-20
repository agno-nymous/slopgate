# 68 — The old-commit install fails for every repo that uses setuptools-scm

## Summary

- **Goal:** Make the pinned install of ticket 53 work for an old commit of a repo that uses `setuptools-scm`. Now the pinned install fails, and the unpinned fallback `pip install -e .` installs the newest dependencies.
- **Checkable finish condition:** On pytest-7220, pytest-5227, pluggy 0.13.1, and xarray v0.16.0, the pinned install part of the command (without `|| pip install -e .`) builds the environment.
- **Evidence:** Before: the ticket 58 probes on 2026-10-18 (see Context). After: the same probes.
- **Constraints:** Do not change the install of a repo that does not use `setuptools-scm`, except the `atomicwrites` fix (user decision, 2026-10-19, see Comments). `.slopgate.toml` still wins.

**Blocked by:** 58

**Status:** done

**Type:** bug.

## Context

Ticket 53 installs an old commit with `uv pip install --exclude-newer <commit date> --exclude-newer-package setuptools=2100-01-01 -e . ...`. So setuptools is the newest release, but setuptools-scm has the version of the commit date. A setuptools-scm from 2019 or 2020 imports `pkg_resources`. The newest setuptools does not have `pkg_resources`, so the build stops:

```
File ".../setuptools_scm/version.py", line 10, in <module>
    from pkg_resources import iter_entry_points
ModuleNotFoundError: No module named 'pkg_resources'
```

uv gives this hint: add `pkg_resources` to `[tool.uv.extra-build-dependencies]`, or install it and use `--no-build-isolation`.

Ticket 58 measured this on 4 old commits (pytest-7220, pytest-5227, pluggy 0.13.1, xarray v0.16.0). The failure occurs with and without `SETUPTOOLS_SCM_PRETEND_VERSION`. The fallback then gives wrong environments:

- pluggy 0.13.1 gets the newest pytest: `ImportError: cannot import name 'HookimplOpts' from 'pluggy'`.
- xarray v0.16.0 gets numpy 2: `np.unicode_` was removed.
- pytest-7220 gets a new pluggy. The dry-run trace `33fc3e7d` shows `PytestPluginManager.__init__() takes 1 positional argument but 2 were given` 54 times.

A second probe also took setuptools-scm out of the date limit (`--exclude-newer-package setuptools-scm=2100-01-01`). All 4 commits still failed with the same last line. The full traceback was not read, so it is not known which build imports `pkg_resources` in that run.

## Design

1. Read the full traceback of the run with both packages out of the date limit. Find the package that imports `pkg_resources`.
2. Measure these options on the 4 commits:
   - Limit setuptools to the last release that has `pkg_resources`, instead of the newest one. Ticket 53 needs a setuptools from 2022 or later for the editable install.
   - Take setuptools-scm out of the date limit too, if step 1 shows that another package causes the error.
3. Choose the option that builds the most environments. A small test run must pass on each: for example `testing/test_hookcaller.py` for pluggy.

## Acceptance

- [x] The Comments give the result of each option on the 4 commits.
- [x] On the 4 commits, the pinned install builds the environment, and the fallback does not run.
- [x] `uv run pytest -q` passes.

## Comments

### 2026-10-19 — what ticket 59 changes for this ticket

Ticket 59 builds each old commit on the Python of its date. It measured 3 of the 4 commits of this ticket:

- pytest-7220 (2020-05-30) now gets `python:3.8-slim`. The pinned install builds the environment, and the fallback does not run. The newest setuptools for 3.8 still has `pkg_resources`, so the error of this ticket does not occur. The environment has pluggy 0.13.1, and `testing/test_mark.py` gives 89 passed, 1 failed.
- xarray v0.16.0 (`56769263`, 2020-07-11) now gets `python:3.8-slim`. The pinned install builds the environment, and the fallback does not run. `xarray/tests/test_utils.py` gives 34 passed.
- pytest-5227 (2019-05-07) now gets `python:3.7-slim`. The pinned install still fails, but with a new cause: `there are no versions of atomicwrites`. PyPI now has only `atomicwrites` 1.4.1 (2022-07-08), so `--exclude-newer 2019-05-07` leaves no version. A fix is `--exclude-newer-package atomicwrites=2100-01-01`, or a general retry that removes the date limit of a package that has no version before the date.

So 2 of the 4 commits need no fix now, and 1 has a new cause. pluggy 0.13.1 (2019-11) was not measured again: probe it first. On the code of ticket 59 it gets `python:3.7-slim`, and the newest setuptools for 3.7 (68.0) still has `pkg_resources`.

### 2026-10-19 — done

**What was built.** Two changes to the old-commit install in `pinned_install` (`slopgate/sandbox.py`):

- For a setuptools-scm repo, the build uses setuptools at most `max(commit date, SETUPTOOLS_EDITABLE)`. `SETUPTOOLS_EDITABLE` (`slopgate/config.py`) is 2022-08-12: setuptools 64.0 (2022-08-11) is the first release with `build_editable`. Before, the build used the newest setuptools.
- For every old commit, `atomicwrites` is out of the date limit (`--exclude-newer-package atomicwrites=2100-01-01`). PyPI re-uploaded every `atomicwrites` file on 2022-07-09, so a date limit leaves no file.

**The cause.** The newest setuptools in the build, next to a date-limited setuptools-scm and `packaging`, gives 3 different errors:

| Error | Commits | Python |
|---|---|---|
| `No module named 'pkg_resources'` (from `setuptools_scm/version.py`) | xarray v0.18.0, pluggy 1.0.0 | 3.9 |
| `canonicalize_version() got an unexpected keyword argument 'strip_trailing_zero'` | pytest 7.0.0, xarray v2022.06.0 | 3.10 |
| `no such comparison operator ">=>="` (`setuptools>=>=42.0` in `setup.cfg`) | pytest 6.2.0 | 3.8 |

Ticket 59 hid the first error on the 4 commits of this ticket: they get Python 3.7 or 3.8, and the newest setuptools there still has `pkg_resources`. So the probe also used 5 setuptools-scm commits from 2020-12 to 2022-07, which get Python 3.8 to 3.10.

**The atomicwrites fix changes non-scm installs (user decision).** Without the fix, uv does not fail on a commit from 2018-05 to 2019. It silently picks an older pytest that does not need `atomicwrites`. django 2019-02 got pluggy 0.6.0 (pytest about 3.5). With the fix, it gets pluggy 0.8.1, the pytest of its date. `utils_tests.test_text` passes with both. xarray 2019-10-12: pluggy 0.6.0 before, 0.13.0 after, and `xarray/tests/test_utils.py` gives 25 passed with both. The user chose to apply the fix to all old commits.

**Measured results (ConTree, 2026-10-19).** Each row builds with the gate's own `commands()` and `Contree.prepare()`, without the `|| pip install -e .` fallback. Then a small test file of the repo runs. The options a to d include the `atomicwrites` fix.

| Commit | Date | Python | Before | Only atomicwrites | a. setuptools before 81 | b. setuptools ≤ 2023-01-15 (65.7) | c. setuptools ≤ max(date, 2022-08-12) | d. setuptools-scm out of the date limit |
|---|---|---|---|---|---|---|---|---|
| pytest-5227 | 2019-05-07 | 3.7 | fail (`atomicwrites`) | ok | ok | ok | ok | ok |
| pytest-7220 | 2020-05-30 | 3.8 | ok | ok | ok | ok | ok | ok |
| pluggy 0.13.1 | 2019-11-21 | 3.7 | ok | ok | ok | ok | ok | ok |
| xarray v0.16.0 | 2020-07-11 | 3.8 | ok | ok | ok | ok | ok | ok |
| pytest 6.2.0 | 2020-12-12 | 3.8 | fail | fail | fail | fail | fail | fail |
| xarray v0.18.0 | 2021-05-06 | 3.9 | fail | fail | ok | ok | ok | fail |
| pluggy 1.0.0 | 2021-08-25 | 3.9 | fail | fail | ok | ok | ok | fail |
| pytest 7.0.0 | 2022-02-03 | 3.10 | fail | fail | fail | ok | ok | fail |
| xarray v2022.06.0 | 2022-07-22 | 3.10 | fail | fail | fail | ok | ok | fail |
| **Builds** | | | 3 of 9 | 4 of 9 | 6 of 9 | 8 of 9 | 8 of 9 | 4 of 9 |

- Option a (the ticket's first option) fixes only the `pkg_resources` error. setuptools 71 and later prefer the installed `packaging`, so the `strip_trailing_zero` error stays.
- Options b and c tie. c follows the commit date, so an scm commit from 2023 keeps a setuptools of its date. A fixed cap would give it a setuptools older than its date. c is in the code.
- Option d: the error is not in setuptools-scm alone. A new setuptools-scm with the newest setuptools still fails.

The final code, on 11 commits (the 9 above, django 2019-02, and xarray 2019-10-12): 10 build with the pinned install and pass the small test. On the 4 commits of this ticket, the fallback does not run:

| Commit | Small test |
|---|---|
| pytest-5227 | `testing/test_mark.py`: 73 passed, 1 xfailed (before: fallback) |
| pytest-7220 | `testing/test_mark.py`: 89 passed, 1 failed, 1 xfailed (the same as ticket 59) |
| pluggy 0.13.1 | `testing/test_hookcaller.py`: 17 passed |
| xarray v0.16.0 | `xarray/tests/test_utils.py`: 34 passed, 3 skipped |
| xarray v0.18.0 | 36 passed, 3 skipped (before: fallback) |
| pluggy 1.0.0 | 19 passed (before: fallback) |
| pytest 7.0.0 | 89 passed, 1 xfailed (before: fallback) |
| xarray v2022.06.0 | 39 passed, 3 skipped (before: fallback) |
| django 2019-02 | `utils_tests.test_text` OK |
| xarray 2019-10-12 | 25 passed, 3 skipped |
| pytest 6.2.0 | build fails (ticket 71) |

A build takes 13 s to 24 s.

**Worked example.** xarray v0.18.0 (`8b028e3f`, 2021-05-06) with one added function `first_tag` (nested `if` blocks in a `try` with `except Exception: pass`) in `xarray/core/utils.py`. Dry run: `slopgate review --repo <clone> --base 8b028e3f --head c0f65910 --dry-run`.

- Before: the pinned install stopped with `ModuleNotFoundError: No module named 'pkg_resources'`. The fallback `pip install -e .` installed the newest dependencies.
- After: `commands` gives `python:3.9-slim` and `... uv pip install ... --exclude-newer 2021-05-06T12:41:17-06:00 --exclude-newer-package setuptools=2022-08-12T00:00:00+00:00 --exclude-newer-package atomicwrites=2100-01-01 -e . pytest --reinstall && ...`. Trace `b67a5728` (project `slopgate-gate`): `sandbox.prepare` 17.1 s with no error. The repo suite baseline ran for 72.5 s with exit 0. The test agent wrote its file in 9 commands (58.7 s). The gate rejected the rewrite: `rewrite leaves the slop: swallowed_error`. This is correct: the broad `except` hides an error of any iterable, so a rewrite cannot remove it and keep the behavior.

A second dry run on pluggy 1.0.0 (trace `748d8e97`): the install worked, and the repo suite gave 81 passed. The test agent stopped at the step limit with `coverage has no data for src/pluggy/_tracing.py`. The cause is pluggy's own `.coveragerc`: `include = pluggy/*`, but the code is in `src/pluggy/`. Ticket 70 has it.

**Traces.** No trace has status `ERROR`. No model call returned `finish_reason: "length"`. No `sandbox.prepare` took more than 60 s.

**Offline tests.** 4 new or changed tests in `tests/test_review.py`. `uv run pytest -q`: 455 passed.

The dry runs above used the first version of the code, with the bare date `2022-08-12` as the limit. After the review fixes, the probe ran again on the final code (timestamp limit `2022-08-12T00:00:00+00:00`): the same 10 of 11 commits build and give the same test counts.

**Code review (Opus, thermo-nuclear).**

1. `max(since, "2022-08-12")` compared strings and ignored the UTC offset. A bare date also makes uv use the local time. Applied: `SETUPTOOLS_EDITABLE` is a timestamp in `slopgate/config.py`, `max` compares with `datetime.fromisoformat`, and a test covers a date near the floor.
2. The old comment said that a setuptools from before 2022 cannot build an editable install. Applied: one comment with the 64.0 boundary.
3. The `atomicwrites` fix breaks the Constraint as written. Applied: the Constraint names the user decision.
4. The ticket had no results. Applied: this entry.
5. Ticket 71 gave the wrong setuptools range. Applied.
6. No test checked `atomicwrites` for an scm commit. Applied.
7. The `CLAUDE.md` code map did not have the new rules. Applied.

**Known limits.**

- pytest 6.2.0 does not build (ticket 71).
- A repo `.coveragerc` that does not match a `src/` layout hides the target from coverage (ticket 70).
- The `atomicwrites` fix names one package. Another package that re-uploaded its old files would fail the same way. A general retry would remove the date limit of a package with no file before the date.
- The floor picks setuptools 64.0.0, the first release with `build_editable`. It worked on the 5 commits that use it.

