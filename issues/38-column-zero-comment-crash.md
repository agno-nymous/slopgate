# 38 — A comment at column 0 inside a method crashes `classify`

## Summary

- **Goal:** Stop the gate from crashing on a method that has a comment at the start of a line. Example: the commented-out line `#            self.best = None` inside `get_name`.
- **Checkable finish condition:** `classify` returns a result for that example, with no `IndentationError`. All 34 such functions from ticket 37 parse.
- **Evidence:** Before: the example raises `IndentationError: unexpected indent`. After: a new test passes on the example and on a method with a multi-line string, and `uv run pytest -q` passes.
- **Constraints:** Fix it once, with one helper in `slopgate/functions.py`, and use the helper everywhere the code dedents a function before it parses it. Do not change the text inside multi-line strings.

**Blocked by:** —

**Status:** done

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

- [x] `kinds.measured` and `classify` give a result for the example above, with no exception.
- [x] Every caller in `slopgate/` that dedents a function before `ast.parse` uses the new helper.
- [x] A test covers the example above and a method with a multi-line string.
- [x] The 34 functions from ticket 37 parse with the helper.
- [x] `uv run pytest -q` passes.

## Comments

### 2026-10-10 — the same bug crashes the whole review

A full-gate run on the held-out SWE-bench items of ticket 37 (16 items from django and sympy) found a larger effect. `index.build` calls `structure_hash` (`slopgate/functions.py`) on every function of the base commit. `structure_hash` parses `textwrap.dedent(source)`, so it raises `IndentationError: unexpected indent` on one function with a comment at column 0. `review` builds the index for each change to a module-level function. So the whole review crashes. It gives no result, not only a missed function.

In that run, 8 of 16 reviews crashed this way: 6 sympy items and 2 django items, each with a changed module-level function. Example: `sympy/ntheory/generate.py:prevprime` with an injected `lookup_table`.

The fix must also cover `structure_hash`. Do this ticket before ticket 10.

### 2026-10-10 — done

**What was built.**

- `slopgate/functions.py` has a new helper, `dedent`. It takes the indentation of the first line that is not blank, and removes that prefix from each line that starts with it. A line with less indentation stays as it is. Examples are a comment at column 0 and a line inside a multi-line string.
- All 10 `textwrap.dedent` calls in `slopgate/` now use `dedent`: `structure_hash`, `complexity`, and `nesting` in `functions.py`; `has_dead_code`, `repeated_checks`, and `flattenable` in `kinds.py`; `same_code`, `characterize`, and the two calls in `trial` in `review.py`. `bench/` is not changed, because its function filter defines the benchmark set of ticket 37.
- The scan of all 12 repos found two more causes of the same `index.build` crash. The user approved a fix for both in this ticket:
  - **Backslash continuation into a comment.** The last statement of a function can end in `\`, and the next line can hold only a comment. `parse` cut the function at `end_lineno`, so the source ended with `\` and did not parse alone (`unexpected EOF while parsing`). `parse` now adds that one line to the function. Examples: sympy `test_guess_rational_cv` and pylint `Foo.meth3`.
  - **A file that is not UTF-8.** pylint has a Latin-1 test file. `index.build` decodes `git show` output as UTF-8 and raised `UnicodeDecodeError`. A new helper, `diff.python_sources`, gives the text of each `.py` file and skips a file that does not decode. `index.build`, `removal`, and `replace_calls` all use it.
- The code review found 3 more defects, and this ticket fixes them:
  - `removal` found the caller with `f.end == fn.end_lineno`. The backslash fix makes `Function.end` one line longer, so `next()` raised `StopIteration`. `removal` now matches on the line range.
  - `trial` indents the rewrite back with `textwrap.indent`. A line inside a multi-line string that is left of the `def` then gets the indent, and the string value changes. After `dedent`, the gate cannot tell such a line from a normal one. So `trial` rejects the function with the reason "a line is left of the def, so the gate cannot re-indent a rewrite", before any model call. A comment line left of the `def` does not cause a rejection.
  - `removal` and `replace_calls` had the same `UnicodeDecodeError` as `index.build` (see above).
- The review also found that `parse` splits lines on a form feed. That is ticket 47.

**Worked example.** `requests/packages/chardet/charsetgroupprober.py`, `CharSetGroupProber.get_charset_name`:

```python
    def get_charset_name(self):
        if not self._mBestGuessProber:
            self.get_confidence()
            if not self._mBestGuessProber:
                return None
#                self._mBestGuessProber = self._mProbers[0]
        return self._mBestGuessProber.get_charset_name()
```

- Before: `textwrap.dedent` leaves the source unchanged, and the parse gives `IndentationError unexpected indent (<old>, line 1)`.
- After: `dedent` removes 4 spaces from each line except the comment. `classify` returns `{}`. `nesting` is 2, `complexity` is 3, and `structure_hash` gives `3f9f68dfc594…`.

**Measured results.**

- The 34 functions of ticket 37 (the same filter as `bench/detect.py`): 34 fail with `textwrap.dedent`. With the fix, all 34 parse, and `structure_hash`, `nesting`, `complexity`, and `kinds.measured` give a result for each.
- All functions in the 12 SWE-bench Lite repos, test files included (94,761 functions): `structure_hash` failed on 224 before, and on 2 after the `dedent` fix only. With the backslash fix, it fails on 0.
- `index.build` on the real checkouts: sympy gives 19,922 records in 22.8 s, and pylint gives 5,072 records in 15.7 s. Before, both crashed.
- `uv run pytest -q`: 298 passed, 17 deselected. Each new test failed on the old code, except the test that a comment left of the `def` gets a rewrite. That test failed when the comment exemption was removed.

**Full gate on the 9 SWE-bench items that crashed before.** The first full-gate run on the held-out items (16 items) had 9 errors: 8 `IndentationError` and 1 sandbox upload time-out. With this ticket (before the review fixes), the 9 items ran again:

- 8 of 9 reviews ran to the end. The 1 error is the same Contree upload time-out (`ApiTimeoutError`) on `dup_deflate`.
- 8 of 9 found the injected kind, and each got an inline note.
- 0 of 9 got a proven rewrite. The causes: the test agent hit the step or time limit (3), its tests failed on the original Django code (1), the rewrite kept the slop (1), the rewrite made no change (1), and the repo suite failed (2).
- The 2 repo-suite failures are both `test_FracElement___call__`. The same test fails on the original sympy code (`5 failed, 765 passed` without `-x`). Ticket 48 holds the fix.
- Cost: 567,547 input and 36,704 output tokens, $0.205, 532 s wall time.

**Known limits.**

- `index.build` skips a file that is not UTF-8. Its functions are not in the duplicate search.
- A rewrite reply whose first line that is not blank is a comment at column 0, followed by indented code, still does not parse. `textwrap.dedent` had the same problem.
- A pull request that changes a file that is not UTF-8 still crashes in `diff.changed_functions`. This comes from reading the code. It is not reproduced.
- Several backslash lines in a row (`x = 1 \`, then `    \`, then a comment line) still give a source that does not parse. The review found this with a synthetic probe. The 12 repos have no such function.
