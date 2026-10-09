# 38 — A comment at column 0 inside a method crashes `classify`

**What to build:** The gate must handle a method that has a comment at column 0. Now `classify` raises `IndentationError` on it.

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
