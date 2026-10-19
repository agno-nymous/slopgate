# Ticket order

This file gives the order in which to do the open tickets. The deadline is **2026-10-30, 10:00 PT** (Nebius x NVIDIA hackathon).

## Next ticket

**58 — A repo that takes its version from the git history does not install in the sandbox.** Then 59, then 67. Ticket 10 is `needs-live-check` (the Serverless Job and the instance count are open). Its run with the gate's own install (2026-10-18) gives a working environment on 6 of 15 instances: 5 fail with setuptools-scm (58), and 4 need a Python older than 3.10 (59). Ticket 67 adds an agent that installs from the repo's own instructions, and the ticket 10 benchmark measures it.

## Plan to the deadline (set on 2026-10-17)

The goal is an overall prize. The judges score 4 criteria (1 to 5, equal weight): Technological Implementation, Design, Potential Impact, and Quality of the Idea. The submission needs a working demo URL.

| Days | Dates | Work |
|---|---|---|
| 1 to 3 | 2026-10-17 to 10-20 | The benchmark headline: tickets 60, 42, 48, then 10 with 10 to 15 instances. |
| 3 | 2026-10-20 | **Decision point.** Read the acceptance rate and the silent-break rate of ticket 10. If the gate proves few rewrites, the headline becomes the precision of the gate and the write-time hook: do ticket 65 before ticket 64. |
| 4 to 6 | 2026-10-21 to 10-23 | Ticket 64: the hosted demo on a Nebius Serverless Endpoint. |
| 7 to 9 | 2026-10-24 to 10-26 | Ticket 65: the hook on and off with a Nemotron coding agent, only if tickets 10 and 64 are done. |
| 10 to 12 | 2026-10-27 to 10-29 | Ticket 11: README, video, feedback, public repos. Submit on 2026-10-29. |

