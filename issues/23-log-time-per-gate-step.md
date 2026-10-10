# 23 — Log the time of each gate step

## Summary

- **Goal:** Show the 3 slowest steps of a review in the summary comment on the pull request. Example: "Slowest: sandbox setup 6m 10s, index 4m 2s, repo suite money 2m 1s."
- **Checkable finish condition:** `result["timings"]` holds the steps with seconds as numbers, and the summary has a "Slowest:" line with at most 3 steps. `uv run pytest -q` passes.
- **Evidence:** Before: the review of PR #9 took 33 min 53 s, but the log had no time for each step, so the cause is not known. After: a test pull request on the demo repo shows the "Slowest:" line, and the numbers go into the Comments of ticket 25.
- **Constraints:** Ticket 32 covers the time of each step when tracing is on, so this ticket adds only the `Slowest:` line for runs without tracing. A result with only `timings` is still empty, so no comment is posted. Use the existing `duration` helper in `slopgate/github.py`.

Ticket 32 (Phoenix tracing) gives the time of each step when tracing is on. So this ticket adds only the `Slowest:` line, for runs without tracing. The parts that the spans cover are removed below.

**Blocked by:** None — can start immediately.

**Status:** ready-for-agent

## Context

The Slopgate review of PR #9 took 33 min 53 s. The review step itself took 32 min 55 s. The model tokens cost $0.0095 (20,620 tokens), so the time is not spent on model calls. The log has no time for each step, so the cause is not known. These are the likely costs, but they are not measured:

1. The sandbox setup. It installs the repo with torch on each review.
2. The index build of the base commit (`index.build` in `slopgate/index.py`). It embeds every function with CodeRankEmbed on a 2-core runner.
3. The full repo test suite. The gate runs it once after each rewrite that passes its characterization tests (the `test` command in the loop of `review` in `slopgate/review.py`).

Ticket 25 (faster proof) needs these numbers before it starts.

## Design

1. Add one small timing helper, for example a context manager `step(name)` in `slopgate/review.py`. It adds `(name, seconds)` to a list in the result, `result["timings"]`.
2. Time these steps:
   - `diff`: find the changed functions.
   - `index`: build the base index.
   - `duplicates`: the embedding search and the Super same-job calls, for all functions.
   - `classify`: the Lightning calls, for all functions.
   - `sandbox setup`: `sandbox.prepare`.
   - For each candidate: `tests <function>`, `rewrite <function>`, `repo suite <function>`.
3. `summary` in `slopgate/github.py` adds one line with the 3 slowest steps, for example "Slowest: sandbox setup 6m 10s, index 4m 2s, repo suite money 2m 1s." Use the existing `duration` helper in that file.
4. `publish` must ignore `timings` when it decides whether the result is empty.

## Acceptance

- [ ] `result["timings"]` holds the same steps, with seconds as numbers.
- [ ] The summary body has a "Slowest:" line with at most 3 steps.
- [ ] A result with only `timings` is still treated as empty: no comment is posted.
- [ ] `uv run pytest -q` passes.

## How to use the result

After merge, open a test pull request on the demo repo and read the "Slowest:" line. Record the numbers in the Comments of ticket 25.

## Comments
