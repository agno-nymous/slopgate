# 27 — Run the gate automatically on a self-hosted runner

## Summary

- **Goal:** Start the Slopgate gate again when a pull request opens, on a self-hosted GitHub runner on the user's Mac. Example: a new pull request starts the `slopgate` job, and the job posts its result.
- **Checkable finish condition:** A new pull request starts the `slopgate` job on the Mac runner, the job posts its result, and the job takes less than 10 min.
- **Evidence:** Before: the gate took 33 min 57 s on a GitHub runner for PR #9 and ran only by hand after ticket 26. On the Mac, `--pr 11 --dry-run` took 2 min 51 s and 3 min 10 s. Two boxes are done: the workflow uses `runs-on: self-hosted` and not `actions/setup-python`. The live check is still open.
- **Constraints:** The job does not use `uses: ./`, because `actions/setup-python` fails on a self-hosted Mac. `ci.yml` stays on `ubuntu-latest`. Before the repo is public (2026-10-30), set `runs-on: ubuntu-latest` again and remove the runner.

**Blocked by:** 26 (done)

**Status:** wontfix

## Context

Ticket 26 removed `.github/workflows/slopgate.yml` and added `slopgate review --pr <number>`. After that, the gate ran only when someone typed the command. The user expected the gate to start when a pull request opens.

Run times of the gate:

| Where | Pull request | Time |
|---|---|---|
| GitHub runner (`ubuntu-latest`) | #9 | 33 min 57 s |
| GitHub runner (`ubuntu-latest`) | #11 | more than 30 min, cancelled |
| Mac, `--pr 11 --dry-run` | #11 | 2 min 51 s and 3 min 10 s |
| Mac, `--pr 12 --dry-run` | #12 | 8 min 59 s |

A self-hosted runner gives both: the workflow starts when a pull request opens, and the job runs on the Mac.

## Design

1. Restore `.github/workflows/slopgate.yml` with `runs-on: self-hosted`. The job checks out the repo and runs `uv run slopgate review --base "$BASE" --head "$HEAD"` with the Mac's `uv`.
2. The job does not use `uses: ./`. The action runs `actions/setup-python`, and on a self-hosted Mac that step fails with `mkdir: /Users/runner: Permission denied` (seen on PR #14, also with `AGENT_TOOLSDIRECTORY` set in the runner's `.env`). `uv` uses its own cache, and `~/.cache/huggingface` stays between runs, so the job needs no install step and no cache step. `action.yml` does not change.
3. `ci.yml` (pytest) stays on `ubuntu-latest`.
4. `CLAUDE.md` and the `/start-dev` skill say that the gate runs on the runner, and that `--pr` is the manual fallback when the runner is offline.
5. Before the repo is public (2026-10-30), set `runs-on: ubuntu-latest` again and remove the runner. On a public repo, a pull request from a fork could run its code on the Mac.

## Runner setup (the user does this once)

1. On GitHub, open the repo, then **Settings → Actions → Runners → New self-hosted runner**. Select **macOS** and **ARM64**.
2. In a terminal, run the download and `./config.sh --url https://github.com/agno-nymous/slopgate --token <token>` commands that the page shows. Use a folder such as `~/actions-runner`. Accept the default name and labels.
3. Run `./svc.sh install` and then `./svc.sh start` in that folder. The runner then starts at login.
4. After that, use the repo `Makefile`: `make runner-start`, `make runner-stop`, `make runner-status`, and `make runner-logs`.

## Acceptance

- [x] `.github/workflows/slopgate.yml` uses `runs-on: self-hosted`.
- [x] The job runs the gate with `uv` and does not use `actions/setup-python`.
- [ ] A new pull request starts the `slopgate` job on the Mac runner, and the job posts its result to the pull request.
- [ ] The job takes less than 10 min.
- [x] `CLAUDE.md` says to switch back to `ubuntu-latest` before the repo is public.

## Comments

### 2026-10-25 — wontfix

The `slopgate` repo became public on 2026-10-25. A pull request from a fork can add a workflow that runs on a self-hosted runner. So the user removed the Mac runner, and the Slopgate workflow runs on `ubuntu-latest` now. Step 8 of the public flip in `ROADMAP.md` replaces the live check of this ticket.
