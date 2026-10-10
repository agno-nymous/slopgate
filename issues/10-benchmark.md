# 10 — Benchmark on SWE-bench with injected slop

## Summary

- **Goal:** Measure how well the whole gate works on real repos. Example: inject a redundant check into a real SWE-bench commit, run the gate, and see whether it finds and fixes the check.
- **Checkable finish condition:** One run on 30 to 50 SWE-bench instances saves a results file with four numbers (detection recall, complexity change, acceptance rate, silent-break rate), for the whole run and for each slop kind. A run of 10 instances costs less than $5. The README links the file and holds the job command.
- **Evidence:** Not started. Today the gate has no such numbers on real repos. Ticket 37 only measures detection. After this ticket, the results file holds all four numbers and the total token spend.
- **Constraints:** Use the preloaded sandbox image of each instance, with no fresh install. The injection writes the ground truth (kind, function, file) before the gate runs. The hidden SWE-bench tests run on every accepted rewrite, and the gate never sees them. The run starts as a Nebius Serverless Job. Blocked by 02, 03, 04, 37 (stage 1: detection only), 30, and 35.

**Blocked by:** 02, 03, 04 (done), 37 (stage 1: detection only), 30, 35

**Status:** ready-for-agent

## Details

Steps of the benchmark:

1. Take 30 to 50 SWE-bench instances that have preloaded Nebius sandbox images.
2. Use Nemotron to inject known slop into a real commit. The slop kinds are: deep nesting, a one-use wrapper, a redundant check, and a copy of an existing helper. The injection records the ground truth.
3. Run `slopgate review --dry-run` (the command that runs the gate and applies no changes) on each slopified commit.
4. Report four numbers:
   - **detection recall:** the share of injected slop that the gate finds
   - **complexity change:** the complexity before and after the rewrite
   - **acceptance rate:** the share of rewrites that the gate proves
   - **silent-break rate:** the share of accepted rewrites that fail the SWE-bench hidden tests. The gate never sees these tests.

- [ ] The injection step writes the ground truth for each instance (kind, function, file) before the gate runs.
- [ ] The run uses the preloaded sandbox image of each instance. It does not use a fresh install.
- [ ] The report gives all four numbers for the whole run and for each slop kind.
- [ ] The run computes the silent-break rate. It runs the hidden tests on every accepted rewrite.
- [ ] The run starts as a Nebius Serverless Job. The README contains the job command.
- [ ] The report gives the total token spend of the run. A run of 10 instances costs less than $5.
- [ ] The results are saved in a file. The README can link to this file.
