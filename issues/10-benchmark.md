# 10 — Benchmark on SWE-bench with injected slop

## Summary

- **Goal:** Measure how well the whole gate works on real repos. Example: inject a redundant check into a real SWE-bench commit, run the gate, and see whether it finds and fixes the check.
- **Checkable finish condition:** One run on 30 to 50 SWE-bench instances saves a results file with four numbers (detection recall, complexity change, acceptance rate, silent-break rate), for the whole run and for each slop kind. A run of 10 instances costs less than $5. The README links the file and holds the job command.
- **Evidence:** Before: the gate had no such numbers on real repos. Ticket 37 only measures detection. After: `bench/results/swebench/swebench.md` holds all four numbers and the total token spend for 15 instances (see Comments).
- **Constraints:** The hidden tests run on the preloaded SWE-bench image of each instance. The gate builds its own sandbox with its normal install (the user changed this on 2026-10-18; the first design used the image for the gate too). The injection writes the ground truth (kind, function, file) before the gate runs. The hidden SWE-bench tests run on every accepted rewrite, and the gate never sees them. The run starts as a Nebius Serverless Job. Blocked by 02, 03, 04, 37 (stage 1: detection only), and 41 (it replaces 30 and 35).

**Blocked by:** 02, 03, 04 (done), 37 (stage 1: detection only), 41 (replaces 30 and 35)

**Status:** done

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

- [x] The injection step writes the ground truth for each instance (kind, function, file) before the gate runs.
- [x] The hidden tests run in the SWE-bench image of each instance. `select` imports the image once. The gate uses its own install. (The user changed this box on 2026-10-18. See Comments.)
- [x] The report gives all four numbers for the whole run and for each slop kind.
- [x] The run computes the silent-break rate. It runs the hidden tests on every accepted rewrite.
- [ ] ~~The run starts as a Nebius Serverless Job. The README contains the job command.~~ Wontfix (the user decided on 2026-10-25, see Comments).
- [x] The report gives the total token spend of the run. A run of 10 instances costs less than $5.
- [x] The results are saved in a file. The README can link to this file.

## Comments

### 2026-10-18 — benchmark built, two runs on 15 instances

**What was built.** `bench/swebench.py` runs the whole gate on SWE-bench Lite instances with injected slop. Command: `uv run --env-file .env python -m bench.swebench [select|run|report]`.

- `select` imports the SWE-bench image of each instance into ConTree. It applies the test patch and runs the hidden tests with coverage on the base commit.
- It injects one slop kind into each of up to 3 functions whose body the hidden tests run. The kinds are the 5 AST transforms of ticket 37, a one-use wrapper, and a Super-written copy of a function (`duplicate`).
- It keeps an injection only when the hidden tests that pass on the base commit still pass on it.
- It keeps an injection only when the hidden tests can see a break: a `raise` at the first body statement of the function must break a hidden test or stop the pytest summary.
- It deletes the hidden test files from the injected commit, and it writes the ground truth to `groundtruth.json` before the gate runs.
- `run` runs `review.review` on each injected commit. It runs the hidden tests on the image for each accepted rewrite. A test that passes on the injected commit and fails after the rewrite is a silent break. A timeout is a break. A rewrite that stops the pytest summary is a break. The benchmark runs a failed test again on the injected commit to remove flaky tests.
- `report` writes `bench/results/swebench/swebench.md` and `.json`: recall, complexity change, acceptance, silent-break rate, and cost, for each kind and in total.

Instances: pytest (5), sphinx (3), pylint (2), requests, flask (2), xarray, seaborn. scikit-learn, astropy, and matplotlib were left out: the scikit-learn hidden suite passed the 1,000 s limit.

**Worked example.** `pylint-dev__pylint-7993`, `NamingStyle.get_regex` in `pylint/checkers/base/name_checker/naming_style.py`. The original returns `{...}[name_type]` (complexity 1). The `lookup_table` injection replaces the dict with 11 `if`/`elif` branches and `raise KeyError(name_type)` (complexity 12). The gate found `lookup_table`. Super wrote 14 characterization tests, and the rewrite passed them in the sandbox: "nesting 1 -> 1, complexity 12 -> 2". The hidden tests passed on the rewrite: no silent break. The gate accepted this item in both runs.

**Run 1: the gate uses the SWE-bench image** (`bench/results/swebench/image-sandbox/`). This was the design of the ticket.

