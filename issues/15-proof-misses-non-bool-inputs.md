# 15 — Proof misses behavior on inputs the tests never try

**What to build:** Characterization tests prove a rewrite only on the inputs they try. On the demo pull request (https://github.com/agno-nymous/slopgate-demo/pull/1), Slopgate accepted this rewrite of `can_checkout`:

```python
def can_checkout(user_active, has_items, address_ok, paid):
    return user_active and has_items and address_ok and paid
```

The original nested `if` version always returns `True` or `False`. The rewrite returns its first falsy argument: `can_checkout(None, True, True, True)` returns `None` where the original returns `False`, and `can_checkout(True, True, True, 1)` returns `1` where the original returns `True`. The recorded tests passed because Super proposed only `True`/`False` inputs.

Make the proof cover this class of change. Options to compare: ask for at least one non-bool truthy and one non-bool falsy value for each parameter that is used only in a boolean test; or a static rule check that rejects a rewrite whose return expressions change from bool constants to a bare `and`/`or` chain.

**Blocked by:** 14

**Status:** ready-for-agent

- [ ] The `can_checkout` demo rewrite above is rejected, or rewritten to return the same values (for example with `bool(...)`).
- [ ] A rewrite that keeps bool results (for example `return bool(a and b)`) is still accepted.

## Comments
