# 19 — Several slop kinds per function

## Summary

- **Goal:** Let the gate fix all slop kinds of one function in one rewrite. Example: a function with deep nesting and a filler comment gets one suggestion that names `nesting` and `filler_comment`.
- **Checkable finish condition:** One function with several kinds gives one rewrite request with a numbered list of fixes, one proof, and one suggestion that names every kind. `uv run pytest -q` passes.
- **Evidence:** Before: the gate gave each function exactly one kind. After: ticket 36 built this in its stage 2 on 2026-10-09, with tests that replace the boxes in this ticket. The `SlopKinds` list gave 868 false kinds in the measurement of ticket 36, so `classify` now sends one `Check` call for each model kind.
- **Constraints:** Keep the `wrapper` and `duplicate` paths as they are. Send one rewrite with all instructions as a numbered list. The Ultra retry gets the same list. Entries in `rejected` and follow-ups hold a `kinds` field.

**Blocked by:** 18, 21, 36 (the design of 36 decides the input of `classify`, which this ticket changes)

**Status:** done

## Context

A function can have more than one problem, for example deep nesting and comments that only repeat the code. Today the gate gives each function exactly one kind. The loop in `review` (`slopgate/review.py`) picks the first match in this order:

1. `wrapper`: a one-use wrapper (ticket 05). It has its own fix path.
2. `duplicate`: a copy of an existing helper (ticket 04). It has its own fix path.
3. `dead`: vulture finds unused code (`has_dead_code`). The gate stops here, so a function with unused code and deep nesting gets only `dead`.
4. A kind from Lightning (`classify`), only when the function is complex (complexity >= 6) or deeply nested (nesting > 2). `classify` returns one name from `KINDS`, or `None`.

`KINDS` in `slopgate/review.py` maps each in-place kind to its rewrite instruction.

## Design

1. Add the model in `slopgate/review.py`:

   ```python
   class SlopKinds(BaseModel):
       """Report the slop kinds of the function."""

       kinds: list[Literal[*KINDS]] = Field(description="Every slop kind from the list that the function has. An empty list when the function has none.")
   ```

   Build the `Literal` from the keys of `KINDS`, so the schema allows only known names. Leave out `dead`: vulture finds it, not the model. Remove `none`: an empty list means the same.
2. `classify` calls `llm.decide(LIGHTNING, prompt, SlopKinds)` (ticket 18, a forced tool call) and returns a list of kinds. `None` from `decide` gives an empty list. The new `CLASSIFY_PROMPT` (the `{kinds}` lines come from `KINDS` without `dead`, one line per kind in the form `- name: instruction`):

   ````
   Name every slop kind that the Python function below has.

   Kinds:
   {kinds}

   Reply by calling the tool `SlopKinds`.

   ```python
   {source}
   ```
   ````

   A check on 2026-10-04 with a deeply nested function that has a filler comment returned `['nesting', 'filler_comment']` from Super (2 of 2) and from Lightning (1 of 2; the other reply also added `redundant_check`). Then no caller uses the `json` parameter of `complete` in `slopgate/llm.py`. Remove that parameter, and remove it from the fake in `tests/conftest.py`.
3. In the loop of `review`, keep `wrapper` and `duplicate` as they are. For all other functions, build one list:
   - add `dead` when `has_dead_code` is true;
   - add the kinds from `classify` when the function is complex or deeply nested.

   No kinds: skip the function.
4. Send one rewrite request with all instructions for the kinds, as a numbered list. Change the first line of `REWRITE_PROMPT` (ticket 21) from "Rewrite the Python function below. {instruction}" to:

   ```
   Rewrite the Python function below. Fix these problems:

   1. {instruction for kind 1}
   2. {instruction for kind 2}
   ```

   The rest of the prompt stays as ticket 21 sets it. The Ultra retry gets the same list.
5. The suggestion summary names all kinds, for example "Slopgate (`nesting`, `filler_comment`) rewrite of `shipping_label`".
6. A `rejected` entry and a follow-up entry hold the list of kinds in a field `kinds`. Update `publish` and `summary` in `slopgate/github.py`, which read `kind` today.

Tradeoff: one rewrite is proven once and makes one suggestion. When the proof fails, the gate cannot tell which kind caused the failure. Separate rewrites for each kind would need more model calls and sandbox runs, and their suggestions would overlap on the same lines.

## Acceptance

- [ ] A fake `decide` reply `SlopKinds(kinds=["nesting", "filler_comment"])` gives one rewrite request. The prompt has both instructions as a numbered list.
- [ ] A function with unused code and deep nesting gets `dead` plus the kinds from Lightning in one rewrite.
- [ ] A fake `decide` reply `SlopKinds(kinds=[])` with no dead code gives no candidate and no `rejected` entry.
- [ ] A kind name that is not in `KINDS` fails validation, so `decide` returns `None`. A test checks that the `SlopKinds` schema has an `enum` with exactly the keys of `KINDS` except `dead`.
- [ ] The suggestion body names every kind.
- [ ] `uv run pytest -q` passes.

## Comments

### 2026-10-09 — done in ticket 36

Ticket 36 built this ticket in its stage 2. The design changed: the `SlopKinds` list in step 1 gave 868 false kinds in the measurement of ticket 36 (Lightning names every kind). So `classify` sends one `Check` tool call for each model kind, and Ruff, vulture, and `nesting()` measure the other kinds. Steps 3 to 6 are built as written: one list of kinds for each function, one rewrite with a numbered list of fixes, the suggestion names every kind, and the entries have a field `kinds`. The acceptance boxes above refer to `SlopKinds`. The tests of ticket 36 stage 2 replace them.
