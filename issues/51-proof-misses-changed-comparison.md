# 51 — The proof accepts a rewrite that changes a comparison

## Summary

- **Goal:** Do not post a suggestion that changes what the code does. Example: on PR #23, the gate suggested a `nesting` rewrite of `transformed` in `bench/detect.py`. The rewrite changed `if len(found) == count: break` to `if len(found) >= count: break`. With `count=0`, the original returns every accepted item, and the rewrite returns 1 item. The 5 characterization tests used only `count` 1, 2, and 5, so they passed on both.
- **Checkable finish condition:** A dry run on PR #23 (`0a8887b`) gives no suggestion that changes `==` to `>=` in `transformed`. A new offline test shows the check that rejects such a rewrite.
- **Evidence:** Before: ticket 49 traces, trace `1d049b18`, span `3b9bf168` (proof passed) and the repo suite passed. 1 of the 2 suggestions in the 10 traced runs changed the behavior. After: the dry run and the offline test.
- **Constraints:** Measure the false rejects of the new check on the accepted rewrites of the ticket 41 benchmark before the build. The sandbox proof stays the main check. Do not add a model call. On 2026-10-14 the user added option 2 (mutation hint for the agent) to this ticket. Option 2 adds agent steps. The comparison rule of option 1 still adds no model call.

**Blocked by:** —

**Status:** done

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
- [x] Option 2: the Comments give the boundary kill rate before and after the hint round, measured in one bench run (each function is its own control).
- [x] Option 2: the proof rate does not fall, and the bench run has 0 errors from the mutant code.
- [x] Option 2: the Comments give the added seconds, steps, and tokens for each function, and how often the hint round runs.
- [x] Option 2: offline tests show the mutant generator, the hint round, the case with no survivor, the fallback to the round-1 test file, and the case with no budget left.

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

### 2026-10-17: mutation hint for the test agent (option 2)

**What was built.** `characterize` in `slopgate/review.py` has a hint round after round 1.
- `boundary_mutants` makes the boundary mutants of the function from its source text. It uses `tokenize` and changes one comparison operator for each mutant: `==` to `>=` and `<=`, `!=` to `>` and `<`, `<` to `<=`, `<=` to `<`, `>` to `>=`, `>=` to `>`. It skips the decorators. It takes the sites in turn, so a late site gets a mutant before an early site gets its second one. The cap is `HINT_MUTANTS = 8`.
- `survivors` runs the round-1 test file against each mutant in the sandbox, with a limit of `MUTANT_SECONDS = 60` for each run. A mutant whose run exits 0 survives.
- If a mutant survives, `harden` starts a new agent conversation with `HINT_TASK`. The task lists each surviving change and tells the agent to add tests that pass on the original and fail with the change. The hint round has its own limits: `HINT_STEPS = 8` and `HINT_SECONDS = 90`.
- The gate uses the hinted test file only if it passes the same check as round 1 and its survivors are a strict subset of the round-1 survivors. Otherwise the gate keeps the round-1 file. An error in the hint round also keeps the round-1 file and prints the error to stderr.
- The `gate.mutants` span records the exit code of each mutant. The `gate.hint` span records the stop reason and the result (`hinted` or `kept round 1`).

