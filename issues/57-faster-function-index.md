# 57 — Building the function index takes more than 80 s on a large repository

## Summary

- **Goal:** Build the function index of a commit in a few seconds. Example: on sympy#30301, `gate.index` took 83 s. The gate then had not yet started one test.
- **Checkable finish condition:** `gate.index` on sympy#30301 takes less than 20 s in a traced dry run, and the duplicate results are the same as before.
- **Evidence:** Before: ticket 49 (2026-10-11): `gate.index` took 82 s and 83 s on sympy, and 163 s on django (a blob-less clone). On one sympy commit (1,602 files, 35,837 functions), one `git show` per file took 21.5 s, parsing took 3.2 s, and `structure_hash` took 10.7 s. One `git cat-file --batch` read all 1,602 files in 0.10 s. After: the traced dry run.
- **Constraints:** Keep the index format of `.slopgate/<sha>.json`. Keep the duplicate results the same.

**Blocked by:** —

**Status:** ready-for-agent

## Context

`review` in `slopgate/review.py` calls `index.build` 2 times: at the merge-base and at the head. The head index is used only for the set of `(path, qualname)`, so its hashes are not needed. `index.build` reads each file with its own `git show` process.

## Design

1. Read all files of a commit with one `git cat-file --batch` process.
2. At the head, collect only `(path, qualname)`, with no `structure_hash`.
3. Measure each step on the sympy commit, and record the times in the Comments.

## Acceptance

- [ ] The Comments give the time of each step before and after.
- [ ] `gate.index` on sympy#30301 takes less than 20 s.
- [ ] `uv run pytest -q` passes.

## Comments
