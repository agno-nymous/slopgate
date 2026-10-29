# 11 — Hackathon submission package

## Summary

- **Goal:** Give a judge everything that the Devpost submission needs, so that the judge can understand, run, and score the project. Example: a README that a fresh clone can follow to install the gate and the hook.
- **Checkable finish condition:** The eight boxes below are checked. For example, the video script fits in 3 minutes, and the Devpost text names the Coding and Agentic Engineering track.
- **Evidence:** A fresh clone that follows the README installs and runs the gate and the hook. The README links the benchmark results of ticket 10.
- **Constraints:** The repo has the MIT license, visible at the top of the repo page. The video is 3 minutes long at most. Keep the total spend under about $50 (see Comments).

**Blocked by:** 06, 10

**Status:** needs-live-check

## Details

The README describes how the project uses Nemotron, Token Factory, Sandboxes, and Serverless Jobs. It links to the benchmark results and the comparison results. The submission also has:
- A feedback section on Token Factory, Sandboxes, and the NVIDIA models.
- The MIT license, visible at the top of the repo page.
- A script for the demo video.
- The Devpost project text.

- [ ] The README covers the install, the Action workflow file, the hook setup, and `slopgate index` (the command that builds the index of the repo). A fresh clone works when the user follows the README.
- [x] The README has a table that shows which Nemotron model does which job, and why.
- [x] The README explains the sandbox checkpoint-and-trial pattern with a diagram.
- [x] The README links the benchmark results (ticket 10). If ticket 09 is done, the README also links the classifier comparison.
- [x] The feedback section lists the concrete problems and suggestions from the build. It includes the SDK gaps that ticket 02 found.
- [x] The video script covers: the problem, a live gate review on the demo repo, the benchmark numbers, the use of Token Factory and Nemotron, and (optional) the write-time hook that catches a duplicate. Use the `plural` or `jaccard` prompt of ticket 08 for the hook scene: both gave a note on 2026-10-27. Ticket 08 (plan-time flag) is wontfix. Drop the hook scene if the run fails on the day of the recording. The video fits in 3 minutes.
- [x] The Devpost text names the Coding and Agentic Engineering track. It links the public repo, the demo repo, and the showcase page of ticket 64.
- [ ] Public flip of `slopgate-demo`, before 2026-10-30, 10:00 PT (1:00 PM ET). Run `gitleaks git` on its full history. Make the repo public. Open one pull request on it, and check that the public Action posts its review. The `slopgate` repo is already public.

## Comments

- Facts from the planning handoff: The model prices per 1M tokens (input / output) are: Lightning $0.06 / $0.24, Super $0.30 / $0.90, Ultra $1.00 / $3.00. `Nemotron-3-Nano-Omni` left the pay-per-call catalog on 2026-08-31. Credits are $25 with code `NEBIUS-DEVPOST-GLOBAL26`, plus $25 from the Builders Program (dev.nebius.com/builders). Keep the total spend under about $50. The submission needs: a public repo with the MIT license visible, a README with setup and Nebius/NVIDIA usage, a working demo URL, a video of 3 minutes at most, and feedback on the tools.

### 2026-10-25 — how to present the numbers (decided with the user)

**Headline.** Use these sentences in the README, the video, and the Devpost text. The numbers come from the ticket 10 rerun of 2026-10-25 (15 SWE-bench Lite instances, 45 injected items).

- "Slopgate flags 91% of injected slop on real SWE-bench repos." (41 of 45 items.)
- "34% of the flagged items get a proven one-click fix. 0 of these fixes broke a hidden test." (14 of 41. The gate never sees the hidden tests.)
- "The other flagged items get a review note that names the slop and the fix." (27 of 41. `review.unproven` writes the note, marked "(not rewritten)".)
- "The run costs $1.16 for 15 SWE-bench instances from 7 repositories." (Changed by the user on 2026-10-28: the first text said "15 repos".)
- Short form: "Flags 91% of slop. Proves a one-click fix for a third of it, with 0 broken hidden tests."