**Worked example.** Input: `transformed` in `bench/detect.py` at commit `0a8887b` (the PR #23 function), trace `cd3c18ea`.
- Round 1 proved a test file. The mutant `line 237: if len(found) == count: changed to if len(found) >= count:` survived it. That mutant is the PR #23 rewrite.
- The hint round added `test_transformed_count_zero_boundary`. It calls `transformed(["kind"], pool, 0)` with two accepted items and asserts 2 results. The original never breaks for `count=0`. The `>=` version breaks after the first item.
- The hinted file kills the mutant, so the gate uses it.
- The real PR #23 rewrite, spliced into the file, now fails the final test file: exit code 1, `1 failed, 5 passed`.

**Measurement: bench run on 2026-10-17.** Input: the 36 functions of the ticket 41 benchmark plus `transformed@0a8887b`. Each function is its own control: the survivors of the round-1 file against the survivors of the final file.

- Proof rate: 31 of 37 proved. 0 errors from the mutant code. The hint round runs only after round 1 passes, and it falls back to the round-1 file, so it cannot turn a proof into a failure. The 6 failures are round-1 failures: 3 fail on the original, 1 is nondeterministic across two runs, 1 wrote no test file in the time limit, and 1 uses `uuid`. The first bench run on 2026-10-14 proved 30 of 37.
- The 31 proved functions have 25 boundary mutants. 2 are equivalent, and no test can kill them:
  - `df % s != 0` to `> 0` in `_dup_decompose` (`s >= 2`);
  - `len(args) == 1` to `<= 1` in `make_response` (an empty `args` returns earlier).
- 2 more are equivalent for every numeric input: `argindex == 1` to `<= 1` and `argindex == 2` to `<= 2` in `Ynm.fdiff`. A lower number raises the same `ArgumentIndexError` in the `else` branch. Only `argindex=None` tells them apart: the mutant raises `TypeError`.

| | Real mutants killed (Ynm counted) | Kill rate | Without the 2 Ynm mutants | Kill rate |
|---|---|---|---|---|
| Round-1 test files | 16 of 23 | 70% | 16 of 21 | 76% |
| Final test files (after the hint round) | 20 of 23 | 87% | 20 of 21 | 95% |

- The 3 real survivors: the 2 `Ynm.fdiff` mutants, and `fused[i] >= HOOK_FLOOR` to `> HOOK_FLOOR` in `matches`. A test for `matches` must make a fused score exactly equal to the floor.
- The first bench run (2026-10-14, before the review fixes) gave 59% to 86% on 22 real mutants. Round 1 varies from run to run, so the "before" numbers differ.

**Cost.** The hint round ran on 7 of 31 proved functions (23%). It used the hinted file on 4 and kept the round-1 file on 3. The 3 kept files are the 3 functions whose survivors are equivalent for numeric inputs.

| Function | Hint seconds | Steps | Input tokens | Output tokens | Survivors before, after | Result |
|---|---|---|---|---|---|---|
| `matches` | 60.3 | 8 | 45,219 | 3,440 | 2, 1 | hinted |
| `Response.json` | 51.8 | 8 | 36,704 | 2,780 | 1, 0 | hinted |
| `SingleByteCharSetProber.get_confidence` | 27.7 | 8 | 22,407 | 1,374 | 1, 0 | hinted |
| `transformed` | 29.0 | 8 | 22,978 | 1,050 | 1, 0 | hinted |
| `_dup_decompose` | 29.2 | 8 | 22,198 | 1,035 | 1, 1 | kept round 1 |
| `Ynm.fdiff` | 25.8 | 8 | 24,188 | 1,052 | 2, 2 | kept round 1 |
| `make_response` | 24.4 | 8 | 20,957 | 973 | 1, 1 | kept round 1 |

- Mutant runs: 21 of 31 proved functions have no boundary site, and they add 0 s. The other 10 add 2.5 s to 34.3 s (sum 84 s). Each hint-round file that passes the check gets one more mutant run: 2.4 s to 35.7 s (sum 56 s for 5 runs).
- The slowest function in the bench took 225 s in all. The hint round adds no model call outside the 7 functions with a survivor.

**Traces.** Project `slopgate-t51`: 1,833 spans, 0 `ERROR` spans, 0 replies with `finish_reason: "length"`. It has 7 `gate.hint` spans and 43 `gate.mutants` spans. The 543 `ChatCompletion` spans match the 543 `gate.agent` spans, so this run has no nested spans (ticket 61): each process opens its first span in its main thread.

**Dry run on PR #23.** Base `6665674`, head `0a8887b`, the code of this ticket, trace `7b5ff8d9` (164 s). The run gave 0 suggestions and 1 note. It rejected `transformed` with `rule: signature changed`, the same as the two option 1 dry runs. `gate.mutants` and `gate.hint` ran under `gate.characterize`, so they keep their parent. The trace has 0 `ERROR` spans and 0 `length` stops.
- The `>=` mutant survived round 1, and the hint round kept the round-1 file (15.5 s, 5 commands). The agent ran the tests once, then wrote "No additional tests needed; change undetectable." and stopped. `count=0` detects the change, so this is a miss.
- Over all runs, the hint round killed the `transformed` mutant in 5 of 7 runs: bench run 1, bench run 2, 3 of 4 runs of variant A below, and not in this dry run.

**Prompt variants of the hint round.** The miss above raised the question: does the sentence "If no input can tell a change from the original, skip that change." let the agent give up too early? Input: one round-1 test file for each of 4 functions with a real survivor (`matches`, `Response.json`, `get_confidence`, `transformed`). Each file let 1 mutant survive. `harden` ran 4 times for each function and each variant (16 runs for each variant). Project `slopgate-t51-variants`: 2,169 spans, 0 `ERROR` spans, 0 `length` stops.

| Variant | Mutants killed | Runs that used the hinted file |
|---|---|---|
| A: current text | 14 of 16 | 14 |
| B: without the "skip" sentence | 14 of 16 | 14 |
| C: "Each change gives a different result for some input. Find that input." in its place | 13 of 16 | 13 |

The variants give the same result, so `HINT_TASK` keeps its text. Each run took 42 s to 94 s, with the two mutant runs included.

**Offline tests.** `tests/test_review.py` has 17 new tests:
- the generator: one operator for each mutant, the cap, the order across sites, and the skip of the decorators;
- the hint round: it adds a test, no round without a survivor, the fallback when the agent gives no better file, a file that kills no new mutant, a file that lets an earlier kill survive again, a file that kills more and is used;
- the limits: its own step limit, its own time budget, `MUTANT_SECONDS` for each mutant run, and the limit that `Local.run` gets;
- the trace of the exit codes and the outcome, an unreadable source file, and an error after round 1.

`uv run pytest -q`: 355 passed.

**Known limits.**
- Every hint round used all 8 steps. The stop line in `HINT_TASK` did not make the agent stop early.
- The gate cannot detect an equivalent mutant. The 3 hint rounds on equivalent mutants cost 79 s with no gain.
- The mutant runs are sequential, with `MUTANT_SECONDS = 60` each. In the worst case (8 mutants that hang, run on the round-1 file and on the hinted file, plus `HINT_SECONDS = 90`), the hint round adds about 17 minutes to one function. The slowest mutant stage in the bench took 36 s.
- Only operators change. A changed operand (`n == c - 1`) or a changed constant gives no mutant.
- The cap of 8 mutants leaves later sites out of a function with many comparisons. No function in the bench had more than 8.
- The hint round makes the test file stronger. It does not look at the rewrite. A rewrite that changes behavior in a way that no boundary mutant shows can still pass.
