# 04 — Duplicate detection in the gate

**What to build:** The gate finds a new module-level function that does the same job as a function already in the repo, and replaces it with a call to the existing helper.

`slopgate index` builds a function index at a git ref. For each function the index stores the structure hash and a CodeRankEmbed vector, computed on the local CPU. The index lives in `.slopgate/`.

At review time, the index is built at the base ref, so the pull request cannot match its own code:
1. An exact structure-hash match needs no model call.
2. Otherwise, vector search returns the top 5 functions above a score of 0.75.
3. Nemotron Super checks whether each candidate does the same job and states any behavior difference.
4. Proof is a differential test: the new function's characterization tests run against the existing helper.
5. The rewrite deletes the new function and changes its callers to call the helper.

The rewrite touches more than the diff, so it goes into `followup`.

**Blocked by:** 01

**Status:** done

- [x] `slopgate index --ref <ref>` writes the index to `.slopgate/`, and a second load returns the same functions and vectors.
- [x] A renamed exact copy of an existing helper is found with zero LLM calls.
- [x] A restructured copy (extra `None` check, temp variable) is found through vector search under the `live` marker.
- [x] When the copy raises a different error on `None` than the helper, the result is still reported, and its reason names the difference.
- [x] A candidate below the 0.75 floor causes no LLM call.
- [x] Methods are never treated as duplicates.
- [x] The accepted result is in `followup`, with the new function deleted and every caller calling the helper; the repo's tests pass on it.
- [x] Embedding uses the query prefix from the spec for queries and no prefix for indexed functions.

## Comments

- 2026-10-03: Built. New `slopgate/embed.py` (the only path to CodeRankEmbed), `slopgate/index.py` (index at `.slopgate/<commit sha>.json`, loaded instead of rebuilt), `structure_hash` in `slopgate/functions.py`, and the duplicate path in `slopgate/review.py`. The caller rewrite is mechanical (AST positions, no LLM); the repo's tests must pass on it.
- Followup now has one shape for every kind: `{"function", "kind", "reason", "files": {path: full new content}}`. Ticket 06 reads this shape.
- Dependency pins: CodeRankEmbed's remote code fails on sentence-transformers 6 / transformers 5 (`'NomicBertModel' object has no attribute 'get_extended_attention_mask'`), so `sentence-transformers<6`, `transformers<5`, and `einops` are pinned. First download plus load: 53 s; load from cache: 15 s. The default test run never loads the model (autouse fake in `tests/conftest.py`).
- Rename scope: loads are renamed in the defining file and in files with `from <module> import <name>`. Not handled: `import mod; mod.name()` and relative imports; the repo-test run rejects a rewrite that breaks them.
- Real CodeRankEmbed scores against the base helper `slugify` (measured 2026-10-03):

  | Head function | With query prefix | Without prefix |
  |---|---|---|
  | Renamed exact copy | 0.686 | 0.750 |
  | Restructured copy, renamed parameter | 0.681 | 0.744 |
  | Restructured copy, same parameter name (live fixture) | 0.787 | not measured |
  | Copy with TypeError on None | 0.811 | 0.874 |
  | Unrelated `can_edit` | 0.012 | 0.018 |
  | Unrelated `shipping_band` | 0.147 | 0.156 |

  With the spec's floor of 0.75 and the query prefix, a copy that renames its parameters is missed by vector search (exact copies are still caught by the hash). Open decision for the user: lower `DUPLICATE_SCORE` (unrelated pairs score at most 0.16 here; Nemotron Super still judges every candidate), or drop the prefix for code-to-code queries.
- 34 offline tests pass; 16 code mutations each fail at least one test (15 by the delegate, plus the changed-function exclusion added in review). Live: 5 passed.
- 2026-10-03: The user lowered `DUPLICATE_SCORE` from 0.75 to 0.6 after the score table above (spec updated to match). Nemotron Super still judges every candidate, so the floor only limits cost.
- 2026-10-03: Live check after the change: the restructured copy scores 0.79 with the helper's parameter name and 0.62 with a renamed parameter (both found now; the second was missed at 0.75). The 0.62 margin is narrow; ticket 10's benchmark should measure recall at this floor.
