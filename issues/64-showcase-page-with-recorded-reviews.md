# 64 — Showcase site: recorded reviews of example repositories, a live try-it panel, and a local command

## Summary

- **Goal:** A judge opens one URL and sees how Slopgate works on real code. The site has 5 pages: home (one real fix), how it works (the 5 gate steps), reviews (recorded reviews of real repositories), benchmark (the headline numbers), and try it (a live panel and the local command). The site shows proven fixes only. A judge who wants to try Slopgate pastes a Python function and their own key into the live panel, or runs one local command.
- **Checkable finish condition:** The site loads as static files, shows at least 3 recorded reviews with proven fixes of at least 2 kinds, and makes no request until the judge runs the live panel. The README has the local command. The pages and the recordings hold no API key.
- **Evidence:** Before: the Devpost submission needs "a URL to a working demo", and Slopgate has none. After: the URL, a recorded review for each example, and a panel that runs the gate in the judge's browser.
- **Constraints:** No hosted service of the project uses the user's API keys. The recordings come from reviews that the user ran once, offline, before the submission. The live panel (added 2026-10-26, user decision) keeps the judge's key in the memory of the browser tab and sends it only to `api.tokenfactory.nebius.com`. No server of the project ever sees a key. Keep the deadline of 2026-10-30 in view.

**Blocked by:** 10 (the site shows the benchmark headline, and the best examples come from the rerun)

**Status:** needs-live-check

**Type:** build.

## Context

The judging criteria score Design equally with the other 3 criteria: "Does the project deliver a complete, coherent product experience, not just a technical proof of concept?" The judges also look at how well a project uses Nebius. The submission uses 3 Nebius services: Token Factory (Nemotron), ConTree (the sandbox), and the Serverless Job of ticket 10 (the benchmark).

The first design of this ticket (2026-10-17) was a hosted service on a Nebius Serverless Endpoint. The user dropped it on 2026-10-25, because a public page would spend the user's API keys. On 2026-10-26 the user asked for a panel where a judge enters their own key. The panel runs in the judge's browser. It is not a hosted service.

The judging days are 2026-12-01 to 2026-12-15. Static files have no cold start and no credits to run out, so the site still works then.

## Design

1. **Pick the examples.** Choose real reviews of SWE-bench repositories that have proven fixes. The user decided on 2026-10-26 to show successes only. The benchmark page shows the kinds that get no fix (`redundant_check`, `wrapper`).
2. **Record them once.** For each example, run `slopgate review --repo <clone> --base <ref> --head <ref> --dry-run` with the user's keys. Save the output unedited under `docs/demo/recordings/<name>.json`. `python -m bench.showcase meta` reads the step times, the tokens, the cost, and the final test files from the Phoenix trace of the run. Do not edit a recording by hand.
3. **Build the pages.** `bench/pages.py` writes 9 static files from the recordings and `swebench.json`: `index.html`, `how.html`, `reviews.html`, `benchmark.html`, `try.html`, and one `reviews/<name>.html` for each recording. `style.css` is shared. The fonts (Fira Sans and Fira Code, Latin, weights 400 and 600) are in `docs/demo/fonts/`. There is no build step for the reader, no framework, and no request from a page, except the live panel after the judge presses "Run the gate".
4. **The live panel.** `docs/demo/try.js` holds the panel. It runs the gate steps in the browser: rewrite and tests with Nemotron Super through Token Factory, then both versions in Pyodide (a Web Worker with a 20 s limit). It also builds the local command for a GitHub repository.
5. **The local command.** The README holds the exact steps. A dry run posts nothing to GitHub.
6. **Publish.** Serve `docs/` with GitHub Pages. The README and the Devpost text link the site.
7. **No secret in the files.** One offline test checks that no file in `docs/demo/` has a string that looks like a Nebius key, and that every recording parses as JSON.

## Acceptance

