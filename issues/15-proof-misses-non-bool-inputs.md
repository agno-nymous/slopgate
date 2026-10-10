# 15 — Proof misses behavior on inputs that the tests never try

## Summary

- **Goal:** Stop the gate from accepting a rewrite that returns other values than the original. Example: on demo PR #1, the rewrite `return user_active and has_items and address_ok and paid` gave `None` for `can_checkout(None, True, True, True)`, and the original gave `False`.
- **Checkable finish condition:** The gate rejects the `can_checkout` demo rewrite, or the rewrite uses `bool(...)`. The gate still accepts `return bool(a and b)`.
- **Evidence:** Before: the recorded tests passed because Super tried only `True` and `False`. After: a static rule rejects the rewrite, 5 new offline tests passed, and 7 planted bugs each failed one test. 3 live runs on the demo PR head gave `bool(...)` and 0 rejected.
- **Constraints:** The fix compared two options: ask for non-bool test inputs, or add a static rule check. The built fix is the static rule in `broken_rule` in `slopgate/review.py`. It makes no model call.

**Blocked by:** 14

**Status:** done

## Details

Characterization tests (tests that record what the old code does) prove a rewrite only on the inputs that they try. The demo pull request is at https://github.com/agno-nymous/slopgate-demo/pull/1. On that pull request, Slopgate accepted this rewrite of `can_checkout`:

```python
def can_checkout(user_active, has_items, address_ok, paid):
    return user_active and has_items and address_ok and paid
```

The original version has nested `if` statements. It always returns `True` or `False`. The rewrite returns its first falsy argument. `can_checkout(None, True, True, True)` returns `None`. The original returns `False`. `can_checkout(True, True, True, 1)` returns `1`. The original returns `True`. The recorded tests passed because Super proposed only `True` and `False` inputs.

Make the proof cover this class of change. Compare these options. Option 1: for each parameter that only a boolean test uses, ask for at least one non-bool truthy value and one non-bool falsy value. Option 2: add a static rule check. The check rejects a rewrite when the return expressions change from bool constants to a bare `and`/`or` chain.

- [x] The gate rejects the `can_checkout` demo rewrite above, or the rewrite returns the same values (for example with `bool(...)`).
- [x] The gate still accepts a rewrite that keeps bool results (for example `return bool(a and b)`).

## Comments
- 2026-10-03: The change is a static rule in the function that checks rules on a rewrite (`broken_rule` in `slopgate/review.py`). The rule covers both test forms and makes no model call. Each `return` of the original can give a bool. A bool is a bool constant, a comparison, `not`, a call to `bool`, `isinstance`, `issubclass`, `callable`, `hasattr`, `all`, or `any`, or an `and`/`or`/`if` expression built only from these. The function `boolish` makes this check. In that case, each `return` of the rewrite must also give a bool. If not, the gate rejects the rewrite before any trial. The reason is "rule: returns a non-bool value where the original returns only bools". The rewrite prompt also states the rule. Super then writes `bool(...)`, and the gate does not lose the candidate.
- Some test fixtures returned a bare `and` chain for the bool-only function `can_edit`. These fixtures now use `bool(...)`. The result-type check of ticket 14 moved to a function that returns a number. That function is `log_value`, and the rewrite returns `float(value)`.
- The change has 5 new seam tests: 3 rejected shapes, 3 accepted shapes, the prompt line, and the moved type test. There were 7 mutations. Each mutation fails one test. The mutations are: rule off, rule on for every function, `and`/`or` with any bool part, `if` expression with either side, any call counted as bool, comparisons not counted, and prompt line removed.
- Live test with real Super and a real sandbox. The input was the head of the demo pull request before the applied suggestion (`441d235`). There were 3 runs. Each run produced `return bool(user_active and has_items and address_ok and paid)` for `can_checkout`. Each run had 2 suggestions, 2 follow-ups, and 0 rejected.
