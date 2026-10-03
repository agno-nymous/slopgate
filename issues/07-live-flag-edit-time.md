# 07 — Live duplicate flag at edit time

**What to build:** While a coding agent works in Claude Code, a hook checks every file the agent writes or edits. When a new function duplicates an existing one, the hook adds a note to the agent's context. The note names the existing function, its file, and a confidence score. The hook never blocks the write.

The hook first parses the new functions, checks the structure hash, and runs a local keyword and vector search. It calls the classifier only when a candidate passes the score floor. The classifier is Nemotron Lightning, limited to a one-token yes/no answer, with the token's log-probability as confidence. The flag threshold is 0.8.

Each new function goes into the index as soon as it is written, so the agent's own earlier functions are checked too. The ticket also documents how to install the hook in a project's Claude Code settings.

**Blocked by:** 04

**Status:** ready-for-agent

- [ ] `slopgate hook` reads a recorded `PostToolUse` payload for `Write` or `Edit` from stdin and prints a note in the format Claude Code accepts as added context.
- [ ] A write that duplicates an existing helper produces a note naming that helper, its file, and the confidence.
- [ ] A write with no candidate above the floor prints nothing and makes no network call; a test asserts this.
- [ ] On the no-candidate path, median runtime on the test machine is recorded in the ticket's Comments. (The embedding model stays loaded or is cached, so a cold model load is measured separately.)
- [ ] A function written earlier in the same session is found when the agent writes a copy of it later.
- [ ] Classifier confidence below 0.8 produces no note.
- [ ] The hook exits 0 in every case, including a parse error in the written file.
