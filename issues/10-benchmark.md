# 10 — Benchmark on SWE-bench with injected slop

**What to build:** A benchmark that measures how well the gate works on real repos.

1. Take 30 to 50 SWE-bench instances that have preloaded Nebius sandbox images.
2. Nemotron injects known slop into a real commit: deep nesting, a one-use wrapper, a redundant check, and a copy of an existing helper. The injection records ground truth.
3. The benchmark runs `slopgate review --dry-run` on each slopified commit.
4. It reports four numbers:
   - **detection recall:** the share of injected slop that is found
   - **complexity change:** before and after
   - **acceptance rate:** the share of rewrites that are proven
   - **silent-break rate:** the share of accepted rewrites that fail the SWE-bench hidden tests, which the gate never sees

The benchmark runs as a Nebius Serverless Job.

**Blocked by:** 02, 03, 04

**Status:** ready-for-agent

- [ ] The injection step writes the ground truth per instance (kind, function, file) before the gate runs.
- [ ] The run uses each instance's preloaded sandbox image, not a fresh install.
- [ ] The report gives all four numbers overall and per slop kind.
- [ ] The silent-break rate is computed by running the hidden tests on every accepted rewrite.
- [ ] The run starts as a Nebius Serverless Job, and the job command is in the README.
- [ ] Total token spend for the run is reported, and a 10-instance run costs less than $5.
- [ ] Results are saved in a file that the README can link to.
