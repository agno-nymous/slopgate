# 51 — The proof accepts a rewrite that changes a comparison

## Summary

- **Goal:** Do not post a suggestion that changes what the code does. Example: on PR #23, the gate suggested a `nesting` rewrite of `transformed` in `bench/detect.py`. The rewrite changed `if len(found) == count: break` to `if len(found) >= count: break`. With `count=0`, the original returns every accepted item, and the rewrite returns 1 item. The 5 characterization tests used only `count` 1, 2, and 5, so they passed on both.
- **Checkable finish condition:** A dry run on PR #23 (`0a8887b`) gives no suggestion that changes `==` to `>=` in `transformed`. A new offline test shows the check that rejects such a rewrite.
- **Evidence:** Before: ticket 49 traces, trace `1d049b18`, span `3b9bf168` (proof passed) and the repo suite passed. 1 of the 2 suggestions in the 10 traced runs changed the behavior. After: the dry run and the offline test.
- **Constraints:** Measure the false rejects of the new check on the accepted rewrites of the ticket 41 benchmark before the build. The sandbox proof stays the main check. Do not add a model call. On 2026-10-14 the user added option 2 (mutation hint for the agent) to this ticket. Option 2 adds agent steps. The comparison rule of option 1 still adds no model call.

**Blocked by:** —

**Status:** in-progress

## Context

`trial` in `slopgate/review.py` accepts a rewrite when `broken_rule` finds no rule break, `leftover` finds no slop, and the characterization tests pass. The tests come from the test agent. The agent covers every branch, but it does not test the edge values of each comparison. So a rewrite can change a comparison operator and still pass.

The rewrite prompt says "Keep the exact signature, the decorators, and the behavior, bugs included." The model still changed the operator: it read `== count` as "stop at count", and `>=` gives the same result for `count >= 1`.

## Design

Measure 2 options:

1. **Comparison rule.** In `broken_rule`, collect each comparison of the original and of the rewrite as `(left, op, right)`. Check a comparison of the rewrite only if the original compares the same two operands. Then allow it only if the original has the same comparison or its negation. A guard clause needs the negation: it turns `if a == b:` into `if a != b: continue`. Otherwise return "changes a comparison". The first text of this option checked every comparison of the rewrite. The 2026-10-14 measurement (Comments) gave that version 4 false rejects in 121 rewrites, so the user chose the check on the same operand pair only.
2. **Mutation hint for the agent.** After the tests pass, run the tests on a copy of the function with each comparison mutated. A mutant that survives means that the tests do not pin that comparison. Give the agent the surviving mutants, and let it add tests. This costs more steps.

Option 1 is cheap and needs no model. Measure its false rejects first.

## Acceptance

- [x] The Comments give the false-reject count of option 1 on the accepted rewrites of the ticket 41 benchmark.
- [x] A dry run on PR #23 gives no suggestion that changes `==` to `>=`.
- [x] `uv run pytest -q` passes.
- [ ] Option 2: the Comments give the boundary kill rate before and after the hint round, measured in one bench run (each function is its own control).
- [ ] Option 2: the proof rate does not fall, and the bench run has 0 errors from the mutant code.
- [ ] Option 2: the Comments give the added seconds, steps, and tokens for each function, and how often the hint round runs.
- [ ] Option 2: offline tests show the mutant generator, the hint round, the case with no survivor, the fallback to the round-1 test file, and the case with no budget left.

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

### 2026-10-14: comparison rule in `broken_rule` (pairs only)

**What was built.** `broken_rule` in `slopgate/review.py` has a new check. It collects each comparison of the original and of the rewrite as `(left, op, right)`. It splits a chained comparison into pairs. It writes `b > a` as `a < b`, and it sorts the operands of `==`, `!=`, `is`, and `is not`. A comparison of the rewrite on the same two operands as the original must be the same comparison or its negation (`FLIP` in `slopgate/kinds.py`). Otherwise the check returns "changes a comparison". A comparison with new operands is not checked. The check makes no model call and no sandbox run.

**Worked example.** Input: the real PR #23 rewrite of `transformed` (trace `1d049b18`, span `3b9bf168`). The original has `if len(found) == count: break`. The rewrite has `if len(found) >= count: break`. Before this ticket, the proof passed, and the gate posted the suggestion. Now `broken_rule(original, rewrite)` returns `"changes a comparison"`. The pair (`len(found)`, `count`) is in the original with `==`. The rewrite uses `>=` on the same pair. `>=` is not `==` and not its negation `!=`, so the gate rejects the rewrite before the sandbox run.