| kind | items | detected | accepted |
|---|---|---|---|
| nesting | 8 | 8 | 4 |
| redundant_check | 8 | 8 | 0 |
| swallowed_error | 7 | 7 | 0 |
| lookup_table | 2 | 2 | 2 |
| dead | 7 | 7 | 5 |
| wrapper | 6 | 6 | 2 |
| duplicate | 7 | 5 | 5 |
| total | 45 | 43 | 18 |

- Recall 0.956. Acceptance 18 of 43 detected (0.419). Silent breaks 0 of 18.
- Complexity of the accepted rewrites in place: −1.91 against the injected code. Nesting: −0.64.
- Cost $1.24 for 15 instances. Mean time 229 s for each instance.

**Run 2: the gate uses its own install** (`bench/results/swebench/swebench.md`). The user changed the design on 2026-10-18: the gate must install the repo as it does for a user. The hidden tests stay on the image.

| kind | items | detected | accepted |
|---|---|---|---|
| nesting | 6 | 4 | 2 |
| redundant_check | 6 | 6 | 0 |
| swallowed_error | 4 | 4 | 0 |
| lookup_table | 1 | 1 | 1 |
| dead | 3 | 3 | 2 |
| wrapper | 5 | 5 | 0 |
| duplicate | 5 | 3 | 2 |
| total (with an environment) | 30 | 26 | 7 |

- 45 items in the ground truth. 15 items have no environment and are left out of the table. Recall 0.867. Acceptance 7 of 26 detected (0.269). Silent breaks 0 of 7. Cost $0.67. Mean time 136 s for each instance.
- All 5 pytest instances fail the install: `LookupError: setuptools-scm was unable to detect version for /repo` (ticket 58).
- 4 more instances install with exit 0, but their tests cannot run on Python 3.10. sphinx-7975, sphinx-8506, and sphinx-8627: `TypeError: required field "lineno" missing from alias` in the conftest. requests-3362: a 2016 pytest does `from UserDict import DictMixin`. The report counts these 8 detected items as gate rejections ("characterization tests fail on original"), but the cause is the environment.
- So 6 of 15 instances have a working environment (flask 2, pylint 2, xarray, seaborn). On these 6, acceptance is 7 of 17 detected (0.41), near the 0.419 of run 1. The drop from run 1 comes from the environment, not from the proof.
- Tickets 58, 59, and 67 (an install agent) address the environment.

**Control: can the hidden tests see a break?** The check inserts `raise RuntimeError('control')` at the first body statement of a function and runs the hidden tests.

- On the run 1 items, before the fixes: 27 of 45 items showed a break. 10 items stopped the pytest summary, and `check` counted that as unmeasured. 9 items showed no break: 8 of them have a decorator, and the coverage window counted the `def` line, which runs at import.
- Fixes: the coverage window starts at the first body statement. `check` counts a missing summary as a break when the injected commit gives a summary. `select` now runs the control on each candidate. A blind candidate is dropped, and `select` tries the next function of the same kind.
- In run 2, 2 candidates were blind after the window fix.
- Limit: the control shows only that a raise in the function is visible to the hidden tests. A rewrite can change behavior in a way that the hidden tests do not check. So 0 silent breaks in 7 accepted rewrites is a small sample, not a proof.

**Gate defects found and fixed.**

- `Contree.run` cut the output at 65,535 bytes. The flask suite lost its pytest summary, and the baseline could not compare. `OUTPUT_LIMIT` is now 10 MiB in `slopgate/sandbox.py`.
- `pytest_result` did not match a summary line with `]` in the parameters or a line that pytest cut off (xarray, pytest-5692). The whole line is now the key.

**Traces** (project `slopgate-bench`).

- Run 1: no ERROR span, no `sandbox.prepare` over 60 s, no `finish_reason: length` in 637 model calls. 12 of 39 `characterize` spans stopped at the step or token limit (for example trace `69f3240778d9961f1c5712b64f175a26`, xarray, "fail on original").
- Run 2: 5 ERROR spans, all `sandbox.prepare` with the setuptools-scm error (the same error as trace `4c87f3e07523a8937ce8c220665ca07c` of an earlier run 2 attempt). No `sandbox.prepare` over 60 s. No `finish_reason: length` in 362 model calls. 12 of 24 `characterize` spans stopped at a limit (9 step, 2 token, 1 time), and 3 more failed on the original code. Most of these are on the 4 broken environments.

**Known limits.**

