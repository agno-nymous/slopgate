# 08 — Live duplicate flag at plan time

## Summary

- **Goal:** When a coding agent submits a plan, tell it which plan step an existing function already does. Example: the step "write a slug helper" gets a note that names `slugify`. The agent can then change the plan.
- **Checkable finish condition:** `slopgate hook` reads a recorded `PreToolUse` payload for `ExitPlanMode`. It prints a note when a step matches an existing function, and prints nothing when no step matches. It exits 0.
- **Evidence:** Not built yet. Before: no check runs at plan time. After: tests with recorded plan payloads show the note and the empty output, and one test shows that all steps go to the classifier in one call.
- **Constraints:** The hook never blocks the plan. Nemotron Lightning writes each function summary once, and `slopgate index` stores it. Make one batched classifier call for all steps. A step with a classifier confidence below 0.8 gives no note.

**Blocked by:** 07

**Status:** ready-for-agent

## Details

The index gains a one-line summary for each function. Nemotron Lightning writes each summary once. The hook works as follows:
1. Split the plan into steps.
2. Search the summaries for each step.
3. Make one batched classifier call for all steps.

- [ ] The command that builds the index (`slopgate index`) writes a one-line summary for each function. Functions that the hook adds at write time also get a summary.
- [ ] The command that runs the hook (`slopgate hook`) reads a recorded `PreToolUse` payload for `ExitPlanMode`. It prints a note when a step matches an existing function.
- [ ] A plan has numbered or bulleted steps. The hook splits this plan into one query for each step.
- [ ] A plan has no matching step. In this case, the hook prints nothing.
- [ ] All steps of one plan go to the classifier in one call.
- [ ] A step is vague, for example "handle errors properly". When the classifier confidence is below 0.8, this step produces no note.
- [ ] The hook never blocks the plan. The hook exits 0.
