# 54 — The gate flags slop in old lines that the pull request did not write

## Summary

- **Goal:** Flag only the slop that a pull request adds. Example: flask#5818 changed the signature and one condition of `Flask.update_template_context`. The gate flagged `nesting` on the function. The nested `for` / `if` / `for` block is old code that the pull request did not change.
- **Checkable finish condition:** A dry run on flask#5818 gives no candidate for the 4 functions whose nesting is old. An offline test shows that a function with old slop and a new one-line change gets no candidate, and that a function with new slop still gets one.
- **Evidence:** Before: ticket 49 (2026-10-11), 10 pull requests from 6 SWE-bench repositories. 6 of the 7 candidate runs had their slop only in old lines: flask#5818 (4 functions) and flask#4646 (`find_best_app`, 2 runs). Each candidate then cost one test agent run (60 s to 73 s, 87,000 to 169,000 tokens). After: the dry run and the test.
- **Constraints:** Use the static checks of `classify`; add no model call. Keep the duplicate and the wrapper paths as they are.

**Blocked by:** —

**Status:** done

## Context

`review` in `slopgate/review.py` takes each function that the diff touches (`diff.changed_functions`, from the merge-base). `classify` then checks the whole function at the head. It does not compare with the function at the merge-base. So a one-line change in an old function brings in all the old slop of that function.

On maintained code, this is the main source of candidates: in ticket 49, 5 of the 164 classified external functions were flagged, and the slop of all 5 was old.

## Design

Measure 2 options on the ticket 49 external pull requests and on the ticket 37 benchmark:

1. **New kinds only.** Run `classify` on the function at the merge-base too, when it exists there. Keep only the kinds that the head has and the merge-base does not have.
2. **Kinds on added lines only.** Keep a kind only when one of its reported lines is in the added lines of the diff.

Option 1 is simple and does not depend on line numbers. Option 2 also keeps new slop that is added to a function that already has the same kind.

## Acceptance

- [x] The Comments give the candidates of option 1 on the ticket 49 external pull requests, a by-hand reading for option 2 (`classify` has no lines for `nesting`), and the recall on the ticket 37 benchmark.
- [x] A dry run on flask#5818 gives no candidate for old nesting.
- [x] `uv run pytest -q` passes.

## Comments

### 2026-10-12 — built option 1

**What was built.** `review` in `slopgate/review.py` now classifies the function at the merge-base too. It keeps only the kinds that the head function has and the merge-base function lacks. `diff.old_function` finds the old function by path and qualname. If there is no old function (a new function, a new file, a renamed function, or a base file that does not parse), the gate keeps all kinds, as before. When the head function has no kind, the gate does not read the base file. The duplicate and wrapper paths do not change. No model call is added.

**Why option 1 and not option 2.** `classify` reports lines only for `redundant_check`. It reports no lines for `nesting`, `dead`, `lookup_table`, and `swallowed_error`. Option 2 would need new line reports for 4 kinds. Option 1 needs no line report, and it gave the result below.

**Worked example.** flask#5818 (base `adf36367`, head `6a649690`) changed the signature and one condition of `Flask.update_template_context`.

- Before: `classify` gave `nesting` for 4 functions of this pull request. Each one cost one agent run of 61 s to 73 s.
- After: `uv run --env-file .env slopgate review --repo <full clone of flask> --base adf36367 --head pr5818 --dry-run` printed no suggestion, no rejection, and no note. The run took 12 s.

**Measured results.**

External pull requests: the 10 pull requests of ticket 49 (229 changed functions).

| Option | Candidates (kind found) |
|---|---|
| Before (head only) | 6: 4 in flask#5818, 1 in flask#4646, 1 in django#21736 |
| Option 1 (new kinds only) | 1: the django#21736 test method (`dead`), a new function with no old version |

All 5 candidates that option 1 removes had the same kind (`nesting`) at the merge-base. The django#21736 function has no old version: its name is not in the base file (0 matches).

Option 2 cannot run as the ticket describes it. `classify` reports no lines for `nesting`. So I read the added lines of the 5 functions by hand and compared them with the nested block:

