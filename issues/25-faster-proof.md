# 25 — Faster proof: candidates in parallel, and one repo suite run

## Summary

- **Goal:** The gate reviews a pull request faster. It proves candidates in parallel, and it runs the full repo test suite once for all accepted rewrites. Example: the review of PR #9 took 33 min.
- **Checkable finish condition:** With 3 candidates and a fake sandbox that sleeps 1 s for each run, the review takes less than half the time it takes today. With 3 accepted rewrites and a passing repo suite, the suite runs once. `uv run pytest -q` passes.
- **Evidence:** Before: the review of PR #9 took 33 min, and Phoenix span times (ticket 32) must show that the proof steps are the slow part. After: the review time of a demo pull request, before and after, is in the Comments.
- **Constraints:** Wait for ticket 32. If the sandbox setup or the index build is the slow part, record that in the Comments and stop. Use a `ThreadPoolExecutor(8)`, wrap the worker with `trace.bind`, and keep the result order the same. Reject a rewrite that fails alone with "rewrite fails repo tests".

**Blocked by:** 32. Phoenix span times show where the review time goes, so this ticket waits for them.

**Status:** done

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

- [x] With 3 candidates and a fake sandbox that sleeps 1 s for each run, the review takes less than half the time it takes today. (The test sleeps 0.25 s for each call, and it also counts the peak number of calls at the same time.)
- [x] With 3 accepted rewrites and a passing repo suite, the repo suite runs once.
- [x] With 3 accepted rewrites where one breaks the repo suite, only that one is rejected, with the reason "rewrite fails repo tests".
- [x] The order of `suggestions` and `rejected` is the same as with one thread.
- [x] `uv run pytest -q` passes.
- [x] Record the review time of a demo pull request before and after this change in the Comments.

## Comments

### 2026-10-10 — done

**Precondition: the proof is the slow part.** One traced review of demo PR #1 (`slopgate-demo`, base `0584a3a`, head `fc03fcc`) took 87 s. The `gate.function` spans took 68 s (78%). `sandbox.prepare` took 11 s. `gate.index` took 0.3 s. So the design of this ticket applies.

**What was built.**

- `review` gives each candidate its proof in a `ThreadPoolExecutor(WORKERS)`. `WORKERS = 8` is in `slopgate/config.py`. `threads.map` keeps the candidate order. The worker is wrapped with `trace.bind`.
- `prove` holds the `gate.function` span and the error handling. `trial` holds the steps of one candidate. It returns one outcome `(into, entry, suggested)`.
- The repo suite no longer runs inside the loop for a rewrite. `repo_suite` runs it once on all accepted rewrites together, in a `gate.repo_suite` span. Two rewrites in one file are spliced from the bottom up.
- If that run fails, each rewrite runs alone. A rewrite that fails alone gets "rewrite fails repo tests". If the rewrites that pass alone fail together, the gate keeps the first. It rejects the next with "rewrite conflicts with another rewrite".
- A broken suite run (for example, a sandbox error) rejects the accepted rewrites with "internal error". The other results stay.
- A wrapper and a duplicate still run the repo suite in their own proof.
- The Ultra retry now follows only a rule failure, leftover slop, or a failed characterization test. Before, it also followed a repo-suite failure.
- `llm.step` returns `(message, prompt_tokens)`. Before, `characterize` read `llm.usage[-1]`. With 8 threads, that entry can belong to another candidate, so the 150,000-token limit counted the wrong numbers.
- The `fake_llm` fixture sets `WORKERS` to 1, because its replies are a FIFO queue.
- `spec.md` (Proof) and the code map in `CLAUDE.md` describe the new flow.

**Worked example.** The range of PR #29 on this repo (base `9c44c2a`, head `1ba23b5`) has 2 candidates. I ran the same review twice in ConTree, with tracing on. The only change was `WORKERS`:

| WORKERS | review | candidate phase | `sandbox.prepare` | result |
|---|---|---|---|---|
| 1 | 386 s | 305 s | 53 s | 2 rejected, 2 notes |
| 8 | 226 s | 140 s | 59 s | 2 rejected, 2 notes |

The review took 41% less time. Both runs gave the same result. `summary` failed its characterization tests, and `review` stopped at the time limit (ticket 45).

**Demo PR #1, before and after.** Before: 90 s (87 s in the `gate.review` span). After: 138 s. The after run is not slower because of this change. Its `sandbox.prepare` took 32 s (11 s before), and its one `characterize` took 88 s (57 s before). The PR has 2 candidates, and one of them takes 95% of the candidate time. So a thread pool cannot make this PR faster. ConTree times vary by up to 3 times between runs.

**Tests.** `uv run pytest -q`: 289 passed, 17 deselected, in 4 min 17 s. The new tests are:

- `test_candidates_run_in_parallel`: the peak number of sandbox calls at the same time is 1 with 1 worker and 3 with 8 workers. The wall time was 3.89 s and 1.48 s.
- `test_accepted_rewrites_share_one_repo_suite_run`
- `test_rewrite_that_breaks_the_repo_suite_alone_is_the_only_one_rejected`
- `test_rewrites_that_pass_alone_but_fail_together_keep_the_first`
- `test_parallel_results_keep_the_candidate_order`
- `test_broken_repo_suite_run_rejects_the_accepted_rewrites_and_keeps_the_other_results`
- `test_agent_counts_the_tokens_of_its_own_replies_when_other_threads_add_usage`

Each test failed when its behavior was removed from the code (6 code mutations).

**Known limits.**

- A pull request with 1 or 2 candidates gets little gain. One slow candidate sets the time.
- A suite run that passes proves the rewrites together, not each one alone. A reviewer can apply only some of the suggestions.
- Live test `test_agent_proves_characterization_tests` after the change to `llm.step`: the `broken_rule` case passed 4 of 6 runs. The 2 failures were "step limit" with one test that failed on the original code. The other case passed. Ticket 41 measured the same variance (6 of 10 functions proved 3 of 3).
