# 65 — Measure the write-time hook on a Nemotron coding agent

## Summary

- **Goal:** Show that Slopgate stops slop while an agent writes code, and that the agent still solves its task. Example: a Nemotron Super coding agent fixes a SWE-bench issue in a ConTree sandbox. With the hook on, the agent gets a note such as "`parse_header` nests 5 blocks deep. Flatten it with guard clauses." and its patch has less slop.
- **Checkable finish condition:** A results file gives, for the same SWE-bench tasks with the hook on and with the hook off: the resolve rate by the hidden tests, the slop findings per patch by `classify`, the tokens, and the cost. The README links the file.
- **Evidence:** Before: the hook flags only duplicates, and only in Claude Code. No measurement shows that a note at write time changes the code that an agent writes. After: the results file.
- **Constraints:** Do this ticket after ticket 64, unless the decision point of 2026-10-20 in `ROADMAP.md` moves it first. The coding agent is Nemotron Super through Token Factory, and its sandbox is ConTree. Keep the total cost under $15. Use the same tasks, the same prompts, and the same step limits in both arms. Run each task at least 2 times in each arm. The resolve rate with the hook on must not fall: report it with its range.

**Blocked by:** 10

**Status:** ready-for-agent

**Type:** measurement, then build.

## Context

Ticket 49 found 0 suggestions on 10 pull requests. All 7 candidate runs ended in a harness rejection. A fix after the pull request is expensive: an agent run, a sandbox proof, and the repo suite for each function. A note at write time costs one `classify` call, with no model call. The agent that writes the code also has the context and can run its own tests.

The test agent of ticket 41 already has a tool loop on a ConTree session (`llm.step`, the `execute` tool). A coding agent can use the same loop.

## Design

1. **Hook note.** After each file write by the agent, run `classify` on the changed functions. If it finds a kind, add one line for each kind to the next tool result: the function, the kind, the measured value, and the fix text from `kinds.py`. Do not call a model.
2. **Agent.** Super with one `execute` tool in a ConTree session at the base commit of each task. The task prompt is the SWE-bench problem statement. The step and token limits are the same in both arms.
3. **Tasks.** 10 to 15 SWE-bench Lite tasks from the repos that install in the sandbox (ticket 53: django, requests, sympy, flask).
4. **Judge.** The SWE-bench hidden tests (`FAIL_TO_PASS` and `PASS_TO_PASS`) on the final patch. `classify` on each changed function of the final patch.
5. **Report.** The resolve rate and the slop per patch in each arm, with a bootstrap range over tasks.

## Acceptance

- [ ] The results file gives the resolve rate, the slop findings per patch, the tokens, and the cost in each arm.
- [ ] Each task runs at least 2 times in each arm.
- [ ] The total cost is under $15.
- [ ] The README links the results file.
- [ ] `uv run pytest -q` passes.

## Comments
