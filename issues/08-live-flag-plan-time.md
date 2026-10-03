# 08 — Live duplicate flag at plan time

**What to build:** When a coding agent submits a plan in Claude Code, the hook checks each plan step against existing functions before any code is written. If a step is already done by an existing function, the agent gets a note that names the step and the function, so it can change the plan.

The index gains a one-line summary per function, written once by Nemotron Lightning. The hook works as follows:
1. Split the plan into steps.
2. Search the summaries for each step.
3. Make one batched classifier call for all steps.

The hook never blocks the plan.

**Blocked by:** 07

**Status:** ready-for-agent

- [ ] `slopgate index` writes a one-line summary per function, and functions added at write time get a summary too.
- [ ] `slopgate hook` reads a recorded `PreToolUse` payload for `ExitPlanMode` and prints a note when a step matches an existing function.
- [ ] A plan with numbered or bulleted steps is split into one query per step.
- [ ] A plan with no matching step prints nothing.
- [ ] All steps of one plan go to the classifier in one call.
- [ ] Vague steps (for example "handle errors properly") produce no note when the classifier confidence is below 0.8.
- [ ] The hook never blocks the plan and exits 0.
