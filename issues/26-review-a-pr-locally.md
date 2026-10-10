# 26 — Review a pull request on the local machine

## Summary

- **Goal:** Run the gate on the local machine for one pull request, and post the review to GitHub. Example: `slopgate review --pr 11`.
- **Checkable finish condition:** `slopgate review --pr 7` reviews the base and head commits of the pull request and posts to it (offline test with a fake `gh`). `slopgate review --pr 11 --dry-run` posts nothing. `.github/workflows/slopgate.yml` is deleted. `uv run pytest -q` passes.
- **Evidence:** Done. Before, the GitHub run took 33 min 57 s on PR #9 and more than 10 min on PR #11. After, `--pr 11 --dry-run` took 2 min 51 s, gave 0 suggestions, and posted nothing (PR #11 had 0 comments). The offline suite gave 110 passed. The run also found and fixed a crash: `embed.load` used the ONNX model when `onnxruntime` was not installed.
- **Constraints:** Without `--pr`, the behavior does not change. The parser stops with an error when it gets no `--pr` and not both `--base` and `--head`. With `--pr`, the gate fetches the base and head commits itself and does not read `GITHUB_EVENT_PATH`. Keep `action.yml`, the workflow example in `README.md`, and `.github/workflows/ci.yml`. Document the command in `README.md` and `CLAUDE.md`.

**Blocked by:** None — can start immediately.

**Status:** done

## Context

The Slopgate workflow is slow on GitHub runners. The review of PR #9 took 33 min 57 s. The review of PR #11 took more than 10 min. The CI workflow (`ci.yml`) takes about 3 min. The slow workflow delays each merge on this repo.

The gate reads only git objects (`git show <sha>:<path>` and `git archive <sha>`). It does not need a checkout. It needs only the base and head commits. `git fetch origin <base sha> pull/<number>/head` gets both commits.

`github.publish` needs the pull request object and the repository name. The REST response of `gh api repos/<owner>/<name>/pulls/<number>` has the same shape as the `pull_request` object of the workflow event. `publish` posts with the `gh` CLI. It pushes the follow-up branch with a temporary git index, so it does not change the working tree.

Ticket 24 (model cache on `main`) changes the workflow of this repo. This ticket removes that workflow. Ticket 24 now applies only to the demo repo and to the workflow example in `README.md`.

## Design

1. `slopgate/github.py`: add `pull_request(repo, number)`. It gets the `owner/name` of the repo with `gh repo view`. It reads the pull request with `gh api repos/<owner>/<name>/pulls/<number>`. It fetches the base commit and `pull/<number>/head` from `origin`. It returns an event: `{"pull_request": <pr>, "repository": {"full_name": <owner/name>}}`.
2. `slopgate/cli.py`: add `--pr <number>`. `--base` and `--head` become optional. The parser stops with an error when it gets no `--pr` and not both `--base` and `--head`. With `--pr`, the review uses the base and head SHAs of the event, and `publish` uses the event. `GITHUB_EVENT_PATH` is not read. With `--pr --dry-run`, the gate fetches and reviews, but it posts nothing. Without `--pr`, the behavior does not change.
3. Delete `.github/workflows/slopgate.yml`. Keep `action.yml`, the workflow example in `README.md`, and `.github/workflows/ci.yml`.
4. Document the command in `README.md` and in `CLAUDE.md`.

## Acceptance

- [x] `slopgate review --pr 7` reviews the base and head SHAs of the pull request and posts the review to it (offline test with a fake `gh`).
- [x] The local clone does not need the head commit before the run. The gate fetches it.
- [x] `slopgate review` with no `--pr` and no `--base` stops with a parser error.
- [x] `slopgate review --help` shows `--pr`.
- [x] `slopgate review --pr 11 --dry-run` on this repo posts nothing and prints the result.
- [x] `.github/workflows/slopgate.yml` is deleted.
- [x] With the cached ONNX model and no `onnxruntime`, the gate uses the torch model and does not stop.
- [x] `uv run pytest -q` passes.

## Comments

- 2026-10-06: Built. `github.pull_request` in `slopgate/github.py` reads the pull request with `gh` and fetches its base and head commits from `origin`. `slopgate/cli.py` has the new `--pr` option. With `--pr`, the review uses the SHAs of the pull request, and `publish` uses the event that `pull_request` returns. `.github/workflows/slopgate.yml` is deleted.
- Worked example. PR #11 (ticket 22) is open. Its GitHub Slopgate run started at 02:09 UTC. At 02:36 UTC it was still running (more than 26 min). On the local machine, this command finished in 2 min 51 s:

  ```bash
  uv run --env-file .env slopgate review --pr 11 --dry-run
  ```

  The result was empty: 0 suggestions, 0 follow-up changes, 0 rejected. PR #11 had 0 comments and 0 reviews after the run, so `--dry-run` posted nothing.
- `--sandbox local` does not work for this repo on macOS. `.slopgate.toml` sets a setup command for the Contree Linux image (`apt-get ...`). With `--sandbox local`, the run took 23.6 s and rejected the candidate with "apt-get: command not found". So the commands in `CLAUDE.md` and `README.md` use the default sandbox (Contree).
- Bug found and fixed in this ticket. `embed.load` used the ONNX model when `~/.cache/slopgate/coderank-int8.onnx` existed. `onnxruntime` is in the `hook` extra, so plain `uv sync` does not install it. The first local run stopped with `ModuleNotFoundError: No module named 'onnxruntime'`. Now `embed.load` uses the ONNX model only when the file exists and `onnxruntime` is installed. In all other cases, it uses the torch model. `test_cached_onnx_model_is_used_only_when_onnxruntime_is_installed` checks both cases. Without the fix, the "not installed" case fails.
- Run with plain `uv sync` (no `onnxruntime`) and the fix: `--pr 11 --dry-run` finished in 3 min 10 s with the torch model. It gave 1 rejected item: `has_dead_code`, because a test file from Super ended with a stray ```` ``` ```` line (`SyntaxError`). Ticket 21 (strict code-block extractor) fixes that problem. The run posted nothing.
- Tests: `test_pr_flag_fetches_the_pull_request_reviews_it_and_posts_to_it` runs the real `pull_request` with a fake `gh` and a real `git fetch` from a bare origin. The clone uses `--no-local`, so the head commit is not in the clone before the run. With the fetch line removed, the test fails. `test_review_needs_pr_or_base_and_head` checks the parser error. Full offline suite: 110 passed, 10 deselected.
