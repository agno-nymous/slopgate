# 34 — Readable rejection reasons in the review comment

## Summary

- **Goal:** Start each rejection in the review comment with one plain sentence that says why the gate skipped the function. The raw pytest output follows in a code block. Example: on PR #20, the rejection of `characterize` showed raw pytest output, and markdown turned a line that starts with `>` into a quote.
- **Checkable finish condition:** A test checks the markdown that `github.py` builds: a rejection with pytest output gives one summary line plus a fenced block, and the summary holds the counts of failed and passed tests. A rejection with no tool output has no code block. `uv run pytest -q` passes. The posted comment on one real pull request shows no quote lines and keeps the indentation.
- **Evidence:** Not built yet. Before: the user read the PR #20 comment as a crash of the gate, but the rejection was the normal result (the tests that Super wrote failed on the unchanged code). After: the test above and a comment on one real pull request.
- **Constraints:** Keep the full reason in the JSON output of `--dry-run`, so existing tests and scripts still see it. Take the counts from the pytest summary line when it is there. The summary is one sentence.

**Blocked by:** None — can start immediately.

**Status:** needs-live-check

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

- [x] A rejection with pytest output renders as one summary line plus a fenced block. A test checks the markdown that `github.py` builds.
- [x] The summary of "characterization tests fail on original" gives the counts of failed and passed tests.
- [x] A rejection with no tool output (for example "rewrite makes no change") has no code block.
- [ ] The posted comment on one real pull request shows no quote lines and keeps the indentation of the output.
- [x] `uv run pytest -q` passes.

## Comments

### 2026-10-10: built

**What was built.** `rejection()` in `slopgate/github.py` builds each item of the "Rejected" list. The `SENTENCES` table maps the 5 reasons that hold pytest output to one plain sentence:

| Reason in the JSON | Sentence in the comment |
|---|---|
| `characterization tests fail on original` | "F of T generated tests failed on the unchanged code, so the gate could not check a rewrite." |
| `characterization tests time out` | "The generated tests ran past the time limit of the sandbox." |
| `rewrite fails characterization tests` | "The rewrite failed F of T characterization tests." |
| `rewrite fails repo tests` | "The rewrite failed F of T repo tests." |
| `differential tests fail on helper` | "The existing helper failed F of T generated tests." |

The pytest output goes under the sentence in a fenced block. The block is indented by 2 spaces, so it stays in the list item. The fence is longer than each run of backticks in the output. F and T come from the last pytest summary line. F counts only `failed`. Pytest `errors` are files or fixtures that broke, not tests, so they stay out of the counts. With no summary line or no failed test, the sentence has no counts.

A one-line reason that is not in the table stays as before, with no code block. A multi-line reason that is not in the table gets its prefix as the sentence and a code block. Thus a new reason with tool output in `review.py` cannot bring back the quote lines.

`slopgate/review.py` did not change. The `--dry-run` JSON keeps the full reason.

**Worked example.** Input: the reason of PR #20 in the shape that `review.py` writes, `characterization tests fail on original: ` plus the pytest tail with `>           result = getattr(result, p)` and the summary line `9 failed, 1 passed in 0.31s`. Output of `summary()`:

````
- `characterize` (nesting) in slopgate/review.py: 9 of 10 generated tests failed on the unchanged code, so the gate could not check a rewrite.

  ```
          # an empty list if just the module is wanted.
          result = mod
          for p in parts:
  >           result = getattr(result, p)
  E           AttributeError: module 'slopgate.review' has no attribute 'sandbox'
  ...
  9 failed, 1 passed in 0.31s
  ```

- `can_edit` (nesting) in app/perms.py: rewrite makes no change
````

The GitHub markdown API (`gh api markdown -f mode=gfm`) rendered this body. The `>` line is in a `<pre><code>` block, the indentation is kept, and the HTML has no `<blockquote>`.

**Measured results.**
- `uv run pytest -q`: 287 passed, 17 deselected. The 6 new tests are in `tests/test_github.py`.
- On the old `github.py`, 3 of the new tests fail (the code block, the backtick fence, and the time-out sentence). The "no code block" test passes on the old code too, because it checks an absence that the old code also gave.
- The code review (thermo-nuclear, Opus) gave 6 findings. Applied: errors are not counted as failed tests; a multi-line reason with an unknown prefix gets a code block; an empty output gives no empty block. Not applied: a time-out during the rewrite run reads as "the rewrite failed characterization tests" (old behavior of `review.py`; the code block shows the time-out), and the capitalization of the sentence (correct as it is).

**Known limits.**
- The sentences do not start with "Skipped:", as in the Design examples. The list is under the "Rejected" heading, so the word is not necessary.
- `characterization tests miss branches: N` stays as before. It holds no tool output, so step 2 of the Design does not apply to it.
- The `SENTENCES` keys must match the reason prefixes in `review.py`. A changed prefix falls back to the prefix as the sentence, with the code block.
