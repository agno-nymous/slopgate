---
name: start-dev
description: Pick up the next Slopgate ticket from issues/ROADMAP.md and work it end to end - branch, poteto-mode implementation, verification, ticket Comments, roadmap update, and a PR that merges only after the user approves and the checks pass. Use when the user types /start-dev, optionally with a ticket number.
argument-hint: "[ticket number]"
disable-model-invocation: true
---

# Start dev: work the next Slopgate ticket

Continue Slopgate (Nebius x NVIDIA hackathon). The deadline is **2026-10-30, 10:00 PT**.

Argument: `$ARGUMENTS`. If it holds a ticket number, work that ticket. If it is empty, work the "Next ticket" in `issues/ROADMAP.md`.

## 1. Read before you plan

1. Run `git pull --ff-only` in the main checkout before you read any file. Do it before `EnterWorktree`: after it, the session refuses git commands on the main checkout. Another session may have merged a ticket since the last pull. A stale checkout shows an old ROADMAP.md: on 2026-10-10 it still named ticket 41 as next after PR #27 had merged it. If the pull fails (local changes, or the main checkout is not on `main`), tell the user, run `git fetch origin`, and read each file with `git show origin/main:<path>`. Do not switch the branch of the main checkout: other sessions may work there. The ticket starts from `origin/main`.
2. Read `CLAUDE.md` in full. It holds the commands, the code map, the secrets rule, and the model rules.
3. Read `issues/ROADMAP.md`. Find the ticket to work. Do not take tickets by number order.
4. Read the whole ticket file. Each ticket has its context, design, prompt texts, and acceptance boxes.
5. Check the `Blocked by:` line. Every listed ticket must have `Status: done`. If one does not, tell the user, and propose the next open ticket in the ROADMAP.md table whose blockers are all done. Then stop and wait for the user.
6. Make sure that the self-hosted CI runner runs on this Mac. The `slopgate` check of every pull request runs on it (ticket 27).
   - Run `make runner-status`. It must show `Started:` with a process number.
   - Run `gh api repos/agno-nymous/slopgate/actions/runners -q '.runners[] | .name + " " + .status'`. The runner must be `online`.
   - If the runner is stopped or offline, run `make runner-start` and check again. If it is still offline, tell the user. Show the user the output of `make runner-logs`, and continue the ticket. The `slopgate` check waits in the queue until the runner is online.
7. Start Phoenix for every ticket. The gate and the live tests send their traces to it.
   - Run `curl -s -m 3 -o /dev/null -w "%{http_code}" http://127.0.0.1:6006/`. The answer `200` means that Phoenix runs.
   - If it does not run, start it with a background Bash call: `PHOENIX_HOST=127.0.0.1 uvx arize-phoenix serve`. Poll the `curl` command until it answers `200`.
   - The main checkout `.env` has no `PHOENIX_COLLECTOR_ENDPOINT` line, so a live command does not trace by default. Put `PHOENIX_COLLECTOR_ENDPOINT=http://127.0.0.1:6006` before each live command in steps 3 to 6 (`PHOENIX_COLLECTOR_ENDPOINT=http://127.0.0.1:6006 uv run --env-file <main checkout>/.env ...`). Never set it in a shell profile.

## 2. Start the ticket

1. Call the `EnterWorktree` tool with `name: ticket-<NN>-<short-slug>`, for example `ticket-22-nested-params`. It creates a worktree from `origin/main` under `.claude/worktrees/` and moves the session into it. Then run `git branch -m ticket-<NN>-<short-slug>`, so the branch has the ticket name. Run `uv sync` in the worktree.
   The worktree has no `.env` file. Run live commands with `uv run --env-file "$(git worktree list | head -1 | cut -d' ' -f1)/.env" ...`.
2. Set `**Status:** in-progress` in the ticket file.
3. Give the user a short plan: the steps, the files that change, and the tests that prove each acceptance box. Then start. Do not wait, unless the ticket leaves a design decision open. In that case, ask about that decision only.

## 3. Implement in poteto mode

1. Invoke the `pstack:poteto-mode` skill and follow it.
2. Research and design before code, when the ticket needs it:
   - The ticket leaves a design decision open, or the change crosses a function boundary: use the `pstack:architect` skill. If the design is contested, use the `pstack:interrogate` skill before you implement.
   - You must learn how a part of this repo works first: use the `pstack:how` skill.
   - The ticket needs facts from outside the repo (a library, a model, an API, a benchmark): use the `anthropic-skills:deep-research` skill, or a `library-explorer` subagent for one library.
   - Measure a fact when you can (a prototype, a timing, a live call). Do not ask the user for it.
