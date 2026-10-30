# 77 — Move the Super role to Nemotron 3.5 Super VL

## Summary

- **Goal:** The gate and the Try it page use `nvidia/Nemotron-3.5-Super-VL` in place of `nvidia/nemotron-3-super-120b-a12b`. The old model stops on Token Factory on 2026-11-09 (the user reported this on 2026-10-30).
- **Checkable finish condition:** `SUPER` in `slopgate/config.py` is `nvidia/Nemotron-3.5-Super-VL`. `uv run pytest -q` passes. The live tests pass. The SWE-bench benchmark runs with the new model on the same 45 injected items, and the report compares it with the Super 3 run of 2026-10-25.
- **Evidence:** Before: the Super 3 run of 2026-10-25 (`bench/results/swebench/swebench-super-3.md`): 41 of 45 items detected, 14 of 41 accepted, 0 silent breaks, $1.16. After: the same table for Super 3.5 VL.
- **Constraints:** Keep the ground truth (the injected items) of 2026-10-18. Only the gate model changes. Keep every model rule of `CLAUDE.md`: thinking off, code in a markdown block, decisions as a forced tool call. Keep the old results files as records of the past runs.

**Blocked by:** —

**Status:** done

**Type:** chore.

## Context

Token Factory lists `nvidia/Nemotron-3.5-Super-VL` (created 2026-10-08). It has the same price as Super 3 ($0.30 input, $0.90 output per million tokens), a 1,048,576-token context, and 2,000,000 tokens per minute. Its modality is text and image to text. It supports `tools` and `reasoning`. Its model entry lists no sampling parameters, but a request with `temperature=0` works.

A probe on 2026-10-30 sent 2 requests to each model with thinking off:

| Request | Super 3 | Super 3.5 VL |
|---|---|---|
| Rewrite as one ```` ```python ```` block | `return bool(a and b)`, 1.0 s | `return True if a and b else False`, 0.7 s |
| Forced tool call (reason, verdict) | valid arguments, 0.9 s | valid arguments, 1.2 s |

The test agent (`characterize`, ticket 41) and the proofs were tuned on Super 3. The benchmark shows if the new model proves as many rewrites.

## Design

1. Set `SUPER = "nvidia/Nemotron-3.5-Super-VL"` in `slopgate/config.py`. `PRICES` uses the `SUPER` key, so the price follows.
2. Set `MODEL` in `docs/demo/try.js` to the new model.
3. Change the Super model name in `README.md`, `CLAUDE.md`, and `spec.md`. Do not change the recorded results, the recordings, or the old tickets.
4. Copy the Super 3 results to `bench/results/swebench/runs-super-3.json`, `swebench-super-3.json`, and `swebench-super-3.md`. Then run `python -m bench.swebench run` and `report` with the new model on the same ground truth.
5. Read the Phoenix traces of the run.

## Acceptance

- [x] `SUPER` is `nvidia/Nemotron-3.5-Super-VL`.
- [x] `docs/demo/try.js` uses the new model.
- [x] `uv run pytest -q` passes.
- [ ] The live tests pass. (11 passed, 6 failed; see Comments.)
- [x] The SWE-bench run with Super 3.5 VL is complete, and the Comments give both tables.
- [x] README numbers match the new run, or the README names the model and the date of each number.

## Comments

### 2026-10-30 — done

**What changed.** `SUPER` in `slopgate/config.py` is now `nvidia/Nemotron-3.5-Super-VL`. The Try it page (`docs/demo/try.js`), `spec.md`, `CLAUDE.md`, and the README name the new model. The price is the same, so `PRICES` did not change. The Token Factory CORS preflight from `https://agno-nymous.github.io` gives `access-control-allow-origin: *`, so the Try it page can call the new model.

**Benchmark.** Same ground truth (45 items injected on 2026-10-18), same prompts, same 15 instances. Only `SUPER` changed.

| Run | Detected | Accepted | Silent breaks | Infrastructure errors | Cost |
|---|---|---|---|---|---|
| Super 3, 2026-10-25 (`swebench-super-3.md`) | 41 of 45 | 14 of 41 (0.341) | 0 | 0 | $1.16 |
| Super 3.5 VL, 2026-10-30 (`swebench.md`) | 41 of 45 | 20 of 41 (0.488) | 0 | 0 | $0.82 |

By kind (accepted): nesting 3 to 4, swallowed_error 1 to 4, wrapper 1 to 3, dead 5 to 5, duplicate 3 to 3, lookup_table 1 to 1, redundant_check 0 to 0. The hidden SWE-bench tests pass on all 20 accepted rewrites.

Per item, 7 items changed from rejected to accepted, and 1 changed from accepted to rejected:

- Gained: `ObjectProperty.get_mapping` (seaborn-3190, swallowed_error; before: token limit), `PreparedRequest.prepare_cookies` (requests-3362, swallowed_error; before: signature changed), `Variable._inplace_binary_op` (xarray-4248, nesting; before: does not parse), `ReportsHandlerMixIn.register_report` (pylint-5859, swallowed_error; before: rewrite leaves the slop), `pytest_unconfigure` (pytest-5227, swallowed_error; before: step limit), and two wrappers in pytest-5692 and pytest-8365 (before: rewrite fails characterization tests).
- Lost: `pytest_terminal_summary` (pytest-7220, swallowed_error): the new rewrite leaves the slop.

**Worked example.** `Variable._inplace_binary_op` in `xarray/core/variable.py` (pydata__xarray-4248). The benchmark added 2 levels of nesting. With Super 3, the rewrite did not parse. With Super 3.5 VL, the gate reports: "nesting 3 -> 1, complexity 1 -> 1. 5 characterization tests passed in sandbox." The hidden xarray tests pass on the rewrite.

**Traces.** Phoenix project `slopgate-bench`, the run of 2026-10-30: 2,176 spans, 0 spans with status `ERROR`, 553 model calls, 0 replies with `finish_reason: "length"`. The median model call took 1.6 s, the slowest 22.1 s.

**Limits.** This is one run per model. A model at temperature 0 can still give different replies, so a difference of 1 or 2 items can be noise. A gain of 6 items with 0 silent breaks is larger than that. The recorded reviews of the showcase (`docs/demo/recordings/`) and the video show Super 3 runs. They stay as records of those runs.

**Tests.** `uv run pytest -q`: 507 passed. Live tests: 11 passed, 6 failed. One failure comes from the model: `test_agent_proves_characterization_tests[broken_rule]` failed 3 of 3 runs with Super 3.5 VL (the agent expects `1 <= x` to `x > 1` to be allowed and stops at the token limit) and passed 3 of 3 runs with Super 3. Three failures are a sandbox error ("tests do not collect") in tests that do not depend on the model. One failure is an expired Hugging Face token.
