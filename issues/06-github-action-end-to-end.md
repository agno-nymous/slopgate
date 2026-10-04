# 06 — GitHub Action end to end

**What to build:** A maintainer adds one workflow file and one API key. Then every pull request gets a Slopgate review.

The action does these things:
- It posts the inline results as one review with GitHub suggested changes. The review uses event `COMMENT` and never uses `REQUEST_CHANGES`.
- It opens a follow-up pull request for the `followup` results. The branch of the follow-up pull request is `slopgate/<head branch>`. The follow-up pull request targets the branch of the author.
- It adds a short summary. Nemotron Ultra writes the summary.
- It never fails CI.
- It caches the CodeRankEmbed model between runs.

The ticket ends with a public demo repo. The demo repo shows a real review on a real pull request.

**Blocked by:** 02, 03

**Status:** done

- [x] The action takes the Nebius API key as an input. The action uses the GitHub token of the workflow. The README states that checkout needs full history.
- [x] The action posts a rewrite inline only when both conditions are true. The rewrite edits one file. Every replaced line is in the added lines of the diff. The action sends all other rewrites to the follow-up pull request.
- [x] The action opens no follow-up pull request when `followup` is empty.
- [x] The review has one summary comment. Ultra writes the comment. The comment lists the counts of accepted and rejected results.
- [x] When the sandbox install fails, the action posts one notice comment. The job still succeeds.
- [x] The public demo repo has a pull request that adds slop. This pull request gets at least 2 suggestions. When a maintainer applies one suggestion, CI stays green.
- [x] The summary comment shows the token cost of the review.

## Comments

- 2026-10-03: Built. The command `slopgate review` without `--dry-run` reads the event file at `GITHUB_EVENT_PATH`. It posts through `gh` (the function that posts the results is `publish` in `slopgate/github.py`). The suggestions go in one review with event `COMMENT`. When the result has no suggestions, the summary is a plain pull request comment. When the result has nothing in it, the action posts nothing. Git plumbing commits each follow-up onto the head commit. This commit does not change the working tree. The action force-pushes the commit to `slopgate/<head branch>`. Slopgate owns this branch. When an open pull request exists on this branch, the action reuses it. Otherwise, the action creates a pull request against the branch of the author. Fork pull requests get no follow-up branch. Each follow-up holds whole files that the sandbox proved alone. For this reason, two follow-ups that edit the same file cannot both apply. The action keeps only the first follow-up, and the summary says so. Fixed lines follow the Ultra summary. These lines give the counts of accepted and rejected results. They give the token cost from `llm.usage`, priced with `PRICES` in `slopgate/config.py`. They also give the reasons for the rejected results in a collapsed list. When the Ultra call fails, the action still posts the results without the summary sentence. When the install fails, the action posts one notice comment and makes no Ultra call.
- The file `action.yml` defines a composite action. It uses Python 3.12. It uses a cache for `~/.cache/huggingface` (the cache of CodeRankEmbed). It runs a pip install of the action path with CPU-only torch. Then it runs the review. Both steps use `continue-on-error`. The CLI always exits 0.
- There are 9 seam tests in `tests/test_github.py`. They use a fake `gh` on `PATH` that logs its arguments. They use a local bare repo as `origin`. There are 12 mutations. Each mutation fails one test. The mutations are: event `REQUEST_CHANGES`, post when empty, fork pushes, duplicate pull request, push without force, wrong base, no install notice, summary failure fatal, overlapping follow-ups merged, no rejected list, swapped prices, and wrong parent commit.
- Left: the public demo repo and a real run on GitHub. Only the real run checks the real token cost line and the CodeRankEmbed cache.
- 2026-10-03: The first real run on https://github.com/agno-nymous/slopgate-demo/pull/1 posted nothing. The review found 2 suggestions and 2 follow-ups. This result is the same as the local dry run. The action pushed `slopgate/add-checkout`. Then `gh pr create` exited 1. The repo setting "Allow GitHub Actions to create and approve pull requests" is off by default (`can_approve_pull_request_reviews: false`). The exception stopped `publish`, so the action lost the proven suggestions. The log showed no stderr. Fixed: a failed push or a failed follow-up pull request no longer stops the review. The summary states which step failed, with the stderr. When only the pull request failed, the summary links the pushed branch. Errors from `gh` and `git` now carry their stderr. There are 2 new seam tests. 3 mutations each fail one test. The README names the setting.
- 2026-10-03: The live check passed on https://github.com/agno-nymous/slopgate-demo/pull/1. The action was at `agno-nymous/slopgate@main`. The check used real Nemotron and real ConTree. The run posted one `COMMENT` review with 2 suggested changes. The first change reduces the nesting of `can_checkout` from 4 to 0. The second change reduces the complexity of `shipping_label` from 7 to 1. The run also posted an Ultra summary. The summary states "Accepted: 2 inline suggestions, 2 follow-up changes in https://github.com/agno-nymous/slopgate-demo/pull/2. Rejected: 0." It also states "Token cost: $0.0061 (8,518 tokens)." Follow-up pull request #2 targets `add-checkout`. It holds the changes for the `format_total` duplicate and the `discounted` wrapper. Commit `1c2ce85` applied the `shipping_label` suggestion. CI stayed green. The install step took 65 s on the first run. The demo repo needed the setting "Allow GitHub Actions to create and approve pull requests" turned on.
- The accepted `can_checkout` rewrite returns a falsy argument that is not a bool. The original returns `False`. This difference is filed as ticket 15.
- 2026-10-03: A later demo run lost its summary comment. This run came after a person committed a suggestion from the GitHub UI. The command `gh pr comment` got `HTTP 503: No server is currently available`. The green job hid the error. Now `gh` calls retry up to 3 times. They wait 10 s, then 20 s. They retry only on `HTTP 5xx`. They do not retry other failures, such as "not permitted". The summary now also states the review time next to the token cost ("Time: 1 min 43 s"). The action skips every step for pull requests from `slopgate/` branches. For this reason, Slopgate no longer reviews its own follow-up pull requests. Those runs waited for approval as `action_required`. There are 5 new seam tests. 5 mutations each fail one test.
