# 72 — The benchmark test command breaks pytest 2.9

## Summary

- **Goal:** Make the gate review `psf__requests-3362` in the SWE-bench benchmark. The environment builds, but the test command that `select` writes into `.slopgate.toml` carries `--continue-on-collection-errors`. pytest 2.9 rejects this flag, so the collection check fails and the gate posts `NO_ENVIRONMENT` for all 3 items.
- **Checkable finish condition:** After `python -m bench.swebench run` and `report`, `psf__requests-3362` has no `no_environment` item.
- **Evidence:** Before: ticket 67 benchmark of 2026-10-21. All 3 `infrastructure_errors` are `psf__requests-3362`, with `unrecognized arguments: --continue-on-collection-errors`. After: the next benchmark report.
- **Constraints:** Do not change the production default test command. `collect_error` already retries without the flag for the commands that it builds itself.

**Blocked by:** 67

**Status:** done

**Type:** bug.

## Context

`bench/swebench.py` line 90 (`PYTEST`) and line 422 put `--continue-on-collection-errors` in the test command of each instance. The flag exists since pytest 3.0. The gate runs this command as it is, so an older pytest fails.

## Design

1. The benchmark drops the flag for instances where the pinned pytest is older than 3.0. The gate stays as it is.
2. Add an offline test.

## Acceptance

- [x] `psf__requests-3362` reaches the characterization step in the benchmark.
- [x] `uv run pytest -q` passes.

## Comments

### 2026-10-25

**What was built.** `bench/swebench.py` has a new function, `gate_test_command(instance_id, repo)`. `select` calls it to write the `test` line of `.slopgate.toml`. It leaves out `--continue-on-collection-errors` for the instances in `OLD_PYTEST` (now only `psf__requests-3362`). All other instances keep the flag. The gate is unchanged. I chose the benchmark fix and not a gate retry: a retry in the gate would edit a user's own test command, and only one instance needs the change.

**Cause.** The hidden-test runs use the pytest of the SWE-bench image, which accepts the flag (`base_pass` is not empty). The gate sandbox pins the dependencies to the commit date (2016-06) and installs pytest 2.9. `collect_error` retries without the flag only when the flag comes from `collect_error` itself. Here the flag was already in the test command, so the retry changed nothing.

**Worked example.** Offline test `test_gate_test_command_drops_the_collection_flag_for_pytest_before_3`:
- `gate_test_command("psf__requests-1963", "psf/requests")` has the flag.
- `gate_test_command("psf__requests-3362", "psf/requests")` returns `python -m pytest -q -rfE -p no:cacheprovider tests`.

Live run (`select` and `run` for this one instance, on copies of the result files in a scratch folder; then I copied the new instance record, its 3 items, and its run into `bench/results/swebench/`): the gate gave no `no_environment` item. Before, all 3 items had `unrecognized arguments: --continue-on-collection-errors`. After, the 3 items reached the characterization step and ended as `rejected`, reason `step limit: coverage has no data for requests/<file>.py`. The run took 111.7 s and cost $0.0887.

**Measured.** `uv run pytest -q`: 489 passed, 17 deselected. Phoenix trace `417788f9` (project `slopgate-bench`): no `ERROR` span, no `finish_reason: length`, `sandbox.prepare` 17.4 s. The 3 `gate.characterize` spans took 81 s to 86 s.

**Stored results.** `select` skips a stored instance, and `clone_at` rebuilds the clone. The live run rebuilt the clone of `psf__requests-3362`, so the old stored head `d3282776` no longer exists (the Opus review found this). I replaced the instance record, its 3 items, and its entry in `runs.json` with the new ones (head `2b471e02`). The items changed: `cert_verify:nesting`, `merge_cookies:redundant_check`, and `prepare_cookies:swallowed_error` replace `request_alt:duplicate`, `Retry._is_read_error:dead`, and `_unquote_unreserved_impl:wrapper`. I updated the kind counts in `groundtruth.meta.json` and the cost in `runs.meta.json`.

**Not done.** I did not rerun the full benchmark. `swebench.md` and `swebench.json` (the report) still hold the old numbers for this instance. The full rerun and `report` belong to ticket 73 (its open box).

**New finding.** The 3 items now end at the step limit with `coverage has no data` (ticket 75). Ticket 70 has the same message, but this repo has no coverage configuration file.
