# 34 — Report the slop of each function without a rewrite, and no raw failures in the review comment

## Summary

- **Goal:** The review comment shows each finding in plain words. A function with slop that Slopgate did not rewrite gets an inline note with the slop and the fix. The note says that Slopgate changed nothing. The comment shows no rejection list and no raw pytest output.
- **Checkable finish condition:** A test checks the posted review: the rejected function has one inline note with its slop kinds, the fix, and the sentence that Slopgate changed nothing. The review body has no "Rejected" section and no pytest output. `uv run pytest -q` passes.
- **Evidence:** Before: on PR #20, the "Rejected" section showed raw pytest output, and the user read it as a crash of the gate. After: the tests below and a gate dry run on this branch.
- **Constraints:** Keep the full reasons in `result["rejected"]` (the JSON output of `--dry-run`) and in the Phoenix traces, for debugging.

**Blocked by:** None — can start immediately.

**Status:** done

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

The first version (2026-10-10) kept the "Rejected" section and gave each reason one plain sentence, with the pytest output in a code block. The user then decided that the comment must not show the failed attempts at all. The design below replaces the first version.

1. Each function with slop and no rewrite gets an inline review comment (a note) on the function. The note gives the slop kinds, the issue, and the fix, from the same text as the notes on test files. It ends with: "Slopgate could not prove a rewrite of this function, so it changed nothing."
2. This applies to each rejection in the loop over candidates and to the wrapper rule rejection. When the test environment cannot be built, every candidate gets a note that ends with: "Slopgate could not build the test environment, so it could not prove a rewrite and changed nothing."
3. A `wrapper` note says: "`<function>` only forwards to `<inner>`. Inline it into its single caller."
4. The label of every note is `(not rewritten)`, also for test files.
5. The review summary has no "Rejected" section and no "Rejected: N" count. The counts line is `Accepted: X inline suggestions, <follow-up changes>. Notes: N.`
6. The prompt of the Ultra summary gets the results without `rejected`, so the summary cannot repeat the failures.
7. The reasons stay in `result["rejected"]`, in the `--dry-run` JSON, and in the traces.

## Acceptance

- [x] A function that the gate rejects gets an inline note with its slop kinds, the issue, the fix, and the sentence that Slopgate changed nothing. A test checks it for a failed characterization and for a failed rewrite.
- [x] A wrapper that the gate rejects gets a note that names the inner function.
- [x] When the test environment cannot be built, each candidate gets a note.
- [x] The posted review has no "Rejected" section and no pytest output, and the Ultra summary prompt has no rejection reason. A test checks it.
- [x] A classify error and an accepted rewrite get no note.
- [x] `uv run pytest -q` passes.

## Comments

### 2026-10-10: built (first version, replaced below)

**What was built.** `rejection()` in `slopgate/github.py` builds each item of the "Rejected" list. The `SENTENCES` table maps the 5 reasons that hold pytest output to one plain sentence:

| Reason in the JSON | Sentence in the comment |
|---|---|
| `characterization tests fail on original` | "F of T generated tests failed on the unchanged code, so the gate could not check a rewrite." |
| `characterization tests time out` | "The generated tests ran past the time limit of the sandbox." |
| `rewrite fails characterization tests` | "The rewrite failed F of T characterization tests." |
| `rewrite fails repo tests` | "The rewrite failed F of T repo tests." |
| `differential tests fail on helper` | "The existing helper failed F of T generated tests." |

The pytest output goes under the sentence in a fenced block. The block is indented by 2 spaces, so it stays in the list item. The fence is longer than each run of backticks in the output. F and T come from the last pytest summary line. F counts only `failed`. Pytest `errors` are files or fixtures that broke, not tests, so they stay out of the counts. With no summary line or no failed test, the sentence has no counts.

`characterize` can put the stop reason of the test agent before the reason, for example `step limit: characterization tests fail on original: ...`. The stop reason then goes into the sentence: "... so the gate could not check a rewrite (the test agent stopped: step limit)."

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
- `uv run pytest -q`: 289 passed, 17 deselected. The 8 new tests are in `tests/test_github.py`.
- On the old `github.py`, 3 of the new tests fail (the code block, the backtick fence, and the time-out sentence). The "no code block" test passes on the old code too, because it checks an absence that the old code also gave.
- The code review (thermo-nuclear, Opus) gave 6 findings. Applied: errors are not counted as failed tests; a multi-line reason with an unknown prefix gets a code block; an empty output gives no empty block. Not applied: a time-out during the rewrite run reads as "the rewrite failed characterization tests" (old behavior of `review.py`; the code block shows the time-out), and the capitalization of the sentence (correct as it is).

