# 37 — Detection benchmark on SWE-bench code with injected slop (stage 1 of ticket 10)

**What to build:** A benchmark that measures only the detection step of the gate (`classify` in `slopgate/kinds.py`) on real code from SWE-bench repos. It runs no sandbox and writes no rewrite. It reports the precision and the recall for each slop kind, and the false-positive rate on clean code.

**Blocked by:** 36

**Status:** done

**Type:** measurement. Ticket 10 (the full gate on SWE-bench) is stage 2. It comes after tickets 30 and 35.

## Context

Ticket 36 measured the detection design on 60 functions. 12 of these functions were written for that ticket, and 27 are Slopgate's own code. So the numbers can favor the examples. The gate must work on code that neither Slopgate's authors nor the model wrote.

The PR #20 problem was false positives: the gate posted 24 wrong notes. So the benchmark measures the false-positive rate on clean code as well as the recall on injected slop.

The detection step costs little: Ruff, vulture, and `nesting()` need no model, and `classify` sends at most 2 Lightning calls for each function. The benchmark can run on a laptop.

## Design

1. **Source code.** Take the repos and the base commits of SWE-bench Lite (the Hugging Face dataset `princeton-nlp/SWE-bench_Lite`). Use at least 6 repos, for example django, sympy, requests, flask, astropy, and scikit-learn. Clone each repo at one base commit.
2. **Clean functions (negatives).** Take 200 top-level functions and methods from the non-test files, at random, with a fixed seed. Keep functions of 5 to 60 lines. The expected result for a clean function is "no kind". Before the run, a person reads each function that the gate flags. When the person finds real slop, the function becomes a positive for that kind. Record each such decision in the results file.
3. **Injected slop (positives).** Make slop copies of other functions from the same pool. Inject each kind into at least 10 functions. Use both methods:
   - **Code transforms** (exact ground truth): turn guard clauses into nested `if` blocks (`nesting`); wrap the body in `try` / `except Exception: return None` (`swallowed_error`); turn a dict lookup into an if/elif chain (`lookup_table`); add a check that an earlier check already guarantees (`redundant_check`); add comments that repeat the next line (`filler_comment`); add an unused variable or code after a `return` (`dead`).
   - **Nemotron injection** (realistic): ask Super to add one named kind to a function, as a coding agent would write it. Keep a function only when it still parses. Record the kind and the changed lines.
   - Put 2 kinds into some functions, to measure the multi-kind result.
4. **Ground truth first.** The injection step writes the ground truth (repo, commit, path, function, kinds, changed lines) to a file before `classify` runs.
5. **Run.** Call `classify(function, text)` on each function, with `text` being the file with the function in it. Run each function 3 times, because Lightning can give different results across runs.
6. **Report.** Write one JSON file and one Markdown table, with:
   - the precision and the recall for each kind, and in total;
   - the false-positive rate on the clean functions (the share of clean functions that get a kind);
   - the results for the code transforms and for the Nemotron injection, separately;
   - the time for each function, and the total token cost;
   - the stability: the share of functions that got the same kinds in all 3 runs.
7. Put the benchmark script in `bench/`. It must run with one command, and the README must give that command.

## Acceptance

- [x] The injection step writes the ground truth before `classify` runs.
- [x] The run uses at least 200 clean functions from at least 6 SWE-bench repos, and at least 10 injected functions for each of the 6 kinds.
- [x] The report gives the precision, the recall, and the false-positive rate for each kind and in total, with code transforms and Nemotron injection separate.
- [x] Each flagged clean function has a recorded person's decision (real slop or false positive). Claude drafted each decision; the user accepted the drafts without a review of each row.
- [x] The report gives the total token cost and the time for each function.
- [x] The results file is saved in the repo, and the README links to it.
- [x] A `## Comments` entry names each kind whose precision or recall is below 0.8, with examples, and proposes a fix or a follow-up ticket.

## Comments

### 2026-10-09 — results

**What was built.** `bench/` holds a benchmark for the detection step only (`classify`). It runs no sandbox and writes no rewrite. One command runs it: `uv run --env-file .env python -m bench.detect`. It has 4 stages, and each stage skips the work that is already done:

1. `sample` reads SWE-bench Lite from the Hugging Face datasets-server API. It clones 12 repos at the base commit of their first instance. It takes 25 clean functions from each of 8 repos (django, sympy, requests, flask, astropy, scikit-learn, sphinx, pytest), with seed 37. The functions have 5 to 60 lines and come from non-test files.
2. `inject` makes slop copies of other functions. Code transforms (`bench/transforms.py`) give 12 items for each kind, plus 12 items with 2 kinds. Super gives up to 10 items for each kind. The stage writes `bench/results/groundtruth.json` before `classify` runs. It keeps a copy only when the code still parses and when no measured kind appears that was not injected.
3. `run` calls `classify` 3 times on each item, in 8 worker processes. It records the kinds, the evidence lines, the time, and the tokens of each run in `bench/results/runs.json`.
4. `report` writes `bench/results/detection.json` and `bench/results/detection.md`. The scoring is in `bench/score.py`.

`bench/labels.json` holds 2 kinds of decisions:

- One decision for each kind that the gate found on real code (clean functions and injection sources): real slop or false positive, with a reason. 139 decisions.
- One decision for each Super injection: valid or not valid. 6 of the 9 `redundant_check` injections were not valid, because Super added `if hasattr(...): pass` and no earlier check guarantees it. These were decided before the classify run.

