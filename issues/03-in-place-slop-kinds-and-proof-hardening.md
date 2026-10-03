# 03 — All in-place slop kinds and proof hardening

**What to build:** The gate handles every slop kind that is fixed inside one function, and it refuses to trust weak proof.

Nemotron Lightning classifies each statically flagged function as one of `nesting`, `redundant_check`, `swallowed_error`, `lookup_table`, `filler_comment`, `dead` (from a `vulture` hit), or "none". Bad JSON or an unknown kind counts as "none".

A rule check runs before any sandbox time is spent. It rejects a rewrite that does not parse, changes the signature, adds a class, or adds a function. When a rewrite fails its tests, Nemotron Ultra retries once and gets the failing output.

The proof rejects characterization tests that give different results on two runs of the original, and tests that miss a branch of the original function. Methods are rewritten in place and keep their indentation.

**Blocked by:** 01

**Status:** ready-for-agent

- [ ] A fixture with one function per in-place kind produces one suggestion per kind, and each body names its kind.
- [ ] A rewrite that changes the signature, adds a class, adds a function, or does not parse appears in `rejected` with the rule it broke, and no sandbox trial runs for it.
- [ ] A function that uses `random` appears in `rejected` with reason containing "nondeterministic".
- [ ] Characterization tests that leave a branch uncovered cause a rejection whose reason states the number of missed branches.
- [ ] When the first rewrite fails, exactly one Ultra retry happens; when the retry also fails, the candidate is in `rejected`.
- [ ] A method rewrite keeps its original indentation, and the suggested code parses in place.
- [ ] A classifier reply of "none", bad JSON, or an unknown kind produces no suggestion and no rejection entry.
