# 33 — Add a time limit to each sandbox run

## Summary

- **Goal:** Each sandbox run stops after a time limit. A run that waits for input or loops forever then fails with a clear reason, and the gate goes on to the next function. Example: a model-written call `f(input())` blocks the run today.
- **Checkable finish condition:** A Local sandbox run of `python -c "while True: pass"` returns after the limit with "timed out after <n> s". A run of `python -c "input()"` returns at once with a failure. `uv run pytest -q` passes.
- **Evidence:** Before: `shell` in `slopgate/sandbox.py` has no `timeout`, and during ticket 20 one offline test run stalled for about 10 minutes. After: the tests above pass, a live Contree run of `sleep <limit + 5>` stops at the limit, and the slowest normal run time is in the Comments next to the chosen limit.
- **Constraints:** Set `SANDBOX_TIMEOUT` in `slopgate/config.py` well above the slowest normal run, and measure that run first. Pass `stdin=subprocess.DEVNULL` and return `(124, "timed out after <n> s")`. If the Contree client has no timeout option, stop and tell the user.

**Blocked by:** None — can start immediately.

**Status:** ready-for-agent

## Context

The code review of ticket 20 (2026-10-08) found that sandbox runs have no time limit:

- `shell` in `slopgate/sandbox.py` calls `subprocess.run` with no `timeout`. The child process gets the parent's stdin.
- `Contree.run` calls `.wait()` with no limit.

The gate runs code that the model writes. `record` evaluates the call arguments that Super writes, and the characterization tests run the target. Since ticket 20, the gate also records every call in a script reply, so more model-written arguments run. An argument such as `input()` or `list(iter(int, 1))`, or a target that loops forever on one input, blocks the run with no end:

- On a terminal, a local `slopgate review` waits forever.
- On the self-hosted runner, the job runs until GitHub cancels it.

During ticket 20, one offline test run stalled for about 10 minutes while a new test failed. The cause was not found.

## Design

1. Add `SANDBOX_TIMEOUT` (in seconds) to `slopgate/config.py`. Measure the slowest normal run first: the repo test suite of this repo and of `slopgate-demo` in Contree. Set the limit well above it.
2. In `shell`, pass `stdin=subprocess.DEVNULL` and `timeout=SANDBOX_TIMEOUT`. Catch `subprocess.TimeoutExpired`, and return `(124, "timed out after <n> s")`.
3. Give `Contree.run` the same limit. Check whether the Contree client has a timeout option on `run` or on `wait`. If it has none, stop and tell the user.
4. The callers already turn a failed run into a `rejected` entry. Check that the reason holds "timed out after <n> s".

## Acceptance

- [ ] A Local sandbox run of `python -c "input()"` returns at once with a failure, and does not wait for stdin.
- [ ] A Local sandbox run of `python -c "while True: pass"` returns after the limit with "timed out after <n> s". The test sets a short limit.
- [ ] A fake reply with the call `f(input())` gives a `rejected` entry, and the review goes on to the next function.
- [ ] Contree: a run of `sleep <limit + 5>` stops at the limit (live test, `-m live`).
- [ ] The measured time of the slowest normal run is in the Comments, next to the chosen limit.
- [ ] `uv run pytest -q` passes.

## Comments
