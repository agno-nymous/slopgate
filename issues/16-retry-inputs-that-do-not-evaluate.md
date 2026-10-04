# 16 — Retry once when proposed inputs do not evaluate

**What to build:** In the inputs form (ticket 14), the recorder evaluates each proposed item as `capture(<item>)`. A real run with Nemotron Super on `is_public(name, module, exported, private_prefix)` got `{"inputs": ["\"\" , False , [] , _", ...]}`: a bare `_` where the string `"_"` was meant. The recorder stopped with `NameError: name '_' is not defined`, and the candidate was rejected with "could not record calls" at once. Failing tests get one retry with the failure (ticket 13); a failed recording got none. Give a failed recording the same single retry: ask Super once more with the original request, its earlier reply, and the recorder's error output, and tell it that each input must evaluate as Python with only literals and builtins. The reply may use either form and goes through the same checks as a first reply. One retry per candidate in total, whatever failed first.

**Blocked by:** 14

**Status:** done

- [x] When the recording fails, exactly one more SUPER call is made; its prompt starts with the original request and contains the earlier reply and the recorder error (`NameError`).
- [x] When the retry reply records and passes, the proof continues as normal.
- [x] When the retry also fails, the candidate is rejected with the reason of the second failure: "could not record calls" or "characterization tests fail on original".
- [x] A candidate gets at most one retry, whether the recording or the tests failed first.
- [x] The ticket 13 and 14 tests pass; the one ticket 14 test whose contract changed is updated (see Comments).

## Comments

- 2026-10-03: Built in `characterize` (`slopgate/review.py`). The function now has one loop of at most two attempts. Each attempt asks Super (the original request plus the retry text of the previous attempt), records the inputs or takes the test file, and runs the double run. A failed recording sets the retry text to the new `INPUTS_RETRY` (earlier reply and recorder error); failing tests set it to `TESTS_RETRY` as before. After the last attempt, the failure is the rejection reason. The one-caller helper `tests_from` and the two early `if failure: return` branches are gone. The first tests prompt is unchanged.
- Contract change: `test_recorder_that_ends_without_results_is_rejected` expected a rejection after one SUPER call. It is now `test_recorder_that_ends_without_results_twice_is_rejected`: `"1,,"` (SyntaxError) and then a bare `_` (NameError) are rejected with "could not record calls" after two SUPER calls, and the reason is the second error.
- 4 new seam tests: a bare `_` then valid inputs gives a suggestion with one extra SUPER call; two bad recordings reject; bad inputs then wrong tests, and wrong tests then bad inputs, each reject after one retry with the matching reason. 9 mutations (no retry after a failed recording, recorder error not sent, earlier reply not sent, original request dropped, two retries, no rejection after the last attempt, test failure reason dropped, pytest output not sent, recorder failure ignored) each fail at least one test.
- Not done: the first tests prompt still states "literals and builtins only" without the quoting rule. Add it there if live runs show the retry is often needed.
