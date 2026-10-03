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

**Status:** ready-for-agent

- [ ] The action takes the Nebius API key as an input and uses the workflow's GitHub token; the README states that checkout needs full history.
- [ ] A rewrite is posted inline only if it edits one file and every replaced line is in the diff's added lines; all others go to the follow-up pull request.
- [ ] No follow-up pull request is opened when `followup` is empty.
- [ ] The review has one summary comment written by Ultra, which lists accepted and rejected counts.
- [ ] A sandbox install failure posts one notice comment, and the job still succeeds.
- [ ] On the public demo repo, a pull request that adds slop gets at least 2 suggestions, and applying one keeps CI green.
- [ ] The token cost of the review appears in the summary comment.