| Function | Added lines | Added line in the nested block? |
|---|---|---|
| `Flask.update_template_context` | signature, line 605 (`if ctx.has_request`) | no: the nested block starts at line 612 |
| `Flask.preprocess_request` | signature, line 1364 (`req = ctx.request`) | no: the nested blocks start at line 1367 |
| `Flask.process_response` | signature | no |
| `Flask.do_teardown_request` | signature, line 1425 (the outer `for` line) | yes: it is the first line of the nested block |
| `find_best_app` (flask#4646) | lines 55, 56, 74, 76, 82 (error message text) | yes: lines 74 and 76 are inside the nested block |

So an option 2 that counts any added line of the nested block would keep 2 of the 5 candidates. Both changes are edits of text or of a loop header, not new nesting. Option 1 removes all 5, and the reader of ticket 49 judged all 5 as old code. This is the reason to choose option 1. The cost: option 1 misses new slop that is added to a function that already has the same kind (see the known limits).

Recall on the ticket 37 benchmark (current `classify`; the base function is the clean source function of each injected item): 114 of 126 injected kinds are found before, and 114 of 126 after. `filler_comment` is not counted. No injected kind is also in its source function, so option 1 loses no recall. The 12 misses are the same before and after (`nesting` 2 of 26, `redundant_check` 10 of 24).

**Second sample (2026-10-12).** 50 more merged pull requests, 5 from each of 12 SWE-bench repositories: django, sympy, requests, flask, astropy, scikit-learn, sphinx, pytest, matplotlib, xarray, pylint, and seaborn. The pull requests are the 5 newest merged ones that change 1 to 12 `.py` files. 229 changed functions. `classify` gave no error.

| | Candidates |
|---|---|
| Before (head only) | 23: `nesting` 17, `dead` 6 |
| Option 1 | 3: `dead` 2, `nesting` 1 |

- 20 of the 23 had the same kind at the merge-base. They come from 14 pull requests, for example requests `_encode_files` in 4 pull requests, astropy `TableElement.parse` in 3, and sympy `_preprocess` in 1.
- 2 kept candidates are `dead` in new test functions (sympy#30711 `test_issue_30710`, sympy#30706 `test_issue_30705`). They have no old version, so they are new code. In a test file they get a note, not an agent run.
- 1 kept candidate is requests#7505 `RequestEncodingMixin._encode_params`: `nesting` at the head, none at the base. The pull request changed one condition from `isinstance(data, _SupportsRead)` to `_t.has_read(data)`. The `flattenable` check treats `isinstance` as a pure call and the new call as not pure, so the same shape became "flattenable". The old code already had this shape. This is a false new slop. It stays a known limit of option 1: a change inside a slop shape can flip the check.

Both samples together: 60 pull requests, 458 changed functions. Candidates fall from 29 to 4. 25 of 29 had the same kind at the merge-base. Of the 4 left, 3 are new functions (django#21736 and the 2 sympy test functions), and 1 is the `flattenable` flip above.

**Tests.** 3 new tests in `tests/test_review.py`: old slop with a one-line change gives no candidate and no model call; new slop in an existing function gives a note; a base file that does not parse does not hide the slop. `test_partly_changed_function_lands_in_followup_with_full_file` in `tests/test_duplicates.py` now starts from a clean base function, because its old setup had only old slop.

**Code review (Opus, `pstack:thermo-nuclear-code-quality-review`).**

1. A base file that does not parse made the head function an "internal error". Applied: `old_function` returns `None` on `SyntaxError` and `ValueError`. Test added.
2. `classify` of the base function ran once for each head kind. Applied: it runs once, and only when the head function has a kind.
3. Two functions with one qualname in the base file (a property getter and its setter, `@overload`) match the first one. Rejected: rare. It is a known limit.
4. The `(Function, text)` tuple that `old_function` returns. Rejected: it is only a style point.

**Known limits.**

- A pull request that adds a second slop of a kind that the function already has gets no candidate. Option 2 would keep it. The data has no such case.
- A function that the pull request renames or moves counts as new, so the gate keeps all its kinds.
- The sample is small: 6 candidates, and 5 of them come from 2 flask pull requests.
