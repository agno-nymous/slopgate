# 63 — CrossHair as a second equivalence check

## Summary

- **Goal:** Find out if CrossHair (`crosshair diffbehavior`) can reject a rewrite that changes behavior. CrossHair is a symbolic execution tool for Python. It uses an SMT solver to search for an input on which two functions give different results. It needs no model call.
- **Checkable finish condition:** The Comments give the result of CrossHair on the PR #23 rewrite of `transformed`, on the rewrites in the local Phoenix traces, and on boundary mutants.
- **Evidence:** See the Comments of 2026-10-17.
- **Constraints:** Do not add a model call. Do not change the gate in this ticket.

**Blocked by:** —

**Status:** wontfix

**Type:** measurement.

## Context

Ticket 51 (The proof accepts a rewrite that changes a comparison) found a rewrite that passed the proof and changed behavior: `len(found) == count` became `len(found) >= count` in `transformed` (PR #23). The Opus review in ticket 51 did not recommend symbolic checks, because old SWE-bench code mostly has no type hints. That was an inference, not a measurement. This ticket measures it.

## Comments

### 2026-10-17: measurement

**Setup.** CrossHair 0.0.111 on Python 3.12, in a scratch environment. Each run used `crosshair diffbehavior <original> <rewrite> --per_condition_timeout 10`. The scripts and outputs are scratch files. They are not in the repository.

**1. PR #23, `transformed`.**

| Setup | Result | Time |
|---|---|---|
| Callees replaced by plain stubs, typed parameters | Difference found: `count=0` gives `[7645, 1770]` on the original and `[7645]` on the rewrite | 20 s |
| Real module at `0a8887b` with the real callees | "No differences found" after 2,263 iterations | 60 s |

With the real callees, no symbolic input gets through `accept`, because `accept` reads files and parses code. The gate has no stubs. Stubs need hand work or a model call.

**2. Rewrites from the local Phoenix traces.** The ticket 41 benchmark has no rewrites, so this ticket used the 150 rewrites in Phoenix: 122 from the ticket 51 corpus (`t51.rewrite`), 18 from `gate.rewrite`, and 10 from `gate.retry`. Each pair ran as a module with only the two functions, with no imports of the repo.

| Result | Count |
|---|---|
| Does not load (a name in an annotation or an import is missing) | 36 |
| Does not parse | 2 |
| "No differences found" (a bounded search, not a proof) | 84 |
| Difference reported | 28 |

Of the 28 differences, 27 are artifacts: a missing global name, or a symbolic `self` that has no attributes, so one side raises an exception. 1 is a real change. `get_fontext_synonyms` (matplotlib, `lookup_table`) returns `None` for an unknown extension, and the rewrite returns `[]` (`mapping.get(fontext, [])`). Ticket 51's comparison rule does not reject this rewrite. The corpus rewrites did not go through the sandbox proof, so it is not known whether the characterization tests would kill it.

A filter that counts only a difference where both sides return a value keeps the real one and removes all 27 artifacts.

**3. Boundary mutants.** 200 mutants of 55 corpus functions that load (`==` to `>=`, `<` to `<=`, `>` to `>=`, `<=` to `<`, `>=` to `>`, `!=` to `<`):

| Result | Count |
|---|---|
| Difference where both sides return a value | 20 (10%) |
| Difference where one side raises | 60 |
| "No differences found" | 120 |

This is the result on untyped code without its imports. It is not the general rate of CrossHair. In the sandbox, the repo imports would load, but the inputs stay untyped.

**Decision: wontfix.** CrossHair finds the PR #23 change only with stubs. It misses the change with the real callees. On real code it does not load 24% of the pairs, and it catches 10% of the boundary mutants with a clean difference. Ticket 51 option 1 (the comparison rule) rejects the PR #23 rewrite with no runtime cost.

**Follow-up idea, not a ticket yet.** An AST rule could reject a `lookup_table` rewrite that changes the implicit `return None` at the end of an if-chain into `.get(key, default)` with a default other than `None`. 1 of the 122 corpus rewrites does this.
