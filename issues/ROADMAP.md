# Ticket order

This file gives the order in which to do the open tickets. The deadline is **2026-10-30, 10:00 PT** (Nebius x NVIDIA hackathon).

## Next ticket

**17 — Test files get review notes only.**

When a ticket is done, mark it done in the table below and move "Next ticket" to the next open row.

## Order

| Order | Ticket | Status | Blocked by | Why it is in this position |
|---|---|---|---|---|
| 1 | [22 — Dead-code check ignores nested parameters](22-dead-code-ignores-nested-parameters.md) | done | — | Smallest fix. It removes the two false "dead" hits from PR #9. |
| 2 | [21 — Code replies: one Python block, thinking off, reject "no change"](21-rewrite-reply-as-python-block.md) | done | — | Stops cut-off replies and empty suggestions. Ticket 20 uses its `strip_fence` and thinking changes. |
| 3 | [28 — Keyword duplicate search in the gate](28-keyword-duplicate-search.md) | needs-live-check | — | The user set it next. The gate then needs no embedding model: the torch fallback took 14 GB on the 16 GB Mac. |
| 4 | [17 — Test files get review notes only](17-test-files-get-notes-only.md) | ready-for-agent | — | Stops the gate from changing tests. Fixes the `fake_llm` failure at its cause. |
| 5 | [20 — Tests reply as one pydantic object, sent as markdown](20-tests-reply-as-pydantic-object.md) | ready-for-agent | 21 | Stops prose from becoming a test file, for every function. |
| 6 | [18 — Model decisions through pydantic tool calls](18-decisions-through-pydantic-tool-calls.md) | done | — | Adds `decide`. Ticket 19 needs it. |
| 7 | [19 — Several slop kinds per function](19-several-slop-kinds-per-function.md) | ready-for-agent | 18, 21 | Fixes all problems of a function in one suggestion. |
| 8 | [23 — Log the time of each gate step](23-log-time-per-gate-step.md) | ready-for-agent | — | The review of PR #9 took 33 min, and the cause is not measured. |
| 9 | [24 — Save the embedding model cache on main](24-model-cache-on-main.md) | wontfix | — | Ticket 28 removes the embedding model from the gate. |
| 10 | [25 — Faster proof](25-faster-proof.md) | ready-for-agent | 23 | Needs the numbers from ticket 23 first. |
| 11 | [08 — Live duplicate flag at plan time](08-live-flag-plan-time.md) | ready-for-agent | 07 (done) | The second half of the live flag in the spec. Ticket 11 needs it. |
| 12 | [10 — Benchmark on SWE-bench with injected slop](10-benchmark.md) | ready-for-agent | 02, 03, 04 (done) | The results go into the submission. Ticket 11 needs it. |
| 13 | [09 — Jev classifier backend and comparison](09-jev-backend-and-comparison.md) | ready-for-agent | 07 (done) | Lowest priority. Skip it if time runs short. |
| 14 | [11 — Hackathon submission package](11-submission-package.md) | ready-for-agent | 06, 08, 10 | Last. It describes the finished project. Before the repo is public, set the Slopgate workflow back to `ubuntu-latest` (ticket 27). |

Added after the order was set:

| Ticket | Status | Note |
|---|---|---|
| [26 — Review a pull request on the local machine](26-review-a-pr-locally.md) | done | Adds `slopgate review --pr <number>`. |
| [27 — Run the gate automatically on a self-hosted runner](27-gate-on-self-hosted-runner.md) | needs-live-check | The workflow runs on the user's Mac. It needs the runner to be registered. |

Tickets 01 to 07, 12 to 16, 18, 21, 22, and 26 are done. Ticket 28 needs a live check of the workflow. Ticket 24 is wontfix.

## Rules for the order

1. Tickets 17 to 22 change the gate's model replies and its proof. They come first, because a wrong suggestion on a demo pull request costs more than a slow one.
2. Tickets 17, 19, 20, 21, and 22 all edit `slopgate/review.py`. Do them one at a time, in the order above, to prevent merge conflicts.
3. Ticket 24 edits only `action.yml`, the workflow, and `README.md`. It can run in parallel with any other ticket.
4. If a ticket is blocked, take the next open row whose blockers are all done.
5. Before the submission (ticket 11), make the `slopgate` and `slopgate-demo` repos public. They stay private until then.

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
