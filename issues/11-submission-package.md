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
