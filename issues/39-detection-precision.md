# 39 — Design: better detection for `redundant_check` and `nesting`; remove `filler_comment`

## Summary

- **Goal:** Remove the `filler_comment` kind from the gate. Make the detection of `redundant_check` and `nesting` more accurate on real code. Example: in `isatty` (astropy), Lightning missed a repeated `hasattr(file, 'isatty')` check in all 3 runs.
- **Checkable finish condition:** `filler_comment` is gone from the gate, the benchmark, and the tests. Each design question has an answer with a measurement on the ticket 37 benchmark. On the held-out set, the false-positive rate on clean functions goes down, and the 95% range of that difference is above 0. The recall on injected items does not fall by more than its range. `bench/results/detection.md` holds the new numbers.
- **Evidence:** Before (ticket 37): 21.7% of clean function runs got a false kind. Precision was 0.593 for `nesting`, 0.456 for `filler_comment`, and 0.462 for `redundant_check`. First live check in Comments: Super with thinking on gave precision 0.89 and recall 0.78 for `redundant_check`, against 0.46 and 0.50 for the gate now. After: the updated `bench/results/detection.md` (not done yet).
- **Constraints:** The user decided on 2026-10-09 to remove `filler_comment` and keep `redundant_check`. Blocked by ticket 37. The first measurements used the same labels that chose the checks, so confirm each result on new labelled functions before you build it. This ticket is a design first, then a build.

**Blocked by:** 37

**Status:** done

**Type:** design, then build.

## Context

Ticket 37 measured the detection on 200 clean functions and 134 injected functions from 12 SWE-bench Lite repos, 3 runs each. 21.7% of the clean function runs got a false kind. Three kinds have a precision or a recall below 0.8 (all items, 3 runs pooled):

| Kind | Precision | Recall | False-positive rate on clean functions |
|---|---|---|---|
| `nesting` | 0.593 | 1.0 | 0.090 |
| `filler_comment` | 0.456 | 0.892 | 0.135 |
| `redundant_check` | 0.462 | 0.476 | 0.023 |

The other 3 kinds (`swallowed_error`, `lookup_table`, `dead`) have a precision of 0.967 or more and a recall of 1.0.

`bench/results/detection.md` lists each false positive and each false negative. `bench/labels.json` gives the reason for each decision on real code.

### `nesting`

The detector counts every block (`if`, `for`, `while`, `try`, `with`, `match`). Depth more than 2 is slop. On real code, a person decided this for 33 functions:

| Depth | Slop | False positive |
|---|---|---|
| 3 | 4 | 21 |
| 4 | 3 | 3 |
| 5 or more | 2 | 0 |

Most false positives are a loop inside a `with` or a `try`, where each block does real work. Example: `DatabaseWrapper.check_constraints` in django (`with cursor` / `for table` / `for key column` / `for bad row`). The slop cases are nested `if` blocks that can become guard clauses or a `continue`.

A limit of 3 removes 21 false positives, but 16 of the 26 injected `nesting` items have depth 3, so the recall falls.

### `filler_comment`

Lightning reports comments that explain a step or give context. 62 of 73 functions on real code were false positives. Examples: `# bpo-23890: manually break a reference cycle`, `# type: ignore`, `# docstring inherited`, `# {rel_field: {pk: rel_obj}}`. The grounding check accepts each one, because it is a comment line of the function.

### `redundant_check`

Lightning misses clear cases. In `isatty` (astropy, transform), `if not (hasattr(file, 'isatty')):` comes directly after `if hasattr(file, 'isatty'): return file.isatty()`. All 3 runs missed it. The transform recall is 0.533.

Lightning can also quote almost the whole function as one evidence line. In `RequestEncodingMixin._encode_files` (requests), one evidence entry had 40 lines. The grounding check accepts it, because each line is in the source and one line has `if`. 7 evidence entries in the benchmark have more than 2 lines.

## Decision (2026-10-09)

The user decided:

- **Remove `filler_comment` from the gate.** A comment that restates code costs little, and the check gave the most false kinds (62 of 73 flagged functions on real code). The gate does not check comments.
- **Keep `redundant_check`.** A check that an earlier check already decides is real slop. Make its detection better. Its precision is 0.462 and its recall is 0.476.

So design question 2 is closed. The change removes `filler_comment` from `KINDS` and `RULES` in `slopgate/kinds.py`, from the `bench/` transforms and Nemotron injection, and from the tests.

## Design questions

