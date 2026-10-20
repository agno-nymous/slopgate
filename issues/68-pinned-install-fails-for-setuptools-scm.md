# 68 — The old-commit install fails for every repo that uses setuptools-scm

## Summary

- **Goal:** Make the pinned install of ticket 53 work for an old commit of a repo that uses `setuptools-scm`. Now the pinned install fails, and the unpinned fallback `pip install -e .` installs the newest dependencies.
- **Checkable finish condition:** On pytest-7220, pytest-5227, pluggy 0.13.1, and xarray v0.16.0, the pinned install part of the command (without `|| pip install -e .`) builds the environment.
- **Evidence:** Before: the ticket 58 probes on 2026-10-18 (see Context). After: the same probes.
- **Constraints:** Do not change the install of a repo that does not use `setuptools-scm`. `.slopgate.toml` still wins.

**Blocked by:** 58

**Status:** ready-for-agent

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

- [ ] The Comments give the result of each option on the 4 commits.
- [ ] On the 4 commits, the pinned install builds the environment, and the fallback does not run.
- [ ] `uv run pytest -q` passes.

## Comments

### 2026-10-19 — what ticket 59 changes for this ticket

Ticket 59 builds each old commit on the Python of its date. It measured 3 of the 4 commits of this ticket:

- pytest-7220 (2020-05-30) now gets `python:3.8-slim`. The pinned install builds the environment, and the fallback does not run. The newest setuptools for 3.8 still has `pkg_resources`, so the error of this ticket does not occur. The environment has pluggy 0.13.1, and `testing/test_mark.py` gives 89 passed, 1 failed.
- xarray v0.16.0 (`56769263`, 2020-07-11) now gets `python:3.8-slim`. The pinned install builds the environment, and the fallback does not run. `xarray/tests/test_utils.py` gives 34 passed.
- pytest-5227 (2019-05-07) now gets `python:3.7-slim`. The pinned install still fails, but with a new cause: `there are no versions of atomicwrites`. PyPI now has only `atomicwrites` 1.4.1 (2022-07-08), so `--exclude-newer 2019-05-07` leaves no version. A fix is `--exclude-newer-package atomicwrites=2100-01-01`, or a general retry that removes the date limit of a package that has no version before the date.

So 2 of the 4 commits need no fix now, and 1 has a new cause. pluggy 0.13.1 (2019-11) was not measured again: probe it first. On the code of ticket 59 it gets `python:3.7-slim`, and the newest setuptools for 3.7 (68.0) still has `pkg_resources`.
