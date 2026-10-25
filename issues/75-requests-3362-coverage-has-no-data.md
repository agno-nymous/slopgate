# 75 — The gate gets no coverage data on `psf__requests-3362`

## Summary

- **Goal:** Find why `coverage run` gives no data for `requests/*.py` in the sandbox of `psf__requests-3362`, and fix it. Now the test agent cannot see its missed branches, and the gate rejects all 3 items of the instance.
- **Checkable finish condition:** A rerun of `psf__requests-3362` (see ticket 72, Comments) has no item with the reason `coverage has no data`.
- **Evidence:** Before: ticket 72 live run of 2026-10-25. 3 of 3 items ended as `step limit: coverage has no data for requests/adapters.py` (and `cookies.py`, `models.py`). Trace `417788f9` in the project `slopgate-bench`. After: the same run.
- **Constraints:** Keep the repo's own coverage settings. The cause is not known.

**Blocked by:** 72

**Status:** done

**Type:** bug.

## Context

The clone (`~/.cache/slopgate/bench/swebench/psf__requests-3362`) has no `.coveragerc`, `setup.cfg`, or `tox.ini`. So ticket 70 (a `.coveragerc` include pattern) does not explain it. The sandbox installs pytest 2.9 and Python 3.6 or older pins from 2016-06. The `gate.characterize` spans took 81 s to 86 s each.

## Design

1. Open the three `gate.characterize` spans of trace `417788f9` and read the agent commands. Find out which `requests` the tests import (the repo, or a copy in `site-packages`), and what `coverage debug config` shows.
2. Fix the cause. If the install is not editable, make the tests import the repo files.
3. Add an offline test if the fix is in code.

## Acceptance

- [x] The cause is written in Comments.
- [x] `psf__requests-3362` has no `coverage has no data` rejection.
- [x] `uv run pytest -q` passes.

## Comments

### 2026-10-25

**Cause.** Coverage works in the sandbox: `python -m coverage report -m` in trace `417788f9` shows data for `requests/*.py`. The failure is in the gate. The sandbox of `psf__requests-3362` runs Python 3.6, and the newest coverage for Python 3.6 is 6.2. The JSON report of coverage 6.2 has no `missing_branches` key (coverage 7 added it). The `MISSED` script read that key, raised `KeyError: 'missing_branches'`, and `check` turned the traceback into `coverage has no data for <path>`. The agent saw the same traceback and spent its steps on it, so all 3 items ended at the step limit. Ticket 70 is not the cause: the repo has no coverage configuration file. This defect affects every instance that installs coverage older than 7.

**What was built.** `MISSED` in `slopgate/review.py` now reads the missed branches through the coverage Python API: `Coverage().load()`, then `_analyze(path).missing_branch_arcs()`. Coverage 6.2 and 7.x give the same pairs. The command no longer uses `coverage json`. Before it reads the arcs, the script stops with `coverage has no data for <path>` unless the file is in `measured_files()` (an `assert` would vanish under `PYTHONOPTIMIZE`). Without this check, a missing `.coverage` file or a file in `omit` prints `[]`, and the gate reads that as "every branch is covered". A stop prints no JSON line, and `check` still gives `coverage has no data`. `bench/swebench.py` keeps `coverage json`: it reads only `executed_lines`, which coverage 6.2 has.

**Worked example.** `m.py` has `def f(x): if x > 1: return 1; return 2`, and the test calls `f(2)` only. I ran the final `MISSED` text with coverage 6.2 and 7.6.0:
- measured file: `[[2,4]]` on both versions (the branch from line 2 to line 4 is missed);
- file that the tests did not run: `AssertionError` on both;
- no `.coverage` data: `AssertionError` on both;
- `relative_files = True` with `parallel = True`, after `combine`: `[[2,4]]` on both.

Offline test `test_missed_script_reads_the_missed_branches_from_the_coverage_data` runs the script on real coverage data and checks the `[[2,4]]` output and the non-zero exit code after `coverage erase`. The existing test `test_coverage_that_omits_the_file_is_not_called_nondeterministic` caught the first version of the assert (`measured_files()` not empty): `_analyze` still reads an omitted file, so the reason became `miss branches: 8`. The check now tests that the file itself is measured.

**Measured.** Live run of the 3 items of `psf__requests-3362` (the `job` function of `bench/swebench.py`, trace `0257431f` in project `slopgate-bench`): 94.3 s, $0.073, 0 `ERROR` spans, 0 `finish_reason: length`, and no `coverage has no data` rejection. Before: 3 of 3 items. After, the items end for other reasons:
- `cert_verify:nesting` and `prepare_cookies:swallowed_error`: `rule: signature changed`;
- `merge_cookies:redundant_check`: a repo test fails on the rewrite.

`uv run pytest -q`: 490 passed, 17 deselected.

**Known limits.** `_analyze` is a private coverage method. It exists in coverage 6.2 and 7.6, and the public API has no call for missed branch arcs. A file in `[run] omit` of the repo coverage configuration gives `coverage has no data` as before. The offline test runs on the coverage of the dev environment (7.x), not on 6.2: the 6.2 check was by hand. When `check` gives `coverage has no data`, it drops the traceback, and that hid this cause until the trace was read. The stored benchmark results and the report still hold the old rejections for this instance. The full rerun (ticket 10) replaces them.