**Measurement 1: false accepts of the proof before this ticket (no model call).**
- Input: the 38 proved test files of design D in `bench/results/characterize/runs.json` (25 functions, runs 0 to 2).
- Each file ran in ConTree against every boundary mutant of its function: `==` to `>=` and `<=`, `!=` to `>` and `<`, `<` to `<=`, `<=` to `<`, `>` to `>=`, `>=` to `>`. The control run on the unmutated function passed for all 38 files.
- 11 test files have a boundary site. They give 29 mutants. 15 mutants survived.
- 1 survivor is equivalent: `df % s != 0` to `df % s > 0` in `_dup_decompose`, where `s >= 2`.
- So the tests let 14 of 28 real boundary mutants through (50%). 9 of the 11 test files let at least one through. The negation mutants of ticket 41 had a kill rate of 86%.
- Examples: `len(self.content) > 3` to `>= 3` in `requests` `Response.json`, `r >= 1.0` to `r > 1.0` in `chardet` `get_confidence`, and `row.hash == code_hash` to `<=` in `slopgate` `matches`.
- The new check rejects each of the 14. A boundary mutant keeps its operands and changes the operator to one that is not the negation.

**Measurement 2: false rejects.** The ticket 41 benchmark writes only tests. It has no rewrites. Two rewrite sets took its place:

1. All 26 rewrites in the local Phoenix traces (`gate.rewrite` and `gate.retry`, ticket 49 and older). 8 of them passed the proof. The check rejects 2: both PR #23 rewrites of `transformed`. Both are true rejects. It rejects none of the other 6 accepted rewrites.
2. A corpus of 122 Super rewrites. Each one uses the gate's real `REWRITE_PROMPT` with the kinds from `classify`, on each ground-truth item of ticket 37 that `classify` flags. The corpus has 10 SWE-bench repos (sympy 28, matplotlib 22, django 19, astropy 14, sphinx 10, pylint 10, scikit-learn 7, xarray 6, pytest 4, requests 2). 106 rewrites have injected slop, and 16 are real code. These rewrites had no sandbox proof, so each count below is an upper bound for accepted rewrites.

| Variant | Corpus rejects after the older rules | False rejects | True rejects | Phoenix rejects |
|---|---|---|---|---|
| Strict: check every comparison of the rewrite (first text of option 1) | 7 | 4 | 3 | 4 |
| Pairs only: check only the same operand pair (chosen) | 0 | 0 | 0 | 2 |

I labeled each reject by hand.
- False rejects of the strict variant: a local variable for an operand (`_get_representation_info`), a list changed to a tuple in an `in` (`semilogx`), `result is None` in a `lookup_table` rewrite (`get_ticks_position`), and `len(self.args) > 0` in a `swallowed_error` fix (`Plane.p1`).
- True rejects that only the strict variant finds: `len(NAME or '')` to `len(NAME)`, so `None` raises `TypeError` (`get_connection_params`); the original reads the undefined name `pmats` (`fk5_to_gal`); the rewrite yields when `config` is `None` (`pytest_collection`). Each one changes an operand, not an operator.
- Two more variants added the inlining of single-assignment locals and the list-to-tuple change. They gave no gain over the two rows above.

**Dry run on PR #23.** Two runs with base `6665674`, head `0a8887b`, and the code of this ticket: traces `646d7c31` (144 s) and `1ff7fe11` (133 s). Each run gave 0 suggestions and 1 note, and it rejected `transformed` with `rule: signature changed`. Super wrote `len(found) >= count` in both runs (4 of 4 runs in all traces). It also added `from typing import List`, so the older signature check rejected the rewrite first. Without the import line, the rewrite of `646d7c31` gives "changes a comparison". The dry run passes the acceptance box, but the new check did not decide it. The offline test with the real rewrite of `1d049b18` proves the new check.

**Traces.** The two dry runs have 0 `ERROR` spans and 0 replies with `finish_reason: "length"`. `gate.characterize` passed in 64 s. The corpus run made 122 Super calls with 0 errors and 0 `length` stops. The largest reply had 937 output tokens, and the slowest took 6.4 s. Finding: each corpus call has 8 nested `ChatCompletion` spans, because `trace._setup` has no lock. Ticket 61 holds it.

**Offline test.** `test_broken_rule_rejects_a_changed_comparison_and_allows_negations` has 13 cases. 5 must be rejected: the PR #23 rewrite, a mirrored changed operator, a chained comparison, `>=` to `>`, and `!=` to `<`. 8 must pass: a guard clause with `!=`, `not (a == b)`, `b > a` for `a < b`, a symmetric swap, a mirrored guard, a chained guard, a dropped comparison, and new operands. With the check removed, exactly the 5 reject cases fail.

**Cost.** The corpus used 122 Super calls with about 43,000 input tokens and 24,000 output tokens. The boundary run used 67 ConTree runs (38 controls and 29 mutants). The scripts are scratch scripts. They are not in the repository.

**Known limits.** The check accepts these changes. The tests must find them:
- An inversion without a branch swap: `return a < b` to `return a >= b`. Negations are allowed. The tests killed 86% of such mutants in ticket 41.
- A dropped `not`: `return not a == b` to `return a == b`.
- A changed operand: `n == c` to `n == c - 1`. The pair is new.
- A new local with a changed operator: `k = len(n)` and then `k >= c`.
- Comparisons that move between two branches. The check compares sets, not positions.
- `a >= b` as the negation of `a < b`. These differ for NaN and for sets.

A rule failure gets no retry, the same as each older rule. So each reject turns a suggestion into a note.
