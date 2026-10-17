# 61 — Each model call gets 8 nested spans when the first span opens in a thread pool

## Summary

- **Goal:** Record each model call as one LLM span, also when a script opens its first span in a thread pool.
- **Checkable finish condition:** An offline test opens the first `trace.span` in 8 threads at once. `phoenix.otel.register` runs one time.
- **Evidence:** Before: on 2026-10-14, the ticket 51 corpus script (`trace.start("slopgate-t51")`, then 8 threads) made 122 Super calls. Phoenix holds 976 `ChatCompletion` spans for them: 8 nested spans for each call, with the same output. After: the offline test, and one span for each call in a rerun.
- **Constraints:** Keep the lazy setup. With tracing off, `slopgate.trace` imports no OpenTelemetry module.

**Blocked by:** —

**Status:** ready-for-agent

**Type:** bug.

## Context

`_setup` in `slopgate/trace.py` calls `register(..., auto_instrument=True)` when `_tracer is None`. It has no lock. When 8 threads open their first span at the same time, each thread sees `_tracer is None`, and each thread calls `register`. Each call instruments the OpenAI client again, so one request makes 8 nested `ChatCompletion` spans.

The race does not occur in the gate now. The `slopgate review` command opens the `gate.review` span in `slopgate/cli.py` on the main thread. It does this before `review` starts a thread pool. The race occurs in a bench script or a live test that opens its first span in a thread pool. Phoenix then shows token counts that are 8 times too high.

## Design

Put a `threading.Lock` around the check and the `register` call in `_setup`.

## Acceptance

- [ ] An offline test with a fake `register` opens the first span in 8 threads and counts 1 call.
- [ ] A rerun of a script that opens its first span in a thread pool shows one `ChatCompletion` span for each model call.
- [ ] `uv run pytest -q` passes.
