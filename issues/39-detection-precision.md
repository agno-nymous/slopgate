# 39 — Design: better detection for `redundant_check` and `nesting`; remove `filler_comment`

## Summary

- **Goal:** Remove the `filler_comment` kind from the gate. Make the detection of `redundant_check` and `nesting` more accurate on real code. Example: in `isatty` (astropy), Lightning missed a repeated `hasattr(file, 'isatty')` check in all 3 runs.
- **Checkable finish condition:** `filler_comment` is gone from the gate, the benchmark, and the tests. Each design question has an answer with a measurement on the ticket 37 benchmark. The false-positive rate on clean functions goes down. The recall on injected items does not fall by more than the measured noise (stability is 0.80 across 3 runs). `bench/results/detection.md` holds the new numbers.
- **Evidence:** Before (ticket 37): 21.7% of clean function runs got a false kind. Precision was 0.593 for `nesting`, 0.456 for `filler_comment`, and 0.462 for `redundant_check`. First live check in Comments: Super with thinking on gave precision 0.89 and recall 0.78 for `redundant_check`, against 0.46 and 0.50 for the gate now. After: the updated `bench/results/detection.md` (not done yet).
- **Constraints:** The user decided on 2026-10-09 to remove `filler_comment` and keep `redundant_check`. Blocked by ticket 37. The first measurements used the same labels that chose the checks, so confirm each result on new labelled functions before you build it. This ticket is a design first, then a build.

**Blocked by:** 37

**Status:** ready-for-agent

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

## Acceptance

- [ ] `filler_comment` is removed from the gate, the benchmark, and the tests.
- [ ] Each design question has an answer with a measurement on the ticket 37 benchmark.
- [ ] The false-positive rate on clean functions goes down, and the recall on injected items does not fall by more than the measured noise (stability is 0.80 across 3 runs).
- [ ] `bench/results/detection.md` is updated with the new numbers.

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
