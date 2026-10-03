# 03 — All in-place slop kinds and proof hardening

**What to build:** The gate handles every slop kind that is fixed inside one function, and it refuses to trust weak proof.

Nemotron Lightning classifies each statically flagged function as one of `nesting`, `redundant_check`, `swallowed_error`, `lookup_table`, `filler_comment`, `dead` (from a `vulture` hit), or "none". Bad JSON or an unknown kind counts as "none".

A rule check runs before any sandbox time is spent. It rejects a rewrite that does not parse, changes the signature, adds a class, or adds a function. When a rewrite fails its tests, Nemotron Ultra retries once and gets the failing output.

The proof rejects characterization tests that give different results on two runs of the original, and tests that miss a branch of the original function. Methods are rewritten in place and keep their indentation.

**Blocked by:** 01

**Status:** done

- [x] A fixture with one function per in-place kind produces one suggestion per kind, and each body names its kind.
- [x] A rewrite that changes the signature, adds a class, adds a function, or does not parse appears in `rejected` with the rule it broke, and no sandbox trial runs for it.
- [x] A function that uses `random` appears in `rejected` with reason containing "nondeterministic".
- [x] Characterization tests that leave a branch uncovered cause a rejection whose reason states the number of missed branches.
- [x] When the first rewrite fails, exactly one Ultra retry happens; when the retry also fails, the candidate is in `rejected`.
- [x] A method rewrite keeps its original indentation, and the suggested code parses in place.
- [x] A classifier reply of "none", bad JSON, or an unknown kind produces no suggestion and no rejection entry.

## Comments

- 2026-10-03: Built. Kinds live in one table (`KINDS` in `slopgate/review.py`) that maps each in-place kind to its rewrite instruction.
- Static pass: complexity >= 6, nesting > 2, or a vulture hit of type `unreachable_code` or `variable` inside the function. A vulture hit sets kind `dead` with no classifier call. Vulture's unused function, argument, and import hits are ignored; they would flag every new public function or force a signature change.
- Every flagged function is classified before the sandbox installs the repo, so an all-"none" review never installs.
- Nondeterminism has two layers: a static check for `random`, `secrets`, `uuid`, `time`, `datetime` (rejects before any test is written), and two runs of the characterization tests with `PYTHONHASHSEED=1` and `2` (a pass/fail split rejects as "nondeterministic").
- Known limit: a function that imports `from random import choice` and calls `choice()` passes the static check; only the double run can catch it.
- Known tension: a truly redundant `if` creates an unreachable branch, so the coverage rule rejects it. Redundant checks inside boolean expressions (`x is not None and x is not None`) are provable, since coverage.py does not measure short-circuit arcs.
- 24 offline tests pass; 8 code mutations (no vulture, accept unknown kind, skip random check, skip coverage, skip rule check, no retry, kind missing from body, skip double run) each fail at least one test. Live: 4 passed against the real sandbox.
- The first delegate stalled for 10 minutes while writing tests; the review code it left was complete and correct, and the remaining tests were written in the main session.
