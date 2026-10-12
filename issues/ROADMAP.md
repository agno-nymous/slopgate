# Ticket order

This file gives the order in which to do the open tickets. The deadline is **2026-10-30, 10:00 PT** (Nebius x NVIDIA hackathon).

## Next ticket

**44 — The import line is wrong for a repo with a `src/` layout.** Tickets 49, 53, and 54 are done. Ticket 44 is a small change with the highest external count (5 of 7 candidates). Then tickets 55 and 52 together (one live comparison of the agent prompt and session), then 57 and 56.

When a ticket is done, mark it done in the table below and move "Next ticket" to the next open row.

## Order

| Order | Ticket | Status | Blocked by | Why it is in this position |
|---|---|---|---|---|
| 1 | [22 — Dead-code check ignores nested parameters](22-dead-code-ignores-nested-parameters.md) | done | — | Smallest fix. It removes the two false "dead" hits from PR #9. |
| 2 | [21 — Code replies: one Python block, thinking off, reject "no change"](21-rewrite-reply-as-python-block.md) | done | — | Stops cut-off replies and empty suggestions. Ticket 20 uses its `strip_fence` and thinking changes. |
| 3 | [28 — Keyword duplicate search in the gate](28-keyword-duplicate-search.md) | done | — | The user set it next. The gate then needs no embedding model: the torch fallback took 14 GB on the 16 GB Mac. |
| 4 | [17 — Test files get review notes only](17-test-files-get-notes-only.md) | done | — | Stops the gate from changing tests. Fixes the `fake_llm` failure at its cause. |
| 5 | [20 — Tests reply as one pydantic object, sent as markdown](20-tests-reply-as-pydantic-object.md) | done | 21 | Stops prose from becoming a test file, for every function. |
| 6 | [18 — Model decisions through pydantic tool calls](18-decisions-through-pydantic-tool-calls.md) | done | — | Adds `decide`. Ticket 19 needs it. |
| 7 | [32 — Trace every model request in Arize Phoenix](32-phoenix-tracing.md) | done | — | The user set it next on 2026-10-08. Each prompt and reply becomes visible, so a failed proof can be explained from the real run. Starts with a design stage for the span names. |
| 8 | [36 — Design: how the gate picks a slop kind, and what input the model gets](36-design-slop-kind-input.md) | done | — | Design ticket. On PR #20, all 12 notes were wrong by the gate's own checks: complexity counts asserts, and the model's kind is not checked. |
| 9 | [37 — Detection benchmark on SWE-bench code with injected slop](37-detection-benchmark.md) | done | 36 | The user set it next on 2026-10-09. It measures the detection of ticket 36 on code that nobody on the project wrote, with no sandbox. |
| 10 | [30 — Give the test writer the constants the target reads](30-constants-in-callee-context.md) | wontfix | — | Replaced by ticket 41: the test agent reads the constants itself. |
| 11 | [35 — Tell the test writer that the tests run without network and keys](35-tests-run-without-network.md) | wontfix | 30 | Replaced by ticket 41: the rule is in the agent's system prompt, and the agent runs the tests. |
| 12 | [29 — Keep the passing characterization tests](29-keep-passing-characterization-tests.md) | wontfix | 20 | Replaced by ticket 41: the agent fixes or removes a failing test itself. |
| 13 | [31 — Retry once for missed branches, with 3 attempts in total](31-retry-missed-branches.md) | wontfix | 29 | Replaced by ticket 41: the agent sees the missed branches and adds tests. |
| 14 | [33 — Add a time limit to each sandbox run](33-sandbox-time-limit.md) | done | — | A model-written call such as `input()` blocks the gate with no end. |
| 15 | [34 — Report the slop of each function without a rewrite, and no raw failures in the review comment](34-readable-rejection-reasons.md) | done | — | The raw pytest output on PR #20 looked like a crash of the gate. |
| 16 | [19 — Several slop kinds per function](19-several-slop-kinds-per-function.md) | done | 18, 21, 36 | Fixes all problems of a function in one suggestion. Built in ticket 36, stage 2. |
| 17 | [23 — Log the time of each gate step](23-log-time-per-gate-step.md) | wontfix | — | Reduced on 2026-10-08 to the `Slowest:` line in the pull request comment. The Phoenix spans of ticket 32 give the time of each step. |
| 18 | [24 — Save the embedding model cache on main](24-model-cache-on-main.md) | wontfix | — | Ticket 28 removes the embedding model from the gate. |
| 19 | [25 — Faster proof](25-faster-proof.md) | done | 32 | Needs the step times from one traced review first. |
| 20 | [49 — Find the gate's errors in the Phoenix traces, and fix the harness](49-trace-review-harness-fixes.md) | done | — | The user set it first on 2026-10-11. The traces show the most frequent causes of wrong results, so the next fixes go where they help most. |
| 21 | [54 — The gate flags slop in old lines that the pull request did not write](54-flag-only-slop-the-pr-adds.md) | done | — | Found by ticket 49 on external pull requests: 6 of 7 candidate runs had their slop only in old lines. Each one cost an agent run of 60 s to 73 s. |
| 22 | [53 — An old commit installs today's versions of its dependencies](53-old-commit-installs-new-dependencies.md) | done | — | Found by ticket 49: 5 of 7 external candidates. The sandbox ignores `uv.lock` and the dependency groups, so flask#5818 (2025) got a `pytest` without `monkeypatch.notset`. Do it before ticket 10. |
| 23 | [44 — The import line is wrong for a repo with a `src/` layout](44-src-layout-import-line.md) | ready-for-agent | — | All 6 pytest functions failed in every design of ticket 41. Ticket 49: 5 of 7 external candidates. A small change. |
| 24 | [55 — The test agent passes only with changes that the judge does not keep](55-agent-run-differs-from-judge-run.md) | ready-for-agent | — | Found by ticket 49: 4 of 7 external candidates. The agent moved `conftest.py` or set an environment variable, and the judge did not. Do it together with ticket 52: both change how the agent is prompted or how its session behaves, so one live comparison on the same functions answers both. Test a rule that says "run the test file after each rewrite" too (the pylint trace of ticket 53 never ran its last rewrite). |
| 25 | [52 — The test agent uses its steps to read code](52-agent-reads-code-step-by-step.md) | ready-for-agent | — | Found by ticket 49: 77 of 201 agent commands only read code. External: 1 of 7. Do it together with ticket 55 (one live comparison). The traces of ticket 53 show 2 of 4 agent runs ended at the step limit after 3 to 8 steps of reading or experiments. |
| 26 | [57 — Building the function index takes more than 80 s on a large repository](57-faster-function-index.md) | ready-for-agent | — | Found by ticket 49: `gate.index` took 82 s to 163 s on sympy and django. Speed only. |
| 27 | [56 — The test-file rule misses `tests.py`, and django tests do not run under pytest](56-django-test-layout.md) | ready-for-agent | — | Found by ticket 49 on django#21736: a django test method got an agent run instead of a note. |
| 28 | [48 — Compare the repo suite with a baseline run of the original code](48-repo-suite-baseline.md) | ready-for-agent | — | A repo test that fails on the original code rejects every rewrite: 2 of 8 sympy rewrites in the ticket 38 run. |
| 29 | [51 — The proof accepts a rewrite that changes a comparison](51-proof-misses-changed-comparison.md) | ready-for-agent | — | Found by ticket 49 on this repository's pull requests: a suggestion changed `== count` to `>= count` (2 of 2 runs). No external rewrite reached the proof, so the external count is not known. |
| 30 | [45 — The test agent cannot characterize large functions](45-characterize-large-functions.md) | ready-for-agent | 41 (done) | The agent proved no function of complexity 17 or more. Ticket 49: 7 of 12 wrong results on this repository's pull requests, 0 of 7 on external pull requests. |
| 31 | [50 — The gate cannot fix `swallowed_error` around a call to other code](50-swallowed-error-external-call.md) | ready-for-agent | — | Found by ticket 49 on this repository's pull requests: 2 of 12. 0 of 164 external functions got `swallowed_error`. |
| 32 | [43 — The gate cannot prove a `redundant_check` rewrite](43-dead-branch-of-redundant-check.md) | ready-for-agent | 39 (done) | No rewrite of this kind can pass the branch coverage rule. |
| 33 | [40 — Limit the output tokens of `decide`](40-limit-decide-output.md) | ready-for-agent | — | 5 of 1,407 runs took 60 s to 110 s. Speed only. |
| 34 | [47 — `parse` splits lines on a form feed, so later functions get the wrong source](47-parse-splits-on-form-feed.md) | ready-for-agent | — | Not seen in the 12 SWE-bench Lite repos. |
| 35 | [27 — Run the gate automatically on a self-hosted runner](27-gate-on-self-hosted-runner.md) | needs-live-check | 26 (done) | Turn the Slopgate workflow on again only when the user says so. Then do the live check on a real pull request. It also checks ticket 46 on GitHub. |
| 36 | [42 — Benchmark statistics: label agreement, run metadata, and pass@k](42-benchmark-statistics.md) | ready-for-agent | 37 (done) | Do it before ticket 10. |
| 37 | [10 — Benchmark on SWE-bench with injected slop](10-benchmark.md) | ready-for-agent | 37, 41 | Stage 2: the full gate. The results go into the submission. Ticket 11 needs it. |
| 38 | [08 — Live duplicate flag at plan time](08-live-flag-plan-time.md) | ready-for-agent | 07 (done) | Moved after the gate work on 2026-10-11. Ticket 11 needs it, or the submission leaves it out. |
| 39 | [09 — Jev classifier backend and comparison](09-jev-backend-and-comparison.md) | ready-for-agent | 07 (done) | Lowest priority. Skip it if time runs short. |
| 40 | [11 — Hackathon submission package](11-submission-package.md) | ready-for-agent | 06, 08, 10 | Last. It describes the finished project. Before the repo is public, set the Slopgate workflow back to `ubuntu-latest` (ticket 27). |

Added after the order was set:

| Ticket | Status | Note |
|---|---|---|
| [26 — Review a pull request on the local machine](26-review-a-pr-locally.md) | done | Adds `slopgate review --pr <number>`. |
| [38 — A comment at column 0 inside a method crashes `classify`](38-column-zero-comment-crash.md) | done | Found by ticket 37. Also fixes two more `index.build` crashes: a backslash continuation into a comment, and a file that is not UTF-8. |
| [39 — Design: better detection for `redundant_check` and `nesting`; remove `filler_comment`](39-detection-precision.md) | done | Found by ticket 37. On the held-out set, the false-kind rate on clean function runs fell from 0.117 to 0.013. |
| [41 — Characterization tests by an agent in a ConTree sandbox](41-characterization-agent-in-contree.md) | done | A plain tool loop (design D) proved 24 of 36 functions; the old flow proved 7. `characterize` uses it now. Tickets 29, 30, 31, and 35 are wontfix. |
| [58 — A repo that takes its version from the git history does not install in the sandbox](58-setuptools-scm-needs-version.md) | ready-for-agent | Found by ticket 53 on `pytest-dev/pytest` (1 of 5 SWE-bench repos). Do it after ticket 55. |
| [59 — A commit from before 2020 needs an older Python than 3.10](59-commits-before-2020-need-old-python.md) | ready-for-agent | Found by ticket 53 on `pydata/xarray` 2019 (1 of 5 SWE-bench repos). Do it before ticket 10 if the benchmark uses commits from 2019 or earlier. |
| [46 — Find the changed functions from the merge-base, not from the base tip](46-diff-from-merge-base.md) | done | Found by the code review of ticket 34. An inline comment on a line outside the pull request diff makes GitHub reject the whole review. Do it before the Slopgate workflow is on again. |

Tickets 01 to 07, 12 to 22, 25, 26, 28, 32, 33, 34, 36, 37, 38, 39, 41, 46, 49, 53, and 54 are done. Tickets 23, 24, 29, 30, 31, and 35 are wontfix.

## Rules for the order

1. Tickets 17 to 22 and 29 to 31 change the gate's model replies and its proof. They come first, because a wrong suggestion on a demo pull request costs more than a slow one. Ticket 32 comes before 29 to 31, because the user set it next: its traces show the real prompts that those tickets change. Ticket 36 comes next, because the gate posts wrong slop kinds now. Ticket 19 waits for the design of 36, because 19 changes `classify`.
2. Tickets 17, 19, 20, 21, 22, 29, 30, and 31 all edit `slopgate/review.py`. Do them one at a time, in the order above, to prevent merge conflicts.
3. Ticket 24 edits only `action.yml`, the workflow, and `README.md`. It can run in parallel with any other ticket.
4. If a ticket is blocked, take the next open row whose blockers are all done.
5. Ticket 41 comes before tickets 30, 35, 29, and 31. Its comparison decides whether an agent in the sandbox replaces their fixes.
6. Before the submission (ticket 11), make the `slopgate` and `slopgate-demo` repos public. They stay private until then.

## How to do a ticket

1. Read the ticket file in full. Read `CLAUDE.md` at the repo root.
2. Create a branch from `main`, for example `ticket-22-nested-params`.
3. Set `Status: in-progress` in the ticket.
4. Do the work. Check every acceptance box only after you verify it.
5. Run `uv run pytest -q`. Run the live tests that the ticket names with `uv run --env-file .env pytest -m live -q`.
6. Add a `## Comments` entry with the date, what was built, a worked example, and the measured results.
7. Set `Status: done`. Update the table above and "Next ticket".
8. Run a code review with the `pstack:thermo-nuclear-code-quality-review` skill (an Opus subagent). Apply the findings, or reject each one with a reason.
9. Ask the user before you commit or push. Start each commit message with the ticket number: `ticket-<NN>: type(scope): message`. Then open a pull request to `main`.
