# 64 — Hosted demo: review a public pull request from a web page

## Summary

- **Goal:** A judge opens one URL, pastes a public pull request URL, and watches the gate work: the slop it finds, the Nemotron rewrite, the sandbox proof, and the suggestion. Example: the judge pastes a `slopgate-demo` pull request URL and sees a proven `nesting` rewrite with its characterization tests in about 3 minutes.
- **Checkable finish condition:** The demo URL runs a review of a `slopgate-demo` pull request from a fresh browser session and shows at least 1 proven suggestion. The service runs on a Nebius Serverless Endpoint. The README links the URL.
- **Evidence:** Before: the Devpost submission needs "a URL to a working demo", and Slopgate has none. A judge must install the GitHub Action or the CLI to see it work. After: the URL and a recording of one run.
- **Constraints:** The page posts nothing to GitHub. It shows the dry-run result only (`--dry-run`). It reviews only public pull requests. The service holds `NEBIUS_API_KEY` and `NEBIUS_PROJECT_ID` as endpoint secrets, never in the page. Limit the cost: at most 1 review at a time, a size limit on the pull request, and a cache of finished reviews by head SHA. Keep the deadline of 2026-10-30 in view: a plain page is enough.

**Blocked by:** 10 (the demo shows the benchmark headline)

**Status:** ready-for-agent

**Type:** build.

## Context

The judging criteria score Design equally with the other 3 criteria: "Does the project deliver a complete, coherent product experience, not just a technical proof of concept?" The judges also score how well a project uses Nebius. A Serverless Endpoint is one more Nebius service in the submission.

The coding track has several entries with a web UI. One example is ARCHON, with a Next.js view of its reasoning, its sandbox terminal, and its diff.

## Design

1. **Check first.** Confirm that a Nebius Serverless Endpoint can run a container with an HTTP server and outbound network access to Token Factory, ConTree, and GitHub. Record the result in the Comments before the build.
2. **Service.** A small HTTP server (standard library or one small dependency) with 2 routes: `POST /review` starts a dry-run review of a pull request URL, and `GET /review/<id>` streams the progress. Use the existing `review` code path. Add no second implementation of the gate.
3. **Progress.** Show each gate step as it ends: candidates, kinds, characterization, proof, and the final suggestion as a diff. The Phoenix span names of ticket 32 give the steps.
4. **Page.** One static HTML page: an input for the pull request URL, a list of steps, and the result. Show the benchmark headline of ticket 10 at the top.
5. **Fallback.** Add a "show a recorded run" link, in case the endpoint is cold or the credits are low on the judging days (2026-12-01 to 2026-12-15).

## Acceptance

- [ ] The Comments record the result of the check in Design step 1.
- [ ] A review of a `slopgate-demo` pull request from a fresh browser session shows at least 1 proven suggestion.
- [ ] The page shows each gate step as it ends.
- [ ] A second request for the same head SHA returns the cached result with no model call.
- [ ] The page posts nothing to GitHub.
- [ ] The README links the demo URL and the recorded run.
- [ ] `uv run pytest -q` passes.

## Comments
