# 45 — The test agent cannot characterize large functions

## Summary

- **Goal:** Let the gate prove a rewrite of a large function, or reject a large function at once at no cost. Example: the dry run of ticket 41 on its own commits found `nesting` in `review` (`slopgate/review.py`, 158 lines, complexity 65). The test agent stopped at the 150,000-token limit, and its last test file failed on the original code.
- **Checkable finish condition:** A table in the Comments gives, for each design below, the proof rate, the cost, and the time on the same large functions. The design that the user chooses is built, and `uv run pytest -q` passes.
- **Evidence:** Before: in ticket 41 (run 2, design D), the agent proved no function of complexity 17 or more (0 of 6 runs: `characterize` at b2a2ad0 and at 70c27da, 3 runs each). The most complex function that it proved was `matches` (complexity 10), in 3 of 3 runs. The dataset had no function between complexity 10 and 17. After: the table of this ticket.
- **Constraints:** Keep the judge (`check`) as it is. Do not lower the branch coverage rule. Measure each design on the same functions before a build. Name each ticket with its title in all text to the user.

**Blocked by:** 41

**Status:** ready-for-agent

**Type:** measurement, then build.

## Context

Since ticket 41 (Characterization tests by an agent in a ConTree sandbox), `characterize` in `slopgate/review.py` is a plain tool loop. Super gets one `execute` tool on a sandbox session. The loop stops at 15 model calls, 120 s, or 150,000 input tokens (`AGENT_STEPS`, `AGENT_SECONDS`, `AGENT_TOKENS` in `slopgate/config.py`).

Each model call sends the whole message history again. The history holds every command and its output, for example full pytest runs. So the input tokens grow with each step. On a large function, the agent needs more steps, and each step costs more. The token limit then stops the agent before its file passes.

Measured in ticket 41 (bench/results/characterize/runs.json, design D):

| Function | Lines | Complexity | Proved |
|---|---|---|---|
| `characterize` at 70c27da | 55 | 20 | 0 of 3 |
| `characterize` at b2a2ad0 | 52 | 17 | 0 of 3 |
| `matches` at b2a2ad0 | 19 | 10 | 3 of 3 |
| `Response.iter_lines` (requests) | 24 | 9 | 1 of 1 |
| `review` at ticket 41 HEAD | 158 | 65 | 0 of 1 (gate dry run) |

Large functions are where a `nesting` rewrite helps most. So a gate that cannot prove them misses the most useful suggestions. An agent run that fails also costs the most: up to 15 calls and 150,000 input tokens, about $0.05, and up to 120 s.

## Design

### Stage 1: measure

Add the functions below to the dataset of `bench/characterize.py`, with `--only` filters:

- `review` at ticket 41 HEAD, `characterize` at b2a2ad0 and at 70c27da;
- at least 10 functions of complexity 15 or more from the ticket 37 pool (`~/.cache/slopgate/bench/sample.json`), from the repos that install in ticket 41 (django, requests, sympy, flask).

Compare these designs, 3 runs each, with the kill rate of the mutation check:

1. **Now.** `characterize` as it is.
2. **Short history.** Keep the full output of the last 2 tool calls only. Replace each older output with one line, for example `[output of an earlier command removed]`. The token use per step then stays about flat.
3. **Limits that grow with the size.** Scale `AGENT_STEPS` and `AGENT_TOKENS` with the complexity of the function, with a fixed upper limit.
4. **Reject at once.** Above a complexity limit, reject the function before any model call: `too large to characterize: complexity N`. This costs nothing. It is the fallback if no other design proves large functions.

Designs 2 and 3 can be combined.

### Stage 2: build

The user chooses the design from the table. Record the chosen limits in `slopgate/config.py` and `CLAUDE.md`.

## Acceptance

### Stage 1

- [ ] The dataset has at least 13 functions of complexity 15 or more.
- [ ] A table gives the proof rate, the kill rate, the cost, and the time for each design.
- [ ] The user chooses the design.

### Stage 2

- [ ] `characterize` uses the chosen design.
- [ ] `uv run pytest -q` passes.
- [ ] A dry run of the gate on the commits of ticket 41 gives a result for `review` that the chosen design explains: proved, or rejected at once with the reason.

## Comments

### 2026-10-11 — count from ticket 49

The traced dry runs of ticket 49 (10 pull requests, 15 candidates) gave 7 wrong results from this cause: `review` 4 times (81 to 158 lines), `removal` (77 lines), and `characterize` 2 times (55 lines). Each run stopped at the step limit (5) or the token limit (2), and used 105,000 to 190,000 tokens and 65 s to 99 s.

In 5 of these runs, the output of the failing pytest runs was 61 % to 73 % of the message history. Design 2 (short history) addresses this. A pytest option such as `--tb=short` is another way to cut it, but it is a prompt change and needs a live comparison first.

A live comparison in ticket 49 on 7 functions (variant A: now; variant B: the missed-branch command filtered to the lines of the target; variant C: B plus a stop rule) gave 2, 2, and 3 passes of 7, and 91, 90, and 89 steps. The same function passed in one run and failed in the next at temperature 0. So a design comparison here needs at least 3 runs for each function.
