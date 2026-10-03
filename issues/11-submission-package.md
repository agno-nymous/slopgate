# 11 — Hackathon submission package

**What to build:** Everything the Devpost submission needs, so that a judge can understand, run, and score the project:
- A README with setup steps and a description of how Nemotron, Token Factory, Sandboxes, and Serverless Jobs are used. It links to the benchmark and comparison results.
- A feedback section on Token Factory, Sandboxes, and the NVIDIA models.
- The MIT license, visible at the top of the repo page.
- A script for the demo video, at most 3 minutes.
- The Devpost project text.

**Blocked by:** 06, 08, 10

**Status:** ready-for-agent

- [ ] The README covers install, the Action workflow file, the hook setup, and `slopgate index`, and a fresh clone works by following it.
- [ ] The README has a table of which Nemotron model does which job, and why.
- [ ] The README explains the sandbox checkpoint-and-trial pattern with a diagram.
- [ ] The README links the benchmark results (ticket 10) and, if done, the classifier comparison (ticket 09).
- [ ] The feedback section lists concrete problems and suggestions met during the build, including any SDK gaps found in ticket 02.
- [ ] The video script covers: the problem, a live gate review on the demo repo, the live flag catching a duplicate, the benchmark numbers, and how Token Factory and Nemotron are used. It fits in 3 minutes.
- [ ] The Devpost text names the Coding and Agentic Engineering track and links the public repo and the demo repo.