3. Implementation goes to `pstack:poteto-agent` subagents. The main session designs, reviews the diff, and verifies on the real artifact.
4. Dispatch subagents without `isolation: "worktree"`. That option is broken in this setup: the subagent's shell refuses every command with "The working-directory isolation context for this agent was lost". A subagent without `isolation` works in the session's worktree from step 2.
5. Choose each subagent's model by its role and by the complexity of its task. Always pass `model` explicitly. Never use Fable.

   | Role | Model | `model` value | Use it for |
   |---|---|---|---|
   | Design and review | Opus 5.5 | `"opus"` | Design and architecture (`pstack:architect`, `pstack:how`, `pstack:interrogate`, arena panels). Root-cause research for a bug whose cause is not known. Every code review, including the review in step 4.6. Opus never writes the implementation. |
   | Implementer, complex | Sonnet 5.5 | `"sonnet"` | All code that is not mechanical: a change in any number of files, a change to a signature that other files call, model prompts and reply parsing in `slopgate/review.py`, new tests, fixes for failing tests. |
   | Implementer, mechanical | Haiku 5.5 | `"haiku"` | Mechanical work: rename, move code, edit ticket or doc text, run commands and summarize their output or logs. |

   Only Sonnet 5.5 and Haiku 5.5 write code. For a complex task, let an Opus subagent write the design first (types, signatures, the steps, the tests). Then give that design to a Sonnet implementer. If you are not sure between Haiku and Sonnet, choose Sonnet. If a Haiku subagent fails or returns wrong work, give the task to Sonnet. If a Sonnet subagent fails, ask an Opus subagent to find the cause and to make the design more specific, then give the task to Sonnet again. `~/.claude/pstack-models.md` sets the same split: implementer roles run on sonnet, and design, review, and panel roles run on opus.
6. Follow the ticket's design. If the code shows that the design is wrong, stop and tell the user with evidence. Do not change the design silently.
7. Do not add features, abstractions, or error handling that the ticket does not ask for.
8. Read every line of each subagent's diff. Compare each command line in docs with the original: subagents drop flags such as `--env-file .env` and still report success. Run `uv run pytest -q` yourself after the last subagent edit.
9. When a fix depends on a model reply, send the real prompt to the live model in a scratchpad script, and compare the fix variants with about 8 tries each. Choose by the counts. A prompt rule against a bad reply can make it more frequent.

## 4. Verify

1. Run `uv run pytest -q`. All tests must pass.
2. Run the live tests that the ticket names: `PHOENIX_COLLECTOR_ENDPOINT=http://127.0.0.1:6006 uv run --extra hook --env-file <main checkout>/.env pytest -m live -q` (or the single test path).
3. For a gate change, run one local dry run: `PHOENIX_COLLECTOR_ENDPOINT=http://127.0.0.1:6006 uv run --env-file <main checkout>/.env slopgate review --repo <repo> --base <ref> --head <ref> --dry-run`. Do not use `--sandbox local` on this repo: `.slopgate.toml` installs with `apt-get`, which exists only in the Contree Linux image.
   If the ticket changes the dependencies in `pyproject.toml`, also check the `setup` line of `.slopgate.toml` and the install step of `action.yml`. Both install with pip, and pip does not install uv dependency groups.
4. Read the Phoenix traces of every live run in steps 2 and 3. Do this each time, also when the run passes. Invoke the `phoenix-cli` skill, and use `PHOENIX_ENDPOINT=http://127.0.0.1:6006` with `--project slopgate-gate` (gate runs) or `--project slopgate-tests` (live tests).
   - List the traces of the run: `px trace list --project <project> --last-n-minutes 60 --format raw --no-progress`. Each `gate.review` trace is one run. Open each one with `px trace get <trace-id>`.
   - Look for: a trace with status `ERROR`, a `sandbox.prepare` span that failed or took more than 60 s, a `characterize` span that stopped at the step or token limit, a `sandbox.run` span that exited non-zero, and a model call that returned `finish_reason: "length"`.
   - Say what you found, with the trace id, in the Comments entry of step 5 and in the final report. A failure that has a cause in the trace is a finding, not noise. If it is outside the ticket, write it as a new ticket.
