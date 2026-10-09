# 37 — Detection benchmark on SWE-bench code with injected slop (stage 1 of ticket 10)

**What to build:** A benchmark that measures only the detection step of the gate (`classify` in `slopgate/kinds.py`) on real code from SWE-bench repos. It runs no sandbox and writes no rewrite. It reports the precision and the recall for each slop kind, and the false-positive rate on clean code.

**Blocked by:** 36

**Status:** ready-for-agent

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

- [ ] The injection step writes the ground truth before `classify` runs.
- [ ] The run uses at least 200 clean functions from at least 6 SWE-bench repos, and at least 10 injected functions for each of the 6 kinds.
- [ ] The report gives the precision, the recall, and the false-positive rate for each kind and in total, with code transforms and Nemotron injection separate.
- [ ] Each flagged clean function has a recorded person's decision (real slop or false positive).
- [ ] The report gives the total token cost and the time for each function.
- [ ] The results file is saved in the repo, and the README links to it.
- [ ] A `## Comments` entry names each kind whose precision or recall is below 0.8, with examples, and proposes a fix or a follow-up ticket.

## Comments
