# 70 — A repo `.coveragerc` that does not match a `src/` layout gives "coverage has no data"

## Summary

- **Goal:** Get the coverage data of the target file when the repo's own coverage configuration excludes it. Now the test agent cannot see its missed branches, and the gate rejects the function.
- **Checkable finish condition:** On pluggy 1.0.0 (`4259fdd7`, 2021-08-25) with one added function in `src/pluggy/_tracing.py`, the dry run gets the missed branches of the function, and the rejection reason is not `coverage has no data`.
- **Evidence:** Before: the ticket 68 dry run (2026-10-19, see Context). After: the same dry run.
- **Constraints:** Keep the repo's other coverage settings (for example `parallel = 1`, see `COMBINE` in `slopgate/review.py`).

**Blocked by:** 68

**Status:** ready-for-agent

**Type:** bug.

## Context

Ticket 68 made the pinned install of pluggy 1.0.0 work. The dry run then rejected the added function `first_tag` with `step limit: coverage has no data for src/pluggy/_tracing.py` (trace `748d8e97`, project `slopgate-gate`). The agent's tests passed (`3 passed`), but each `coverage run` printed `CoverageWarning: No data was collected.` The agent used its steps to try `--source=src` and other options.

The cause is the repo's `.coveragerc`. `python -m coverage debug config` in the sandbox shows `run_include: pluggy/*`. The code is in `src/pluggy/`, so the pattern matches no file. The repo moved to a `src/` layout and kept the old pattern.

The gate runs `python -m coverage run --branch -m pytest -q <test file>` (`slopgate/review.py`). It does not set the include pattern, so the repo's pattern wins.

## Design

1. Measure how often this happens: run `coverage debug config` on the old commits of ticket 10.
2. Option: pass `--include=<target file>` to `coverage run`. The command-line option replaces the `include` of the configuration file. Check that `--include` and a repo `source` setting do not conflict (coverage ignores `--include` when `source` is set).
3. Measure on pluggy 1.0.0 and on one repo whose coverage configuration works now (for example xarray v0.18.0).

## Acceptance

- [ ] On pluggy 1.0.0, the dry run gets the missed branches of `first_tag`.
- [ ] A repo whose coverage works now gives the same missed branches as before.
- [ ] `uv run pytest -q` passes.