- [x] The Comments list the chosen examples and the reason for each.
- [x] `docs/demo/recordings/` holds at least 3 unedited dry-run outputs of real pull requests, with at least 1 proven rewrite in each of 2 kinds. (The user dropped the rejection requirement on 2026-10-26.)
- [ ] The pages open from a local file and from the published URL, and the browser network log shows no request to an API or a model before the judge runs the panel.
- [x] The benchmark page shows the headline of ticket 10, and the numbers equal `swebench.md`.
- [x] The how-it-works page shows the 5 gate steps. Each review page shows the diff, the tests, the proof result, the time, and the cost.
- [x] The pages are readable at 375 px, 768 px, and 1280 px, in light and dark mode, with no horizontal scroll.
- [x] The README has the local command. A run in an empty folder with the user's own key gives a review (the Comments record the time and the cost).
- [x] The offline test finds no key in `docs/demo/`, finds no broken local link, and checks that each page makes no request. `uv run pytest -q` passes.
- [ ] A run of the live panel in a real browser with a real key gives a verdict. (Not done: the agent must not type the key.)
- [ ] The site is published at a URL. The README and the Devpost text link it.

## Comments

### 2026-10-25

**Design change.** The user decided that the hosted demo must not use the user's API keys, that it shows recorded reports of example repository pull requests, and that a judge brings their own keys to try Slopgate. I rewrote the ticket from "hosted service on a Serverless Endpoint" to "static page with recorded reviews and a local command".

### 2026-10-25 — headline wording

Use the headline sentences of ticket 11 (Comments, 2026-10-25) on the site. They give the share of flagged items, the share of proven fixes, and the 0 silent breaks.

### 2026-10-26

**What was built.** A 5-page static site in `docs/demo/`, made by `bench/pages.py` from the recordings:

- `index.html`: one real fix (pylint `NamingStyle.get_regex`, before and after, complexity 12 to 2), the proof line, and the 3 headline numbers.
- `how.html`: the 5 gate steps. Steps 3 to 5 are inside a frame that is labeled "Nebius ConTree sandbox".
- `reviews.html` and `reviews/<name>.html`: a flat list of 4 reviews. Each review page shows the diff first. The tests and the step times are the only folds.
- `benchmark.html`: one square for each of the 45 injected functions, and the numbers of `swebench.json`. It names the kinds with no proven fix.
- `try.html`: the live panel (key, sample or pasted function, repository command builder), the local command, and the cost of one review.

The layout and the type follow a brief from another session: Fira Sans for text, Fira Code for code only, cool gray ground, one blue accent, green and red only in diffs and verdicts, 1 px rules, no cards, no gradients. The one motion is a 150 ms color change on links.

**Chosen examples and why.**

| Recording | Proven fixes | Why chosen |
|---|---|---|
| `pylint-7993` | `NamingStyle.get_regex` (lookup_table), 15 tests | The clearest before and after: a 12-branch `elif` chain becomes a dict. It is the example on the home page. |
| `pytest-7220` | `_get_multicapture` (dead), 8 tests | Dead code in the capture code of pytest. |
| `seaborn-3190` | `ObjectProperty.get_mapping` (swallowed_error), `Continuous.tick` (nesting), 5 and 7 tests | Two kinds in one run, in a plotting library. |
| `flask-4992` | `Flask.auto_find_instance_path` (dead), `Config.get_namespace` (nesting), 3 and 10 tests | Two kinds in one run, in a web framework. |

I removed `demo-checkout` (slopgate-demo) and `pytest-5227` (3 rejections) from the site, because the user asked for proven fixes only. The slop in all 4 examples was injected by the benchmark. The pages say so.

**Measured (Phoenix traces of the 4 recorded runs).**

| Review | Wall time | Cost | Proven | Other flagged |
|---|---|---|---|---|
| `pylint-7993` | 531 s | $0.046 | 1 | 2 |
| `pytest-7220` | 375 s | $0.0455 | 1 | 2 |
| `seaborn-3190` | 333 s | $0.103 | 2 | 1 |
| `flask-4992` | 154 s | $0.080 | 2 | 1 |

I ran several recordings at the same time, so they shared Token Factory. One review alone is faster: a run of `slopgate-demo` in an empty folder took 84 s (the traced run of the same refs took 210 s and cost $0.019). Token Factory answered with a 529 "System is overloaded" for 3 items of the first parallel run. Ticket 76 covers the retry.

