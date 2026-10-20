# 71 — An old commit with a malformed `setup_requires` does not build

## Summary

- **Goal:** Build the test environment of an old commit whose `setup.cfg` has a requirement that the new `packaging` rejects. pytest at 6.2.0 has `setup_requires = setuptools>=>=42.0`.
- **Checkable finish condition:** On pytest 6.2.0 (`e7073afe`, 2020-12-12), the pinned install builds the environment, and `testing/test_mark.py` passes.
- **Evidence:** Before: the ticket 68 probes (2026-10-19, see Context). After: the same probe.
- **Constraints:** Do not change the install of a commit that builds now. `.slopgate.toml` still wins.

**Blocked by:** 68

**Status:** ready-for-agent

**Type:** bug.

## Context

Ticket 68 measured 5 setuptools options on pytest 6.2.0. All 5 failed with the same error:

```
Call to `setuptools.build_meta.get_requires_for_build_editable` failed: no such comparison operator ">=>=", must be one of ~= == != <= >= < > ===
    setuptools>=>=42.0
```

The typo is in the repo's `setup.cfg`. An old `packaging` accepted it as a legacy specifier. The build setuptools of the 5 options was the newest one, the newest before 81.0, 65.7 or older, and 64.0 (the floor of ticket 68). All rejected the typo. It is not known which `packaging` the build used.

The plain fallback `pip install -e .` probably builds it, but with the newest dependencies. SWE-bench has pytest instances from 2020-12 to 2021, so the typo can affect ticket 10.

## Design

1. Find the first and the last pytest commit with the typo.
2. Find which `packaging` the build environment uses, and why it is not the vendored one.
3. Measure options: a setuptools of the commit date for the build, or an edit of `setup.cfg` in the sandbox before the install.

## Acceptance

- [ ] The Comments give the commit range of the typo and the result of each option.
- [ ] On pytest 6.2.0, the pinned install builds the environment.
- [ ] `uv run pytest -q` passes.
