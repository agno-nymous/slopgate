# 48 — Compare the repo suite with a baseline run of the original code

## Summary

- **Goal:** The gate rejects a rewrite only for a repo test that the rewrite breaks. A test that also fails on the original code does not reject a rewrite.
- **Checkable finish condition:** A test makes a repo with one repo test that fails on the original code. A correct rewrite of another function gets its suggestion. A rewrite that breaks a test that passed before is rejected. `uv run pytest -q` passes.
- **Evidence:** On 2026-10-10, ticket 38 ran the full gate again on 9 SWE-bench items. 2 sympy rewrites passed their characterization tests and were rejected only because `sympy/polys/tests` failed. The same suite fails on the original code (see Context).
- **Constraints:** Run the baseline once for each review, not once for each rewrite. Keep the exit codes 0 and 5 as a pass.

**Blocked by:** —

**Status:** ready-for-agent

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

- [ ] A test with a repo test that fails on the original code: a correct rewrite gets its suggestion.
- [ ] A test with a rewrite that breaks a test that passed on the original code: the rewrite is rejected with "rewrite fails repo tests".
- [ ] `repo_suite`, `inline`, and `deduplicate` all use the baseline.
- [ ] The full gate on the 2 sympy items of ticket 38 (`dup_sqf_norm`, `rs_cos_sin`) no longer fails on `test_FracElement___call__`.
- [ ] `uv run pytest -q` passes.

## Comments
