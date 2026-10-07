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

1. Read `CLAUDE.md` in full. It holds the commands, the code map, the secrets rule, and the model rules.
2. Read `issues/ROADMAP.md`. Find the ticket to work. Do not take tickets by number order.
3. Read the whole ticket file. Each ticket has its context, design, prompt texts, and acceptance boxes.
4. Check the `Blocked by:` line. Every listed ticket must have `Status: done`. If one does not, tell the user, and propose the next open ticket in the ROADMAP.md table whose blockers are all done. Then stop and wait for the user.
5. Run `git fetch origin`. The ticket starts from `origin/main`. Do not switch the branch of the main checkout: other sessions may work there.

## 2. Start the ticket

1. Call the `EnterWorktree` tool with `name: ticket-<NN>-<short-slug>`, for example `ticket-22-nested-params`. It creates a worktree from `origin/main` under `.claude/worktrees/` and moves the session into it. Then run `git branch -m ticket-<NN>-<short-slug>`, so the branch has the ticket name. Run `uv sync` in the worktree.
   The worktree has no `.env` file. Run live commands with `uv run --env-file "$(git worktree list | head -1 | cut -d' ' -f1)/.env" ...`.
2. Set `**Status:** in-progress` in the ticket file.
3. Give the user a short plan: the steps, the files that change, and the tests that prove each acceptance box. Then start. Do not wait, unless the ticket leaves a design decision open. In that case, ask about that decision only.

## 3. Implement in poteto mode

1. Invoke the `pstack:poteto-mode` skill and follow it.
2. Implementation goes to `pstack:poteto-agent` subagents. The main session designs, reviews the diff, and verifies on the real artifact.
3. Dispatch subagents without `isolation: "worktree"`. That option is broken in this setup: the subagent's shell refuses every command with "The working-directory isolation context for this agent was lost". A subagent without `isolation` works in the session's worktree from step 2.
4. Dispatch every subagent with `model: "opus"` (Opus 5.5, the most capable model). Never use Fable, also not for pstack roles that default to "strongest" or for arena, architect, and interrogate panels. `~/.claude/pstack-models.md` already maps every pstack role to opus.
5. Follow the ticket's design. If the code shows that the design is wrong, stop and tell the user with evidence. Do not change the design silently.
6. Do not add features, abstractions, or error handling that the ticket does not ask for.

## 4. Verify

1. Run `uv run pytest -q`. All tests must pass.
2. Run the live tests that the ticket names: `uv run --env-file <main checkout>/.env pytest -m live -q` (or the single test path).
3. For a gate change, run one local dry run: `uv run --env-file <main checkout>/.env slopgate review --repo <repo> --base <ref> --head <ref> --dry-run`. Do not use `--sandbox local` on this repo: `.slopgate.toml` installs with `apt-get`, which exists only in the Contree Linux image.
4. Check each acceptance box only after you see it pass. If a box cannot pass (for example, it needs an external service that is not available), leave it open, and use `Status: needs-live-check` instead of `done`.
5. Measure the numbers that the ticket asks for (time, counts, rates). Do not estimate them.

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
2. Use the conventional commit format: `type(scope): message`. Keep each commit to one logical change.
3. Open a PR to `main` with `gh pr create`. The PR text says what changed, why, and the measured results.
4. Read the `slopgate` check and the review that it posts. The check runs on the self-hosted runner on the user's Mac (ticket 27). If it stays queued because the runner is offline, run the gate by hand: `uv run --env-file <main checkout>/.env slopgate review --pr <number>`.
5. Bind the PR with the app's PR tools, and read its checks there. Do not use auto-merge: the repo has no branch protection, so auto-merge would merge before the checks finish.
6. When all checks pass, report the result to the user. Merge only when the user says to merge. Then call `ExitWorktree` with `action: "remove"`.
7. In the final report, give a worked example and a plain explanation of what changed.

## Rules for every step

- Write tickets, Comments, PR text, and replies in ASD-STE100 Simplified Technical English: one idea per sentence, short sentences, active voice, one term for one concept.
- Never print, paste, or commit an API key. Run live commands with `--env-file` pointed at the main checkout's `.env` (step 2).
- Never run a destructive git command (`reset --hard`, `branch -D`, `push --force`) without the user's approval.
- Work only in the ticket's worktree (step 2). Never switch the branch of the main checkout. Other sessions may use it.
- Before the submission (ticket 11), remind the user to make the `slopgate` and `slopgate-demo` repos public.

## Decisions that are final

These were measured from 2026-10-04 to 2026-10-06. Do not reopen them without new data. `CLAUDE.md` ("Model rules") and tickets 18 to 21 hold the evidence.

- Code replies (tests, rewrites) come back as one ```` ```python ```` block in markdown. Never put code in JSON or in tool-call arguments.
- Decisions (slop kinds, the duplicate verdict) come back as a forced tool call with a pydantic model, with the reason field before the verdict.
- Every model request sends `chat_template_kwargs: {"enable_thinking": False}`.
- No DSPy, no Pydantic AI, no instructor.
- Test files get review notes only (ticket 17).
