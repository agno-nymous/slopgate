# 27 — Run the gate automatically on a self-hosted runner

**What to build:** The Slopgate workflow starts again when a pull request opens on this repo. The job runs on a self-hosted GitHub runner on the user's Mac, not on a GitHub runner.

**Blocked by:** 26 (done)

**Status:** needs-live-check

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

1. Restore `.github/workflows/slopgate.yml` with `runs-on: self-hosted`. The steps do not change: checkout, then `uses: ./`.
2. In `action.yml`, run the `actions/cache` step only on GitHub runners (`runner.environment == 'github-hosted'`). On the Mac, `~/.cache/huggingface` stays between runs, so a cache restore only downloads 506 MB again.
3. `ci.yml` (pytest) stays on `ubuntu-latest`.
4. `CLAUDE.md` and the `/start-dev` skill say that the gate runs on the runner, and that `--pr` is the manual fallback when the runner is offline.
5. Before the repo is public (2026-10-30), set `runs-on: ubuntu-latest` again and remove the runner. On a public repo, a pull request from a fork could run its code on the Mac.

## Runner setup (the user does this once)

1. On GitHub, open the repo, then **Settings → Actions → Runners → New self-hosted runner**. Select **macOS** and **ARM64**.
2. In a terminal, run the download and `./config.sh --url https://github.com/agno-nymous/slopgate --token <token>` commands that the page shows. Use a folder such as `~/actions-runner`. Accept the default name and labels.
3. Run `./svc.sh install` and then `./svc.sh start` in that folder. The runner then starts at login.

## Acceptance

- [x] `.github/workflows/slopgate.yml` uses `runs-on: self-hosted`.
- [x] `action.yml` skips `actions/cache` on a self-hosted runner.
- [ ] A new pull request starts the `slopgate` job on the Mac runner, and the job posts its result to the pull request.
- [ ] The job takes less than 10 min.
- [x] `CLAUDE.md` says to switch back to `ubuntu-latest` before the repo is public.

## Comments
