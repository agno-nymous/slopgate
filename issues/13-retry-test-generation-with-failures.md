# 13 — Retry characterization tests once with the failing output

**What to build:** Nemotron Super writes characterization tests without running the code, so it sometimes predicts an exact value wrong (for example `round(0.005, 2)`). Those tests fail on the original code and the candidate is lost, even though the rewrite may be fine. When the characterization tests fail on the original, ask Super once more with the failing pytest output, so it can correct the expected values to what the code actually does. Apply the same checks to the second attempt (double run, branch coverage).

**Blocked by:** 12

**Status:** ready-for-agent

- [ ] When the first test file fails on the original, exactly one more SUPER call is made, and its prompt contains the failing assertion output.
- [ ] When the second test file passes, the proof continues as normal; when it also fails, the candidate is rejected with "characterization tests fail on original".
- [ ] Tests that are nondeterministic or miss a branch are not retried.
- [ ] Under the `live` marker, the ticket 12 demo succeeds in at least 9 of 10 runs; the measured rate is recorded in Comments.

## Comments

- 2026-10-03: From ticket 12's live runs: 6 of 9 real runs accepted; the one rejection captured in detail was a mispredicted exact value (`round(0.005, 2)`) in an otherwise correct test file; the other two were not captured.
