# 55 — The test agent passes only with changes that the judge does not keep

## Summary

- **Goal:** Make the test agent's passing run the same as the judge's run. Example: on flask#5818, the agent's tests failed in flask's `tests/conftest.py`. The agent ran `mv tests/conftest.py` and added `--source=src` to its command. Then its tests passed. The judge (`check`) runs the test file alone on a fresh copy of the checkpoint, with the fixed command. So the judge got the failure again and rejected the function.
- **Checkable finish condition:** On the 4 ticket 49 runs that had this cause, the agent's last passing command and the judge's command give the same result. The Comments show the result of a dry run on flask#5818 and django#21736.
- **Evidence:** Before: ticket 49 (2026-10-11), 4 of 7 external candidates. flask#5818: the agent moved `conftest.py` (3 runs), or used `--noconftest` and `--source=src` (1 run). django#21736: the agent passed only with `DJANGO_SETTINGS_MODULE=tests.auth_tests.settings` on its command line, and the judge failed with "settings are not configured". After: the dry runs.
- **Constraints:** The judge stays as it is: only the test file is kept, and the command is fixed. Change a prompt only after a live comparison with at least 3 runs for each function (ticket 49 showed that one run is noise).

**Blocked by:** —

**Status:** done

## Context

`characterize` gives the agent a sandbox session. The agent can change any file and run any command in it. `AGENT_RULES` says "Do not change any file except {test_path}", but it does not say that the judge runs exactly `{cmd}` on a fresh copy and keeps only the test file.

## Design

Compare, with at least 3 runs for each function:

1. **Now.**
2. **A rule in the prompt:** "Only the test file is kept. The judge runs exactly `<cmd>` on a fresh copy of the repository. Put each setting (for example, an environment variable) in the test file."
3. **The session runs the judge.** Before each `execute`, reset every file except the test file. Run the agent's test commands with the fixed `cmd` only.

## Acceptance

- [x] A table in the Comments gives the pass rate of each design on the 4 functions.
- [x] The chosen design is built, and `uv run pytest -q` passes.

## Comments

### 2026-10-12: the cause is a package install, and a prompt rule fixes it

**What was built.** One rule in `AGENT_RULES` (`slopgate/review.py`): "Do not install packages. The tests run later on a copy of the repository that has only the packages that are installed now. If a module is missing, replace it in {test_path}, for example with unittest.mock.patch.dict(sys.modules, ...)." One offline test checks that the system prompt has the rule.

**What the traces showed.** The causes in the ticket text (a moved `conftest.py`, an environment variable) did not appear in 72 runs on flask#5818 and the django test method. Ticket 53 (pinned dependencies) removed the flask `notset` failure. One cause remained: the agent ran `pip install` in its own session. The judge uses a fresh copy of the checkpoint, so the package is missing there.

**Worked example.** `RangeField.to_python` (`django/contrib/postgres/fields/ranges.py`). The class imports `psycopg2`, and the sandbox has no `psycopg2`.

- Before: trace `eae6b1a9` (Phoenix project `slopgate-exp`). The agent ran `pip install psycopg2-binary`. Its tests passed twice (3 passed). The judge ran the same file on the fresh copy and got `ModuleNotFoundError: No module named 'psycopg2'`. Result: rejected, "characterization tests fail on original".
- After: trace `cfcb3f86`. The agent wrote `sys.modules['psycopg2'] = Mock()` and `sys.modules['psycopg2.extras'] = Mock()` at the top of the test file. Result: proved.

**Measured results.** Live runs with Nemotron Super as the test agent, ConTree sandbox, 3 runs for each function unless stated. All runs were traced in Phoenix (project `slopgate-exp`). A first round without tracing had a script defect: it never called `trace.start`. It was run again with tracing.

Install rule on `RangeField.to_python` (5 runs for each design):

| Design | Proved | Mean tokens | Mean seconds |
|---|---|---|---|
| Current prompt | 0 of 5 | 71,800 | 96 |
| Prompt rule (built) | 4 of 5 | 35,100 | 138 |
| The session refuses `pip install` and tells the agent why | 3 of 5 | 30,700 | 170 |

Before the rule, the current prompt proved 0 of 9 runs of this function in the earlier rounds. With the built rule: 3 of 3.

Designs from the ticket on 3 flask functions (18 runs each, 2 rounds) and the django test method (6 runs):

| Design | flask | django test method | Mean tokens | Mean seconds |
|---|---|---|---|---|
| Now | 16 of 18 | 0 of 6 | 114,000 | 72 |
| A rule: "only the test file is kept, the judge runs this command" | 11 of 18 | 0 of 6 | 86,000 | 75 |
| The session resets every file except the test file before each command | 10 of 18 | 0 of 6 | 55,000 | 122 |
| A rule: "run the judge command after your last change" | 14 of 18 | 0 of 6 | 85,000 | 78 |

None of them beats the current prompt. They address files and environment variables, and the traces show no failure of that kind. The session reset is also slower.

No regression with the built rule on 7 other functions (3 flask, `handle_url_build_error`, `iter_lines`, `_dup_decompose`, `_print_LeviCivita`): 11 of 12 in one round, and 8 of 9 for the 3 functions that the API stalls had hit in the first try.

**Finding from the traces: the Token Factory API stalls.** In one window the median model call took 11 s to 14 s (normally 1.5 s), and single calls took 113 s to 129 s. The agent has a limit of 120 s, so those runs ended with "time limit" or "no test file". 6 of the 7 failures of the first run with the built rule came from this. I stopped the runs, waited until a probe call took 1.5 s again, and ran the 3 affected functions again. Phoenix showed it: a failure with one very long `ChatCompletion` span is the API, not the design.

**Other findings.**

- Nemotron Ultra as the test agent: 4 of 24 runs proved (Super: 22 of 24 on the same functions with the built rule). 15 runs ended with "no test file": Ultra probed with `python -c` one-liners for 15 steps and wrote no test file (trace `8c96fc60`). Super stays the test agent.
- The django test method (`EmailValidatorDeprecationTests...`) fails in every design: a django `SimpleTestCase` needs django's own runner and settings. That is ticket 56.

**Known limits.** The sample is 3 runs for each function and 8 functions. `RangeField` is the only function with this cause, so the gain is measured on one function. The rule does not help when a package is missing and cannot be replaced by a mock, for example when the test needs the real package.