**Gate dry run on the ticket commits** (`--base origin/main --head HEAD`): 0 suggestions, 1 rejection. The gate flagged `summary` in `slopgate/github.py` as `swallowed_error` (the old `except Exception`). The test agent stopped at the step limit, and 1 of its 5 tests failed on the unchanged code: the test expected `Time: 0 min 1 s.`, but the code gives `Time: 2 s.` This is the normal result, not a defect of this ticket. The dry run also found that the first version of `rejection()` used `Step limit.` as the sentence for this reason. The fix is above, and a test covers it. With the fix, the item reads:

```
- `summary` (swallowed_error) in slopgate/github.py: 1 of 5 generated tests failed on the unchanged code, so the gate could not check a rewrite (the test agent stopped: step limit).
```

**Known limits.**
- The sentences do not start with "Skipped:", as in the Design examples. The list is under the "Rejected" heading, so the word is not necessary.
- `characterization tests miss branches: N` stays as before. It holds no tool output, so step 2 of the Design does not apply to it.
- The `SENTENCES` keys must match the reason prefixes in `review.py`. A changed prefix falls back to the prefix as the sentence, with the code block.

### 2026-10-10: posted comment on a real pull request

The Slopgate workflow is disabled, so the gate posts no review now. To check box 4, `summary()` built one comment from a real pytest run: 3 characterization tests of a `resolve` function, 2 of which fail with `AttributeError`. The comment is on PR #29: https://github.com/agno-nymous/slopgate/pull/29#issuecomment-6103059744

The HTML that GitHub rendered for the posted comment (`gh api ... -H "Accept: application/vnd.github.html+json"`) has 0 `<blockquote>` elements. The line `>           result = getattr(result, p)` is in the `<pre>` block with its indentation. The item reads: "`resolve` (nesting) in app/review.py: 2 of 3 generated tests failed on the unchanged code, so the gate could not check a rewrite." The item "rewrite makes no change" has no code block.

### 2026-10-10: notes for functions without a rewrite; the Rejected list is removed

**What was built.** The user decided that the review comment must not show failed attempts. The first version (the plain sentences and the code blocks above) is deleted. Now each function with slop and no rewrite gets an inline note with the slop kinds, the issue, the fix, and the sentence that Slopgate changed nothing. `note()` in `slopgate/review.py` builds every note. `unproven()` builds the notes of the rejected candidates in one pass after the loop, and of all candidates when the test environment cannot be built. The review summary has no "Rejected" section and no rejected count. The Ultra summary prompt gets the results without `rejected`. The reasons stay in `result["rejected"]` and in the traces.

**Worked example.** `slopgate review --pr 29` with this code (2026-10-10). The gate found `swallowed_error` in `summary` in `slopgate/github.py`. Its rewrite failed the characterization tests. The posted inline note at `slopgate/github.py:124` (https://github.com/agno-nymous/slopgate/pull/29#discussion_r4239632374):

> **swallowed_error** (not rewritten): `summary`: It catches broad exceptions or wraps code that cannot raise in a try block. Narrow each except to the exceptions that the code in its try block raises, and remove try blocks around code that cannot raise. Every input must still give the same result. Slopgate could not prove a rewrite of this function, so it changed nothing.

The review body:

> Slopgate reviewed the pull request and proved each accepted rewrite with characterization tests in a sandbox. It found a swallowed error in `slopgate/github.py:124` but could not prove a rewrite, so it changed nothing.
>
> Accepted: 0 inline suggestions, 0 follow-up changes. Notes: 1.

The comment has no pytest output. The reason "rewrite fails characterization tests: ..." is only in the JSON output.

**Measured results.**
- `uv run pytest -q`: 282 passed, 17 deselected. The count is lower than in the first version, because the 8 tests of the deleted Rejected list are gone.
- PR #29: 1 note, 0 suggestions, $0.0439, 2 min 34 s. GitHub accepted the inline note.
- PR #20 (merged): 1 note on `characterize` (`nesting`, `dead`), 0 suggestions, $0.0944, 4 min 47 s. The rejection reason was "token limit: nondeterministic: characterization tests differ across two runs". The comment does not show it.
- The code review (thermo-nuclear, Opus) of the notes gave 6 findings and 3 nits. Applied: one code path for the notes, built after the loop and outside the `finally`; the match or plan travels in the candidate tuple; absence tests for a classify error and an accepted rewrite; a separate text for the install failure. Moved to ticket 46: the diff uses the base tip, not the merge-base, so a note can land on a line outside the pull request diff. Not applied: a note with a changed text is posted again on a later run (for example, the old "(not proven)" notes on test files get one new "(not rewritten)" note).

**Known limits.**
- Ticket 46: on a pull request whose base branch moved ahead, a note can land on a line outside the pull request diff. GitHub then rejects the whole review.
- A classify error gives no note, because the gate does not know the slop kinds.
- A note on a merged pull request shows no line number on GitHub, because the code changed after the merge.

