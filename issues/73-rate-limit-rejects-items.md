# 73 — A model rate limit rejects items of the gate

## Summary

- **Goal:** The gate retries a request that Token Factory refuses with a rate limit (HTTP 429), and does not reject the item.
- **Checkable finish condition:** In a benchmark run with 8 workers, no item has the reason `agent error: RateLimitError`.
- **Evidence:** Before: ticket 67 benchmark of 2026-10-21. 5 of 42 items were rejected with `agent error: RateLimitError(... 429 ...)`. After: the next benchmark report.
- **Constraints:** The wait between tries stays short. A run must not wait without a limit.

**Blocked by:** —

**Status:** needs-live-check

**Type:** bug.

## Context

The benchmark runs 8 instances at the same time. Each instance runs the test agent with long contexts. The token quota of Token Factory is reached (ticket 67 stage 0 saw the same 429 with 200,000 tokens in one request). The OpenAI client retries 2 times by default. That is not enough here.

## Design

1. Read the `Retry-After` header or use a back-off of 5 s, 15 s, 45 s in `slopgate/llm.py`.
2. Count the retries in the trace, so a slow run is explained.
3. Add an offline test with a fake client that raises 429 twice.

## Acceptance

- [x] A fake client that raises 429 twice gives a normal reply.
- [ ] A benchmark rerun has no `RateLimitError` rejection.
- [x] `uv run pytest -q` passes.

## Comments

### 2026-10-25

**What was built.** `slopgate/llm.py` has a new function, `create`. The functions `complete`, `step`, and `decide` send their requests through it. When Token Factory answers with a 429, `create` waits and sends the request again. The waits are 5 s, 15 s, and 45 s (`RATE_LIMIT_WAITS` in `config.py`). If the 429 has a `Retry-After` header with a number from 0 up, the header wins. A header value above 60 becomes 60 s. A negative, `nan`, or text value is ignored. After the third wait, `create` sends the request one more time, and a 429 then raises as before. Each wait has an `llm.rate_limit` span with the fields `attempt` and `wait`, so a slow run is explained in Phoenix.

`yes_probability` does not use `create`. The hook calls it, and the hook has a 30 s timeout. A hook that sleeps on a 429 would be killed. It must print the error to stderr and exit 0.

**Worked example (offline test, fake client).** The fake client raises 429 two times, then answers.
- Input: `llm.decide("m", "p", SameJob)`.
- Output: `SameJob(difference="", same_job=True)`. The recorded sleeps are `[5, 15]`.
- With the headers `Retry-After: 2`, `999`, and `soon`, the sleeps are `[2, 60, 45]`.
- With four 429 answers in a row, `RateLimitError` raises after the sleeps `[5, 15, 45]`.

**Measured.** `uv run pytest -q` passes. Five live tests of `llm` (`config_model_ids`, `complete`, `decide`) pass. The tests do not show a real 429 from Token Factory.

**Not done.** The box "A benchmark rerun has no `RateLimitError` rejection" is open. The rerun costs money and time, and ticket 72 (the pytest 2.9 flag) changes the same benchmark. Run the benchmark once, after ticket 72.

**Known limits.**
- The OpenAI client keeps its own 2 retries inside each try. One call can send up to 12 requests. With a `Retry-After` of 60 s, the worst case is long (the Opus review computed about 660 s). With no header it is about 77 s.
- The waits count in the time limit of the test agent (`AGENT_SECONDS`, `HINT_SECONDS`). A rate-limited agent can now end with "time limit" and not with `RateLimitError`. After the rerun, compare the count of rejected items, not only the reason text.
- The waits have no jitter. 8 workers that hit the quota together retry at the same times.
- A request that is larger than the quota by itself (ticket 67 stage 0: 200,000 tokens) never passes. Each such request now waits 65 s or more before it fails.
- The give-up call has no span.
