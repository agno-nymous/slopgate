# 49 — Find the gate's errors in the Phoenix traces, and fix the harness

## Summary

- **Goal:** Find why the gate gives wrong or lost results on real pull requests, from the traces in Arize Phoenix. Each error gets a cause and a fix. Example: a rejection "characterization tests fail on original" on `review` (PR #32 dry run). The trace shows that the test agent's test called `llm.decide` with no key. The fix can be a rule in the agent's prompt, a fake in the sandbox, or a cheap early reject.
- **Checkable finish condition:** A table in `## Comments` lists every gate result of the traced runs that is wrong or lost. Each row has the trace id, the step, the cause, and a fix: either a merged change, or a new ticket under `issues/`. The traced runs cover at least 10 pull requests.
- **Evidence:** Before: Phoenix holds 8 `gate.review` traces (2026-10-11). Nobody has read them for errors as a set. The open gate tickets (40, 43, 44, 45, 47, 48) come from single runs and code reviews. After: the error table, with a count for each cause.
- **Constraints:** Measure, do not guess: each cause in the table points to a span in a trace. Change a model prompt only after a live comparison of the variants (about 8 tries each, as in `CLAUDE.md`). Do not post to GitHub: use `--dry-run`. The Slopgate workflow stays disabled until the user says so.

**Blocked by:** None — can start immediately.

**Status:** done

## Context

Ticket 32 traces every model request, sandbox command, and gate step in Phoenix. The span names are `gate.review`, `gate.function`, `gate.classify`, `gate.duplicate`, `gate.same_job`, `gate.characterize`, `gate.agent`, `gate.tests`, `gate.proof`, `sandbox.prepare`, `sandbox.run`, and `sandbox.execute`. Each span holds its input and output.

The gate has errors that the user sees on pull requests: wrong slop kinds (PR #20, ticket 36), lost reviews (ticket 46), rejections with no clear cause, and slow runs. The open tickets fix the errors that one run showed. Nobody has read many traced runs as a set yet, so the most frequent causes are not known.

## Design

1. Start Phoenix: `PHOENIX_HOST=127.0.0.1 uvx arize-phoenix serve`. Set `PHOENIX_COLLECTOR_ENDPOINT` in `.env` (see the tracing rules in `CLAUDE.md`).
2. Run the gate with tracing on, as a dry run, on at least 10 pull requests:
   - the merged pull requests of this repo from #20 to #32: `uv run --env-file .env slopgate review --pr <number> --dry-run`;
   - the pull requests of `slopgate-demo`.
3. Read the traces with the `phoenix-cli` skill. For each function that the gate looks at, record: the kind, the result (suggestion, note, rejection), the step that decided it, the tokens, and the time.
4. Mark each result as right or wrong. A result is wrong when:
   - the kind is wrong for the code;
   - a rejection comes from the harness (the sandbox, the import line, the prompt, a missing fake), not from the rewrite;
   - the agent stops at the token limit or the time limit;
   - a step takes more than 60 s.
5. Group the wrong results by cause. Count each cause.
6. For each cause: fix it in this ticket when the fix is small and clear, or write a new ticket. When a cause is already an open ticket (40, 43, 44, 45, 47, 48), add the count to that ticket and do not write a new one.
7. Re-run the gate on the same pull requests after the fixes. Compare the counts.

## Acceptance

- [x] At least 10 pull requests have a traced gate run in Phoenix.
- [x] `## Comments` has the error table: trace id, function, step, cause, fix or ticket.
- [x] Each cause has a count.
- [x] Each cause has a merged fix or a ticket under `issues/`.
- [x] A re-run after the fixes gives the new counts.
- [x] `uv run pytest -q` passes.

## Comments

### 2026-10-11 — results on external pull requests (main sample)

**Why this sample.** The user said that a sample of this repository's own pull requests overfits the gate to its own code. So the main sample is 10 pull requests from 6 SWE-bench repositories. The own-PR results are below, as a second sample.

**What was done.** The gate ran as a traced dry run (`--dry-run`) on these pull requests: pallets/flask#5818, #5736, #4646; sphinx-doc/sphinx#14140; sympy/sympy#30323, #30301; django/django#21886, #21736; pydata/xarray#11645; pytest-dev/pytest#14921. An Opus subagent read the spans of each candidate and judged the kind and the cause. It also ran `classify` again on each changed function, to find slop that the gate missed. The main session checked the top cause by hand on flask#5818.

**Worked example.** Trace `b7843283`, flask#5818, `Flask.update_template_context` (`nesting`).

- The pull request changed only 2 parts of the function: the signature, and the line `if (ctx := _cv_app.get(None)) is not None and ctx.has_request:`, which became `if ctx.has_request:`.
- The nested `for` / `if` / `for` block that gave `nesting` is old code. The pull request did not write it (ticket 54).
- The sandbox installed the newest `pytest`, because `commands` ignores flask's `uv.lock`. Flask's `tests/conftest.py` then failed: "has no attribute 'notset'" (ticket 53).
- The test agent passed only after `mv tests/conftest.py` and `--source=src`. The judge runs the test file alone on a fresh copy, so the judge failed again (ticket 55).
- The agent also wrote `from src.flask.app import Flask` (ticket 44).
- Result: "step limit: characterization tests fail on original", after 15 steps, 86,791 tokens, and 61 s.

**Per-candidate table.** 7 candidate runs of 6 functions: `find_best_app` ran 2 times (before and after fix 2). All 7 are harness rejections. The 10 pull requests got 0 suggestions and 0 follow-ups. "char" is the `gate.characterize` span.

| Trace | PR | Function | Kind | Result | Kind right? | Cause | Tokens | Time |
|---|---|---|---|---|---|---|---|---|
| b7843283 | flask#5818 | `Flask.update_template_context` | nesting | rejected, char step limit | old code | 54; 53 (`notset`); 55 (`mv conftest.py`, `--source=src`); 44 | 87,000 | 61 s |
| b7843283 | flask#5818 | `Flask.preprocess_request` | nesting | rejected, char step limit | old code | 54; 53; 55; 44 | 89,000 | 67 s |
| b7843283 | flask#5818 | `Flask.process_response` | nesting | rejected, char step limit | old code | 54; 53; 55 (`--noconftest --source=src`); 44 | 104,000 | 72 s |
| b7843283 | flask#5818 | `Flask.do_teardown_request` | nesting | rejected, agent error 400 | old code | `shown()` put one line of 721,143 chars into the prompt 2 times: "prompt contains at least 229377 input tokens" (fixed here); 54; 53; 44 | 100,000 | 73 s |
| 1d564d20 | flask#4646 | `find_best_app` | nesting | rejected, char token limit | old code | no install for a `setup.py` repo (fixed here); 54; 44 | 169,000 | 59 s |
| c76dc0c3 | flask#4646 (re-run) | `find_best_app` | nesting | rejected, char token limit | old code | Werkzeug 3 has no `url_quote` (53); 54 | 169,000 | 60 s |
| 1ce129a1 | django#21736 | `EmailValidatorDeprecationTests.test_call_override_using_stock_validate_domain_part_warns` | dead | rejected, char step limit | right (`user_part` is not used), but it is a test method | `tests.py` is not a test file (56); the agent passed only with `DJANGO_SETTINGS_MODULE` on its command line (55); 3 steps were `echo 'Task complete.'` (52) | 94,000 | 60 s |

**Count for each cause (external).** One candidate can have more than one cause.

| Cause | Count | Fix or ticket |
|---|---|---|
| The kind is in old lines that the pull request did not write | 6 of 7 | 54 (new) |
| The sandbox installs the newest dependencies and ignores `uv.lock` and the dependency groups | 5 of 7 | 53 (extended) |
| `src/` layout import line | 5 of 7 | 44 (count added) |
| The agent's passing run differs from the judge's run | 4 of 7 | 55 (new) |
| `shown()` puts a long single line into the prompt 2 times | 1 of 7 | fixed here |
| No install for a `setup.py` repo | 1 of 7 | fixed here |
| `tests.py` is not a test file, and django has no settings | 1 of 7 | 56 (new) |
| The agent uses steps after its tests pass | 1 of 7 | 52 |

**Missed slop (recall).** `classify` ran again on each changed function that is not a test.

| PR | Functions | Flagged | Missed |
|---|---|---|---|
| flask#5818 | 25 | 4 (old code) | 1 |
| flask#5736 | 24 | 0 | 0 |
| flask#4646 | 13 | 1 (old code) | 0 |
| sphinx#14140 | 11 | 0 | 0 |
| sympy#30323 | 9 | 0 | 0 |
| sympy#30301 | 21 | 0 | 0 |
| django#21886 | 24 | 0 | 0 |
| django#21736 | 7 | 0 (plus 1 test method) | 0 |
| xarray#11645 | 27 | 0 | 0 |
| pytest#14921 | 3 | 0 | 0 |
| Total | 164 | 5 | 1 |

The miss is a `redundant_check` in `src/flask/ctx.py::AppContext.pop`: line 456 (`ctx is None or self._cv_token is None`) repeats the check of line 451, which already raised. The lines are old. The `_cv_app.get(None)` call on line 454 resets the facts of `repeated_checks`, and the repeated test is inside an `or`. No ticket: the lines are old, so ticket 54 would not flag them.

**Steps over 60 s (external).**

| Step | Count | Fix or ticket |
|---|---|---|
| `gate.index`: 82 s and 83 s (sympy), 163 s (django, blob-less clone) | 3 of 10 runs | 57 (new). Measured on one sympy commit (1,602 files): one `git show` per file 21.5 s, parse 3.2 s, `structure_hash` 10.7 s. One `git cat-file --batch` read all files in 0.10 s. |
| `gate.characterize`: 60 s to 73 s | 6 of 7 candidate runs | each agent used all 15 steps because the environment was broken (53, 55). Function size was not the cause: the 5 functions have 23 to 51 lines. |

**The own-PR causes on external pull requests.**

- Large function (45): 0.
- `swallowed_error` around a call into another module (50): 0. No function of the 164 got `swallowed_error`.
- The proof accepts a changed comparison (51): 0. No rewrite reached the proof, so this cause could not show.

**Fixes in this ticket.**

1. `review` (`slopgate/review.py`) runs the duplicate checks in a thread pool (`WORKERS`, `trace.bind`).
2. `commands` (`slopgate/sandbox.py`) gives `pip install -e .` for a repo with `setup.py`, as for `pyproject.toml`. A repo with only `setup.cfg` keeps the old behavior, because `pip install -e .` fails on it: "neither 'setup.py' nor 'pyproject.toml' found" (pip 26.2.1).
3. `shown` (`slopgate/review.py`) cuts each line to 8,000 characters when the output is longer than 80,000 characters. Then it keeps 5 head lines and 5 tail lines only when more than 10 lines remain. Before, an output with fewer than 10 lines went into the prompt 2 times: `shown(0, "x" * 100_000)` gave 200,067 characters. Now it gives about 8,050 characters.

**Re-run of flask#5818 after fix 3** (trace `59c5b9b0`, 88 s).

| | Before (`b7843283`) | After (`59c5b9b0`) |
|---|---|---|
| `do_teardown_request` result | agent error 400, context overflow | step limit, `conftest.py` fails (53) |
| Largest prompt of one model request | at least 229,377 tokens | 21,303 tokens |
| Agent errors | 1 of 4 | 0 of 4 |
| Suggestions | 0 | 0 |

This re-run does not test fix 3. No command of the new agent runs gave an output longer than 80,000 characters: the marker "characters truncated" is in 0 spans. The agent is not deterministic, so it did not run the command that gave the long line. The offline test `test_shown_cuts_one_huge_line_without_duplicating_it` is the proof of fix 3.

The 4 candidates still fail. The remaining causes are 53, 54, 55, and 44.

**Known limits.**

- 7 external candidate runs of 6 functions is a small number. The counts are per run. `find_best_app` (flask#4646) is in both samples. The 4 flask#5818 candidates share the same environment, so they count as 4 results of one cause set.
- 3 of the 10 external pull requests are from flask. The gate found no candidate in the other 7 repositories, except one django test method.
- The kind judgments and the causes are the reading of one Opus reviewer. The main session checked the top cause (old code) on flask#5818 by hand.
- The `pytest` version in the sandbox was not printed. The error "has no attribute 'notset'" shows that it is a version without `monkeypatch.notset`; `uv.lock` pins 8.4.1.

### 2026-10-11 — results on this repository's pull requests (second sample)

The first run used slopgate #20, #21, #22, #23, #26, #30, #31, #32, slopgate-demo #1, and flask#4646. 13 of its 15 candidates come from this repository. The causes of this sample appear 0 times in the external sample (see above), so tickets 45, 50, and 51 are lower in the ROADMAP.

**Error table (first run).** 15 candidates: 3 right, 12 wrong. "char" is the `gate.characterize` span.

| Trace | PR | Function | Kinds | Result | Step | Cause | Fix or ticket |
|---|---|---|---|---|---|---|---|
| 1d564d20 | flask#4646 | `find_best_app` | nesting | rejected | char, token limit | no install for a `setup.py` repo; `src.` import line | fixed here (`commands`); 44; 53 |
| 7105cf99 | demo#1 | `format_total` | duplicate | follow-up | proof | right | — |
| 7105cf99 | demo#1 | `discounted` | wrapper | follow-up | proof | right | — |
| 3fdd4d1d | #32 | `review` (85 lines) | nesting | rejected | char, step limit | large function | 45 |
| f3bac5b0 | #31 | `python_sources` | nesting | suggestion | proof | right; repo suite passed | — |
| f3bac5b0 | #31 | `removal` (77 lines) | nesting | rejected | char, token limit | large function | 45 |
| f3bac5b0 | #31 | `replace_calls` (41 lines) | nesting | rejected | char, step limit | 13 of 15 commands read code | 52 |
| 7120f1f8 | #30 | `review` (81 lines) | nesting | rejected | char, step limit | large function | 45 |
| 1d049b18 | #23 | `transformed` | nesting | suggestion | proof | wrong: `== count` became `>= count` | 51 |
| 48fc44ee | #22 | `summary` | swallowed_error | rejected | proof | no rewrite can fix a deliberate fallback around `llm.complete` | 50 |
| 48fc44ee | #22 | `review` (158 lines) | nesting | rejected | char, step limit | large function | 45 |
| 17a6c6b6 | #21 | `review` (156 lines) | nesting | rejected | char, token limit | large function | 45 |
| 17a6c6b6 | #21 | `characterize` (55 lines) | dead | rejected | char, step limit | large function | 45 |
| 17a6c6b6 | #21 | `summary` | swallowed_error | rejected | proof | as #22 | 50 |
| 2465d67c | #20 | `characterize` | nesting, dead | rejected | char, step limit | large function | 45 |

**Count for each cause (wrong results).**

| Cause | Count | Fix or ticket |
|---|---|---|
| Large function: the agent stops at the step limit or the token limit | 7 | 45 (counts added) |
| `swallowed_error` around a call into another module | 2 | 50 (new) |
| The proof accepts a changed comparison | 1 | 51 (new) |
| The agent reads code one command at a time and uses up its steps | 1 | 52 (new) |
| No install for a `setup.py` repo | 1 | fixed here |
| `src/` layout import line | 1 (same result) | 44 (count added) |
| An old commit installs new dependency versions | 1 (same result, seen after the fix) | 53 (new) |

**Steps over 60 s (first run).**

| Cause | Count | Fix or ticket |
|---|---|---|
| The duplicate check ran one function at a time: 77 s to 325 s for each pull request | 5 of 10 pull requests | fixed here |
| The repo suite of this repository: 180 s and 205 s (pytest alone 172 s to 199 s) | 2 of 10 | none: it is the speed of the repository's own tests |
| `gate.characterize` over 60 s | 11 of 13 agent runs | 45, 52 |

**Fixes in this ticket.**

1. `review` (`slopgate/review.py`) runs the duplicate checks in a thread pool (`WORKERS`, `trace.bind`).
2. `commands` (`slopgate/sandbox.py`) gives `pip install -e .` for a repo with `setup.py`, as for `pyproject.toml`. A repo with only `setup.cfg` keeps the old behavior, because `pip install -e .` fails on it: "neither 'setup.py' nor 'pyproject.toml' found" (pip 26.2.1).

**Re-run after the fixes (same 10 pull requests).**

| PR | Gate time before | Gate time after | Duplicate phase before | Duplicate phase after |
|---|---|---|---|---|
| #20 | 240 s | 143 s | 125 s | 22 s |
| #21 | 141 s | 135 s | 26 s | 8 s |
| #22 | 275 s | 140 s | 163 s | 27 s |
| #23 | 644 s | 373 s | 325 s | 47 s |
| #26 | 125 s | 24 s | 119 s | 20 s |
| #30 | 175 s | 157 s | 77 s | 14 s |
| #31 | 371 s | 289 s | 60 s | 14 s |
| #32 | 118 s | 94 s | 14 s | 7 s |
| demo#1 | 55 s | 45 s | 7 s | 3 s |
| flask#4646 | 100 s | 77 s | 8 s | 6 s |
| Total | 2,244 s | 1,477 s | 924 s | 168 s |

- The gate time fell by 34 %. The duplicate phase fell by 82 %. No duplicate span lost its parent.
- Wrong results: 12 of 15 before, 12 of 15 after. The fixes do not change a result yet. The flask result now fails on a later cause (ticket 53), not on the install.
- Steps over 60 s in the duplicate phase: 5 before, 0 after.
- `transformed` got the same `>= count` suggestion in the re-run (2 of 2 runs). This confirms ticket 51.
- One check in run 1 (PR #20) has no `gate.duplicate` span: that run printed `Failed to export spans batch`. Its `gate.same_job` spans exist, so the check ran.

**A prompt change that was measured and not made.** The missed-branch command in `AGENT_TASK` lists the missed branches of the whole file, not only of the target. So in #31 the agent saw branches of other functions and went on to the step limit after its tests already covered `python_sources`. A live comparison on 7 functions, one run each:

| Variant | Passed | Steps | Prompt tokens | Time |
|---|---|---|---|---|
| A: now | 2 of 7 | 91 | 746,000 | 444 s |
| B: the command filtered to the lines of the target | 2 of 7 | 90 | 687,000 | 486 s |
| C: B, plus "When you stop, reply with one short line of text and no tool call." | 3 of 7 | 89 | 941,000 | 462 s |

The same function passed in one variant and failed in another at temperature 0 (for example, `transformed` and `summary`). The counts show no gain, so the prompt stays as it is. Tickets 45 and 52 need at least 3 runs for each function.

**Known limits.**

- 10 pull requests, 15 candidates. 13 of the 15 candidates come from this repository. Its gate code is hard to test (mocks of the sandbox and the model), so cause "large function" may count less on other repositories.
- `classify` found no slop kind in 457 of the 470 functions that it checked. This ticket did not check for missed slop.
- The right or wrong mark of each kind is the judgment of one Opus reviewer, checked by hand for `transformed` and `python_sources`.
