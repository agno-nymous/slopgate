# 34 — Readable rejection reasons in the review comment

## Summary

- **Goal:** Start each rejection in the review comment with one plain sentence that says why the gate skipped the function. The raw pytest output follows in a code block. Example: on PR #20, the rejection of `characterize` showed raw pytest output, and markdown turned a line that starts with `>` into a quote.
- **Checkable finish condition:** A test checks the markdown that `github.py` builds: a rejection with pytest output gives one summary line plus a fenced block, and the summary holds the counts of failed and passed tests. A rejection with no tool output has no code block. `uv run pytest -q` passes. The posted comment on one real pull request shows no quote lines and keeps the indentation.
- **Evidence:** Not built yet. Before: the user read the PR #20 comment as a crash of the gate, but the rejection was the normal result (the tests that Super wrote failed on the unchanged code). After: the test above and a comment on one real pull request.
- **Constraints:** Keep the full reason in the JSON output of `--dry-run`, so existing tests and scripts still see it. Take the counts from the pytest summary line when it is there. The summary is one sentence.

**Blocked by:** None — can start immediately.

**Status:** ready-for-agent

## Context

On PR #20 (2026-10-08), the gate rejected `characterize` with this reason:

```
characterization tests fail on original:         # an empty list if just the module is wanted.
        result = mod
        for p in parts:
>           result = getattr(result, p)
E           AttributeError: module 'slopgate.review' has no attribute 'sandbox'
...
```

The reason is a fixed text plus the last 20 lines of pytest output (`tail` in `slopgate/sandbox.py`). `github.py` puts each reason into the "Rejected" section as plain markdown, with no code block. Markdown then changes the output: a line that starts with `>` becomes a quote, and the indentation is lost. The user read the comment as a crash of the gate. The check had passed, and the rejection was the normal result: the tests that Super wrote failed on the unchanged code, so the gate could not prove a rewrite.

## Design

1. Split each rejection into two parts: a summary and an optional detail. The summary is one sentence. The detail is the raw output.
2. Give each rejection reason that holds tool output a plain summary. Examples:
   - "Skipped: 9 of 10 generated tests failed on the unchanged code, so the gate could not check a rewrite."
   - "Skipped: the rewrite failed 1 of 5 characterization tests."
   - "Skipped: the generated tests miss 2 branches of the function."
   Take the counts from the pytest summary line when it is there.
3. In `github.py`, write the summary as the list item. Put the detail under it in a ```` ``` ```` block.
4. Keep the full reason in the JSON output of `--dry-run`, so the existing tests and scripts still see it.

## Acceptance

- [ ] A rejection with pytest output renders as one summary line plus a fenced block. A test checks the markdown that `github.py` builds.
- [ ] The summary of "characterization tests fail on original" gives the counts of failed and passed tests.
- [ ] A rejection with no tool output (for example "rewrite makes no change") has no code block.
- [ ] The posted comment on one real pull request shows no quote lines and keeps the indentation of the output.
- [ ] `uv run pytest -q` passes.

## Comments
