# 40 — Limit the output tokens of `decide`

**What to build:** Give `llm.decide` an output limit, so that a long Lightning reply cannot slow a gate run for 1 to 2 minutes.

**Blocked by:** —

**Status:** ready-for-agent

**Type:** bug.

## Context

Ticket 37 ran `classify` 1,407 times. In 5 runs, Lightning wrote 8,000 or more output tokens. These runs took 60 s to 110 s. The median run took 1.6 s. Example: `_create_nan_agg_method` in xarray, 8,253 output tokens in 109.9 s.

`decide` sends no `max_tokens`, so the server limit of 8,192 output tokens applies. A reply at that limit is cut off. Its tool-call arguments are then not valid JSON, so `decide` returns `None`, and `classify` reports no lines for the kind. A normal `Check` reply has 60 to 800 output tokens (6 live tries on the same function on 2026-10-09).

## Design

1. Send `max_tokens` from a new constant `DECIDE_OUTPUT_TOKENS` in `slopgate/config.py`, for example 2,048.
2. When `finish_reason` is `"length"`, record the cut-off in the trace and return `None`, as for any reply that is not valid.

## Acceptance

- [ ] `decide` sends `max_tokens`.
- [ ] A test with a fake client shows that a cut-off reply returns `None`.
- [ ] A rerun of `uv run --env-file .env python -m bench.detect run` (after removing `bench/results/runs.json`) has no run longer than 30 s, and the precision and the recall do not change by more than the measured noise.

## Comments
