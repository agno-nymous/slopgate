# 75 — The gate gets no coverage data on `psf__requests-3362`

## Summary

- **Goal:** Find why `coverage run` gives no data for `requests/*.py` in the sandbox of `psf__requests-3362`, and fix it. Now the test agent cannot see its missed branches, and the gate rejects all 3 items of the instance.
- **Checkable finish condition:** A rerun of `psf__requests-3362` (see ticket 72, Comments) has no item with the reason `coverage has no data`.
- **Evidence:** Before: ticket 72 live run of 2026-10-25. 3 of 3 items ended as `step limit: coverage has no data for requests/adapters.py` (and `cookies.py`, `models.py`). Trace `417788f9` in the project `slopgate-bench`. After: the same run.
- **Constraints:** Keep the repo's own coverage settings. The cause is not known.

**Blocked by:** 72

**Status:** ready-for-agent

**Type:** bug.

## Context

The clone (`~/.cache/slopgate/bench/swebench/psf__requests-3362`) has no `.coveragerc`, `setup.cfg`, or `tox.ini`. So ticket 70 (a `.coveragerc` include pattern) does not explain it. The sandbox installs pytest 2.9 and Python 3.6 or older pins from 2016-06. The `gate.characterize` spans took 81 s to 86 s each.

## Design

1. Open the three `gate.characterize` spans of trace `417788f9` and read the agent commands. Find out which `requests` the tests import (the repo, or a copy in `site-packages`), and what `coverage debug config` shows.
2. Fix the cause. If the install is not editable, make the tests import the repo files.
3. Add an offline test if the fix is in code.

## Acceptance

- [ ] The cause is written in Comments.
- [ ] `psf__requests-3362` has no `coverage has no data` rejection.
- [ ] `uv run pytest -q` passes.
