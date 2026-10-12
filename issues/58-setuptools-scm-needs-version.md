# 58 — A repo that takes its version from the git history does not install in the sandbox

## Summary

- **Goal:** Install a repo whose version comes from `setuptools-scm`. Example: `pytest-dev/pytest` fails with `LookupError: setuptools-scm was unable to detect version for /repo`.
- **Checkable finish condition:** A dry run on a pull request of `pytest-dev/pytest` builds the test environment, and `import _pytest` works in the sandbox.
- **Evidence:** Before: ticket 53, trace `42ff0bf2` in the Phoenix project `slopgate-gate` (2026-10-12): `sandbox.prepare` failed after 16 s with the error above. The same failure occurs with the code of `main`. After: the dry run.
- **Constraints:** Do not change the install of a repo that does not use `setuptools-scm`. `.slopgate.toml` still wins.

**Blocked by:** —

**Status:** ready-for-agent

**Type:** bug.

## Context

The sandbox gets the repo as the output of `git archive`. The archive has no `.git` folder, so `setuptools-scm` cannot read the version. The build stops.

`setuptools-scm` and `hatch-vcs` both read the environment variable `SETUPTOOLS_SCM_PRETEND_VERSION`. With it, no `.git` folder is needed.

## Design

1. Find out which build tools the repo uses: `setuptools_scm` or `setuptools-scm` in `pyproject.toml` or `setup.py`, and `hatch-vcs`.
2. For such a repo, set `SETUPTOOLS_SCM_PRETEND_VERSION=0.0.0` for the install command only.
3. Measure it on `pytest-dev/pytest` and on 2 other repos that use `setuptools-scm` (for example `pypa/pip` and `pydata/xarray` of a later year).

## Acceptance

- [ ] The Comments give the result on 3 repos.
- [ ] A dry run on a `pytest-dev/pytest` pull request builds the environment.
- [ ] `uv run pytest -q` passes.