5. Check each acceptance box only after you see it pass. If a box cannot pass (for example, it needs an external service that is not available), leave it open, and use `Status: needs-live-check` instead of `done`.
6. Measure the numbers that the ticket asks for (time, counts, rates). Do not estimate them.
7. Run a code review when the feature is done and the tests pass. Dispatch a read-only `pstack:poteto-agent` subagent with `model: "opus"`. Tell it to invoke the `pstack:thermo-nuclear-code-quality-review` skill on the diff against `origin/main` plus the untracked files, and to check the diff against the ticket's design and acceptance boxes. Apply each finding, or reject it with a reason. Then run `uv run pytest -q` again. Give the findings and what you did with each to the user.

## 5. Finish the ticket text

1. Add a `## Comments` entry with today's date. It holds:
   - what was built, in plain words;
   - a worked example: a real input, and the real output that the code gave;
   - the measured results;
   - known limits.
2. Set `**Status:** done` (or `needs-live-check`).
3. In `issues/ROADMAP.md`: set the ticket's status in the table, and move "Next ticket" to the next open row whose blockers are all done.
4. If the ticket changes a rule in `CLAUDE.md` (a command, a model rule, the code map), update `CLAUDE.md`.

## 6. Commit, PR, and merge

1. **Ask the user before you commit and before you push.** Show the list of changed files and the commit message first.
2. Start each commit message with the ticket number, then the conventional commit format: `ticket-<NN>: type(scope): message`, for example `ticket-18: feat(llm): add decide for pydantic tool-call decisions`. Keep each commit to one logical change.
3. Before the push, run the gate on the ticket's own commits: `uv run --env-file <main checkout>/.env slopgate review --repo . --base origin/main --head HEAD --dry-run`. A dry run on an older range reads the old `.slopgate.toml` and code, so it misses breakage that the PR causes. Read every rejection. An import error or "no tests ran" points to the PR or to a gate defect, not to the generated tests. Fix it before the push.
4. Open a PR to `main` with `gh pr create`. The PR text says what changed, why, and the measured results.
5. Read the `slopgate` check and the review that it posts. The check runs on the self-hosted runner on the user's Mac (ticket 27). If it stays queued because the runner is offline, run the gate by hand: `uv run --env-file <main checkout>/.env slopgate review --pr <number>`. If the step shows `cancelled` after about 10 min, the Mac probably slept: the runner log in `~/actions-runner/_diag/` shows `renewjob failed`, and `pmset -g log` shows `Idle Sleep`. That is not a code failure. Keep the Mac awake and on power, and run the job again.
6. Bind the PR with the app's PR tools, and read its checks there. Do not use auto-merge: the repo has no branch protection, so auto-merge would merge before the checks finish.
7. When all checks pass, report the result to the user. Merge only when the user says to merge. Then call `ExitWorktree` with `action: "remove"`.
8. In the final report, give a worked example and a plain explanation of what changed.

## Rules for every step

- Write tickets, Comments, PR text, and replies in ASD-STE100 Simplified Technical English: one idea per sentence, short sentences, active voice, one term for one concept.
- Never print, paste, or commit an API key. Run live commands with `--env-file` pointed at the main checkout's `.env` (step 2).
- Never run a destructive git command (`reset --hard`, `branch -D`, `push --force`) without the user's approval.
- Work only in the ticket's worktree (step 2). Never switch the branch of the main checkout. Other sessions may use it.
- Before the submission (ticket 11), remind the user to make the `slopgate` and `slopgate-demo` repos public.

## Decisions that are final

These were measured from 2026-10-04 to 2026-10-06. Do not reopen them without new data. `CLAUDE.md` ("Model rules") and tickets 18 to 21 hold the evidence.

- Code replies (rewrites) come back as one ```` ```python ```` block in markdown. Never put code in JSON or in tool-call arguments. The one exception is the characterization test agent (ticket 41): it writes the test file with `execute` and a heredoc in a sandbox session.
- Decisions (slop kinds, the duplicate verdict) come back as a forced tool call with a pydantic model, with the reason field before the verdict.
- Every model request sends `chat_template_kwargs: {"enable_thinking": False}`.
- No DSPy, no Pydantic AI, no instructor.
- Test files get review notes only (ticket 17).
