# 48 — Compare the repo suite with a baseline run of the original code

## Summary

- **Goal:** The gate rejects a rewrite only for a repo test that the rewrite breaks. A test that also fails on the original code does not reject a rewrite.
- **Checkable finish condition:** A test makes a repo with one repo test that fails on the original code. A correct rewrite of another function gets its suggestion. A rewrite that breaks a test that passed before is rejected. `uv run pytest -q` passes.
- **Evidence:** On 2026-10-10, ticket 38 ran the full gate again on 9 SWE-bench items. 2 sympy rewrites passed their characterization tests and were rejected only because `sympy/polys/tests` failed. The same suite fails on the original code (see Context).
- **Constraints:** Run the baseline once for each review, not once for each rewrite. Keep the exit codes 0 and 5 as a pass.

**Blocked by:** —

**Status:** done

**Type:** bug.

## Context

The gate runs the repo suite (the `test` command of `.slopgate.toml`) on each rewrite in three places in `slopgate/review.py`: `repo_suite` (the in-place rewrites, ticket 25), `inline` (a wrapper), and `deduplicate` (a duplicate). Each place rejects the rewrite when the exit code is not 0 or 5. The gate never runs the suite on the original code. So when one repo test fails on the original code, the gate rejects every rewrite in that review.

Measured on 2026-10-10 on sympy commit `8dcb12a6cf500e8738d6729ab954a261758f49ca`, in Contree `python:3.9-slim`, with the original code:

- `python -m pytest -q -x -p no:cacheprovider sympy/polys/tests`: `1 failed, 218 passed`. The failure is `test_fields.py::test_FracElement___call__`.
- `python -m pytest -q -p no:cacheprovider sympy/polys/tests`: `5 failed, 765 passed` in 128 s.

All 5 failures are sympy expected-failure tests. Each raises `sympy.utilities.pytest.XFail`, and plain pytest counts it as a failure. The rewrites of `dup_sqf_norm` and `rs_cos_sin` were rejected with the same `test_FracElement___call__` failure.

The benchmark script of that run used `-x`. With `-x`, pytest stops at the first failure, so each rewrite was checked against only 219 of 770 tests.

## Design

1. After `prepare`, run the repo suite once on the checkpoint with no changed files. Save the IDs of the failing tests from the `FAILED <id>` and `ERROR <id>` lines.
2. In the three places, a rewrite fails the repo suite only when the run has a failing test ID that is not in the baseline. If the run has no test ID (for example, a collection error or a time-out) and the exit code is not 0 or 5, the rewrite fails as now.
3. If the baseline itself cannot run (a time-out, or no test was collected), keep the rule of today.
4. Run the baseline in parallel with the characterization, so that it adds little wall time.
5. Say in the documentation of `.slopgate.toml` that the `test` command must not use `-x`.

Open question: pytest prints `FAILED` lines only with the short summary (`-rf`, which `-q` gives by default in pytest 7 and later). Check which pytest versions the sandbox installs, and add `-rfE` to the command if needed.

## Acceptance

- [x] A test with a repo test that fails on the original code: a correct rewrite gets its suggestion.
- [x] A test with a rewrite that breaks a test that passed on the original code: the rewrite is rejected with "rewrite fails repo tests".
- [x] `repo_suite`, `inline`, and `deduplicate` all use the baseline.
- [x] The full gate on the 2 sympy items of ticket 38 (`dup_sqf_norm`, `rs_cos_sin`) no longer fails on `test_FracElement___call__`.
- [x] `uv run pytest -q` passes.

## Comments

### 2026-10-18 — done

**What was built.** The gate now runs the repo suite once on the original code (`baseline` in `slopgate/review.py`). The run starts after `prepare`, in its own thread, in parallel with the characterization. `pytest_result` reads a failing run: the `FAILED` and `ERROR` lines after the last `short test summary info` header, and the total on the last totals line. `suite_run` accepts a failing rewrite run only when these conditions are all true:

- The exit code is 1, and the run did not stop early (no `stopping after` and no `Interrupted` line).
- The summary has one line for each failure and each error on the totals line.
- The run has the same total of tests as the baseline.
- Each failing test also failed in the baseline.