**Checks done.**

- `uv run pytest -q tests/test_showcase.py`: 11 passed (no key in files, every page current, same 5 links on every page, every local link resolves, no request from a page, fonts self-hosted, headline equals `swebench.json`).
- The live panel ran in headless Chrome with real Pyodide and a mocked Token Factory: a good rewrite gave "Proven" with 6 tests in 4 s. A wrong rewrite gave "Rejected: the rewrite fails a test". An endless loop gave "Rejected: a run took longer than 20 s" after 24 s. The request had the `Authorization` header, `enable_thinking: false`, and the Super model name.
- I sent the real request shape to Token Factory from a Python script: status OK, `access-control-allow-origin: *`, `finish_reason: stop`, 0 reasoning tokens, and one fenced `python` block.
- Screenshots in Chrome at 375, 768, and 1280 px, in light and dark mode: no horizontal scroll on any page. The contrast of every text and diff color pair is at least 5.8 (light) and 6.4 (dark).

**Impeccable detector (v0.1.18, `npx impeccable detect <url>` on the served pages, 1280 px).** Before: 4 findings and 2 advisories. The findings were `line-length` on 3 text blocks (89 and 123 characters on a line), and a skipped heading level (h1 then h3) in the live panel. The advisories were a placeholder contrast of 3.6:1 and a one-word last line. Fixes: `max-width: 55ch` on paragraphs (a CSS rule of the same specificity had hidden the first limit), a 55ch limit on the steps list, the live panel at 45rem, `h2` and `h3` in `try.js`, a placeholder color from the muted token, and `text-wrap: pretty`. After: 0 findings at 1280 px and at 390 px, and 0 findings in a scan of `docs/demo/`. A control file with a gradient heading, Inter, and a cream ground gave 4 findings, so the detector does work. The scan of `.css` and `.js` files uses regex only, so the served pages give the full result.

**Code review (Opus subagent, 2026-10-26).** It found 16 points. I fixed these:

- `try.js`: a test block that defines the function under test again now gives an error, not "Proven". The `--pr` command now has `--dry-run`. The default base ref is `HEAD~1`, because `origin/main` and `HEAD` are the same commit after a clone. A cut-off model reply (`finish_reason: length`) gives its own message. The verdict has `role="status"`. The command area has no live region. A retry wait no longer sets a finished step back to running.
- Pages: the home page said "15 repositories" for 15 instances of 7 repositories. The test blocks and the commands had a leading space on each line, which breaks a pasted test file. The waffle squares for "not flagged" had a contrast of 1.59:1 and now use the `--hunk` color. The how-it-works page now names the follow-up pull request. The benchmark sentence on low-fix kinds and the number of recorded reviews now come from the data. The time table has a header row.
- Tests: the key check now reads the `.env` values too. The headline test now compares with `swebench.md`. A new check finds no rejected function on a review page.
- Cleanup: removed dead CSS and the unused `data-theme` blocks, `SANDBOX_STEPS`, and the backtick round trip in the review titles. `python -m bench.pages` now writes the pages.

I did not fix: the `items_of` branch for inline suggestions has no test (no recording uses it); the CSS that `try.js` injects duplicates `style.css`; `try.js` has no committed test (the headless check lives in the scratchpad); the repair-round path of the panel is untested in a browser.

**Known limits.**

- The home page is 1066 px high at 1280 px width. The pylint diff has 23 lines, so the page does not fit one 900 px screen.
- Nobody ran the live panel in a real browser with a real key. The retry wait (5 s, 15 s, 45 s) and the copy button are untested in a browser.
- The `/impeccable` commands (shape, critique, typeset, and so on) did not run. The skill installed during this session (`npx impeccable install --project --providers=claude --no-hooks`), and the session does not load a new skill. The install files (`.claude/skills/impeccable/`, `.claude/agents/`) are not committed.
- GitHub Pages is off for this repository. The user must turn it on (source `docs/`).
