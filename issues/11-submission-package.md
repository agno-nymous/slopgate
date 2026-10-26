# 11 — Hackathon submission package

## Summary

- **Goal:** Give a judge everything that the Devpost submission needs, so that the judge can understand, run, and score the project. Example: a README that a fresh clone can follow to install the gate and the hook.
- **Checkable finish condition:** The seven boxes below are checked. For example, the video script fits in 3 minutes, and the Devpost text names the Coding and Agentic Engineering track.
- **Evidence:** A fresh clone that follows the README installs and runs the gate and the hook. The README links the benchmark results of ticket 10.
- **Constraints:** The repo has the MIT license, visible at the top of the repo page. The video is 3 minutes long at most. Keep the total spend under about $50 (see Comments).

**Blocked by:** 06, 08, 10

**Status:** ready-for-agent

## Details

The README describes how the project uses Nemotron, Token Factory, Sandboxes, and Serverless Jobs. It links to the benchmark results and the comparison results. The submission also has:
- A feedback section on Token Factory, Sandboxes, and the NVIDIA models.
- The MIT license, visible at the top of the repo page.
- A script for the demo video.
- The Devpost project text.

- [ ] The README covers the install, the Action workflow file, the hook setup, and `slopgate index` (the command that builds the index of the repo). A fresh clone works when the user follows the README.
- [ ] The README has a table that shows which Nemotron model does which job, and why.
- [ ] The README explains the sandbox checkpoint-and-trial pattern with a diagram.
- [ ] The README links the benchmark results (ticket 10). If ticket 09 is done, the README also links the classifier comparison.
- [ ] The feedback section lists the concrete problems and suggestions from the build. It includes the SDK gaps that ticket 02 found.
- [ ] The video script covers: the problem, a live gate review on the demo repo, the live flag that catches a duplicate, the benchmark numbers, and the use of Token Factory and Nemotron. The video fits in 3 minutes.
- [ ] The Devpost text names the Coding and Agentic Engineering track. It links the public repo, the demo repo, and the showcase page of ticket 64.

## Comments

- Facts from the planning handoff: The model prices per 1M tokens (input / output) are: Lightning $0.06 / $0.24, Super $0.30 / $0.90, Ultra $1.00 / $3.00. `Nemotron-3-Nano-Omni` left the pay-per-call catalog on 2026-08-31. Credits are $25 with code `NEBIUS-DEVPOST-GLOBAL26`, plus $25 from the Builders Program (dev.nebius.com/builders). Keep the total spend under about $50. The submission needs: a public repo with the MIT license visible, a README with setup and Nebius/NVIDIA usage, a working demo URL, a video of 3 minutes at most, and feedback on the tools.

### 2026-10-25 — how to present the numbers (decided with the user)

**Headline.** Use these sentences in the README, the video, and the Devpost text. The numbers come from the ticket 10 rerun of 2026-10-25 (15 SWE-bench Lite instances, 45 injected items).

- "Slopgate flags 91% of injected slop on real SWE-bench repos." (41 of 45 items.)
- "34% of the flagged items get a proven one-click fix. 0 of these fixes broke a hidden test." (14 of 41. The gate never sees the hidden tests.)
- "The other flagged items get a review note that names the slop and the fix." (27 of 41. `review.unproven` writes the note, marked "(not rewritten)".)
- "The run costs $1.16 for 15 repos."
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