An injected copy is scored only on its injected kinds and on new kinds. A kind that its source already had is scored once, on the source.

**Worked example.** Input: `_words_group` in `astropy/io/fits/util.py`, a clean function. It has the comment `# locations of the blanks` above `blank_loc = np.nonzero(arr == b' ')[0]`. Output of 3 runs:

- Run 1: `{'filler_comment': ['# locations of the blanks']}`, 3.1 s, 1,640 input and 230 output tokens.
- Run 2: the same kind and the same line, 3.9 s.
- Run 3: `{}`, 2.6 s.

The decision in `labels.json` is "slop": the comment only repeats the name `blank_loc`. So runs 1 and 2 are true positives, and run 3 is a false negative. The item is not stable.

A second input: `should_write` in `sphinx/builders/gettext.py`, with its guard clause turned into nested blocks by the `nesting` transform. All 3 runs gave `{'nesting': []}`, which is correct. Before the review fix, the transform wrote `if not (not path.exists(filepath)):`, and Lightning also reported `redundant_check` in 3 of 3 runs.

**Measured results.** 469 items: 200 clean, 129 sources, 84 transform items, 56 Super items (50 valid). 3 runs each, 0 run errors. All counts are item runs (3 runs pooled).

| Kind | Precision (all) | Recall (all) | Recall (transform) | Recall (Super) | False-positive rate on clean functions |
|---|---|---|---|---|---|
| `nesting` | 0.593 | 1.0 | 1.0 | 1.0 | 0.090 |
| `redundant_check` | 0.462 | 0.476 | 0.533 | 0.083 | 0.023 |
| `swallowed_error` | 0.967 | 1.0 | 1.0 | 1.0 | 0.005 |
| `lookup_table` | 1.0 | 1.0 | 1.0 | 1.0 | 0 |
| `filler_comment` | 0.456 | 0.892 | 0.979 | 0.8 | 0.135 |
| `dead` | 1.0 | 1.0 | 1.0 | 1.0 | 0 |
| Total | 0.675 | 0.913 | 0.924 | 0.889 | 0.217 |

- 28.8% of the clean function runs got a kind. 21.7% got a false kind.
- The recall of 1.0 for the 4 measured kinds is true by construction: `inject` keeps a measured injection only when the detector finds it. The useful number for these kinds is the false-positive rate on clean code.
- Time for each function: mean 2.27 s, median 1.62 s, p95 6.12 s, max 109.93 s. The 8 worker processes ran at the same time, so the times include queueing.
- Cost: Lightning 846,069 input and 241,400 output tokens for all `classify` runs, $0.109. Super 43,585 input and 38,719 output tokens for the injection, $0.048. A first injection run that was discarded (Super labelled its own slop) cost about $0.028 more.
- Stability: 80.3% of the items got the same kinds in all 3 runs (clean 82.5%).

**Kinds below 0.8.**

- **`nesting`, precision 0.593.** On real code, 21 of 25 functions with depth 3 were false positives. Example: `DatabaseWrapper.check_constraints` in django (`with cursor` / `for table` / `for key column` / `for bad row`), where each block does real work. The slop cases are nested `if` blocks that guard clauses can flatten, for example `MigrationExecutor.migration_plan` (depth 6). Follow-up: ticket 39.
- **`filler_comment`, precision 0.456.** Lightning reports comments that explain why or give context. 62 of 73 flagged functions on real code were false positives. Examples: `# bpo-23890: manually break a reference cycle`, `# type: ignore`, `# docstring inherited`, `# pragma: no cover`. Follow-up: ticket 39.
- **`redundant_check`, precision 0.462, recall 0.476.** Lightning misses clear cases. In `isatty` (astropy), `if not (hasattr(file, 'isatty')):` comes directly after `if hasattr(file, 'isatty'): return file.isatty()`, and all 3 runs missed it. It found 0 of the 3 valid Super injections in 9 runs. It also reports each branch of an if/elif chain, for example in `NullBooleanSelect.format_value`. One evidence entry in `_encode_files` (requests) was almost the whole function, and the grounding check accepted it. Follow-up: ticket 39.

**Gate defects found.**

- A comment at column 0 inside a method makes `classify` raise `IndentationError`. 34 functions in the 12 repos have one. The benchmark leaves them out. Follow-up: ticket 38.
- In 5 of 1,407 runs, Lightning wrote 8,000 or more output tokens, and the run took 60 s to 110 s. `decide` sends no output limit. Follow-up: ticket 40.

**Known limits.**

- Claude drafted the decisions in `labels.json`. The user accepted them on 2026-10-09 without a review of each row.
- Super is weak at injecting `redundant_check` and `lookup_table`: only 3 valid and 7 items. Super labels its slop when the prompt allows it ("# Slop: unused local variable"). The injection rejects a reply with the word "slop" or with an added comment, except for `filler_comment`.
- Ruff SIM116 flags an if/elif chain only when the compared value is a plain name and each branch returns a constant. So the `lookup_table` sources are only functions with a dict lookup. The 8 clean repos gave 5 such functions, so 4 more SWE-bench Lite repos (matplotlib, xarray, pylint, seaborn) were added to the injection pool only.
- 3 transform items still have `not (not ...)`, where the guard test is a `BoolOp` that starts with `not` (for example `not (not create and alias_list)`).
- One labeller made each decision, with no second pass.
