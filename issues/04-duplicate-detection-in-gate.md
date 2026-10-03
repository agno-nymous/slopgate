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

**Status:** ready-for-agent

- [ ] `slopgate index --ref <ref>` writes the index to `.slopgate/`, and a second load returns the same functions and vectors.
- [ ] A renamed exact copy of an existing helper is found with zero LLM calls.
- [ ] A restructured copy (extra `None` check, temp variable) is found through vector search under the `live` marker.
- [ ] When the copy raises a different error on `None` than the helper, the result is still reported, and its reason names the difference.
- [ ] A candidate below the 0.75 floor causes no LLM call.
- [ ] Methods are never treated as duplicates.
- [ ] The accepted result is in `followup`, with the new function deleted and every caller calling the helper; the repo's tests pass on it.
- [ ] Embedding uses the query prefix from the spec for queries and no prefix for indexed functions.
