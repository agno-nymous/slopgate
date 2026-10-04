# 13 — Retry the characterization tests once with the failing output

**What to build:** Nemotron Super writes characterization tests but does not run the code. Sometimes it predicts an exact value incorrectly (for example `round(0.005, 2)`). These tests fail on the original code. The gate then loses the candidate, although the rewrite can be correct. When the characterization tests fail on the original, ask Super one more time. Give Super the failing pytest output. Super then corrects the expected values to the values that the code returns. Apply the same checks to the second attempt (double run, branch coverage).

**Blocked by:** 12

**Status:** done

- [x] The first test file fails on the original. Then the gate makes exactly one more SUPER call. The prompt of that call contains the failing assertion output.
- [x] The second test file passes. Then the proof continues as normal. The second test file also fails. Then the gate rejects the candidate with "characterization tests fail on original".
- [x] The gate does not retry tests that are nondeterministic or that miss a branch.
- [x] Run the ticket 12 demo under the `live` marker. It succeeds in at least 9 of 10 runs. Record the measured rate in Comments.

## Comments

- 2026-10-03: Ticket 12 had live runs. In 6 of 9 real runs, the gate accepted the candidate. The gate rejected one candidate, and the log of that run has details. In that run, one exact value was predicted incorrectly (`round(0.005, 2)`) in a test file that was otherwise correct. The log does not have details of the other two rejections.
- 2026-10-03: The step that writes and checks the characterization tests (`characterize` in `slopgate/review.py`) has the retry. Both runs on the original fail. Then Super gets the same request plus `TESTS_RETRY` one time. `TESTS_RETRY` is the retry text that holds the earlier test file and the last 60 lines of pytest output. The gate does not retry tests that split across the two runs (nondeterministic). The gate does not retry tests that miss a branch. The retry uses Super, not Ultra. The task is to copy observed values. The task does not need reasoning.
- The change has 2 new seam tests. In the first test, the retry succeeds and the prompt contains the failing assertion. In the second test, two failures reject the candidate. The test for nondeterminism has a new assertion on the model calls. There were 3 mutations (no retry, failure not sent, nondeterminism check skipped). Each mutation fails one test.
- Live test with real Super and a real sandbox on the ticket 12 demo: 10 of 10 runs produced the wrapper followup (before: 6 of 9). In one captured run, the first file asserted `cart_total([0.01], 50) == 0.0`. Super saw `assert 0.01 == 0.0`. The retry asserted `== 0.01` and kept every other assertion.
