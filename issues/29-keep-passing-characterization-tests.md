# 29 — Keep the passing characterization tests

**What to build:** When a test file from Super fails on the original code, the gate removes the failing test functions and keeps the passing ones. If the remaining tests pass in both runs and cover every branch, the gate uses them. This step makes no model call. If it does not give a good file, the gate continues with the retry from ticket 13, as now.

**Blocked by:** 20 (it changes the reply parsing in `characterize`; this ticket changes the same loop)

**Status:** ready-for-agent

## Context

`characterize` in `slopgate/review.py` rejects the whole test file when one test in it fails on the original code. On PR #17 (2026-10-08), the gate rejected these functions although some of their tests passed:

| Function | Result on the original |
|---|---|
| `build` in `slopgate/index.py` | 2 failed, 2 passed (a `MagicMock` that `json` cannot serialize) |
| `find_duplicate` in `slopgate/review.py` | 4 failed, 1 passed (Super guessed `DUPLICATE_SCORE` as 0.8) |
| `test_empty_inputs_get_one_retry_that_asks_for_a_test_file` | 1 error, 1 passed (fixture `trials` not found) |

A characterization test records what the code does now. A test that fails on the original code most likely has a wrong expected value. Meta's TestGen-LLM uses the same rule: it removes each generated test that fails on the original, keeps the tests that pass, and then requires new coverage ([Alshahwan et al. 2024](https://arxiv.org/pdf/2402.09171)). In their evaluation, 57% of test classes got at least one test that passed reliably, and 25% got a test that also added coverage.

The branch coverage check stays. It prevents a file that is too small after the removal from proving a rewrite.

## Design

1. Run the test file as now (`PYTHONHASHSEED=1`, with coverage).
2. If it fails, read the names of the failed tests from the pytest short summary. The lines start with `FAILED <path>::<name>` or `ERROR <path>::<name>`. Remove the part from `[` on (a parametrized case), and remove the ` - <message>` part.
3. Remove each named test function from the file with `ast`. For a name of the form `Class::test_x`, remove the method `test_x` from the class. Keep imports, fixtures, helpers, and the other tests. When a parametrized case fails, remove the whole function.
4. If the summary names no test (for example, a `SyntaxError` or an import error at collection), or if no test function remains, do not remove anything. Continue with the retry from ticket 13.
5. Run the reduced file again with both seeds and with coverage, as for any test file. If it passes in both runs and misses no branch, use it. Otherwise, continue with the retry from ticket 13, and send the output of the full file, not the reduced one.
6. Do not count the removal as an attempt. It makes no model call.

## Acceptance

- [ ] A test file with 1 failing and 2 passing tests that cover every branch gives the 2 passing tests. The fake LLM gets no second tests request.
- [ ] A failing parametrized case removes its whole function. A failing method in a test class removes only that method.
- [ ] A test with an `ERROR` at setup (a missing fixture) is removed like a failed test.
- [ ] A reduced file that misses a branch goes to the retry from ticket 13. The retry prompt contains the output of the full file.
- [ ] A file that fails at collection (`SyntaxError`) goes to the retry from ticket 13 with no change.
- [ ] A reduced file that passes with one seed and fails with the other is rejected as nondeterministic.
- [ ] `uv run pytest -q` passes.
- [ ] Live measurement: run `characterize` on `build`, `seed`, `matches`, `find_duplicate`, and `characterize` at commit b2a2ad0, 4 runs each, before and after the change. Record the proven count for each function in Comments.

## How to verify by hand

1. Run `uv run --env-file .env slopgate review --repo . --base b2a2ad0~1 --head b2a2ad0 --dry-run`.
2. Count the rejections with "characterization tests fail on original". Compare the count with the PR #17 comment.

## Comments
