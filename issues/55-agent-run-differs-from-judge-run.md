# 55 — The test agent passes only with changes that the judge does not keep

## Summary

- **Goal:** Make the test agent's passing run the same as the judge's run. Example: on flask#5818, the agent's tests failed in flask's `tests/conftest.py`. The agent ran `mv tests/conftest.py` and added `--source=src` to its command. Then its tests passed. The judge (`check`) runs the test file alone on a fresh copy of the checkpoint, with the fixed command. So the judge got the failure again and rejected the function.
- **Checkable finish condition:** On the 4 ticket 49 runs that had this cause, the agent's last passing command and the judge's command give the same result. The Comments show the result of a dry run on flask#5818 and django#21736.
- **Evidence:** Before: ticket 49 (2026-10-11), 4 of 7 external candidates. flask#5818: the agent moved `conftest.py` (3 runs), or used `--noconftest` and `--source=src` (1 run). django#21736: the agent passed only with `DJANGO_SETTINGS_MODULE=tests.auth_tests.settings` on its command line, and the judge failed with "settings are not configured". After: the dry runs.
- **Constraints:** The judge stays as it is: only the test file is kept, and the command is fixed. Change a prompt only after a live comparison with at least 3 runs for each function (ticket 49 showed that one run is noise).

**Blocked by:** —

**Status:** ready-for-agent

## Context

`characterize` gives the agent a sandbox session. The agent can change any file and run any command in it. `AGENT_RULES` says "Do not change any file except {test_path}", but it does not say that the judge runs exactly `{cmd}` on a fresh copy and keeps only the test file.

## Design

Compare, with at least 3 runs for each function:

1. **Now.**
2. **A rule in the prompt:** "Only the test file is kept. The judge runs exactly `<cmd>` on a fresh copy of the repository. Put each setting (for example, an environment variable) in the test file."
3. **The session runs the judge.** Before each `execute`, reset every file except the test file. Run the agent's test commands with the fixed `cmd` only.

## Acceptance

- [ ] A table in the Comments gives the pass rate of each design on the 4 functions.
- [ ] The chosen design is built, and `uv run pytest -q` passes.

## Comments