**Show the successful cases.** The showcase page (ticket 64) and the video show proven fixes and notes. Give the acceptance rate as a plain number. Do not hide the missed kinds: `redundant_check` has 0 of 9 accepted, and `wrapper` has 1 of 7.

**Nemotron scores on SWE-bench Verified (official model cards).**

| Model | Job in the gate | SWE-bench Verified |
|---|---|---|
| Nemotron 3 Super (120B-A12B) | test agent and rewrites | 60.5 (OpenHands), 59.2 (OpenCode), 53.7 (Codex) |
| Nemotron 3 Ultra (550B-A55B) | rewrite retry and summary | 70.7 (BF16), 69.5 (NVFP4) |

Sources: https://huggingface.co/nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-BF16 and https://huggingface.co/nvidia/NVIDIA-Nemotron-3-Ultra-550B-A55B-BF16. The NVIDIA build page gives 71.9 for Ultra BF16. Use the Hugging Face numbers.

**Do not compare the two scales.** SWE-bench measures whether a model fixes an issue. The Slopgate benchmark measures whether the gate removes slop and proves that the behavior stays the same. Use this sentence: "Super resolves about 60% of SWE-bench Verified. Slopgate adds a proof, so the fixes it posts broke 0 hidden tests."

**Facts from the official rules (https://nebiusglobalaihackathon.devpost.com/rules).**

- The video must be publicly visible on YouTube. An unlisted video is a risk.
- Judges can score from the text, the images, and the video only. So the video and the text carry most of the score.
- The feedback field is required. It is also a separate prize: 10 prizes of $100, scored on completeness, viability, and impact.
- "Runs on Nebius" means a runtime call to the Token Factory inference API, or AI Cloud compute. Slopgate calls Token Factory on each review.
- The Design criterion asks for "a complete, coherent product experience". Show the GitHub Action on real `slopgate-demo` pull requests, not only the benchmark.

### 2026-10-28 — README, feedback, video script, and Devpost text

**What was built.**

- `README.md` has 3 new sections. "Results" gives the headline numbers of ticket 10 and the missed kinds. "How Slopgate uses Nebius and NVIDIA" has the model table, a mermaid diagram of the checkpoint-and-trial pattern, and the reason why Slopgate uses no Serverless Job. "Feedback on Token Factory, Sandboxes, and Nemotron" gives each problem, the measured evidence, a suggestion, and the ticket number. It includes the 3 SDK gaps of ticket 02: the missing Sandboxes approval, `disposable=True`, and `str` read as a path.
- The README links the showcase page at its GitHub Pages URL. The old link pointed at the HTML file in the repo, and GitHub shows that file as source.
- The video script (`submission/video-script.md` in the main checkout, not in git; the user decided on 2026-10-28): 7 scenes with times, 360 words of narration. Each scene fits its time at about 140 words per minute.
- The Devpost text (`submission/devpost.md` in the main checkout, not in git): the text for each Devpost field. It names the track and links the repo, the demo repo, and the showcase page. The video URL is a placeholder.
- The README links no classifier comparison, because ticket 09 is not done.

**Worked example: the README "Try Slopgate" steps from a fresh clone.** A new clone of `slopgate-demo` in a scratch folder. The command is the README command with `uvx --refresh`:

```sh
uvx --refresh --from git+https://github.com/agno-nymous/slopgate slopgate review --repo . --base 0584a3a --head 441d235 --dry-run
```

Result: exit 0 in 248 s. The gate proved all 4 functions of the pull request: 2 suggestions (`can_checkout`, nesting 4 to 0 with 5 characterization tests; `shipping_label`, complexity 7 to 1 with 8 tests) and 2 follow-up changes (`format_total` is a copy of `money`; `discounted` is a wrapper). `rejected` and `notes` are empty.

**Worked example: the README hook steps in an empty venv.** `uv pip install 'slopgate[hook] @ git+https://github.com/agno-nymous/slopgate'` took 13 s. `slopgate index --ref HEAD` on a copy of `slopgate-demo` indexed 4 functions in 2 s. A new file `shop/format.py` with a copy of `money` under the name `format_price`, sent to `slopgate hook` as a PostToolUse payload, gave this context in 2 s, with exit 0:

```
slopgate: `format_price` (shop/format.py:1) duplicates existing `money` (shop/money.py:1), confidence 1.00. Call `money` instead of keeping `format_price`, unless the behavior must differ.
```

**Other checks.**

- https://agno-nymous.github.io/slopgate/ and its redirect target https://agno-nymous.github.io/slopgate/demo/ answer 200, and the GitHub API gives the Pages status `built`. This is step 7 of the public flip.
- The README mermaid diagram renders in the Mermaid Live Editor and on GitHub (the branch view of README.md): 10 nodes, and the 4 nodes of each candidate are inside the subgraph.
- `gitleaks git` on the full history of `slopgate-demo` (all branches and the `refs/pull/*` refs, 6 commits, 1 of them empty): no leaks. This is step 5 of the public flip for `slopgate-demo`.
- The `slopgate-demo` workflow uses `agno-nymous/slopgate@main` on `ubuntu-latest`. The repo has the secrets `NEBIUS_API_KEY` and `NEBIUS_PROJECT_ID`.

**Known limits.**

- Box 1 stays open. `slopgate-demo` is private, so a clone without GitHub credentials fails (`could not read Username`). A judge cannot follow the "Try Slopgate" steps until the repo is public. The gate and the hook steps work from a fresh clone with credentials.
- Flip step 8 passed on 2026-10-28 (the user approved the pull request). https://github.com/agno-nymous/slopgate-demo/pull/3 has the same change as pull request 1. The Slopgate job ran `agno-nymous/slopgate@main` on `ubuntu-latest` and passed in 98 s. It posted 1 `COMMENT` review with 2 suggested changes (`can_checkout`, 5 tests; `shipping_label`, 7 tests) and opened the follow-up https://github.com/agno-nymous/slopgate-demo/pull/4 with 2 changes. The summary says "Token cost: $0.0191 (55,126 tokens). Time: 1 min 3 s."
- The uvx run had no trace: the `uvx` install has no `phoenix` package, so tracing was off (`slopgate: tracing off: ModuleNotFoundError`). The cost of this run is not measured. The README keeps the $0.019 of the traced 210 s run.
- The index step took 2 s, not about 30 s, because this Mac already had the ONNX model in `~/.cache/slopgate/`. The first run on a new machine was not measured again.
- The "Try it" panel of the showcase page was tested only with a mocked Token Factory (ticket 64, `needs-live-check`). The README and the Devpost text do not say that it was verified with a real key.
- The video is not recorded. The Devpost text is not submitted. The user does both.

**Code review (Opus, thermo-nuclear skill).** 2 high, 8 medium, and 4 low findings. Applied:

- The Nano-Omni item said "during the build". The date is before the build. Fixed.
- The README said that the try-it page "runs the gate steps". It runs only a Super rewrite and tests in Pyodide. Fixed.
- The diagram showed the agent, the mutants, and the proof as parallel trials. It now shows the order for each candidate, and the Ultra retry. The collection check is in step 1.
- "every candidate gets a rewrite" was false (duplicate and wrapper items get none). Fixed.
- Wrong citations: "rewrite replies" are test-file replies (ticket 21), "Here" is ticket 07, `ApiTimeoutError` is tickets 38 and 60. Fixed.
- The 429 item title had the cause backwards. Fixed.
- The Devpost text listed the plan-time hook (wontfix) as next work. Removed.
- "each comparison" is "up to 8 comparisons". "up to 8 runs" is "up to 8 candidates". The Phoenix item now says "during development".
- The video narration went from 388 to 360 words, so each scene has slack.
- The DSPy sentence had no ticket as a source. Removed.

The user changed "15 repos" to "15 SWE-bench instances from 7 repositories" on 2026-10-28. Not changed: "one-click fix". "Accepted" counts both inline suggestions and follow-up pull requests.

**Tests.** `uv run pytest -q`: 507 passed, 17 deselected. The change is docs only.
