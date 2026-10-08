# 31 — Retry once for missed branches, with 3 attempts in total

**What to build:** When the characterization tests pass but miss branches, the gate asks Super once more. The request names each missed branch by its line. Also, `characterize` gets 3 Super attempts in total instead of 2, so that one retry does not use up the attempt that another retry needs.

**Blocked by:** 29 (both change the loop in `characterize`)

**Status:** ready-for-agent

## Context

`characterize` in `slopgate/review.py` has two problems.

1. **No retry for missed branches.** Ticket 13 added a retry for tests that fail on the original code. It does not retry tests that miss a branch, and it gives no reason for that choice. On PR #17 (2026-10-08), the tests for `characterize` passed but missed 20 branches, and the gate rejected the function at once. CoverUp sends a new prompt when the tests do not reach the missing lines, and it tags those lines in the code excerpt. Its authors found that without the tags, the model writes more tests that "do not improve coverage" ([Pizzorno and Berger 2025](https://arxiv.org/html/2403.16218v3)).
2. **Two attempts are too few.** The loop is `for last in (False, True)`. Each retry (`EMPTY_INPUTS_RETRY`, `INPUTS_RETRY`, `TESTS_RETRY`) uses the second attempt. So after an empty-inputs retry, a test file that fails gets no `TESTS_RETRY`. With a new retry for missed branches, a test file that `TESTS_RETRY` corrects would get no retry for its missed branches. On PR #17, the first gate run used both attempts for `matches` on `{"inputs": []}` replies.

A retry for coverage asks for more tests only. It does not ask Super to change an expected value. The "Self-Repair Trap" study warns that retries driven only by a pass result can make assertions weaker ([Li et al. 2026](https://arxiv.org/pdf/2608.05917)). That risk applies to `TESTS_RETRY`, not to this retry.

## Design

1. Change the loop to at most 3 Super calls per `characterize`. Each retry text (`EMPTY_INPUTS_RETRY`, `INPUTS_RETRY`, `TESTS_RETRY`, and the new `BRANCHES_RETRY`) uses one call. The last call that fails gives the rejection reason, as now.
2. When the tests pass in both runs but miss branches in the function, do not reject at once. Send `BRANCHES_RETRY`, if a call remains.
3. `BRANCHES_RETRY` holds the earlier test file and one line for each missed branch, in this form:
   - `- line 42: if not pool: never goes to line 45` (the line number in the file, the stripped source line, and the target line).
   - When the target line is negative (an exit from the function), write `never leaves the function here`.
4. `BRANCHES_RETRY` asks for the full file again: keep every earlier test, and add tests that take the listed branches. It does not ask to change an expected value.
5. The new file goes through the same checks: both runs, coverage, and the removal of failing tests from ticket 29.
6. Use the missed branches from the `MISSED` script output, which gives `[from, to]` pairs. Keep only the pairs whose `from` line is inside the function.

## Acceptance

- [ ] Tests that pass but miss a branch get exactly one more Super call. Its prompt holds the earlier file and a line such as `line 3: if x: never goes to line 4`.
- [ ] When the second file covers every branch, the proof continues. When it still misses a branch and no call remains, the gate rejects with "characterization tests miss branches: <n>".
- [ ] `characterize` makes at most 3 Super calls. A seam test with an empty-inputs reply, then a failing test file, then a passing file proves the function with 3 calls.
- [ ] A missed branch to an exit (negative target) gives `never leaves the function here`.
- [ ] `uv run pytest -q` passes.
- [ ] Live measurement: run `characterize` on `characterize` and `matches` at commit b2a2ad0, 4 runs each, before and after the change. Record the proven count, the Super calls per function, and the time per function in Comments.

## How to verify by hand

1. Run `uv run --env-file .env slopgate review --repo . --base b2a2ad0~1 --head b2a2ad0 --dry-run`.
2. Check that no rejection says "characterization tests miss branches" after only one or two Super calls for that function.

## Comments
