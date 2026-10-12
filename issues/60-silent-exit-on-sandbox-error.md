# 60 — A sandbox error other than an install error gives an empty review and exit code 0

## Summary

- **Goal:** Make a review that stops on a sandbox error show the error. Example: a ConTree timeout on a file upload must not look like "no slop found".
- **Checkable finish condition:** An offline test makes `sandbox.prepare` raise a plain `Exception`. The test checks two facts: `review` returns the notes that it found before `prepare`, with one `rejected` entry that holds the error text; and `slopgate review` exits with code 1.
- **Evidence:** Before: on 2026-10-12, an injected-slop run on `sympy/sympy` (`ZeroMatrix.__pow__`, nesting) ended with `slopgate: ApiTimeoutError(request=RequestInfo(url='https://api.tokenfactory.nebius.com/sandboxes/v1/files', method='POST'), ...)` on stderr. The output was `{"suggestions": [], "followup": [], "rejected": [], "notes": []}` and the exit code was 0. The other 8 runs of the batch had notes. After: the offline test.
- **Constraints:** The rule "always exit 0" belongs to `slopgate hook` only. Do not change the hook. Do not catch an error that is not about the sandbox, such as a failed GitHub call.

**Blocked by:** —

**Status:** ready-for-agent

**Type:** bug.

## Context

`review` in `slopgate/review.py` catches only `InstallError` around `sandbox.prepare`. For this error it adds a `rejected` entry and the notes of the candidates. Any other error goes up to `main` in `slopgate/cli.py`. `main` prints the error to stderr and prints its own empty result: the notes that `review` already found are lost. The exit code stays 0.

In the GitHub Action, the pull request then shows "no slop found". In the benchmark of ticket 10, the run counts a missed detection. Nobody sees the cause.

## Design

1. In `review`, catch every `Exception` from `sandbox.prepare`, not only `InstallError`. Use the same handling: one `rejected` entry with `could not build test environment` and the error text, and the notes from `unproven`.
2. In `main` of `slopgate/cli.py`, exit with code 1 after the result is printed, when an error was caught.
3. Check that `--pr` mode still posts the review when `review` returns a `rejected` entry.

## Acceptance

- [ ] An offline test with a `prepare` that raises `Exception("timeout")` gets the notes and one `rejected` entry that holds `timeout`.
- [ ] An offline test shows that `slopgate review` exits with code 1 when `review` raises.
- [ ] `uv run pytest -q` passes.

## Comments
