# 08 — Live duplicate flag at plan time

**What to build:** A coding agent submits a plan in Claude Code. Before the agent writes any code, the hook checks each plan step against the existing functions. An existing function can already do the work of a step. In this case, the agent gets a note that names the step and the function. The agent can then change the plan.

The index gains a one-line summary for each function. Nemotron Lightning writes each summary once. The hook works as follows:
1. Split the plan into steps.
2. Search the summaries for each step.
3. Make one batched classifier call for all steps.

The hook never blocks the plan.

**Blocked by:** 07

**Status:** ready-for-agent

- [ ] The command that builds the index (`slopgate index`) writes a one-line summary for each function. Functions that the hook adds at write time also get a summary.
- [ ] The command that runs the hook (`slopgate hook`) reads a recorded `PreToolUse` payload for `ExitPlanMode`. It prints a note when a step matches an existing function.
- [ ] A plan has numbered or bulleted steps. The hook splits this plan into one query for each step.
- [ ] A plan has no matching step. In this case, the hook prints nothing.
- [ ] All steps of one plan go to the classifier in one call.
- [ ] A step is vague, for example "handle errors properly". When the classifier confidence is below 0.8, this step produces no note.
- [ ] The hook never blocks the plan. The hook exits 0.
