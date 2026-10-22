# 73 — A model rate limit rejects items of the gate

## Summary

- **Goal:** The gate retries a request that Token Factory refuses with a rate limit (HTTP 429), and does not reject the item.
- **Checkable finish condition:** In a benchmark run with 8 workers, no item has the reason `agent error: RateLimitError`.
- **Evidence:** Before: ticket 67 benchmark of 2026-10-21. 5 of 42 items were rejected with `agent error: RateLimitError(... 429 ...)`. After: the next benchmark report.
- **Constraints:** The wait between tries stays short. A run must not wait without a limit.

**Blocked by:** —

**Status:** ready-for-agent

**Type:** bug.

## Context

The benchmark runs 8 instances at the same time. Each instance runs the test agent with long contexts. The token quota of Token Factory is reached (ticket 67 stage 0 saw the same 429 with 200,000 tokens in one request). The OpenAI client retries 2 times by default. That is not enough here.

## Design

1. Read the `Retry-After` header or use a back-off of 5 s, 15 s, 45 s in `slopgate/llm.py`.
2. Count the retries in the trace, so a slow run is explained.
3. Add an offline test with a fake client that raises 429 twice.

## Acceptance

- [ ] A fake client that raises 429 twice gives a normal reply.
- [ ] A benchmark rerun has no `RateLimitError` rejection.
- [ ] `uv run pytest -q` passes.
