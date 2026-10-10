# 14 — Record real outputs for proposed calls

## Summary

- **Goal:** Make the tests for easy functions correct by construction. Super proposes only the calls. The sandbox runs them on the original code and records the results. Example: for `grade`, which can raise, Super proposes arguments and the test asserts the recorded exception.
- **Checkable finish condition:** A calls reply gives one test for each call, with outcomes from the original code. The recorded tests reject a rewrite that changes a return value, the result type (`1` for `True`), the exception type, the exception message, or an argument. A recorder run with no results rejects the candidate with "could not record calls". A test file reply works as before.
- **Evidence:** Done. Before, Super predicted each expected value, and a wrong prediction failed the tests on the original code. The first version checked only the result, so a rewrite of `Cart.add` that dropped the append passed. After: 8 new offline tests, and each of 8 planted bugs fails at least one test. Live with real Super and a real sandbox: 21 runs, 21 accepted. The ticket 12 wrapper demo had 10 of 10, `grade` 5 of 5, `add_tag` 3 of 3, and `Cart.add` 3 of 3 in the file form.
- **Constraints:** Only module-level functions get the calls form, because the object of a method is not an argument. The recorder runs with `PYTHONHASHSEED=1`. It records `repr` of the result (or the exception type and message) and `repr` of the arguments after the call. The generated file goes through the same checks as a written file: the double run, branch coverage, and the retry of ticket 13.

**Blocked by:** 13

**Status:** done

## Details

Nemotron Super writes characterization tests (tests that record what the old code does). It predicts the expected value of each call. A wrong prediction makes the tests fail on the original code (ticket 13 retries one time). Easy functions do not need prediction. The recorded outcomes become the test file.

The tests prompt offers two reply forms. Super picks one form for each function:

1. Calls form. Use it for functions with plain-value arguments, when the return value or the raised exception shows the full behavior. The reply is JSON `{"inputs": ["<arguments>", ...]}`. Each item is the text between the parentheses of one call.
2. Test file form. Use it for everything else (objects, setup, side effects). The reply is one pytest file, as before, with the ticket 13 retry.

In the calls form, a recorder script runs each call in the sandbox. Each call becomes one test that asserts the recorded values.

- [x] A calls reply produces one test for each call. The outcomes come from the original code. The proof continues as normal.
- [x] The recorded tests reject a rewrite that changes one of these items: a return value, the result type (`1` for `True`), the exception type, the exception message, or an argument.
- [x] A recorder run that ends without results rejects the candidate with "could not record calls".
- [x] A test file reply works as before.

## Comments

- 2026-10-03: The change is in `slopgate/review.py`. The function that reads the tests reply (`proposed_inputs`) reads `{"inputs": [...]}`. The gate uses any other reply as a pytest file. The function that runs the recorder (`record`) runs `slopgate_record.py` in the sandbox. That script evaluates each item as `capture(<arguments>)`. It calls the target. It prints `[outcome, value, argument state]` for each call. Each call becomes a test. The test asserts `repr` of the result (or `type: message` of the exception). The test also asserts `repr((args, kwargs))` after the call. The generated file then gets the double run, branch coverage, and the ticket 13 retry, like a written file.
- The first version took full call expressions (`{"calls": ["cart_total([10], 50)"]}`). It checked only the result. A live run on `Cart.add` showed the problem. `Cart.add` appends to `self.items`. Super proposed `Cart().add("apple", 50)`. The recorded test checked only `True`. A rewrite that dropped the append passed. The fix has three parts. The form takes argument lists. The recorder records the argument state. Only module-level functions get the inputs form (the object of a method is not an argument).
- The change has 8 new seam tests. There were 8 mutations. Each mutation fails at least one test. The mutations are: no value check, no argument check after return, no argument check after an exception, no exception type, no exception message, inputs ignored, no recorder output check, and methods offered the inputs form.
- Live test with real Super and a real sandbox: 21 runs, 21 accepted. The ticket 12 wrapper demo had 10 of 10 (inputs form 9, file form 1). `grade` with a raise had 5 of 5 (inputs form). `add_tag`, which appends to its argument, had 3 of 3 (inputs form). The `Cart.add` method had 3 of 3 (file form; the gate did not offer the inputs form). No run in the inputs form needed the retry.