- 15 instances, not 30 to 50. The Serverless Job is not done. These two parts of the finish condition stay open.
- `redundant_check` 0 of 8 and `swallowed_error` 0 of 7 in run 1. The characterization must cover every branch, and the injected check is a branch that never runs (ticket 43).
- 6 of 7 duplicate items in run 1 are exact structural copies. The gate finds them without characterization. Only 1 copy was rewritten by Super.
- The hidden check runs on each accepted rewrite alone, not on all rewrites together.
- Results change from run to run. An earlier run with the image, before the parser fix, gave different counts for `swallowed_error`, `dead`, and `duplicate`.
- The cost counts Token Factory tokens only, not ConTree compute.

### 2026-10-25 — final rerun, portable run stage, and the decisions of the user

**Decisions of the user (2026-10-25).**

- The benchmark keeps 15 instances. The finish condition says 30 to 50. A larger set needs a new `select` (new injections) and takes about one day.
- The Serverless Job box is wontfix. The hackathon rules do not require it. The rules accept a runtime call to the Token Factory inference API as "runs on Nebius". The gate calls Token Factory on each review. A Serverless Job needs a Nebius AI Cloud tenant. The user has only Token Factory. A new account, its billing, and its secrets take about half a day. The deadline is in 5 days.

**Image box.** The Token Factory Sandboxes docs give no list of ready SWE-bench images. `select` imports the SWE-bench image of each instance (`docker.io/swebench/sweb.eval.x86_64.<id>`) once with `images.oci`, and it stores the checkpoint UUID as `hidden_uuid`. The hidden tests of every run use this checkpoint. All 15 stored UUIDs resolve with `images.use` on 2026-10-25.

**What was built.**

- `run` now works on a machine that has no local clones. `select` writes the injected commit of each instance to `bench/results/swebench/heads/<id>.bundle`. The 15 bundles have 18 KB in total. Before the workers start, `run` calls `restore` for each instance. If the clone does not have the injected commit, `restore` clones the repo at the base commit and fetches the bundle. `job` takes the clone path from `CLONES`. `groundtruth.json` has no `clone` field (a path on the Mac) now.
- `runs-2026-10-21.json` and `runs-2026-10-21.meta.json` keep the old runs. This file mixes two runs. The run of 2026-10-21 gave all entries except one. The ticket 72 rerun of 2026-10-25 replaced the entry of `psf__requests-3362`. The old report on `main` (42 items, 3 infrastructure errors) comes from the run of 2026-10-21 alone.

**Worked example.** `pytest-dev__pytest-7220`, `pytest_terminal_summary` in `src/_pytest/runner.py`, kind `swallowed_error`. The gate found the kind and wrote 10 characterization tests. The rewrite passed them in the sandbox: "nesting 4 -> 3, complexity 11 -> 11". The hidden tests passed on the rewrite. This is the first accepted `swallowed_error` item in any run. In the run of 2026-10-18, all 5 pytest instances failed the install (ticket 58).

**Measured (rerun of 2026-10-25, 15 instances, 8 workers).**

| kind | items | detected | accepted |
|---|---|---|---|
| nesting | 8 | 6 | 3 |
| redundant_check | 9 | 9 | 0 |
| swallowed_error | 8 | 8 | 1 |
| lookup_table | 1 | 1 | 1 |
| dead | 6 | 6 | 5 |
| wrapper | 7 | 7 | 1 |
| duplicate | 6 | 4 | 3 |
| total | 45 | 41 | 14 |

- Recall 0.911. Acceptance 14 of 41 detected (0.341). Silent breaks 0 of 14.
- The run has 0 infrastructure errors. The old report had 3, all on `psf__requests-3362`.
- The run has 0 `RateLimitError` rejections (ticket 73).
- Cost $1.16 for 15 instances. Mean time 251 s for each instance.
- The step limit of the test agent causes 10 of the 27 rejections. In 5, the tests miss branches. In 5, the tests fail on the original code.
- Portability check: `restore` rebuilt `pallets__flask-4992` and `pylint-dev__pylint-7993` in an empty cache folder. `git rev-parse HEAD` equals the head in `groundtruth.json`, and `git show <head>:<path>` reads the injected file.

**Traces** (project `slopgate-bench`). 2,373 spans. No span has the status ERROR. No model call of the 627 returned `finish_reason: length`. 15 `sandbox.prepare` spans.

**Known limits.**

- 15 instances, not 30 to 50 (decision above).
- `redundant_check` is 0 of 9, and `wrapper` is 1 of 7. Tickets 43 and 45 address these kinds.
- `restore` clones the repos one after another before the workers start. On a fresh machine, this adds the clone time of 7 repos.
- The portability check ran `restore` only. Nobody measured a full `run` on a fresh machine.
- The hidden tests use ConTree checkpoints of the Nebius project that ran `select`. A key of another project probably cannot use them (not measured).
