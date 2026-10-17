# 62 — The test agent runs filler commands until the step limit after its test file passes

## Summary

- **Goal:** End the test agent's loop when its test file is done, not at the step limit.
- **Checkable finish condition:** In a bench run, the hint round stops before `HINT_STEPS` in most runs, and the kill rate and the proof rate do not fall.
- **Evidence:** Before: in the ticket 51 variant run (project `slopgate-t51-variants`, 2026-10-17), 41 of 48 `gate.hint` spans stopped at the step limit (`HINT_STEPS = 8`). In span `61152838e7293f05` (`matches`), the file passed at step 4. Steps 5 to 8 were `echo 'Task complete'`, `echo 'Tests written and pass on original code.'`, and `true`. Filler commands (`echo`, `true`, `pwd`, `ls`) are 92 of 493 `sandbox.execute` spans in that project, 111 of 1,088 in `slopgate-t51`, and 43 of 919 in `slopgate-gate`. After: the same counts in a rerun.
- **Constraints:** The sandbox proof stays the judge. Do not add a model call.

**Blocked by:** —

**Status:** ready-for-agent

**Type:** performance.

## Context

`converse` in `slopgate/review.py` ends the loop on a reply with no tool call, or at a step, time, or token limit. `llm.step` sends `tool_choice="auto"`. Super almost never sends a reply without a tool call, so it fills the remaining steps with commands that do nothing. Round 1 has the same problem: ticket 41 found that at least half of the agent runs reach the 15-step limit.

Another Claude session found this in the ticket 51 traces. I checked the counts above in `~/.phoenix/phoenix.db`.

## Design

Measure first: in the existing traces, count how often the agent changed the test file after it first passed. If that is rare, stop the loop on the outside judge. After each command that writes the test file, run `check` on it. In the hint round, also run `survivors`. Stop when the file passes (round 1), or when it passes and kills the target mutants (hint round).

Each `check` costs sandbox runs. Measure that cost against the saved steps.

## Acceptance

- [ ] The Comments give the count of runs where the test file changed after it first passed.
- [ ] A bench run gives the steps, the seconds, the kill rate, and the proof rate, before and after.
- [ ] `uv run pytest -q` passes.
