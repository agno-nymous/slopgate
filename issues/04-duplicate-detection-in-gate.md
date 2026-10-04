# 04 — Duplicate detection in the gate

**What to build:** The gate finds a new module-level function that does the same job as a function that is already in the repo. The gate replaces the new function with a call to the existing helper.

The command `slopgate index` builds a function index at a git ref. For each function, the index stores the structure hash and a CodeRankEmbed vector. The gate computes both on the local CPU. The index lives in `.slopgate/`.

At review time, the gate builds the index at the base ref. The pull request cannot match its own code. The steps are:
1. An exact structure-hash match needs no model call.
2. Otherwise, vector search returns the top 5 functions above a score of 0.75.
3. Nemotron Super checks whether each candidate does the same job. Nemotron Super states any difference in behavior.
4. The proof is a differential test. The characterization tests of the new function run against the existing helper.
5. The rewrite deletes the new function. The rewrite changes the callers of the new function to call the helper.

The rewrite changes more than the diff. For this reason, the rewrite goes into `followup`.

**Blocked by:** 01

**Status:** done

- [x] The command `slopgate index --ref <ref>` writes the index to `.slopgate/`. A second load returns the same functions and vectors.
- [x] The gate finds a renamed exact copy of an existing helper with zero LLM calls.
- [x] Vector search finds a restructured copy (extra `None` check, temp variable) under the `live` marker.
- [x] The copy can raise a different error on `None` than the helper. In this case, the gate still reports the result. The reason names the difference.
- [x] A candidate below the 0.75 floor causes no LLM call.
- [x] The gate never treats methods as duplicates.
- [x] The accepted result is in `followup`. The new function is deleted, and every caller calls the helper. The tests of the repo pass on the result.
- [x] Embedding uses the query prefix from the spec for queries. Embedding uses no prefix for indexed functions.

## Comments

- 2026-10-03: Built. The new file `slopgate/embed.py` is the only path to CodeRankEmbed. The new file `slopgate/index.py` writes the index to `.slopgate/<commit sha>.json`, and the gate loads this file instead of a rebuild. The function `structure_hash` in `slopgate/functions.py` computes the structure hash. The duplicate path is in `slopgate/review.py`. The caller rewrite is mechanical. It uses AST positions and no LLM. The tests of the repo must pass on the rewrite.
- Followup now has one shape for every kind: `{"function", "kind", "reason", "files": {path: full new content}}`. Ticket 06 reads this shape.
- Dependency pins: The remote code of CodeRankEmbed fails on sentence-transformers 6 and transformers 5 (`'NomicBertModel' object has no attribute 'get_extended_attention_mask'`). For this reason, the pins are `sentence-transformers<6`, `transformers<5`, and `einops`. The first download plus load took 53 s. A load from cache took 15 s. The default test run never loads the model. An autouse fake in `tests/conftest.py` replaces it.
- Rename scope: The gate renames loads in the defining file. It also renames loads in files with `from <module> import <name>`. The gate does not handle `import mod; mod.name()` or relative imports. The repo-test run rejects a rewrite that breaks them.
- Real CodeRankEmbed scores against the base helper `slugify` (measured 2026-10-03):

  | Head function | With query prefix | Without prefix |
  |---|---|---|
  | Renamed exact copy | 0.686 | 0.750 |
  | Restructured copy, renamed parameter | 0.681 | 0.744 |
  | Restructured copy, same parameter name (live fixture) | 0.787 | not measured |
  | Copy with TypeError on None | 0.811 | 0.874 |
  | Unrelated `can_edit` | 0.012 | 0.018 |
  | Unrelated `shipping_band` | 0.147 | 0.156 |

  The spec sets a floor of 0.75. With this floor and the query prefix, vector search misses a copy that renames its parameters. The hash still catches exact copies. Open decision for the user: Lower `DUPLICATE_SCORE`. Unrelated pairs score at most 0.16 here, and Nemotron Super still judges every candidate. The other option is to drop the prefix for code-to-code queries.
- 34 offline tests pass. 16 code mutations each fail at least one test (15 by the delegate, plus the changed-function exclusion that was added in review). Live: 5 passed.
- 2026-10-03: The user lowered `DUPLICATE_SCORE` from 0.75 to 0.6 after the score table above. The spec is updated to match. Nemotron Super still judges every candidate. The floor only limits cost.
- 2026-10-03: Live check after the change: The restructured copy scores 0.79 with the parameter name of the helper. It scores 0.62 with a renamed parameter. The gate now finds both copies. The gate missed the second copy at 0.75. The margin of 0.62 is narrow. The benchmark in ticket 10 must measure recall at this floor.
