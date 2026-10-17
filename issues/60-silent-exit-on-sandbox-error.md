# 60 — A sandbox error other than an install error gives an empty review and exit code 0

## Summary

- **Goal:** Make a review that stops on a sandbox error show the error. Example: a ConTree timeout on a file upload must not look like "no slop found".
- **Checkable finish condition:** An offline test makes `sandbox.prepare` raise a plain `Exception`. The test checks two facts: `review` returns the notes that it found before `prepare`, with one `rejected` entry that holds the error text; and `slopgate review` exits with code 1.
- **Evidence:** Before: on 2026-10-12, an injected-slop run on `sympy/sympy` (`ZeroMatrix.__pow__`, nesting) ended with `slopgate: ApiTimeoutError(request=RequestInfo(url='https://api.tokenfactory.nebius.com/sandboxes/v1/files', method='POST'), ...)` on stderr. The output was `{"suggestions": [], "followup": [], "rejected": [], "notes": []}` and the exit code was 0. The other 8 runs of the batch had notes. After: the offline test.
- **Constraints:** The rule "always exit 0" belongs to `slopgate hook` only. Do not change the hook. Do not catch an error that is not about the sandbox, such as a failed GitHub call.

**Blocked by:** —

**Status:** done

**Type:** bug.

## Context

`review` in `slopgate/review.py` catches only `InstallError` around `sandbox.prepare`. For this error it adds a `rejected` entry and the notes of the candidates. Any other error goes up to `main` in `slopgate/cli.py`. `main` prints the error to stderr and prints its own empty result: the notes that `review` already found are lost. The exit code stays 0.

In the GitHub Action, the pull request then shows "no slop found". In the benchmark of ticket 10, the run counts a missed detection. Nobody sees the cause.

## Design

1. In `review`, catch every `Exception` from `sandbox.prepare`, not only `InstallError`. Use the same handling: one `rejected` entry with `could not build test environment` and the error text, and the notes from `unproven`.
2. In `main` of `slopgate/cli.py`, exit with code 1 after the result is printed, when an error was caught.
3. Check that `--pr` mode still posts the review when `review` returns a `rejected` entry.

## Acceptance

- [x] An offline test with a `prepare` that raises `Exception("timeout")` gets the notes and one `rejected` entry that holds `timeout`.
- [x] An offline test shows that `slopgate review` exits with code 1 when `review` raises.
- [ ] `uv run pytest -q` passes.

## Comments

### 2026-10-17: built

**What changed.**

- `review` in `slopgate/review.py` catches every exception from `sandbox.prepare`, not only `InstallError`. It returns the notes of the candidates and one `rejected` entry. For an `InstallError`, the reason holds the output tail, as before. For any other error, the reason holds `repr(error)`, so the type name is always visible. A plain `TimeoutError()` has an empty `str`.
- `main` in `slopgate/cli.py` prints the result. Then it exits with code 1 when the review branch caught an error. `slopgate hook` and `slopgate index` do not change.
- A failed GitHub call is not caught in `review`. It goes up to `main` and now exits with code 1. `test_github_server_errors_give_up_after_three_tries` checks this.

**Worked example.** A scratch repo has one nested function (`can_edit`, 5 levels deep). `Local.prepare` raises a real ConTree `ApiTimeoutError(timeout_type='write')`. The command is `slopgate review --dry-run --sandbox local`.

- Before: `{"suggestions": [], "followup": [], "rejected": [], "notes": []}`. The error is on stderr only, and the exit code is 0.
- After: one rejected entry, `could not build test environment` and then `ApiTimeoutError(request=None, response=None, timeout_type='write')`. One `nesting` note for `can_edit` says that the gate could not build the test environment. The exit code is 0, because the result shows the error.

When `review` itself raises (for example with `--repo /nonexistent-repo`), the CLI prints `slopgate: FileNotFoundError(...)` on stderr, prints the result, and exits with code 1.

**Tests.** Both new tests failed before the fix:

- `test_other_prepare_error_is_one_notice_with_the_error_text` failed with `assert "slopgate: Ex...('timeout')\n" == ''`. The error went up to `main`.
- `test_review_error_prints_the_result_and_exits_1` failed with `Failed: DID NOT RAISE SystemExit`.

**Review.** An Opus thermo-nuclear review approved the change. Its one requested change is applied: use `repr` for errors other than `InstallError`. It kept the wide catch. A narrower list would depend on private error classes of the ConTree SDK, and `repr` shows the type of an error in slopgate's own code.

**Cost.** No model call and no ConTree run. All checks are offline.

**Note.** `action.yml` runs the review step with `continue-on-error: true`, so exit code 1 does not turn the Action check red. Only the self-hosted workflow (disabled) shows a red check.
