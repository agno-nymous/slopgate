# 50 — The gate cannot fix `swallowed_error` around a call to other code

## Summary

- **Goal:** Do not run the test agent or the rewrite for a `swallowed_error` that no rewrite can fix. Example: `summary` in `slopgate/github.py` catches `Exception` around `llm.complete`, and sets the summary text to `""`. The fallback is deliberate: the summary is optional text. The fix text says "narrow each except to the exceptions that the code in its try block raises", and also "every input must still give the same result". For a call into another module, the model cannot know the exceptions, and a narrower except changes the result. So both rewrites fail.
- **Checkable finish condition:** On `summary` at `eb1c0ec` (PR #22) and at `8680b24` (PR #21), the gate gives a note and makes no agent run. On the ticket 37 held-out set, the true `swallowed_error` count does not fall by more than the count that the ticket 37 labels mark as deliberate.
- **Evidence:** Before: in the traces of ticket 49 (2026-10-11), 2 of 15 candidates were `summary` with `swallowed_error`. Both runs used about 120,000 tokens and 70 s, and both were rejected. In #21, Super widened the except to `BaseException`, and Ultra kept `except Exception`, so `leftover` rejected both ("rewrite leaves the slop"). In #22, the Ultra rewrite failed a test that patches `llm.complete` to raise `RuntimeError`. After: the note, with no agent run.
- **Constraints:** Decide the rule with counts from the ticket 37 benchmark, not from these 2 cases. Do not change Ruff's rule set without that measurement. Keep option A of ticket 36 (a handler that uses the caught error is deliberate).

**Blocked by:** —

**Status:** ready-for-agent

## Context

`classify` in `slopgate/kinds.py` maps Ruff `BLE001`, `E722`, `S110`, and `S112` to `swallowed_error`. Option A of ticket 36 drops `BLE001` when the handler body uses the caught error.

The `summary` handler does not use the error. It assigns a fallback value. The try block holds one call, into `slopgate/llm.py`, which calls the `openai` client. The model sees only the source of `summary`. So it cannot list the exceptions of that call.

## Design

Measure 2 options on the ticket 37 benchmark, with the precision and the recall of `swallowed_error`:

1. **Note only.** When every call in the try block goes to a name from another module, give a note and no rewrite.
2. **Deliberate fallback.** Drop `BLE001` when the handler only assigns constants or returns a constant (a fallback), as option A drops a handler that uses the error.

Choose by the counts. Then build the chosen option in `classify` or in `trial`.

## Acceptance

- [ ] A table in the Comments gives the precision and the recall of `swallowed_error` for the current rule and for each option, on the ticket 37 held-out set.
- [ ] `summary` at `eb1c0ec` gets a note and no agent run in a dry run.
- [ ] `uv run pytest -q` passes.

## Comments
