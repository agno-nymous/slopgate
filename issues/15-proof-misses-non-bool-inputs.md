# 15 — Proof misses behavior on inputs the tests never try

**What to build:** Characterization tests prove a rewrite only on the inputs they try. On the demo pull request (https://github.com/agno-nymous/slopgate-demo/pull/1), Slopgate accepted this rewrite of `can_checkout`:

```python
def can_checkout(user_active, has_items, address_ok, paid):
    return user_active and has_items and address_ok and paid
```

The original nested `if` version always returns `True` or `False`. The rewrite returns its first falsy argument: `can_checkout(None, True, True, True)` returns `None` where the original returns `False`, and `can_checkout(True, True, True, 1)` returns `1` where the original returns `True`. The recorded tests passed because Super proposed only `True`/`False` inputs.

Make the proof cover this class of change. Options to compare: ask for at least one non-bool truthy and one non-bool falsy value for each parameter that is used only in a boolean test; or a static rule check that rejects a rewrite whose return expressions change from bool constants to a bare `and`/`or` chain.

**Blocked by:** 14

**Status:** done

- [x] The `can_checkout` demo rewrite above is rejected, or rewritten to return the same values (for example with `bool(...)`).
- [x] A rewrite that keeps bool results (for example `return bool(a and b)`) is still accepted.

## Comments
- 2026-10-03: Built as a static rule in `broken_rule` (`slopgate/review.py`), so it covers both test forms with no model call: when every `return` of the original gives a bool (a bool constant, a comparison, `not`, a call to `bool`/`isinstance`/`issubclass`/`callable`/`hasattr`/`all`/`any`, or an `and`/`or`/`if` expression built only from those; see `boolish`), every `return` of the rewrite must too. Otherwise the rewrite is rejected before any trial with "rule: returns a non-bool value where the original returns only bools". The rewrite prompt also states the rule, so Super writes `bool(...)` instead of losing the candidate.
- Test fixtures that returned a bare `and` chain for the bool-only `can_edit` now use `bool(...)`; the result-type check of ticket 14 moved to a function that returns a number (`log_value` rewritten to return `float(value)`).
- 5 new seam tests (3 rejected shapes, 3 accepted shapes, the prompt line; plus the moved type test); 7 mutations (rule off, rule on for every function, `and`/`or` with any bool part, `if` expression with either side, any call counted as bool, comparisons not counted, prompt line removed) each fail one.
- Live, real Super plus real sandbox, the demo pull request head before the applied suggestion (`441d235`), 3 runs: each produced `return bool(user_active and has_items and address_ok and paid)` for `can_checkout`, with 2 suggestions, 2 follow-ups, 0 rejected.
