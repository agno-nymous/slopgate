# 03 — All in-place slop kinds and proof hardening

**What to build:** The gate handles every slop kind that is fixed inside one function. The gate refuses to trust weak proof.

Nemotron Lightning is the classifier. It classifies each statically flagged function as one of `nesting`, `redundant_check`, `swallowed_error`, `lookup_table`, `filler_comment`, `dead` (from a `vulture` hit), or "none". Bad JSON or an unknown kind counts as "none".

A rule check runs before the gate spends any sandbox time. The rule check rejects a rewrite that does not parse. It also rejects a rewrite that changes the signature, adds a class, or adds a function. When a rewrite fails its tests, Nemotron Ultra retries once. Nemotron Ultra gets the failing output.

The proof rejects two kinds of characterization tests. The first kind gives different results on two runs of the original function. The second kind misses a branch of the original function. The gate rewrites methods in place. A rewritten method keeps its indentation.

**Blocked by:** 01

**Status:** done

- [x] A fixture with one function for each in-place kind produces one suggestion for each kind. Each body names its kind.
- [x] A rewrite that changes the signature, adds a class, adds a function, or does not parse appears in `rejected` with the rule it broke. No sandbox trial runs for it.
- [x] A function that uses `random` appears in `rejected` with a reason that contains "nondeterministic".
- [x] Characterization tests that leave a branch uncovered cause a rejection. The reason states the number of missed branches.
- [x] When the first rewrite fails, exactly one Ultra retry happens. When the retry also fails, the candidate is in `rejected`.
- [x] A method rewrite keeps its original indentation. The suggested code parses in place.
- [x] A classifier reply of "none", bad JSON, or an unknown kind produces no suggestion and no `rejected` entry.

## Comments

- 2026-10-03: Built. The kinds live in one table (`KINDS` in `slopgate/review.py`). The table maps each in-place kind to its rewrite instruction.
- Static pass: A function is flagged when its complexity is >= 6, or its nesting is > 2, or it contains a vulture hit of type `unreachable_code` or `variable`. A vulture hit sets kind `dead` with no classifier call. The gate ignores the vulture hits for unused function, argument, and import. Those hits would flag every new public function or force a signature change.
- The gate classifies every flagged function before the sandbox installs the repo. A review where every function is "none" never installs.
- Nondeterminism has two layers. The first layer is a static check for `random`, `secrets`, `uuid`, `time`, and `datetime`. This check rejects before the gate writes any test. The second layer runs the characterization tests two times, with `PYTHONHASHSEED=1` and `2`. A split between pass and fail rejects the function as "nondeterministic".
- Known limit: A function can import `from random import choice` and call `choice()`. This function passes the static check. Only the double run can catch it.
- Known tension: A truly redundant `if` creates an unreachable branch. The coverage rule rejects it. Redundant checks inside boolean expressions (`x is not None and x is not None`) are provable. The reason is that coverage.py does not measure short-circuit arcs.
- 24 offline tests pass. 8 code mutations each fail at least one test. The mutations were: no vulture, accept unknown kind, skip random check, skip coverage, skip rule check, no retry, kind missing from body, and skip double run. Live: 4 passed against the real sandbox.
- The first delegate stalled for 10 minutes while it wrote tests. The review code that it left was complete and correct. The main session wrote the remaining tests.
