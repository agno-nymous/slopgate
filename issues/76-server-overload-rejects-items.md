# 76 — A Token Factory 529 "System is overloaded" rejects items of the gate

## Summary

- **Goal:** The gate retries a request that Token Factory refuses with HTTP 529 or another 5xx error, and does not reject the item.
- **Checkable finish condition:** A fake client that raises a 529 two times gives a normal reply. In 4 recorded reviews, no item has the reason `agent error: InternalServerError`.
- **Evidence:** Before: the 4 recorded reviews of ticket 64 (2026-10-26). 3 of 13 items got a 529 in the test agent (a `gate.agent` span with `InternalServerError: Error code: 529 - ... 'System is overloaded'`): `discounted` (slopgate-demo#1), `pytest_unconfigure`, and `TerminalReporter._get_progress_information_message` (pytest-5227). Two of them show the 529 in the rejection reason. After: the next 4 reviews.
- **Constraints:** The wait between tries stays short. A run must not wait without a limit. `yes_probability` (the hook) still never sleeps.

**Blocked by:** —

**Status:** ready-for-agent

**Type:** bug.

## Context

Ticket 73 added a retry for HTTP 429 in `slopgate/llm.py` (`create`). A 529 is a different error: the service is overloaded. The OpenAI client retries it 2 times by default, with a short wait. During the 4 parallel reviews of 2026-10-26, that was not enough. The test agent stopped in the middle of a run, and the review showed a rejection that no rewrite or test caused. The same review of `slopgate-demo` PR 1, run alone, proved all 4 functions in 84 s.

## Design

1. In `create`, handle `InternalServerError` (status 500 to 599) with the same waits as the 429 retry (`RATE_LIMIT_WAITS`). Read `Retry-After` when it is present.
2. Keep the `llm.rate_limit` span. Add the status code to it.
3. Do not retry a 4xx error other than 429.
4. Add an offline test with a fake client that raises a 529 twice.

## Acceptance

- [ ] A fake client that raises 529 twice gives a normal reply.
- [ ] A fake client that raises 400 raises at once.
- [ ] `uv run pytest -q` passes.
- [ ] A review of `slopgate-demo` PR 1 has no `InternalServerError` rejection (or a Phoenix trace shows the retry).

## Comments
