# 16 — Retry once when the proposed inputs do not evaluate

## Summary

- **Goal:** When the inputs that Super proposes do not run, ask Super once more instead of rejecting the function. Example: for `is_public(name, module, exported, private_prefix)`, Super wrote a bare `_` where the string `"_"` was meant.
- **Checkable finish condition:** After a failed recording, the gate makes exactly one more Super call. That call holds the original request, the earlier reply, and the recorder error. A candidate gets at most one retry in total. The tests of tickets 13 and 14 pass.
- **Evidence:** Before: the bare `_` caused `NameError: name '_' is not defined`, and the gate rejected the candidate at once with "could not record calls". After (2026-10-03): 4 new offline tests passed. 9 planted bugs each failed at least one test. One ticket 14 test changed its contract and now expects a rejection after two Super calls.
- **Constraints:** A candidate gets one retry in total, whichever failure came first. The retry reply goes through the same checks as a first reply. Do not change the first tests prompt.

**Blocked by:** 14

**Status:** done

## Details

In the inputs form (ticket 14), the recorder evaluates each proposed item as `capture(<item>)`. A failing test already gets one retry with the failure (ticket 13). A failed recording got no retry. Give a failed recording the same single retry. Send the original request, the earlier reply of Super, and the error output of the recorder. Tell Super that each input must evaluate as Python with only literals and builtins. The reply can use either form.

- [x] The recording fails. Then the gate makes exactly one more SUPER call. The prompt of that call starts with the original request. It contains the earlier reply and the recorder error (`NameError`).
- [x] The retry reply records and passes. Then the proof continues as normal.
- [x] The retry also fails. Then the gate rejects the candidate with the reason of the second failure: "could not record calls" or "characterization tests fail on original".
- [x] A candidate gets at most one retry. This is true if the recording failed first and if the tests failed first.
- [x] The ticket 13 and 14 tests pass. Update the one ticket 14 test that has a changed contract (see Comments).

## Comments

- 2026-10-03: The change is in the step that writes and checks the characterization tests (`characterize` in `slopgate/review.py`). The function now has one loop of at most two attempts. Each attempt asks Super. The request is the original request plus the retry text of the previous attempt. Then the attempt records the inputs or takes the test file. Then it runs the double run. A failed recording sets the retry text to the new `INPUTS_RETRY`. This text holds the earlier reply and the recorder error. Failing tests set the retry text to `TESTS_RETRY`, as before. After the last attempt, the failure is the rejection reason. The helper with one caller (`tests_from`) is gone. The two early `if failure: return` branches are also gone. The first tests prompt is unchanged.
- Contract change: The test `test_recorder_that_ends_without_results_is_rejected` expected a rejection after one SUPER call. It is now `test_recorder_that_ends_without_results_twice_is_rejected`. In it, `"1,,"` (SyntaxError) and then a bare `_` (NameError) cause a rejection with "could not record calls" after two SUPER calls. The reason is the second error.
- The change has 4 new seam tests. In the first test, a bare `_` and then valid inputs give a suggestion with one extra SUPER call. In the second test, two bad recordings reject the candidate. In the third and fourth tests, bad inputs then wrong tests, and wrong tests then bad inputs, each reject the candidate after one retry with the matching reason. There were 9 mutations. Each mutation fails at least one test. The mutations are: no retry after a failed recording, recorder error not sent, earlier reply not sent, original request dropped, two retries, no rejection after the last attempt, test failure reason dropped, pytest output not sent, and recorder failure ignored.
- Not done: The first tests prompt still states "literals and builtins only". It does not state the quoting rule. Add the quoting rule to that prompt if live runs show that the retry is often necessary.
