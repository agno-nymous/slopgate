# 43 — The gate cannot prove a `redundant_check` rewrite

## Summary

- **Goal:** Let the gate prove and post a rewrite for a function whose only kind is `redundant_check`.
- **Checkable finish condition:** A function with a repeated check, for example `if x is None: return` followed by `if x is not None:`, gets a proven suggestion in an offline test with `fake_llm`.
- **Evidence:** Before: `characterize` rejects the function with "characterization tests miss branches: 1". After: the test above passes.
- **Constraints:** Found by ticket 39. Do not lower the branch rule for other branches. Only the arcs of the lines that `repeated_checks` reports can stay missed.

**Blocked by:** 39

**Status:** ready-for-agent

**Type:** bug.

## Context

Since ticket 39, `redundant_check` is an AST check (`repeated_checks` in `slopgate/kinds.py`). It reports an `if` whose condition an earlier check already decides. So one branch of that `if` can never run.

`characterize` in `slopgate/review.py` runs the characterization tests with `coverage run --branch`. It rejects the function when a branch of the function is missed ("characterization tests miss branches: N"). The never-run branch of a repeated check is always missed. So every function with only `redundant_check` is rejected, and the gate never posts a suggestion for this kind.

The ticket 39 build agent confirmed this with coverage.py: `if x is None: return` followed by `if x is not None:` gives one partial branch.

Before ticket 39, the Lightning check hid this problem. Most of its evidence lines were conditions that were not repeated, so both branches could run.

## Design

1. Pass the evidence lines of `redundant_check` to `characterize`.
2. Do not count a missed branch whose source line is one of these evidence lines.

## Acceptance

- [ ] An offline test with `fake_llm` shows a proven suggestion for a function with a repeated check.
- [ ] A missed branch on any other line still rejects the function.
