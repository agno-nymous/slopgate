# 06 — GitHub Action end to end

**What to build:** A maintainer adds one workflow file and one API key, and every pull request gets a Slopgate review.

The action does the following:
- Posts the inline results as one review with GitHub suggested changes, with event `COMMENT` and never `REQUEST_CHANGES`.
- Opens a follow-up pull request for the `followup` results. Its branch is `slopgate/<head branch>`, and it targets the author's branch.
- Adds a short summary written by Nemotron Ultra.
- Never fails CI.
- Caches the CodeRankEmbed model between runs.

The ticket ends with a public demo repo that shows a real review on a real pull request.

**Blocked by:** 02, 03

**Status:** done

- [x] The action takes the Nebius API key as an input and uses the workflow's GitHub token; the README states that checkout needs full history.
- [x] A rewrite is posted inline only if it edits one file and every replaced line is in the diff's added lines; all others go to the follow-up pull request.
- [x] No follow-up pull request is opened when `followup` is empty.
- [x] The review has one summary comment written by Ultra, which lists accepted and rejected counts.
- [x] A sandbox install failure posts one notice comment, and the job still succeeds.
- [x] On the public demo repo, a pull request that adds slop gets at least 2 suggestions, and applying one keeps CI green.
- [x] The token cost of the review appears in the summary comment.

## Comments

- 2026-10-03: Built. `slopgate review` without `--dry-run` reads the event file at `GITHUB_EVENT_PATH` and posts through `gh` (`slopgate/github.py`, `publish`). Suggestions go in one review with event `COMMENT`; with no suggestions the summary is a plain pull request comment; a result with nothing in it posts nothing. Follow-ups are committed with git plumbing onto the head commit (no working tree change) and force-pushed to `slopgate/<head branch>`, which Slopgate owns; an open pull request on that branch is reused, otherwise one is created against the author's branch. Fork pull requests get no follow-up branch. Two follow-ups that edit the same file cannot both apply (each holds whole files proven alone), so only the first is kept and the summary says so. The Ultra summary is followed by fixed lines: accepted and rejected counts, the token cost from `llm.usage` priced with `PRICES` in `slopgate/config.py`, and the rejected reasons in a collapsed list. If the Ultra call fails, the results are still posted without the summary sentence. An install failure posts one notice comment and makes no Ultra call.
- `action.yml` is a composite action: Python 3.12, a cache for `~/.cache/huggingface` (CodeRankEmbed), pip install of the action path with CPU-only torch, then the review. Both steps use `continue-on-error`, and the CLI always exits 0.
- 9 seam tests in `tests/test_github.py` use a fake `gh` on `PATH` that logs its arguments and a local bare repo as `origin`. 12 mutations (event `REQUEST_CHANGES`, post when empty, fork pushes, duplicate pull request, push without force, wrong base, no install notice, summary failure fatal, overlapping follow-ups merged, no rejected list, swapped prices, wrong parent commit) each fail one test.
- Left: the public demo repo and a real run on GitHub. The real token cost line and the CodeRankEmbed cache are checked only there.
- 2026-10-03: First real run on https://github.com/agno-nymous/slopgate-demo/pull/1 posted nothing. The review found 2 suggestions and 2 follow-ups (same as the local dry run), pushed `slopgate/add-checkout`, then `gh pr create` exited 1 because the repo setting "Allow GitHub Actions to create and approve pull requests" is off by default (`can_approve_pull_request_reviews: false`). The exception stopped `publish`, so the proven suggestions were lost, and the log showed no stderr. Fixed: a failed push or a failed follow-up pull request no longer stops the review; the summary states which step failed, with the stderr, and links the pushed branch when only the pull request failed. Errors from `gh` and `git` now carry their stderr. 2 new seam tests; 3 mutations each fail one. README names the setting.
- 2026-10-03: Live check passed on https://github.com/agno-nymous/slopgate-demo/pull/1 (action at `agno-nymous/slopgate@main`, real Nemotron, real ConTree). The run posted one `COMMENT` review with 2 suggested changes (`can_checkout` nesting 4 -> 0; `shipping_label` complexity 7 -> 1), an Ultra summary, "Accepted: 2 inline suggestions, 2 follow-up changes in https://github.com/agno-nymous/slopgate-demo/pull/2. Rejected: 0.", and "Token cost: $0.0061 (8,518 tokens)." Follow-up pull request #2 targets `add-checkout` and holds the `format_total` duplicate and the `discounted` wrapper changes. Applying the `shipping_label` suggestion (commit `1c2ce85`) kept CI green. Install step: 65 s on the first run. The demo repo needed "Allow GitHub Actions to create and approve pull requests" turned on.
- The accepted `can_checkout` rewrite returns a non-bool falsy argument where the original returns `False`; filed as ticket 15.