Fix a slop kind (tickets 45, 50, 43) only if the numbers of ticket 10 show that the fix changes the headline. Otherwise turn that kind off in the gate.

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
| 23 | [44 — The import line is wrong for a repo with a `src/` layout](44-src-layout-import-line.md) | done | — | All 6 pytest functions failed in every design of ticket 41. Ticket 49: 5 of 7 external candidates. A small change. |
| 24 | [55 — The test agent passes only with changes that the judge does not keep](55-agent-run-differs-from-judge-run.md) | done | — | Found by ticket 49: 4 of 7 external candidates. The agent moved `conftest.py` or set an environment variable, and the judge did not. Do it together with ticket 52: both change how the agent is prompted or how its session behaves, so one live comparison on the same functions answers both. Test a rule that says "run the test file after each rewrite" too (the pylint trace of ticket 53 never ran its last rewrite). |
| 25 | [52 — The test agent uses its steps to read code](52-agent-reads-code-step-by-step.md) | done | — | Found by ticket 49: 77 of 201 agent commands only read code. External: 1 of 7. Do it together with ticket 55 (one live comparison). The traces of ticket 53 show 2 of 4 agent runs ended at the step limit after 3 to 8 steps of reading or experiments. |
| 26 | [51 — The proof accepts a rewrite that changes a comparison](51-proof-misses-changed-comparison.md) | done | — | Moved up on 2026-10-12. A wrong suggestion that passes the proof costs more than a slow gate. Ticket 10 needs it first: the benchmark must not count wrong rewrites. An Opus review (see the ticket Comments) says: measure the false accepts of the current proof first (no model call), then build the comparison rule. |
| 27 | [60 — A sandbox error other than an install error gives an empty review and exit code 0](60-silent-exit-on-sandbox-error.md) | done | — | Moved up on 2026-10-17 to come before ticket 10: a sandbox error that looks like "no slop found" lowers the detection recall. |
| 28 | [42 — Benchmark statistics: label agreement, run metadata, and pass@k](42-benchmark-statistics.md) | done | 37 (done) | Moved up on 2026-10-17. Ticket 10 uses its metadata and pass@k functions. |
| 29 | [48 — Compare the repo suite with a baseline run of the original code](48-repo-suite-baseline.md) | done | — | Moved up on 2026-10-17. A repo test that fails on the original code lowers the acceptance rate of ticket 10. |
| 30 | [58 — A repo that takes its version from the git history does not install in the sandbox](58-setuptools-scm-needs-version.md) | ready-for-agent | — | Ticket 10 needs it: all 5 pytest instances fail the install with the gate's own install (2026-10-18). |
| 31 | [59 — A commit from before 2020 needs an older Python than 3.10](59-commits-before-2020-need-old-python.md) | ready-for-agent | — | Ticket 10 needs it: sphinx-7975, sphinx-8506, sphinx-8627, and requests-3362 install on Python 3.10, but their tests cannot run (2026-10-18). Ticket 67 section 0 proposes the Python of the commit date. |
| 32 | [10 — Benchmark on SWE-bench with injected slop](10-benchmark.md) | needs-live-check | 37, 41 (done) | Moved up on 2026-10-17. Its four numbers are the headline of the submission, and they judge every later ticket. First step: confirm that ConTree can run the SWE-bench images (the SDK has `images.pull` and `images.oci`, but no list of preloaded images). |
| 33 | [67 — An agent installs the test environment from the repo's own instructions](67-install-agent.md) | ready-for-agent | 58, 59 | Added on 2026-10-18 by the user. With the gate's own install, ticket 10 has a working environment on 6 of 15 instances. The agent reads the README and CI files and installs the rest. |
| 34 | [64 — Hosted demo: review a public pull request from a web page](64-hosted-demo-on-serverless-endpoint.md) | ready-for-agent | 10 | Added on 2026-10-17. The submission needs a working demo URL, and Design is 1 of 4 criteria. |
| 35 | [65 — Measure the write-time hook on a Nemotron coding agent](65-hook-on-off-experiment.md) | ready-for-agent | 10 | Added on 2026-10-17. After ticket 64, if time is left by 2026-10-26. Moves before 64 if the decision point says so. |
| 36 | [45 — The test agent cannot characterize large functions](45-characterize-large-functions.md) | ready-for-agent | 41 (done) | After ticket 10. The numbers of each kind decide: fix the kind, or turn it off in the gate. |
| 37 | [50 — The gate cannot fix `swallowed_error` around a call to other code](50-swallowed-error-external-call.md) | ready-for-agent | — | After ticket 10, for the same reason as ticket 45. |
| 38 | [43 — The gate cannot prove a `redundant_check` rewrite](43-dead-branch-of-redundant-check.md) | ready-for-agent | 39 (done) | After ticket 10, for the same reason as ticket 45. |
| 39 | [56 — The test-file rule misses `tests.py`, and django tests do not run under pytest](56-django-test-layout.md) | ready-for-agent | — | Found by ticket 49 on django#21736: a django test method got an agent run instead of a note. |
| 40 | [27 — Run the gate automatically on a self-hosted runner](27-gate-on-self-hosted-runner.md) | needs-live-check | 26 (done) | Turn the Slopgate workflow on again only when the user says so. Then do the live check on a real pull request. It also checks ticket 46 on GitHub. |
| 41 | [08 — Live duplicate flag at plan time](08-live-flag-plan-time.md) | ready-for-agent | 07 (done) | Ticket 11 needs it for the live-flag scene of the video. If time runs short, the user decides whether to cut it. |
| 42 | [11 — Hackathon submission package](11-submission-package.md) | ready-for-agent | 06, 08, 10 | Last. It describes the finished project. Before the repo is public, set the Slopgate workflow back to `ubuntu-latest` (ticket 27). |
| 43 | [57 — Building the function index takes more than 80 s on a large repository](57-faster-function-index.md) | ready-for-agent | — | Moved to the end on 2026-10-17. Speed only. |
| 44 | [40 — Limit the output tokens of `decide`](40-limit-decide-output.md) | ready-for-agent | — | 5 of 1,407 runs took 60 s to 110 s. Speed only. |
| 45 | [47 — `parse` splits lines on a form feed, so later functions get the wrong source](47-parse-splits-on-form-feed.md) | ready-for-agent | — | Not seen in the 12 SWE-bench Lite repos. |
| 46 | [09 — Jev classifier backend and comparison](09-jev-backend-and-comparison.md) | ready-for-agent | 07 (done) | Lowest priority. Skip it if time runs short. |

Added after the order was set:

| Ticket | Status | Note |
|---|---|---|
| [26 — Review a pull request on the local machine](26-review-a-pr-locally.md) | done | Adds `slopgate review --pr <number>`. |
| [38 — A comment at column 0 inside a method crashes `classify`](38-column-zero-comment-crash.md) | done | Found by ticket 37. Also fixes two more `index.build` crashes: a backslash continuation into a comment, and a file that is not UTF-8. |
| [66 — Some injected items of the detection benchmark change behavior or are not the kind they name](66-injection-items-defects.md) | ready-for-agent | Found by the label review of ticket 42. Do it before the detection numbers go into the submission (ticket 11). |
| [39 — Design: better detection for `redundant_check` and `nesting`; remove `filler_comment`](39-detection-precision.md) | done | Found by ticket 37. On the held-out set, the false-kind rate on clean function runs fell from 0.117 to 0.013. |
| [41 — Characterization tests by an agent in a ConTree sandbox](41-characterization-agent-in-contree.md) | done | A plain tool loop (design D) proved 24 of 36 functions; the old flow proved 7. `characterize` uses it now. Tickets 29, 30, 31, and 35 are wontfix. |
| [61 — Each model call gets 8 nested spans when the first span opens in a thread pool](61-trace-setup-race.md) | ready-for-agent | Found by ticket 51: a script that opens its first span in a thread pool registers the tracer 8 times. The gate does not open its first span in a thread pool. |
| [62 — The test agent runs filler commands until the step limit after its test file passes](62-agent-cannot-stop.md) | ready-for-agent | Found by ticket 51: 41 of 48 hint rounds stopped at the step limit. Filler commands are 5% to 19% of the agent commands in the traces. |
| [46 — Find the changed functions from the merge-base, not from the base tip](46-diff-from-merge-base.md) | done | Found by the code review of ticket 34. An inline comment on a line outside the pull request diff makes GitHub reject the whole review. Do it before the Slopgate workflow is on again. |
| [63 — CrossHair as a second equivalence check](63-crosshair-equivalence-check.md) | wontfix | Measured on 2026-10-17. It finds the PR #23 change only with stub callees, not with the real callees. |

Tickets 01 to 07, 12 to 22, 25, 26, 28, 32, 33, 34, 36, 37, 38, 39, 41, 44, 46, 48, 49, 51, 52, 53, 54, 55, and 60 are done. Tickets 23, 24, 29, 30, 31, 35, and 63 are wontfix.

## Rules for the order

1. Tickets 17 to 22 and 29 to 31 change the gate's model replies and its proof. They come first, because a wrong suggestion on a demo pull request costs more than a slow one. Ticket 32 comes before 29 to 31, because the user set it next: its traces show the real prompts that those tickets change. Ticket 36 comes next, because the gate posts wrong slop kinds now. Ticket 19 waits for the design of 36, because 19 changes `classify`.
2. Tickets 17, 19, 20, 21, 22, 29, 30, and 31 all edit `slopgate/review.py`. Do them one at a time, in the order above, to prevent merge conflicts.
3. Ticket 24 edits only `action.yml`, the workflow, and `README.md`. It can run in parallel with any other ticket.
4. If a ticket is blocked, take the next open row whose blockers are all done.
5. Ticket 41 comes before tickets 30, 35, 29, and 31. Its comparison decides whether an agent in the sandbox replaces their fixes.
6. Ticket 10 comes before the tickets that fix one slop kind (45, 50, 43). Its numbers for each kind decide whether a kind gets a fix or is turned off. Speed-only tickets (57, 40) and ticket 47 come last.
7. Before the submission (ticket 11), make the `slopgate` and `slopgate-demo` repos public. They stay private until then.

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
