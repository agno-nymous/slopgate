# 54 — The gate flags slop in old lines that the pull request did not write

## Summary

- **Goal:** Flag only the slop that a pull request adds. Example: flask#5818 changed the signature and one condition of `Flask.update_template_context`. The gate flagged `nesting` on the function. The nested `for` / `if` / `for` block is old code that the pull request did not change.
- **Checkable finish condition:** A dry run on flask#5818 gives no candidate for the 4 functions whose nesting is old. An offline test shows that a function with old slop and a new one-line change gets no candidate, and that a function with new slop still gets one.
- **Evidence:** Before: ticket 49 (2026-10-11), 10 pull requests from 6 SWE-bench repositories. 6 of the 7 candidate runs had their slop only in old lines: flask#5818 (4 functions) and flask#4646 (`find_best_app`, 2 runs). Each candidate then cost one test agent run (60 s to 73 s, 87,000 to 169,000 tokens). After: the dry run and the test.
- **Constraints:** Use the static checks of `classify`; add no model call. Keep the duplicate and the wrapper paths as they are.

**Blocked by:** —

**Status:** ready-for-agent

## Context

`review` in `slopgate/review.py` takes each function that the diff touches (`diff.changed_functions`, from the merge-base). `classify` then checks the whole function at the head. It does not compare with the function at the merge-base. So a one-line change in an old function brings in all the old slop of that function.

On maintained code, this is the main source of candidates: in ticket 49, 5 of the 164 classified external functions were flagged, and the slop of all 5 was old.

## Design

Measure 2 options on the ticket 49 external pull requests and on the ticket 37 benchmark:

1. **New kinds only.** Run `classify` on the function at the merge-base too, when it exists there. Keep only the kinds that the head has and the merge-base does not have.
2. **Kinds on added lines only.** Keep a kind only when one of its reported lines is in the added lines of the diff.

Option 1 is simple and does not depend on line numbers. Option 2 also keeps new slop that is added to a function that already has the same kind.

## Acceptance

- [ ] The Comments give the candidates of each option on the ticket 49 external pull requests, and the recall on the ticket 37 benchmark.
- [ ] A dry run on flask#5818 gives no candidate for old nesting.
- [ ] `uv run pytest -q` passes.

## Comments
