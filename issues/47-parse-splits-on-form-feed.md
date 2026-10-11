# 47 — `parse` splits lines on a form feed, so later functions get the wrong source

## Summary

- **Goal:** `functions.parse` cuts each function at the lines that `ast` counts.
- **Checkable finish condition:** A test parses a file with a form-feed line (`\x0c`) between two functions. The second function's source is its own `def` and body, and `structure_hash` gives a result for it. `uv run pytest -q` passes.
- **Evidence:** Found by the code review of ticket 38 on 2026-10-10, with a synthetic probe. Not found in the 12 SWE-bench Lite repos (94,761 functions, 0 failures).
- **Constraints:** Fix it in `parse`. Use the same line split in `dedent`.

**Blocked by:** —

**Status:** ready-for-agent

**Type:** bug.

## Context

`parse` in `slopgate/functions.py` splits the file with `str.splitlines(keepends=True)`. `str.splitlines` also splits on `\x0c`, `\x1c`, `\x85`, and `\u2028`. The AST line numbers count only `\n`. So after one of these characters, every function slice starts too late.

The review probe:

```python
"def a(): ...\n\x0c\ndef b(x):\n    if x:\n        return 1\n"
```

The source of `b` is `'\ndef b(x):\n    if x:\n'`. `structure_hash` raises `expected an indented block`. `index.build` calls `structure_hash` on each function of the repo, so the whole review crashes. This is the same symptom as ticket 38.

## Design

Split with `io.StringIO(text).readlines()`. It splits only on `\n`. `diff.git` reads with `text=True`, so `\r\n` and `\r` are already `\n`. Use the same split in the two `splitlines` calls of `dedent`.

## Acceptance

- [ ] A test with a form-feed line between two functions passes: the second function's source is correct, and `structure_hash` works on it.
- [ ] `dedent` uses the same line split.
- [ ] `uv run pytest -q` passes.

## Comments
