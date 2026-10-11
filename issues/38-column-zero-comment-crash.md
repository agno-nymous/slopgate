# 38 — A comment at column 0 inside a method crashes `classify`

## Summary

- **Goal:** Stop the gate from crashing on a method that has a comment at the start of a line. Example: the commented-out line `#            self.best = None` inside `get_name`.
- **Checkable finish condition:** `classify` returns a result for that example, with no `IndentationError`. All 34 such functions from ticket 37 parse.
- **Evidence:** Before: the example raises `IndentationError: unexpected indent`. After: a new test passes on the example and on a method with a multi-line string, and `uv run pytest -q` passes.
- **Constraints:** Fix it once, with one helper in `slopgate/functions.py`, and use the helper everywhere the code dedents a function before it parses it. Do not change the text inside multi-line strings.

**Blocked by:** —

**Status:** ready-for-agent

**Type:** bug.

## Context

Ticket 37 found this bug. Some code has a comment at column 0 inside an indented method, for example a line of code that was commented out:

```python
class Prober:
    def get_name(self):
        if not self.best:
            self.get_confidence()
#            self.best = None
        return self.best.name
```

`textwrap.dedent` removes only the indentation that all lines share. The comment line has none, so `dedent` changes nothing. `ast.parse` then gets an indented `def` and raises `IndentationError: unexpected indent`. `kinds.measured` calls `nesting()` and `has_dead_code`, which both parse the dedented source, so `classify` crashes on the function.

Reproduced on 2026-10-09 with `kinds.measured` on the example above: `IndentationError unexpected indent (<unknown>, line 1)`.

The 12 SWE-bench Lite repos of ticket 37 have 34 such functions: 7 in the 8 repos of the clean set, 19 in matplotlib, and 9 in pylint. One example is `requests/packages/chardet/charsetgroupprober.py` `CharSetGroupProber.get_charset_name`. The benchmark leaves these functions out, so its numbers do not show the crash.

The same `textwrap.dedent` + `ast.parse` pattern is also in `slopgate/functions.py` (`structure_hash`, `complexity`, `nesting`) and in `slopgate/review.py`.

## Design

Dedent a function by the indentation of its `def` line (or its first decorator), not by the shared indentation of all lines. Remove that prefix from each line that starts with it. Leave the other lines as they are. A comment line keeps its text, and the parse no longer fails. Put the helper in `slopgate/functions.py`, and use it in each place that dedents a function before it parses it.

Do not change multi-line strings: a line inside a string that does not start with the prefix stays as it is.

## Acceptance

- [ ] `kinds.measured` and `classify` give a result for the example above, with no exception.
- [ ] Every caller in `slopgate/` that dedents a function before `ast.parse` uses the new helper.
- [ ] A test covers the example above and a method with a multi-line string.
- [ ] The 34 functions from ticket 37 parse with the helper.
- [ ] `uv run pytest -q` passes.

## Comments

### 2026-10-10 — the same bug crashes the whole review

A full-gate run on the held-out SWE-bench items of ticket 37 (16 items from django and sympy) found a larger effect. `index.build` calls `structure_hash` (`slopgate/functions.py`) on every function of the base commit. `structure_hash` parses `textwrap.dedent(source)`, so it raises `IndentationError: unexpected indent` on one function with a comment at column 0. `review` builds the index for each change to a module-level function. So the whole review crashes. It gives no result, not only a missed function.

In that run, 8 of 16 reviews crashed this way: 6 sympy items and 2 django items, each with a changed module-level function. Example: `sympy/ntheory/generate.py:prevprime` with an injected `lookup_table`.

The fix must also cover `structure_hash`. Do this ticket before ticket 10.
