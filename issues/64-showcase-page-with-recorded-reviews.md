# 64 — Showcase page: recorded reviews of example repositories, and a local command to try Slopgate

## Summary

- **Goal:** A judge opens one URL and sees how Slopgate works on real code. The page shows the 5 gate steps, 3 or 4 recorded reviews of real pull requests, and the benchmark headline. A judge who wants to try Slopgate runs one local command with their own API keys.
- **Checkable finish condition:** The showcase URL loads as one static page, shows at least 3 recorded reviews (at least 1 proven rewrite in each of 2 kinds, and at least 1 rejection), and makes no request to any model, GitHub, or other API. The README has the local command. The page and the recordings hold no API key.
- **Evidence:** Before: the Devpost submission needs "a URL to a working demo", and Slopgate has none. A judge must install the GitHub Action or the CLI to see it work. After: the URL, and a recorded review in the page for each example.
- **Constraints:** The user decided on 2026-10-25 that no hosted service uses the user's API keys. So the page runs no model and holds no secret. The recordings come from reviews that the user ran once, offline, before the submission. A judge who wants a live review brings their own `NEBIUS_API_KEY` and `NEBIUS_PROJECT_ID` and runs Slopgate on their own machine. No server of the project ever sees a judge's key. There is no Serverless Endpoint in this ticket. Keep the deadline of 2026-10-30 in view: one plain page is enough.

**Blocked by:** 10 (the page shows the benchmark headline, and the best examples come from the rerun)

**Status:** ready-for-agent

**Type:** build.

## Context

The judging criteria score Design equally with the other 3 criteria: "Does the project deliver a complete, coherent product experience, not just a technical proof of concept?" The judges also look at how well a project uses Nebius. Without a Serverless Endpoint, the submission still uses 3 Nebius services: Token Factory (Nemotron), ConTree (the sandbox), and the Serverless Job of ticket 10 (the benchmark).

The first design of this ticket (2026-10-17) was a hosted service on a Nebius Serverless Endpoint that reviewed a pasted pull request URL. The user dropped it on 2026-10-25, because a public page would spend the user's API keys. A bring-your-own-key form on the page is possible, but a judge would paste a key into a page that they do not control. It is out of scope. Do it as a new ticket only if time is left on 2026-10-28.

The judging days are 2026-12-01 to 2026-12-15. A static page has no cold start and no credits to run out, so it still works then.

The coding track has several entries with a web UI. One example is ARCHON, with a Next.js view of its reasoning, its sandbox terminal, and its diff.

## Design

1. **Pick the examples.** Choose 3 or 4 real reviews. Take them from `slopgate-demo` pull requests and from the benchmark items after the rerun of ticket 10. Cover at least 2 kinds (for example `nesting` or `swallowed_error`, and `duplicate`). Include at least 1 rejection that shows the proof refusing a wrong or unproven rewrite, because it shows that the gate is not a rubber stamp. Do not pick only the best results. Write in the Comments why each example was chosen.
2. **Record them once.** For each example, run `uv run --env-file .env slopgate review --repo <clone> --base <ref> --head <ref> --dry-run` with the user's keys. Save the output unedited under `docs/demo/recordings/<name>.json`. Read the step names and times of the run from its Phoenix trace (`gate.review` spans), and save them next to the JSON. If the JSON lacks the characterization tests, read them from the trace as well. Do not edit a recording by hand.
3. **Build the page.** One static file, `docs/demo/index.html`. It has no build step, no framework, and no request to any server. It holds the recordings inline, so it also works from a local file. Sections:
   - the benchmark headline of ticket 10 (the same numbers as `swebench.md`);
   - the 5 steps (candidates, kinds, characterization tests, rewrite, sandbox proof) as one inline SVG diagram;
   - each recorded review: the pull request link, the kind, the code before and after as a diff, the characterization tests, the proof result, the time, and the cost;
   - "Try it with your own keys": the local command, and a sentence that the keys stay on the judge's machine.
   Make it readable at 375 px width and in light and dark mode. Follow the `artifact-design` skill for the layout.
4. **The local command.** The README holds the exact steps for a judge who has only a pull request URL: clone the repository, set `NEBIUS_API_KEY` and `NEBIUS_PROJECT_ID` in the shell, and run `slopgate review --repo <clone> --base <ref> --head <ref> --dry-run`. A dry run posts nothing to GitHub. Run the steps once in an empty folder with a key of the user and record the time and the cost. Measure the cost of one review, and write it on the page. Install with `uvx --from git+https://github.com/agno-nymous/slopgate` only after the repository is public; test the form that the README gives.
5. **Publish.** Serve `docs/` with GitHub Pages after the repo is public (the public flip of 2026-10-29). A private repo on the free plan has no Pages. Until then, an Artifact link or the local file is enough for review. The README and the Devpost text link the page.
6. **No secret in the files.** Add one offline test: every file in `docs/demo/` has no string that looks like a Nebius key, and every recording parses as JSON. The sandbox environment drops `NEBIUS_*`, but the recordings come from the gate output, so check them.

## Acceptance

- [ ] The Comments list the chosen examples and the reason for each.
- [ ] `docs/demo/recordings/` holds at least 3 unedited dry-run outputs of real pull requests: at least 1 proven rewrite in each of 2 kinds, and at least 1 rejection.
- [ ] `docs/demo/index.html` opens from a local file and from the published URL, and the browser network log shows no request to an API or a model.
- [ ] The page shows the benchmark headline of ticket 10, and the numbers equal `swebench.md`.
- [ ] The page shows the 5 gate steps as a diagram, and for each recorded review the diff, the tests, the proof result, the time, and the cost.
- [ ] The page is readable at 375 px width, in light and dark mode.
- [ ] The README has the local command. A run in an empty folder with the user's own key gives a review (the Comments record the time and the cost).
- [ ] The offline test finds no key in `docs/demo/`. `uv run pytest -q` passes.
- [ ] The page is published at a URL. The README and the Devpost text link it.

## Comments

### 2026-10-25

**Design change.** The user decided that the hosted demo must not use the user's API keys, that it shows recorded reports of example repository pull requests, and that a judge brings their own keys to try Slopgate. I rewrote the ticket from "hosted service on a Serverless Endpoint" to "static page with recorded reviews and a local command". The old design needed a container, 2 routes, a cache by head SHA, a size limit, and a cost limit. The new design needs none of them.

### 2026-10-25 — headline wording

Use the headline sentences of ticket 11 (Comments, 2026-10-25) on the page. They give the share of flagged items, the share of proven fixes, and the 0 silent breaks.
