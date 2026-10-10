# 33 — Add a time limit to each sandbox run

## Summary

- **Goal:** Each sandbox run stops after a time limit. A run that waits for input or loops forever then fails with a clear reason, and the gate goes on to the next function. Example: a model-written call `f(input())` blocks the run today.
- **Checkable finish condition:** A Local sandbox run of `python -c "while True: pass"` returns after the limit with "timed out after <n> s". A run of `python -c "input()"` returns at once with a failure. `uv run pytest -q` passes.
- **Evidence:** Before: `shell` in `slopgate/sandbox.py` has no `timeout`, and during ticket 20 one offline test run stalled for about 10 minutes. After: the tests above pass, a live Contree run of `sleep <limit + 5>` stops at the limit, and the slowest normal run time is in the Comments next to the chosen limit.
- **Constraints:** Set `SANDBOX_TIMEOUT` in `slopgate/config.py` well above the slowest normal run, and measure that run first. Pass `stdin=subprocess.DEVNULL` and return `(124, "timed out after <n> s")`. If the Contree client has no timeout option, stop and tell the user.

**Blocked by:** None — can start immediately.

**Status:** done

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

- [x] A Local sandbox run of `python -c "input()"` returns at once with a failure, and does not wait for stdin.
- [x] A Local sandbox run of `python -c "while True: pass"` returns after the limit with "timed out after <n> s". The test sets a short limit.
- [x] A characterization test that never ends gives a `rejected` entry, and the review goes on to the next function. (Since ticket 41, the agent writes test files, not calls. A call such as `f(input())` gets EOFError at once, as the first box shows.)
- [x] Contree: a run of `sleep <limit + 5>` stops at the limit (live test, `-m live`).
- [x] The measured time of the slowest normal run is in the Comments, next to the chosen limit.
- [x] `uv run pytest -q` passes.

## Comments

### 2026-10-10 — Part of the work is done in ticket 41

Ticket 41 added a time limit for the commands of the test agent only:

- `shell` in `slopgate/sandbox.py` takes a `timeout`. It starts the command in its own process group, passes `stdin=subprocess.DEVNULL`, kills the whole group at the limit, and returns `(124, "<output>\ntimed out after <n> s")`. `LocalSession.execute` uses it.
- `ContreeSession.execute` runs each command as `timeout -k 5 <n> sh -c <command>`, and gives the ConTree client a wait of `<n> + 60` s. A hung command then returns exit 124 before the client gives up.
- The limit is the time that is left of the agent's 120 s (`AGENT_SECONDS` in `slopgate/config.py`).

Still open in this ticket: `Local.run` and `Contree.run` have no limit. These runs are the judge (`check`), the rewrite proof, and the repo tests. Use the same `shell(..., timeout)` and the same `timeout -k 5` wrapper there.

### 2026-10-10 — Done

**What was built.**

- `SANDBOX_TIMEOUT = 600` (seconds) in `slopgate/config.py`.
- `Local.run` calls `shell(cmd, work, SANDBOX_TIMEOUT)`. `shell` already gave the command no stdin and killed its process group at the limit (ticket 41).
- `Contree.run` runs the command as `timeout -k 5 600 sh -c <cmd>`, and gives the ConTree client a wait of 660 s. The new function `bounded` makes this wrapper for `Contree.run` and for `ContreeSession.execute`.
- `Contree.run` decides a timeout by the elapsed time, not by the exit code. A command can exit 124 by itself. A command that ignores SIGTERM is killed after 5 s and exits 137. A run that reaches the limit returns `(124, "<output>\ntimed out after 600 s")`, the same result that `Local.run` gives.
- `check` in `slopgate/review.py` stops after the first run on exit 124, with the reason "characterization tests time out: <tail>". Before, it always ran the tests a second time, so a test that never ends cost 2 × the limit.

**Worked example.** The test file below loops forever. Ticket 33 ran `check` with `Local` and a limit of 2 s:

```python
def test_double():
    while True:
        double(2)
```

The output was `'characterization tests time out: timed out after 2 s'`, after 2.0 s. Before this ticket, `Local.run` had no limit, so this run did not end.

**Measured results.**

| Run | Time |
|---|---|
| Slowest normal run: this repo's test suite in ConTree (274 tests, 3 runs) | 158.4 s, 158.6 s, 159.0 s |
| `slopgate-demo` test suite in ConTree (3 runs) | 1.6 s to 2.6 s |
| Chosen limit `SANDBOX_TIMEOUT` | 600 s (3.8 × the slowest run) |
| Live: `Contree.run` of `sleep 10` with the limit at 5 s | exit 124, "timed out after 5 s", after 7.1 s and 7.4 s in 2 runs (a `true` run took 1.1 s) |
| `Local.run` of `python -c "input()"` | EOFError at once |
| `uv run pytest -q` | 281 passed, 17 deselected, in 224.7 s |
| `pytest -m live -k contree` | 3 passed (the new test and the 2 ContreeSession tests) |

The stdin test runs `Local.run` in a child process whose stdin pipe stays open, because pytest gives its own children /dev/null as stdin. With `stdin=subprocess.DEVNULL` removed from `shell`, the test fails with `TimeoutExpired`. With it, the test passes.

**Known limits.**

- `prepare` (the install step) has no limit of its own. It runs no model-written code, and it runs once for each review. `Contree.prepare` stops at the SDK default of 1000 s (`operation_timeout` in contree-sdk 0.3.6) and raises `ContreeError`, so the review stops with no "could not build test environment" entry. `Local.prepare` has no limit. A cold install of large packages can take more than 600 s, so a limit there needs its own value.
- The Context of this ticket said that `Contree.run` had no limit. That is not fully correct: the SDK default stopped it after 1000 s with `ContreeError`, and `review` reported this as an internal error.
- On a timeout, `ContreeSession.execute` (the agent's command) returns exit 124 with no "timed out after" line. `LocalSession.execute` adds the line. The agent sees the exit code in both cases.
- A rewrite that loops can still cost up to 4 runs at the limit: the proof and the Ultra retry, each with the characterization tests and the repo tests.
