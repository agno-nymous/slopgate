# 51 — The proof accepts a rewrite that changes a comparison

## Summary

- **Goal:** Do not post a suggestion that changes what the code does. Example: on PR #23, the gate suggested a `nesting` rewrite of `transformed` in `bench/detect.py`. The rewrite changed `if len(found) == count: break` to `if len(found) >= count: break`. With `count=0`, the original returns every accepted item, and the rewrite returns 1 item. The 5 characterization tests used only `count` 1, 2, and 5, so they passed on both.
- **Checkable finish condition:** A dry run on PR #23 (`0a8887b`) gives no suggestion that changes `==` to `>=` in `transformed`. A new offline test shows the check that rejects such a rewrite.
- **Evidence:** Before: ticket 49 traces, trace `1d049b18`, span `3b9bf168` (proof passed) and the repo suite passed. 1 of the 2 suggestions in the 10 traced runs changed the behavior. After: the dry run and the offline test.
- **Constraints:** Measure the false rejects of the new check on the accepted rewrites of the ticket 41 benchmark before the build. The sandbox proof stays the main check. Do not add a model call.

**Blocked by:** —

**Status:** ready-for-agent

## Context

`trial` in `slopgate/review.py` accepts a rewrite when `broken_rule` finds no rule break, `leftover` finds no slop, and the characterization tests pass. The tests come from the test agent. The agent covers every branch, but it does not test the edge values of each comparison. So a rewrite can change a comparison operator and still pass.

The rewrite prompt says "Keep the exact signature, the decorators, and the behavior, bugs included." The model still changed the operator: it read `== count` as "stop at count", and `>=` gives the same result for `count >= 1`.

## Design

Measure 2 options:

1. **Comparison rule.** In `broken_rule`, collect each comparison of the original and of the rewrite as `(left, op, right)`. Allow a comparison in the rewrite only if the original has the same comparison or its negation. A guard clause needs the negation: it turns `if a == b:` into `if a != b: continue`. Otherwise return "changes a comparison".
2. **Mutation hint for the agent.** After the tests pass, run the tests on a copy of the function with each comparison mutated. A mutant that survives means that the tests do not pin that comparison. Give the agent the surviving mutants, and let it add tests. This costs more steps.

Option 1 is cheap and needs no model. Measure its false rejects first.

## Acceptance

- [ ] The Comments give the false-reject count of option 1 on the accepted rewrites of the ticket 41 benchmark.
- [ ] A dry run on PR #23 gives no suggestion that changes `==` to `>=`.
- [ ] `uv run pytest -q` passes.

## Comments
