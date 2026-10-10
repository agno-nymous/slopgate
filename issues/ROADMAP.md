# Ticket order

This file gives the order in which to do the open tickets. The deadline is **2026-10-30, 10:00 PT** (Nebius x NVIDIA hackathon).

## Next ticket

**39 — Design: better detection for `redundant_check` and `nesting`; remove `filler_comment`.** Ticket 37 measured 21.7% of clean function runs with a false kind.

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
| 10 | [30 — Give the test writer the constants the target reads](30-constants-in-callee-context.md) | ready-for-agent | — | Super guessed `DUPLICATE_SCORE` on PR #17. No extra model call. |
| 11 | [35 — Tell the test writer that the tests run without network and keys](35-tests-run-without-network.md) | ready-for-agent | 30 | `characterize` on PR #20: the tests called the real model client and patched a parameter by name. Needs a live measurement. |
| 12 | [29 — Keep the passing characterization tests](29-keep-passing-characterization-tests.md) | ready-for-agent | 20 | One failing test rejects the whole file now. No extra model call. |
| 13 | [31 — Retry once for missed branches, with 3 attempts in total](31-retry-missed-branches.md) | ready-for-agent | 29 | Missed branches reject at once now. Costs one Super call. |
| 14 | [33 — Add a time limit to each sandbox run](33-sandbox-time-limit.md) | ready-for-agent | — | A model-written call such as `input()` blocks the gate with no end. |
| 15 | [34 — Readable rejection reasons in the review comment](34-readable-rejection-reasons.md) | ready-for-agent | — | The raw pytest output on PR #20 looked like a crash of the gate. |
| 16 | [19 — Several slop kinds per function](19-several-slop-kinds-per-function.md) | done | 18, 21, 36 | Fixes all problems of a function in one suggestion. Built in ticket 36, stage 2. |
| 17 | [23 — Log the time of each gate step](23-log-time-per-gate-step.md) | ready-for-agent | — | Reduced on 2026-10-08 to the `Slowest:` line in the pull request comment. The Phoenix spans of ticket 32 give the time of each step. |
| 18 | [24 — Save the embedding model cache on main](24-model-cache-on-main.md) | wontfix | — | Ticket 28 removes the embedding model from the gate. |
| 19 | [25 — Faster proof](25-faster-proof.md) | ready-for-agent | 32 | Needs the step times from one traced review first. |
| 20 | [08 — Live duplicate flag at plan time](08-live-flag-plan-time.md) | ready-for-agent | 07 (done) | The second half of the live flag in the spec. Ticket 11 needs it. |
| 21 | [10 — Benchmark on SWE-bench with injected slop](10-benchmark.md) | ready-for-agent | 37, 30, 35 | Stage 2: the full gate. The results go into the submission. Ticket 11 needs it. |
| 22 | [09 — Jev classifier backend and comparison](09-jev-backend-and-comparison.md) | ready-for-agent | 07 (done) | Lowest priority. Skip it if time runs short. |
| 23 | [11 — Hackathon submission package](11-submission-package.md) | ready-for-agent | 06, 08, 10 | Last. It describes the finished project. Before the repo is public, set the Slopgate workflow back to `ubuntu-latest` (ticket 27). |

Added after the order was set:

| Ticket | Status | Note |
|---|---|---|
| [26 — Review a pull request on the local machine](26-review-a-pr-locally.md) | done | Adds `slopgate review --pr <number>`. |
| [27 — Run the gate automatically on a self-hosted runner](27-gate-on-self-hosted-runner.md) | needs-live-check | The workflow runs on the user's Mac. It needs the runner to be registered. |
| [38 — A comment at column 0 inside a method crashes `classify`](38-column-zero-comment-crash.md) | ready-for-agent | Found by ticket 37. 34 functions in the 12 SWE-bench Lite repos. Do it before ticket 10. |
| [39 — Design: better detection for `redundant_check` and `nesting`; remove `filler_comment`](39-detection-precision.md) | ready-for-agent | Found by ticket 37. Next ticket: the gate gives a false kind on 21.7% of clean function runs. |
| [40 — Limit the output tokens of `decide`](40-limit-decide-output.md) | ready-for-agent | Found by ticket 37. 5 of 1,407 `classify` runs took 60 s to 110 s. |
| [42 — Benchmark statistics: label agreement, run metadata, and pass@k](42-benchmark-statistics.md) | ready-for-agent | The user set it on 2026-10-10. Do it before ticket 10. Ticket 39 does the other 3 checks of the evals guide (held-out set, ranges, errors apart). |
| [41 — Characterization tests by an agent in a ConTree sandbox](41-characterization-agent-in-contree.md) | ready-for-agent | The user set it on 2026-10-09. Do it after 39 and before 30, 35, 29, and 31: its result can make those tickets unnecessary. |

Tickets 01 to 07, 12 to 22, 26, 28, 32, and 36 are done. Ticket 24 is wontfix.

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