1. `nesting`: count only nested `if` blocks (the shape that guard clauses fix)? Or use a limit of 3? Or count loops, `with`, and `try` with a lower weight?
2. `filler_comment`: drop pragmas (`# type: ignore`, `# noqa`, `# pragma`), `#:` attribute docs, and comments with a reference (URL, issue number) before the model call? Send only the comment and the next line to the model?
3. `redundant_check`: accept only evidence of one line? Give the model the earlier check and the repeated check as two fields? Ticket 36 design F tried two-line evidence with Lightning and did not get better results. Measure again on this benchmark.
4. Does Super do better than Lightning on these 3 kinds, at what cost?

## How to measure

Ticket 42 gives the context (the evals guide). These 3 rules apply to every answer above.

1. **Held-out set.** Before you try any change, split the ticket 37 items into a tuning set (60%) and a held-out set (40%), by function, with seed 39. An injected item goes to the same set as its source function. Choose the checks and the prompts only on the tuning set. Report the final numbers on the held-out set. Do not change a check after you see the held-out numbers. Label each new flag on the held-out set before you look at its score.
2. **A range for each number.** Report a 95% range for precision, recall, and the false-positive rate. Use a bootstrap over functions: resample whole functions, with their 3 runs together, 1,000 times, with a fixed seed. To compare the gate now with a new check, resample the same functions for both, and report the range of the difference. A change is an improvement only when that range is above 0.
3. **Model errors apart.** A Lightning or Super check that fails (no tool call, a cut-off reply, a request error) is a check error, not "kind not found". `classify` must report it as an error. The benchmark counts check errors for each kind, apart from the misses.

## Acceptance

- [x] `filler_comment` is removed from the gate, the benchmark, and the tests.
- [x] Each design question has an answer with a measurement on the ticket 37 benchmark.
- [x] The false-positive rate on clean functions goes down, and the recall on injected items does not fall by more than the measured noise (stability is 0.80 across 3 runs).
- [x] `bench/results/detection.md` is updated with the new numbers. The new held-out numbers are in `bench/results/detection-t39.md`. `detection.md` is the gate before ticket 39, scored again without `filler_comment`.
- [x] The final numbers come from the held-out set, and each number has a 95% range from a bootstrap over functions.
- [x] Each claimed improvement has a range of the difference that is above 0.
- [x] ~~`classify` reports a failed model check as an error, and `detection.md` counts the errors for each kind.~~ Not applicable: `classify` makes no model call now. `detection.md` lists the run errors (0 on the held-out set).

## Comments

### 2026-10-09 — first measurements (offline, on the ticket 37 labels and runs)

These checks use the existing labels and the 3 existing runs. They make no model call. The labels were also used to choose the checks, so confirm each result on new labelled functions before you build it.

**`nesting`.** Real code: 9 slop and 24 false positives. Injected: 26 items.

| Check | Real slop kept | Real false positives kept | Injected found |
|---|---|---|---|
| Now: all blocks, depth > 2 | 9 | 24 | 26 |
| All blocks, depth > 3 | 5 | 3 | 10 |
| Only `if` blocks, depth > 2 | 5 | 4 | 16 |
| No `for`, `while`, or `with`, depth > 2 | 6 | 7 | 19 |
| Depth > 2 and a Ruff fix rule (RET505-508, SIM102, PLR5501) | 2 | 2 | 18 |
| Depth > 2 and a shape that guard clauses fix (see below) | 6 | 3 | 13 |

The shape check (prototype) looks for 3 shapes: an `if`/`else` where one branch is only `return`, `raise`, `continue`, or `break`; an `if` that holds the rest of a loop or function body and has a block in it; an `if` whose body is only another `if`. It removes 21 of 24 false positives and keeps 6 of 9 real slop. It finds only 13 of 26 injected items, so the shape rules need more work.

**`filler_comment`.** Real code: 11 slop and 62 false positives.

- Drop pragmas, references, TODO markers, why-words, and inline comments before the check: false-positive runs go from 113 to 85. Real slop runs go from 28 to 26. Not enough.
- Word overlap between a comment and its next line: at a share of 0.5 or more, it keeps 8 of 62 false positives but only 3 of 11 real slop. Real filler comments paraphrase the code (`# locations of the blanks` above `blank_loc = ...`).
- Vote across the 3 runs (one result for each item): report the kind only when all 3 runs find it. Precision goes from 0.36 to 0.65, and recall from 1.0 to 0.76. This costs 3 Lightning calls for each comment check.