Otherwise the rule of today applies: every failing run rejects the rewrite. `repo_suite`, `inline`, and `deduplicate` all call `suite_run`. The default test command is now `python -m pytest -q -rfE`. The README says that `test` must be one pytest run, with no `&&` and no `-x`.

**Change from the design.** The design compared only the failing test IDs. The code review found 5 outputs that this rule accepts although a test broke: `-rf` without `E` hides a new error, a parametrize ID with ` - ` is cut, a `FAILED` line in the captured output of a test looks like a result, an old pytest can print other prefixes, and a run can run fewer tests. The count check and the total check close these cases. A chained command (`pytest a && pytest b`) that stops after `a` in both runs is still not found. The README forbids it.

**Open question.** The Contree image `python:3.9-slim` installs pytest 8.4.2, which prints the `FAILED` lines by default. pytest 4.6.11 and 5.4.3 print the same `FAILED <id>` and `ERROR <id>` lines with `-rfE` (measured locally on Python 3.9). pytest 4.6.11 ends the totals line with `in 0.06 seconds`, not `in 0.06s`. The first totals pattern did not read it, so the run was not comparable. `TOTALS_LINE` now reads both forms, and `pytest_result` gives the same result for both versions.

**Worked example.** Input: sympy commit `8dcb12a6cf500e8738d6729ab954a261758f49ca`, with the injected slop of ticket 38 in `dup_sqf_norm` (`nesting`) and `rs_cos_sin` (`dead`) as one new commit. `.slopgate.toml`: `setup = "pip install -e ."`, `test = "python -m pytest -q -rfE -p no:cacheprovider sympy/polys/tests"`. Sandbox: Contree `python:3.9-slim`. The script of ticket 38 is not in the repo, so this case was built again from `bench/results/groundtruth.json`. Both items ran in one review. The `setup` line makes the gate use the image of the `Contree` object (`python:3.9-slim`, as in ticket 38), not the date-pinned path on `python:3.10-slim`. Trace `d102755104cd32f953849353acb9bcb3` (project `slopgate-gate`).

- The baseline found 5 failures of 770 tests, in 137 s: `test_FracElement___call__`, `test_noncommutative_pseudomultivariate`, `test_factor_noeval`, `test_issue_5786`, and `test_poly_matching_consistency`.
- The repo suite on both rewrites gave `5 failed, 765 passed` with the same 5 tests. The gate accepted both rewrites.
- Output: 2 follow-up rewrites. `dup_sqf_norm`: nesting 3 -> 2, 4 characterization tests passed. `rs_cos_sin`: 2 characterization tests passed. Before this ticket, both were rejected with `test_FracElement___call__`.

**Measured results.**

- Full gate wall time: 256 s. The baseline ran from 11 s to 148 s, beside the characterization (11 s to 115 s). The repo suite ran from 121 s to 256 s. `suite_run` reads the baseline only after its own run ends, so the baseline added no wait. Its cost is one more suite run of 137 s of sandbox time.
- The traces have no `finish_reason: "length"` and no `ERROR` span.
- A first run of the same case (trace `5edbd1558002ddc1e093f3e40108485e`, with the ID-only rule) accepted `rs_cos_sin` with the same 5 baseline failures. `dup_sqf_norm` stopped at the agent step limit in that run.
- A second run (trace `f759f781297264f91ad76edf08292b2a`) failed with `ContreeTransportError` (`ReadError`). The Mac slept during the run: the trace takes 20 min, and the script clock (`time.monotonic`, which stops in sleep on macOS) shows 168 s. This is not a code failure.
- `uv run pytest -q`: 397 passed, 17 deselected. New tests: the end-to-end Local tests (a red repo test does not reject a correct rewrite; a broken passing test still rejects it), the `gate_review` tests with a red baseline, a wrapper and a duplicate test with a red baseline, a wrapper reject test, a 13-case table for `suite_run`, an ID test for `pytest_result`, and a test that the baseline runs beside the characterization.

**Known limits.**

- Each review with candidates runs one more full repo suite, also when no rewrite needs it.
- A chained test command that stops early in both runs is not found.
- A test that fails only sometimes (a flaky test) can still reject a rewrite, or pass in the baseline and fail in the rewrite run.
- A test command that is not pytest gets no baseline: its failing runs reject the rewrite as before.
