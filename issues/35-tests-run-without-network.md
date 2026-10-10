# 35 — Tell the test writer that the tests run without network and keys

## Summary

- **Goal:** Tell the test writer that the tests run with no network and no API keys. Example: on PR #20, the generated tests for `characterize` called the real `llm.complete` and failed with `KeyError` on `NEBIUS_API_KEY`.
- **Checkable finish condition:** The rendered tests prompt of `characterize` shows `from slopgate import llm` and the signature of `llm.complete`. `uv run pytest -q` passes.
- **Evidence:** Before: 9 of 10 generated tests failed on the original code for `characterize`. After: counts from 8 Super tries for each of `characterize`, `find_duplicate`, and `apply_discount`, with and without the new rule, are in the Comments. A live test proves `characterize`, or the Comments give the reason why not.
- **Constraints:** Keep the prompt rule only if the counts improve. `apply_discount` must still get the calls form. This ticket waits for ticket 30, because both change the "Code it calls" section.

**Blocked by:** 30 (both change the "Code it calls" section of the tests prompt)

**Status:** wontfix

## Context

On PR #20 (2026-10-08), the gate rejected `characterize` in `slopgate/review.py`: 9 of 10 generated tests failed on the original code. The tests prompt was rebuilt in a scratchpad script and sent to Super 2 more times. The replies showed three causes:

1. **The model call was not replaced.** `characterize` calls `llm.complete(SUPER, ...)`. Neither reply replaced `llm`: the word does not appear in either reply. So the tests called the real client, and `os.environ["NEBIUS_API_KEY"]` (`slopgate/llm.py`) raised `KeyError` in the sandbox. The "Code it calls" section follows plain-name calls only, so `llm.complete` is not shown. The prompt does not say that the tests run with no network. Form 3 of the prompt even says "you do not need to see helpers or imports".
2. **A parameter was patched as a module name.** One reply patched `slopgate.review.sandbox.run`. But `sandbox` is a parameter of `characterize`, not a name in the module, so `patch` raised `AttributeError`.
3. **A constant was guessed.** One reply used `"COVERAGE"` as the coverage marker. The real value is `"--slopgate-coverage--"`. Ticket 30 fixes this cause.

## Design

1. In `called_code`, also show each module that the target uses through an attribute call (`llm.complete(...)`, `diff.git(...)`), when the module is in the repo. Show the import line and the signature of each called function, not its body.
2. Add a rule to `TESTS_PROMPT`: "The tests run with no network and no API keys. Replace each call that reaches a model, the network, or a subprocess. Pass a fake object for each parameter; do not patch a parameter by its name."
3. Measure before you keep the prompt change. Send the real tests prompt of `characterize`, `find_duplicate`, and `apply_discount` to Super, 8 times each, with and without the new rule. Count the tests that pass on the original code and cover every branch. A rule can make a bad reply more frequent, so keep it only when the counts improve. Make sure `apply_discount` still gets the calls form.

## Acceptance

- [ ] The rendered tests prompt of `characterize` shows `from slopgate import llm` and the signature of `llm.complete` in the "Code it calls" section.
- [ ] The counts of step 3 are in the Comments, and the rule is kept only if it improves them.
- [ ] Live test (`-m live`): the gate proves the characterization tests of `characterize`, or the Comments give the measured reason why not.
- [ ] `uv run pytest -q` passes.

## Comments

### 2026-10-10 — wontfix: replaced by ticket 41

Ticket 41 replaced the Super call in `characterize` with an agent loop in a sandbox session. The rule of this ticket is in the agent's system prompt (`AGENT_RULES`): "The tests get no network and no API keys. Do not call real network services or models: patch them." The agent can also run the tests, so it sees a `KeyError` on `NEBIUS_API_KEY` and patches the call.

Measured in ticket 41: the agent's proved test files for `find_duplicate` patch `slopgate.review.llm.decide`. `characterize` at 70c27da (the example of this ticket) is still not proved: in all 6 agent runs of run 2 (designs C and D, 3 each), it stopped at the step limit or the token limit. That limit is recorded in ticket 41.