**`redundant_check`.** A vote across the 3 runs does not help: precision 0.40 to 0.55, recall 0.67 to 0.29.

**Not measured yet (needs live calls):** Super in place of Lightning; one yes/no call for each comment with the log-probability and a threshold (`llm.yes_probability`); a second model that checks each evidence line; real hard negatives from `bench/labels.json` as examples in the prompt; an AST check for the same condition after a guard that exits.

### 2026-10-09 — `redundant_check`: let the model think (live)

The same `CHECK_PROMPT` and `Check` tool as the gate, on 41 labelled functions (20 with real or injected `redundant_check`, 21 that Lightning flagged but a person labelled false positive), plus 60 unreviewed clean functions with 2 or more conditions. 2 tries for each function. `max_tokens` 8,192. The row for the gate now uses the 3 runs of ticket 37.

| Variant | TP | FP | FN | Precision | Recall | Flags on 60 clean functions | Cut off | Median time | Median output tokens |
|---|---|---|---|---|---|---|---|---|---|
| Lightning, thinking off (gate now) | 30 | 35 | 30 | 0.46 | 0.50 | 0 of 180 | 0 | — | — |
| Lightning, thinking on | 28 | 5 | 12 | 0.85 | 0.70 | 3 of 120 | 3 | 10.2 s | 738 |
| Super, thinking off | 31 | 6 | 9 | 0.84 | 0.78 | 0 of 120 | 2 | 1.3 s | 48 |
| Super, thinking on | 31 | 4 | 9 | 0.89 | 0.78 | 0 of 120 | 0 | 1.8 s | 126 |

- Super removes most false kinds and finds more real ones. The difference between Super with thinking off and on (6 against 4 false kinds) is small for 2 tries.
- Lightning with thinking on is better than with thinking off, but it is 8 times slower and was cut off 3 times.
- Limits: only 3 positives are real code; the other 17 are injected, and most have one shape. The 21 negatives are the cases that Lightning got wrong, so they are hard on purpose.

### 2026-10-10 — built: AST checks for `redundant_check` and `nesting`, `filler_comment` removed

**What was built.**

- `filler_comment` is removed from `slopgate/kinds.py`, `bench/transforms.py`, the Nemotron injection, the tests, `spec.md`, and `README.md`. `bench/score.py` ignores the old `filler_comment` data in the stored ground truth and runs.
- `redundant_check` is an AST check now: `repeated_checks` in `slopgate/kinds.py`. It reports an `if` whose test, or the negation of its test, is already known. A fact becomes known inside an `if` body, inside its `else`, and after an `if` that ends with `return`, `raise`, `continue`, or `break`. A fact is dropped when a statement assigns a name that it reads, or calls a function that is not `isinstance`, `hasattr`, `callable`, `len`, `type`, `any`, or `all`. Loop bodies, `except` handlers, and `match` cases start with no facts.
- `nesting` needs a depth of more than 2 and an `if` on the deep chain that a guard clause or a merged condition can make flat (`flattenable`). The 4 shapes: an `if`/`else` where one branch exits and the other holds a block; an `if` at the end of a function or loop body that holds a block; an `if` whose body is only another `if`; an `else: pass`.
- `classify` makes no model call now. Lightning runs only the hook's yes/no check.
- `leftover` rejects a rewrite only when the check still finds the kind in the rewrite.
- `bench/score.py`: `split` (60% tuning and 40% held-out, by function, seed 39), `compare` (a paired bootstrap over functions, 1,000 draws, seed 39). A kind found on the source of an injected item is scored on the source only.
- `python -m bench.detect run <name> <set>` and `report <name> <set>` write `runs-<name>.json` and `detection-<name>.md`.

**Answers to the design questions** (tuning set: 197 functions, 3 runs; real code means clean and source functions).

1. `nesting`: depth more than 2 and a flattenable `if`.

   | Check | Real slop kept (of 5) | Real false positives kept (of 13) | Injected found (of 16) |
   |---|---|---|---|
   | Now: all blocks, depth > 2 | 5 | 13 | 16 |
   | Depth > 3 | 2 | 2 | 6 |
   | Only `if` blocks, depth > 2 | 3 | 2 | 9 |
   | Depth > 2 and a flattenable `if` (chosen) | 3 | 2 | 16 |

