# 41 — Characterization tests by an agent in a ConTree sandbox

## Summary

- **Goal:** Find out whether an agent that works in the ConTree sandbox writes better characterization tests (tests that record what the old code does) than the current flow. Then build the best design into `characterize`. Example: the agent can run `grep` to find the value of `DUPLICATE_SCORE`, which Super guessed on PR #17.
- **Checkable finish condition:** Stage 1: `bench/characterize.py` runs designs A, B, and C on the same functions with one command, and prints one table. Stage 2: `characterize` uses the design that the user chose, `uv run pytest -q` passes, and a dry run on demo PR #1 proves at least as many rewrites as before.
- **Evidence:** Not measured yet. Before: tickets 29, 30, 31, and 35 each record one test failure of the current flow on PR #17 or PR #20. After: the table gives, for each design, the proof rate, the failure reasons, the time, the cost, and for C the steps and the broken file writes.
- **Constraints:** The agent loop runs on the runner, outside the sandbox, and the sandbox gets no API key. Use Super, with thinking off. Do not use the broken mini-swe-agent adapter. Limit the agent to 15 steps and 120 s. The agent writes files with `execute` and a heredoc. The median time must stay below 60 s for each function. The user chooses the design for stage 2.

**Blocked by:** —

**Status:** ready-for-agent

**Type:** measurement, then build.

## Context

`characterize` in `slopgate/review.py` writes characterization tests now in this way:

1. Super writes a test file (or a list of calls) from `TESTS_PROMPT`.
2. The sandbox runs the tests twice on the original code and measures the branch coverage of the target.
3. On a failure, Super gets one retry with the pytest output (`TESTS_RETRY`), the missed branches (`MISSED_RETRY`), or the recorder error (`INPUTS_RETRY`). There are 2 attempts in total.

Super sees only the target function and the functions that it calls. It cannot read other files, and it cannot run anything. 4 open tickets each fix one result of this:

- Ticket 29: one failing test rejects the whole file.
- Ticket 30: Super guessed the value of `DUPLICATE_SCORE` on PR #17, because it could not see the constant.
- Ticket 31: missed branches reject at once.
- Ticket 35: on PR #20, the tests called the real model client and patched a parameter by name.

An agent that can run `grep`, `cat`, and `pytest` in the sandbox can find a constant, see a failure, and fix it. The paper on CoverUp reports that its loop of coverage and feedback gave about 40% of its gains (arXiv 2403.16218).

### The tools

- **LangChain Deep Agents** (`deepagents`): an agent with planning, file tools, and an `execute` tool for a sandbox backend.
- **`ContreeSandbox`**: the ConTree backend for Deep Agents. It is in `contree_sdk.langchain.sandbox`, and the `contree-sdk` 0.3.6 that the gate uses already has it. It runs each command in one ConTree session (`disposable=False`), so files and installs stay between commands. Nebius documents this integration: https://docs.tokenfactory.nebius.com/sandboxes/sdk/integrations/langchain
- The Nebius docs say that the mini-swe-agent ConTree adapter is broken now. Do not use it.

### The agent loop runs outside the sandbox

The agent loop runs on the runner. Only its commands run in ConTree. The sandbox drops `NEBIUS_*`, `PHOENIX_*`, `OTEL_*`, `GH_TOKEN`, and `GITHUB_TOKEN`, because the code of the pull request runs there. An agent inside the sandbox would need the key inside the sandbox. LangChain recommends the same pattern ("sandbox as a tool").

## Design

### Stage 1: compare 3 designs (a prototype, not in the gate)

Put the prototype in `bench/characterize.py`. Use the same Super model and the same sandbox image as the gate.

1. **A: the gate now.** Call `characterize` as it is.
2. **B: a plain loop, no framework.** The same prompts as A, with up to 4 attempts. Each retry gets the pytest output, the missed branches by line, and the module-level constants that the target reads. About 50 lines.
3. **C: Deep Agents with `ContreeSandbox`.** Start the session from the gate's checkpoint (the repo is installed). The task: write `<test_path>` so that it passes twice on the original code and covers every branch of the target, with no network and no keys. The agent can read files and run commands. Limits: 15 steps, 120 s, and a token limit for each function.
   - Model rule: code in tool arguments was worse in ticket 20 (41 proven against 45 for markdown, 3 broken files). Tell the agent to write files with `execute` and a heredoc, not with `write_file`. Count the broken writes.
   - Turn thinking off on each request, as the other model calls do.

For each design, the gate's own check decides the result: the tests pass twice on the original code, the output is the same, and the branch coverage of the target is complete.

**Dataset.**

- The functions whose characterization failed on PR #17 and on PR #20 (from the Phoenix traces or a dry run at the PR heads).
- 30 functions from the ticket 37 pool (`~/.cache/slopgate/bench/sample.json`), at random with a fixed seed, from at least 4 repos. The sandbox must install each repo; use the repos whose install works with `.slopgate.toml` or `pyproject.toml`.

**Measure for each design:**

- proof rate: the share of functions with tests that pass the gate's check;
- the reasons for the failures (fail on original, missed branches, nondeterministic, no reply, step limit);
- time for each function, model calls, tokens, and cost (`config.PRICES`), and sandbox time;
- for C: steps for each function, and the number of broken file writes.

Run each design once on each function, and run C 2 more times on 10 functions, to see its variance.

### Stage 2: build the best design into `characterize`

Choose by the proof rate, then by the cost and the time. The gate runs `characterize` on each function of a pull request, so the median time must stay below 60 s for each function.

- If C wins: add `deepagents` to the dependencies, the `setup` line of `.slopgate.toml`, and the install step of `action.yml` (pip does not install uv groups). Wrap each agent call in `trace.span`.
- If B wins: build the loop in `characterize`, and close tickets 29, 30, and 31 if B covers them.
- Record which of tickets 29, 30, 31, and 35 the winner makes unnecessary, and set them to `wontfix` with a reason.

## Acceptance

### Stage 1

- [ ] `bench/characterize.py` runs designs A, B, and C on the same functions with one command.
- [ ] The dataset has the failed functions of PRs #17 and #20 and at least 30 functions from at least 4 SWE-bench repos.
- [ ] A table gives the proof rate, the failure reasons, the time, the cost, and (for C) the steps and broken writes, for each design.
- [ ] The agent loop runs outside the sandbox, and the sandbox gets no API key (checked with `env` in the sandbox).
- [ ] The user chooses the design for stage 2.

### Stage 2

- [ ] `characterize` uses the chosen design.
- [ ] `uv run pytest -q` passes, and the live tests that the change touches pass.
- [ ] A dry run on demo PR #1 proves at least as many rewrites as before.
- [ ] Tickets 29, 30, 31, and 35 are updated: done, wontfix, or still needed.

## Comments
