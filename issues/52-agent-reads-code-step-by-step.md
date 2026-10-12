# 52 — The test agent uses its steps to read code

## Summary

- **Goal:** Let the test agent spend its steps on tests, not on reading the repository. Example: on PR #31, the agent ran 15 commands for `replace_calls` (`slopgate/review.py`, 41 lines). 13 of them were `sed`, `grep`, or `cat` on one part of the code at a time. It wrote its test file at step 15 and never ran it. It used 55,000 of its 150,000 tokens.
- **Checkable finish condition:** A live comparison on the same functions, at least 3 runs each, shows a higher pass rate or fewer steps for the chosen design than for the current prompt.
- **Evidence:** Before: in the 13 agent runs of ticket 49, 77 of 201 commands only read code. 6 of the 9 runs on this repository started with the same `find` and `ls` commands. Only 1 of the 13 runs stopped by itself. 9 stopped at the step limit and 3 at the token limit. After: the comparison table.
- **Constraints:** Measure before the build: the ticket 49 comparison showed that one run per function is noise. Do not lower the branch coverage rule.

**Blocked by:** —

**Status:** ready-for-agent

## Context

`AGENT_TASK` in `slopgate/review.py` gives the source of the target function, its path, and the import line. It does not give the imports of the module or the source of the functions that the target calls. So the agent reads them with shell commands, one per step.

In ticket 49, 2 prompt changes gave no gain on 7 functions (one run each): a missed-branch command filtered to the lines of the target, and a rule that tells the agent how to stop.

## Design

Compare, with at least 3 runs per function on the ticket 49 functions and on 5 functions from the ticket 37 pool:

1. **Now.**
2. **More context in the task.** Add the import block of the module and the source of each function from the same module that the target calls.
3. **A higher step limit.** `AGENT_STEPS` 25, with the token limit unchanged.

## Acceptance

- [ ] A table in the Comments gives the pass rate, the steps, the tokens, and the time of each design.
- [ ] The chosen design is built, and `uv run pytest -q` passes.

## Comments
