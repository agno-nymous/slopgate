# 07 — Live duplicate flag at edit time

**What to build:** A coding agent works in Claude Code. A hook checks every file that the agent writes or edits. A new function can duplicate an existing function. In this case, the hook adds a note to the context of the agent. The note names the existing function and its file. The note also gives a confidence score. The hook never blocks the write.

The hook does these steps in order:
1. It parses the new functions.
2. It checks the structure hash.
3. It runs a local keyword and vector search.

The hook calls the classifier only when a candidate passes the score floor. The classifier is Nemotron Lightning. It is limited to a one-token yes/no answer. The log-probability of the token is the confidence. The flag threshold is 0.8.

The hook puts each new function into the index when the agent writes it. For this reason, the hook also checks the earlier functions of the agent. The ticket also documents how to install the hook in the Claude Code settings of a project.

**Blocked by:** 04

**Status:** ready-for-agent

- [ ] The command that runs the hook (`slopgate hook`) reads a recorded `PostToolUse` payload for `Write` or `Edit` from stdin. It prints a note in the format that Claude Code accepts as added context.
- [ ] A write duplicates an existing helper. In this case, the hook produces a note. The note names that helper, its file, and the confidence.
- [ ] A write has no candidate above the floor. In this case, the hook prints nothing and makes no network call. A test asserts this behavior.
- [ ] On the path with no candidate, record the median runtime on the test machine in the Comments of the ticket. The embedding model stays loaded or is cached. Measure a cold load of the model separately.
- [ ] The hook finds a function that the agent wrote earlier in the same session. This happens when the agent later writes a copy of the function.
- [ ] A classifier confidence below 0.8 produces no note.
- [ ] The hook exits 0 in every case. This includes a parse error in the written file.
