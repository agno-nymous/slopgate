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

### 2026-10-12: design review by an Opus 5.5 subagent (read-only)

A subagent read `slopgate/review.py`, `CLAUDE.md`, and tickets 41, 43, 48, 51, 52, and 55. It answered the question "Is there a better way than characterization tests on the original and on the rewrite?".

**Result.** Keep the method. Do not replace it. Build option 1 of this ticket (the comparison rule). Measure the false accepts of the current proof first.

**Why a false accept costs most.** When the gate rejects a rewrite, it still posts a note. A wrong suggestion goes into the code with one click. This ticket measured 1 wrong suggestion in 2 traced runs. That sample is too small to give a rate.

**Weak points of the proof, in order:**

1. Branch coverage is not boundary coverage. The agent tests have a median of 4.5 asserts and a mutant kill rate of 86% (ticket 41).
2. The tests exist before the rewrite. They cannot aim at the lines that the rewrite changes.
3. A test that patches a callee tests the mock, not the callee.
4. Some failures only cost recall and fail closed: the agent environment differs from the judge environment (ticket 55), the branch rule blocks `redundant_check` (ticket 43), and the step and time limits stop runs.

**Measure before the build (3 steps):**

1. False accepts of the current proof, with no model call. `bench/results/characterize/runs.json` holds the proved test files under `tests`. Run each file against boundary mutants of its original: `==` to `>=` and `<=`, `<` to `<=`, `>` to `>=`. The `SWAPS` table in `bench/characterize.py` has only negations, and tests kill negations easily, so the 86% kill rate does not predict this ticket. Each surviving mutant is a wrong rewrite that the proof would accept.
2. False rejects of option 1. Dry-run the gate on at least 5 external SWE-bench repositories (for example the 9 items of ticket 38), 3 runs for each item, because run-to-run variance is high. Label each accepted rewrite by hand. The target is 0 false rejects.
3. Offline test: option 1 rejects every surviving mutant from step 1.

**The rule must handle 5 cases.** These set its false-reject rate:

- split a chained comparison into pairs;
- read `not (a == b)` as `a != b`;
- read `b > a` as `a < b`;
- let a rewrite keep only a subset of the original comparisons;
- check `lookup_table` rewrites with care: a new `x in TABLE` is the most likely false reject.

**Other options that the subagent compared:**

| Option | Blocks this ticket's case | Note |
|---|---|---|
| A. Comparison rule (option 1 here) | yes | About 30 lines, no runtime cost, no model call. |
| B. Rewrite-aware agent pass: after a rewrite passes, ask the agent for one test that passes on the original and fails on the rewrite | likely | Adds 60 s to 150 s for each accepted rewrite. A pass that finds no difference does not prove equality. Do it only if the false-accept measurement justifies the cost. |
| C. Hypothesis differential test | yes, for int inputs | Needs a new library in the sandbox. Generators for Django objects are hard to write. |
| D. Mechanical AST transforms for `redundant_check`, `dead`, and collapsible `if` | no | Equivalent by construction, so no agent run. It would also fix ticket 43. This ticket was a `nesting` rewrite. |
| E. Record each return value and compare the original and the rewrite | no | No input reaches `count=0`. Ticket 41 deleted the old recorder. |

**Not recommended:** symbolic checks (they need type hints, and old SWE-bench code mostly has none; this is an inference, not a measurement), full mutation testing as a gate, and reuse of the repo-test coverage.

**Known limits of this review.** The subagent made no edits and ran no sandbox runs. It did not count how many functions each slop kind covers. It did not check that every row of `runs.json` holds a complete test file.
