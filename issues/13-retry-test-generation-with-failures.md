# 13 — Retry characterization tests once with the failing output

**What to build:** Nemotron Super writes characterization tests without running the code, so it sometimes predicts an exact value wrong (for example `round(0.005, 2)`). Those tests fail on the original code and the candidate is lost, even though the rewrite may be fine. When the characterization tests fail on the original, ask Super once more with the failing pytest output, so it can correct the expected values to what the code actually does. Apply the same checks to the second attempt (double run, branch coverage).

**Blocked by:** 12

**Status:** done

- [x] When the first test file fails on the original, exactly one more SUPER call is made, and its prompt contains the failing assertion output.
- [x] When the second test file passes, the proof continues as normal; when it also fails, the candidate is rejected with "characterization tests fail on original".
- [x] Tests that are nondeterministic or miss a branch are not retried.
- [x] Under the `live` marker, the ticket 12 demo succeeds in at least 9 of 10 runs; the measured rate is recorded in Comments.

## Comments

- 2026-10-03: From ticket 12's live runs: 6 of 9 real runs accepted; the one rejection captured in detail was a mispredicted exact value (`round(0.005, 2)`) in an otherwise correct test file; the other two were not captured.
- 2026-10-03: Built in `characterize` (`slopgate/review.py`): when the characterization tests fail on the original in both runs, Super gets the same request plus `TESTS_RETRY` (its earlier file and the last 60 lines of pytest output) once. Tests that split across the two runs (nondeterministic) or miss a branch are not retried. The retry uses Super, not Ultra: the task is copying observed values, not reasoning.
- 2 new seam tests (retry succeeds with the failing assertion in the prompt; two failures reject) and a model-call assertion on the nondeterminism test; 3 mutations (no retry, failure not sent, nondeterminism check skipped) each fail one.
- Live, real Super plus real sandbox on the ticket 12 demo: 10 of 10 runs produced the wrapper followup (was 6 of 9). In a captured run, the first file asserted `cart_total([0.01], 50) == 0.0`; Super saw `assert 0.01 == 0.0` and the retry asserted `== 0.01`, keeping every other assertion.
