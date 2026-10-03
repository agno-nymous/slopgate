# 14 — Record real outputs for proposed calls

**What to build:** Nemotron Super writes characterization tests by predicting the expected value of each call. A wrong prediction makes the tests fail on the original code (ticket 13 retries once). For easy functions, prediction is not necessary: Super can propose the calls only, and the sandbox can run them on the original code and record what each call returns or raises. The recorded outcomes become the test file, so the expected values are correct by construction.

The tests prompt offers two reply forms, and Super picks one per function:

1. Calls form, for functions whose behavior shows fully in the return value or the raised exception, with plain-value arguments: JSON `{"inputs": ["<arguments>", ...]}`, where each item is the text between the parentheses of one call.
2. Test file form, for everything else (objects, setup, side effects): one pytest file, as today, with the ticket 13 retry.

In the calls form, a recorder script runs each call in the sandbox (with `PYTHONHASHSEED=1`) and records `repr` of the result, or the exception type and message, and `repr` of the arguments after the call. Each call becomes one test that asserts the same values. Only module-level functions are offered the inputs form. The test file then goes through the same checks as a written one: the double run and branch coverage.

**Blocked by:** 13

**Status:** done

- [x] A calls reply produces one test per call, with the outcomes recorded from the original code, and the proof continues as normal.
- [x] Recorded tests reject a rewrite that changes a return value, the result type (`1` for `True`), the exception type, the exception message, or a change to an argument.
- [x] A recorder run that ends without results rejects the candidate with "could not record calls".
- [x] A test file reply works as before.

## Comments

- 2026-10-03: Built in `slopgate/review.py`. `proposed_inputs` reads `{"inputs": [...]}` from the tests reply; anything else is used as a pytest file. `record` runs `slopgate_record.py` in the sandbox, which evaluates each item as `capture(<arguments>)`, calls the target, and prints `[outcome, value, argument state]` per call. Each call becomes a test that asserts `repr` of the result (or `type: message` of the exception) and `repr((args, kwargs))` afterward. The generated file then gets the double run, branch coverage, and the ticket 13 retry like a written one.
- First version took full call expressions (`{"calls": ["cart_total([10], 50)"]}`) and checked only the result. A live run on `Cart.add`, which appends to `self.items`, showed the gap: Super proposed `Cart().add("apple", 50)`, and the recorded test checked only `True`, so a rewrite that dropped the append would pass. Fixed by taking argument lists, recording the argument state, and offering the inputs form only to module-level functions (a method's object is not an argument).
- 8 new seam tests; 8 mutations (no value check, no argument check after return, no argument check after an exception, no exception type, no exception message, inputs ignored, no recorder output check, methods offered the inputs form) each fail at least one.
- Live, real Super plus real sandbox, 21 runs, 21 accepted: ticket 12 wrapper demo 10/10 (inputs form 9, file form 1), `grade` with a raise 5/5 (inputs), `add_tag` that appends to its argument 3/3 (inputs), `Cart.add` method 3/3 (file form; inputs not offered). No inputs-form run needed the retry.