2. `filler_comment`: removed (decision of 2026-10-09).
3. `redundant_check`: an AST check, with no model call. One-line evidence does not change Super (all its evidence has one line). With Lightning, it loses 3 true flags. Two fields (the earlier check and the repeated check) give precision 1.0 and recall 0.31 with Super.

   | Variant | TP | FP | FN | Precision | Recall | Real code: true / false flags |
   |---|---|---|---|---|---|---|
   | Lightning, thinking off (gate before) | 24 | 22 | 18 | 0.52 | 0.57 | 5 / 16 |
   | Super, thinking off | 31 | 11 | 9 | 0.74 | 0.78 | 2 / 9 |
   | Super, two fields | 13 | 0 | 29 | 1.0 | 0.31 | 0 / 0 |
   | AST check (chosen) | 33 | 0 | 9 | 1.0 | 0.79 | 3 / 0 |
   | AST check or Super | 34 | 11 | 6 | 0.76 | 0.85 | 3 / 9 |

   The user chose the AST check alone on 2026-10-10.
4. Super against Lightning: Super has fewer false flags (11 against 22) and more true flags (31 against 24). But on real code, Super gave 2 true and 9 false flags. Most of its true flags were on injected items. Super had 2 errors (no tool call after 38 s) in 366 calls. Cost of 366 Super calls: 298,014 input and 39,241 output tokens, 93 s with 8 threads.

**Held-out results** (`bench/results/detection-t39.md`: 132 functions, 188 items, 3 runs). The base is the gate before ticket 39 (`runs.json`, Lightning), without `filler_comment`. Each range is the 95% range of 1,000 bootstrap draws of whole functions.

| Kind | Precision: base, new, difference | Recall: base, new, difference | Clean FP rate: base, new, difference |
|---|---|---|---|
| `nesting` | 0.56, 0.923, +0.363 [0.174, 0.556] | 1.0, 0.857, -0.143 [-0.364, 0.0] | 0.113, 0.013, -0.1 [-0.169, -0.039] |
| `redundant_check` | 0.316, 1.0, +0.684 [0.333, 0.95] | 0.25, 0.625, +0.375 [0.0, 0.778] | 0.004, 0.0, -0.004 [-0.014, 0.0] |
| total | 0.746, 0.979, +0.233 [0.138, 0.342] | 0.882, 0.902, +0.02 [-0.078, 0.109] | 0.117, 0.013, -0.104 [-0.174, -0.042] |

- The clean FP rate falls from 0.117 to 0.013. The range of the difference does not include 0. Total precision goes up, and its range does not include 0.
- The total recall does not fall: +0.02 [-0.078, 0.109].
- The `nesting` recall falls by 0.143. The upper end of its range is 0.0, so the fall is at the edge of the noise. The 2 missed items are Nemotron injections (`AnchoredOffsetbox.draw`, `ASTDeclaration.__init__`) whose deep chain has no flattenable `if`.
- The held-out run gave no unlabelled flag, so no new label was needed. It gave 0 errors.
- The checks are deterministic: stability is 1.0 (it was 0.80). The median time for each function is 0.08 s, with no model call.
- A code review found false flags of `repeated_checks` on synthetic code (a call or a subscript store between the two checks). The fix was made after the first held-out run. The held-out numbers before and after the fix are the same.

**Worked example** (real output of `classify` on benchmark functions):

- `AccumulationBounds.intersection` (sympy): `if self.max <= other.max: return AccumBounds(other.min, self.max)` comes directly before `if self.max > other.max:`. `classify` gives `{'nesting': [], 'redundant_check': ['if self.max > other.max:']}`. The gate before gave only `nesting`.
- `DatabaseWrapper.check_constraints` (django, `with cursor` / `for table` / `for column` / `for row`): depth 4, no flattenable `if`. `classify` gives `{}`. The gate before gave `nesting`, which a person labelled as a false positive.

**Known limits.**

- The AST check finds only a repeated or negated test. It misses semantic repeats, for example `isinstance(x, (int, float)) and x is not None`. On the held-out set, it found 0 of 3 Nemotron `redundant_check` items. All 5 transform items are found, but the transform makes the shape that the check looks for.
- A call between the two checks drops all facts. So `if not uri.startswith('data:')` after a guard with a log call is not found.
- The gate cannot prove a `redundant_check` rewrite: the never-run branch fails the branch coverage rule. Ticket 43 holds this.
- Few positives are real code: 4 real `redundant_check` slop functions and 9 real `nesting` slop functions in the whole benchmark. The ranges are wide.
- Ticket 40 (limit the output tokens of `decide`) no longer applies to `classify`. It still applies to the duplicate verdict.
