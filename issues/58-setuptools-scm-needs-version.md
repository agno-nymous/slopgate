# 58 — A repo that takes its version from the git history does not install in the sandbox

## Summary

- **Goal:** Install a repo whose version comes from `setuptools-scm`. Example: `pytest-dev/pytest` fails with `LookupError: setuptools-scm was unable to detect version for /repo`.
- **Checkable finish condition:** A dry run on a pull request of `pytest-dev/pytest` builds the test environment, and `import _pytest` works in the sandbox.
- **Evidence:** Before: ticket 53, trace `42ff0bf2` in the Phoenix project `slopgate-gate` (2026-10-12): `sandbox.prepare` failed after 16 s with the error above. The same failure occurs with the code of `main`. After: the dry run.
- **Constraints:** Do not change the install of a repo that does not use `setuptools-scm`. `.slopgate.toml` still wins.

**Blocked by:** —

**Status:** done

**Type:** bug.

## Context

The sandbox gets the repo as the output of `git archive`. The archive has no `.git` folder, so `setuptools-scm` cannot read the version. The build stops.

`setuptools-scm` and `hatch-vcs` both read the environment variable `SETUPTOOLS_SCM_PRETEND_VERSION`. With it, no `.git` folder is needed.

## Design

1. Find out which build tools the repo uses. Search `pyproject.toml`, `setup.py`, and `setup.cfg` for `setuptools_scm`, `setuptools-scm`, `use_scm_version`, and `hatch-vcs`. Use `git grep`: it reads bytes, so a setup file that is not UTF-8 does not stop the review.
2. For such a repo, set `SETUPTOOLS_SCM_PRETEND_VERSION` for the install command. The version is the last tag that `git describe --tags --abbrev=0 --match "v[0-9]*" --match "[0-9]*"` finds, without a leading "v". If there is no tag, or the tag is not a version, the version is `0.0.0`.
   - Changed on 2026-10-18, with the approval of the user: the ticket first set `0.0.0`. But `pytest-dev/pytest` has `minversion = "2.0"` in its own configuration at all 5 commits of ticket 10. So pytest 0.0.0 refuses to start, and every test run fails.
   - The command starts with `export ...;`. The variable then also reaches the `|| pip install -e .` fallback.
3. Do not set the variable if `.git_archival.txt` has a `describe-name:` line. `git archive` fills in that line, and setuptools-scm reads the exact version from it (for example `9.2.0.dev388+g420cf37a3`). The variable would make the version less exact.
4. Measure it on `pytest-dev/pytest` and on 2 other repos that use `setuptools-scm`.

## Acceptance

- [x] The Comments give the result on 3 repos.
- [x] A dry run on a `pytest-dev/pytest` pull request builds the environment.
- [x] `uv run pytest -q` passes.

## Comments

### 2026-10-18 — done

**What was built.** `commands` in `slopgate/sandbox.py` finds a repo that takes its version from the git history (`setuptools-scm` or `hatch-vcs`). For such a repo, the install command starts with `export SETUPTOOLS_SCM_PRETEND_VERSION=<last tag>;`. The sandbox gets the repo from `git archive`, which has no `.git` folder, so setuptools-scm cannot read the version without this variable. A repo with a `.git_archival.txt` that has a `describe-name:` line gets no variable: the archive gives the exact version already. A `.slopgate.toml` `setup` still replaces the whole command.

**Worked example.** The ticket 10 instance `pytest-dev__pytest-7220` (merge-base `56bf819c`, 2020-05-30). `commands` gives:

```
export SETUPTOOLS_SCM_PRETEND_VERSION=5.4.0; pip install -q uv && uv pip install --python "$(command -v python)" -q --exclude-newer 2020-05-30T14:33:22-03:00 ... || pip install -e .
```

- Before: `sandbox.prepare` failed with `LookupError: setuptools-scm was unable to detect version for /repo`.
- After: the environment builds in 14 s, and `import _pytest, pytest; print(pytest.__version__)` prints `5.4.0`.
- The dry run `slopgate review --repo <clone> --base 56bf819c --head 3b26c9c4 --dry-run` (trace `33fc3e7d`, project `slopgate-gate`): `sandbox.prepare` is OK in 14 s. The 3 candidates then stop at the step limit, because the characterization tests fail on the original code (see "Known limits").

**Measured results (ConTree, 2026-10-18).**

Repos at old commits, with no `.git_archival.txt`:

| Repo and commit | Before | After | Version |
|---|---|---|---|
| pytest, 5 commits of ticket 10 (2019-05 to 2021-02) | `LookupError` (ticket 10 run 2) | builds, 5 of 5 | 4.4.1, 5.0.1, 5.4.0, 5.4.0, 6.3.0.dev0 |
| pluggy 0.13.1 (2019-11) | `LookupError` | builds | 0.13.1 |
| xarray v0.16.0 (2020-07) | `LookupError` | builds | 0.16.0 |

Repos at HEAD, with a `.git_archival.txt` that has `describe-name:`:

| Repo | Before | After | Test file |
|---|---|---|---|
| pytest | `9.2.0.dev388+g420cf37a3` | same command, same version | 16 passed |
| pluggy | `1.7.1.dev5+g20950ae` | same command, same version | 23 passed |
| attrs (hatch-vcs) | `26.1.1.dev81` | same command, same version | 38 passed |
| xarray | `2026.9.1.dev97+g8da2d0d2` | same command, same version | config error before and after: `unrecognized arguments: --mypy-pyproject-toml-file` (a pytest plugin is missing; ticket 67) |

- Offline tests: 12 new tests in `tests/test_review.py`. `uv run pytest -q`: all pass.
- The Opus review found a regression in the first version: `git show` decoded each setup file as UTF-8, so a latin-1 `setup.py` stopped the review of every repo. `git grep` replaces it. The review also found that a nearer tag such as `latest` hid the release tag. `--match` fixes this. Both have a test.

**Known limits.**

- On the 4 old commits that I probed (pytest-7220, pytest-5227, pluggy 0.13.1, xarray v0.16.0), the pinned install fails, and the unpinned fallback `pip install -e .` builds the environment. The other 3 pytest commits are probably the same, but I did not probe them. The pinned install fails with `ModuleNotFoundError: No module named 'pkg_resources'`: the date-limited setuptools-scm imports `pkg_resources`, and the newest setuptools does not have it. This failure occurs with or without the variable. Ticket 68 has the details. So these environments get the newest dependencies:
  - pluggy 0.13.1 gets the newest pytest: `ImportError: cannot import name 'HookimplOpts' from 'pluggy'`.
  - xarray v0.16.0 gets numpy 2: `np.unicode_` was removed.
  - The pytest commits fail with `TypeError: required field "lineno" missing from alias` (old pytest on Python 3.10, ticket 59). The dry-run trace also shows `PytestPluginManager.__init__() takes 1 positional argument but 2 were given` 54 times. A new pluggy can cause that error, so a part of the failure can come from the fallback versions.
- The variable reaches every build in the install command, also a dependency that builds from an sdist with setuptools-scm. No measured install failed because of this. The code has a `shortcut:` comment with the upgrade path (`SETUPTOOLS_SCM_PRETEND_VERSION_FOR_<NAME>`).
- A clone without tags gives `0.0.0`. The CI checkout uses `fetch-depth: 0`, which fetches the tags.
