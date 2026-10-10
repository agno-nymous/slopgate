# 25 — Faster proof: candidates in parallel, and one repo suite run

## Summary

- **Goal:** The gate reviews a pull request faster. It proves candidates in parallel, and it runs the full repo test suite once for all accepted rewrites. Example: the review of PR #9 took 33 min.
- **Checkable finish condition:** With 3 candidates and a fake sandbox that sleeps 1 s for each run, the review takes less than half the time it takes today. With 3 accepted rewrites and a passing repo suite, the suite runs once. `uv run pytest -q` passes.
- **Evidence:** Before: the review of PR #9 took 33 min, and Phoenix span times (ticket 32) must show that the proof steps are the slow part. After: the review time of a demo pull request, before and after, is in the Comments.
- **Constraints:** Wait for ticket 32. If the sandbox setup or the index build is the slow part, record that in the Comments and stop. Use a `ThreadPoolExecutor(8)`, wrap the worker with `trace.bind`, and keep the result order the same. Reject a rewrite that fails alone with "rewrite fails repo tests".

**Blocked by:** 32. Phoenix span times show where the review time goes, so this ticket waits for them.

**Status:** ready-for-agent

## Context

The loop in `review` (`slopgate/review.py`) handles one candidate at a time. A comment there says: "one trial at a time (well under the cap of 8); a thread pool of 8 when review time matters". Review time now matters: the review of PR #9 took 33 min.

For each candidate, the loop does these steps in order:

1. Write characterization tests and prove them on the original code (`characterize`).
2. Ask for a rewrite and check its rules.
3. Run the characterization tests on the rewrite.
4. Run the full repo suite on the rewrite (`python -m pytest -q`, or the `test` command from `.slopgate.toml`).

Each sandbox run starts from the same checkpoint and writes its own files, so candidates do not share state.

Run one traced review (ticket 32) and read the span times in Phoenix. Use these numbers to confirm that steps 1 to 4 are the slow part before you start. If the sandbox setup or the index build is the slow part, record that in the Comments and stop. Then this ticket needs a new design.

## Design

1. Run the loop body for each candidate in a `ThreadPoolExecutor(8)`. Wrap the worker function with `trace.bind`, so that its spans keep `gate.review` as their parent (ticket 32). Keep the order of the results the same as the order of the candidates.
2. Remove step 4 from the loop. After the loop, apply all accepted rewrites together and run the repo suite once.
3. If that run passes, keep all rewrites.
4. If that run fails, run the repo suite for each rewrite alone, as the loop does today. Reject each rewrite that fails alone, with the reason "rewrite fails repo tests". Two rewrites in one file must be spliced into the file together. Two rewrites can each pass alone and fail together. In that case, keep the first one and reject the second one with the reason "rewrite conflicts with another rewrite".
5. Keep `usage` in `slopgate/llm.py` correct across threads. `list.append` is safe in CPython, but check it.

## Acceptance

- [ ] With 3 candidates and a fake sandbox that sleeps 1 s for each run, the review takes less than half the time it takes today.
- [ ] With 3 accepted rewrites and a passing repo suite, the repo suite runs once.
- [ ] With 3 accepted rewrites where one breaks the repo suite, only that one is rejected, with the reason "rewrite fails repo tests".
- [ ] The order of `suggestions` and `rejected` is the same as with one thread.
- [ ] `uv run pytest -q` passes.
- [ ] Record the review time of a demo pull request before and after this change in the Comments.

## Comments
