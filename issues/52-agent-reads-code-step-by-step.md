# 52 — The test agent uses its steps to read code

## Summary

- **Goal:** Let the test agent spend its steps on tests, not on reading the repository. Example: on PR #31, the agent ran 15 commands for `replace_calls` (`slopgate/review.py`, 41 lines). 13 of them were `sed`, `grep`, or `cat` on one part of the code at a time. It wrote its test file at step 15 and never ran it. It used 55,000 of its 150,000 tokens.
- **Checkable finish condition:** A live comparison on the same functions, at least 3 runs each, shows a higher pass rate or fewer steps for the chosen design than for the current prompt.
- **Evidence:** Before: in the 13 agent runs of ticket 49, 77 of 201 commands only read code. 6 of the 9 runs on this repository started with the same `find` and `ls` commands. Only 1 of the 13 runs stopped by itself. 9 stopped at the step limit and 3 at the token limit. After: the comparison table.
- **Constraints:** Measure before the build: the ticket 49 comparison showed that one run per function is noise. Do not lower the branch coverage rule.

**Blocked by:** —

**Status:** done

## Context

`AGENT_TASK` in `slopgate/review.py` gives the source of the target function, its path, and the import line. It does not give the imports of the module or the source of the functions that the target calls. So the agent reads them with shell commands, one per step.

In ticket 49, 2 prompt changes gave no gain on 7 functions (one run each): a missed-branch command filtered to the lines of the target, and a rule that tells the agent how to stop.

## Design

Compare, with at least 3 runs per function on the ticket 49 functions and on 5 functions from the ticket 37 pool:

1. **Now.**
2. **More context in the task.** Add the import block of the module and the source of each function from the same module that the target calls.
3. **A higher step limit.** `AGENT_STEPS` 25, with the token limit unchanged.

## Acceptance

- [x] A table in the Comments gives the pass rate, the steps, the tokens, and the time of each design.
- [x] The chosen design is built, and `uv run pytest -q` passes.

## Comments

### 2026-10-12: no change; the comparison shows no gain

**What was tried.** Design 2 (the imports of the module and the source of each same-module function that the target calls, in the task) was built, measured, and removed. Design 3 (`AGENT_STEPS` 25) was measured with a patch in a script. The current prompt stays.

**Measured results.** Live runs, Nemotron Super, ConTree sandbox, 3 runs for each function, traced in Phoenix (project `slopgate-exp`), 2 rounds. 5 pool functions (ticket 37) and the 3 flask functions of ticket 49. The django test method is left out: it fails in every design (ticket 56).

| Design | Pool (30 runs) | Flask (18 runs) | All (48) | Mean model calls (pool) | Mean tokens (pool) | Mean seconds (pool) |
|---|---|---|---|---|---|---|
| Now | 22 | 16 | 38 | 14.5 | 87,000 | 90 |
| More context in the task | 25 | 12 | 37 | 13.9 | 83,800 | 86 |
| Step limit 25 | 23 | 14 | 37 | 18.2 | 129,400 | 108 |

The pass rates differ by 1 run of 48. The variance is larger than that: a function went from 3 of 3 to 1 of 3 between two rounds with the same design. More context did not cut the model calls (14.5 to 13.9). A step limit of 25 used 49% more tokens for no gain.

**Finding from the traces.** The steps that read code are not the main cause of the failures. Most failures on flask are the step or time limit after 12 to 15 steps of tests and fixes. The `RangeField.to_python` runs in the pool failed for another cause (an installed package: ticket 55).

**Known limits.** 8 functions, 3 runs each. A gain below about 10 percentage points cannot be seen with this sample. The Token Factory API stalls (see ticket 55) hit some runs of both rounds.
