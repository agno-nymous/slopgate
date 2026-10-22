# 72 — The benchmark test command breaks pytest 2.9

## Summary

- **Goal:** Make the gate review `psf__requests-3362` in the SWE-bench benchmark. The environment builds, but the test command that `select` writes into `.slopgate.toml` carries `--continue-on-collection-errors`. pytest 2.9 rejects this flag, so the collection check fails and the gate posts `NO_ENVIRONMENT` for all 3 items.
- **Checkable finish condition:** After `python -m bench.swebench run` and `report`, `psf__requests-3362` has no `no_environment` item.
- **Evidence:** Before: ticket 67 benchmark of 2026-10-21. All 3 `infrastructure_errors` are `psf__requests-3362`, with `unrecognized arguments: --continue-on-collection-errors`. After: the next benchmark report.
- **Constraints:** Do not change the production default test command. `collect_error` already retries without the flag for the commands that it builds itself.

**Blocked by:** 67

**Status:** ready-for-agent

**Type:** bug.

## Context

`bench/swebench.py` line 90 (`PYTEST`) and line 422 put `--continue-on-collection-errors` in the test command of each instance. The flag exists since pytest 3.0. The gate runs this command as it is, so an older pytest fails.

## Design

1. Choose one of two fixes: the benchmark drops the flag for instances where the pinned pytest is older than 3.0, or the gate removes the flag and retries when pytest says `unrecognized arguments`.
2. Add an offline test for the chosen fix.

## Acceptance

- [ ] `psf__requests-3362` reaches the characterization step in the benchmark.
- [ ] `uv run pytest -q` passes.
