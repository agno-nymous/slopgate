# 41 — Characterization tests by an agent in a ConTree sandbox

## Summary

- **Goal:** Find out whether an agent that works in the ConTree sandbox writes better characterization tests (tests that record what the old code does) than the current flow. Then build the best design into `characterize`. Example: the agent can run `grep` to find the value of `DUPLICATE_SCORE`, which Super guessed on PR #17.
- **Checkable finish condition:** Stage 1: `bench/characterize.py` runs designs A, B, and C on the same functions with one command, and prints one table. Stage 2: `characterize` uses the design that the user chose, `uv run pytest -q` passes, and a dry run on demo PR #1 proves at least as many rewrites as before.
- **Evidence:** Not measured yet. Before: tickets 29, 30, 31, and 35 each record one test failure of the current flow on PR #17 or PR #20. After: the table gives, for each design, the proof rate, the failure reasons, the time, the cost, and for C the steps and the broken file writes.
- **Constraints:** The agent loop runs on the runner, outside the sandbox, and the sandbox gets no API key. Use Super, with thinking off. Do not use the broken mini-swe-agent adapter. Limit the agent to 15 steps and 120 s. The agent writes files with `execute` and a heredoc. The median time must stay below 60 s for each function. The user chooses the design for stage 2.

**Blocked by:** —

**Status:** done

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

- [x] `bench/characterize.py` runs designs A, B, and C on the same functions with one command.
- [x] The dataset has the failed functions of PRs #17 and #20 and at least 30 functions from at least 4 SWE-bench repos.
- [x] A table gives the proof rate, the failure reasons, the time, the cost, and (for C) the steps and broken writes, for each design.
- [x] The agent loop runs outside the sandbox, and the sandbox gets no API key (checked with `env` in the sandbox).
- [x] The user chooses the design for stage 2.

### Stage 2

- [x] `characterize` uses the chosen design.
- [x] `uv run pytest -q` passes, and the live tests that the change touches pass.
- [x] A dry run on demo PR #1 proves at least as many rewrites as before.
- [x] Tickets 29, 30, 31, and 35 are updated: done, wontfix, or still needed.

## Comments

### 2026-10-10 — Stage 1: the comparison of designs A, B, C, and D

**What was built.** `bench/characterize.py` runs each design on the same functions with one command, and writes one JSON row for each result. The command is `uv run --extra bench --env-file <main checkout>/.env python -m bench.characterize --designs A,B,C,D --repeat 10`. The `bench` extra installs `deepagents` and `langchain-openai`. The gate does not need them.

All designs use the same judge: `review.check` in `slopgate/review.py`. It was extracted from `characterize` without a change in behavior. The tests pass with `PYTHONHASHSEED=1` and `PYTHONHASHSEED=2`, and coverage shows no missed branch inside the target. The judge always runs on the original checkpoint, never in the agent's session.

The user asked for design D on 2026-10-10. D tests whether the Deep Agents framework adds anything to C.

**The four designs.**

- **A: the gate now.** `review.characterize`, unchanged. Super gets the function and the code that it calls. Super replies with calls or a test file. There are 2 attempts.
- **B: a plain retry loop.** The same prompts as A, with up to 4 Super calls. The context also holds the module-level constants that the target and its callees read (the design of ticket 30). A retry for missed branches names each branch by its line, for example `- line 42: if not pool: never goes to line 45`.
- **C: Deep Agents with `ContreeSandbox`.** The design in detail:
  - The agent loop runs on the runner. Only its commands run in ConTree.
  - The backend is `contree_sdk.langchain.sandbox.ContreeSandbox(checkpoint.session())`. The session starts from the gate's checkpoint, so the repo is installed. Files stay between commands.
  - The model is `ChatOpenAI(model=SUPER, base_url=BASE_URL, temperature=0, extra_body={"chat_template_kwargs": {"enable_thinking": False}})`. The agent is `create_deep_agent(model, backend, system_prompt, middleware)`.
  - In a probe, Super did not follow the prompt rule to write with a heredoc. It called `write_file`. `permissions=[FilesystemPermission(...)]` raises `NotImplementedError` with a sandbox backend. So C uses the private `deepagents.middleware._tool_exclusion._ToolExclusionMiddleware(excluded={"write_file", "edit_file", "task"})`. Without `task`, no subagent can hide its steps and tokens from the limits.
  - The tools that remain are `execute`, `ls`, `read_file`, `glob`, `grep`, and `write_todos`.
  - The system prompt (`RULES`) says: write files only with `execute` and a heredoc; change no file except the test file; the tests get no network and no API keys, so patch them; stop when the tests pass twice and cover every branch.
  - The task (`TASK`) gives the function source, the test path, the exact import line, the goal, the command that runs the tests with coverage, and the command that shows the missed branches as `[from, to]` pairs.
  - The limits are 15 model calls, 120 s, and 150,000 cumulative input tokens. The loop checks them between the stream updates. Each `execute` call has a 120 s timeout.
  - A heredoc write of a `.py` file that does not parse counts as a broken write. A tool call that does not parse also counts.
- **D: a plain tool loop, no framework.** The same `RULES` (without the sentence about the tools that are off) and the same `TASK` as C. The OpenAI client of `llm.client()` gets one tool, `execute(command)`, on the same `ContreeSandbox` session. The loop stops when a reply has no tool call, or at the same limits as C. The tool output has the same form as in Deep Agents. C and D share all code except the loop.

**The dataset.** 36 functions:

- 6 slopgate functions that failed on PRs #17 and #20: `build`, `seed`, `matches`, `find_duplicate`, and `characterize` at b2a2ad0, and `characterize` at 70c27da. The image is `python:3.12-slim`.
- 30 functions from the ticket 37 pool, with `random.Random(41)`, 6 from each of 5 SWE-bench repos: django, pytest, requests, sympy, and flask. The image is `python:3.9-slim` (imported into ConTree with `images.oci`). On 3.12, the old commits of requests, sympy, and flask do not import.
- Astropy, scikit-learn, and sphinx were not used. They need C builds or old pins.

**The mutation check.** The judge does not check that the tests assert anything. An agent loop that runs until the judge passes could write weak tests. So each proved test file also runs against up to 8 mutants of the target: a comparison swap, `and`/`or`, a number plus 1, `return None`, or `if not`. A control run with the unchanged, unparsed function must pass first. The kill rate is the share of mutants that make the tests fail.

**Measured results.** Run 2, each design once on each function (`bench/results/characterize/table.md`):

| Design | Proved | Median s | p90 s | Input tokens per function | Cost per function | Kill rate | Median asserts |
|---|---|---|---|---|---|---|---|
| A | 7 of 36 (19%) | 19 | 31 | 2.1k | $0.002 | 97% (29/30) | 10 |
| B | 8 of 36 (22%) | 35 | 68 | 5.8k | $0.005 | 97% (30/31) | 12 |
| C | 19 of 36 (53%) | 56 | 89 | 95k | $0.031 | 87% (71/82) | 7 |
| D | 24 of 36 (67%) | 55 | 100 | 80k | $0.027 | 86% (88/102) | 4.5 |

- Run 1 (`runs-1.json`, no mutation check) gave A 7, B 13, and C 24.
- D proved each function that C proved in run 2, and 5 more.
- On the 5 functions that all 4 designs proved, the kill rates are A 100%, B 100%, C 94%, and D 94%. The agent tests are almost as strong as the tests of A.
- Variance, over the first 10 functions with 3 runs each: D proved 6 in 3 of 3 runs, 1 in 2 of 3, and 3 in 0 of 3. C proved 1 in 3 of 3, 3 in 2 of 3, 2 in 1 of 3, and 4 in 0 of 3.
- Broken writes: C 0 of 70, D 2 of 80.
- Without the slopgate and pytest functions: A 6, B 7, C 17, and D 21 of 24.
- The sandbox has no API key. `--env-check` printed `GPG_KEY LANG PATH PS1 PWD PYTHON_SHA256 PYTHON_VERSION SHELL TERM`.

**Worked example.** `find_duplicate` at b2a2ad0 is the case of ticket 30: Super guessed `DUPLICATE_SCORE`. In run 2, D proved it in 2 of 3 runs (13 calls, about 152,000 input tokens, 55 s to 65 s). The third run stopped at the token limit. The proved file starts like this:

```python
from unittest.mock import Mock, patch
from slopgate.review import find_duplicate

def test_exact_match_found():
    function = Mock()
    function.source = "def foo(): pass"
    pool = [
        {"hash": "hash1", "path": "helper1.py", "source": "def helper(): pass"},
        {"hash": "hash2", "path": "helper2.py", "source": "def foo(): pass"}
    ]
    with patch('slopgate.review.structure_hash') as mock_hash:
        mock_hash.return_value = "hash2"
        result = find_duplicate(function, pool)
        assert result["exact"] is True
```

Other tests in the same file patch `slopgate.review.llm.decide`, so no test calls the model. The file killed 6 of 7 mutants.

**Known limits.**

- The 6 pytest functions failed in all designs. The gate makes the import line from the file path (`src._pytest...`), and pytest measures itself. Ticket 44 records the `src/` layout problem.
- `characterize` itself failed in all designs. In run 2, all 12 agent runs (C and D, both versions, 3 runs each) stopped at the step limit or the token limit.
- The agent designs reach the 15-step limit in at least half of the runs. A higher limit can prove more, but it costs more. This was not measured.
- Each design ran once per function in each run. With 36 functions, a difference of about 5 functions is near the run-to-run variance (B gave 13 in run 1 and 8 in run 2).
- The mutation check unparses the function, so it can miss a docstring change. The control run rejects such a file.

**Decision.** The user chose D for stage 2 on 2026-10-10.

### 2026-10-10 — Stage 2: design D in `characterize`

**What was built.** `characterize` in `slopgate/review.py` is now design D, a plain tool loop:

- Super gets the system prompt `AGENT_RULES`, the task `AGENT_TASK`, and one tool, `execute(command)`. The prompts are the stage 1 texts, with the paths made relative to the repo root.
- The commands run in a sandbox session that starts from the checkpoint and keeps files between commands: `Local.session` (a copy in a temporary folder) or `Contree.session` (a ConTree session, `disposable=False`). The agent loop runs on the runner. The session gets no API key.
- `llm.step` sends one step of the loop, with thinking off.
- The loop stops when a reply has no tool call, or at `AGENT_STEPS = 15` model calls, `AGENT_SECONDS = 120` s, or `AGENT_TOKENS = 150,000` input tokens (`slopgate/config.py`).
- Each command gets the time that is left of the 120 s. ConTree runs it as `timeout -k 5 <n> sh -c <command>`, so a hung command returns exit 124.
- A cut-off reply or an error ends the loop, but the file that the agent already wrote is still judged.
- `check` judges the test file on the original checkpoint, never in the session. It returns the rejection text, or `None` when the tests prove.

The old flow is deleted: the tests prompt, the calls form and the recorder, `CANNOT_TEST`, the retry prompts, the reply parser, and `called_code`. `bench/characterize.py` now measures only the gate's `characterize`, with the mutation check. The stage 1 bench (designs A to D) is in commit a834fac. The `bench` extra (deepagents, langchain-openai) is removed.

**Changes after the code review.** An Opus review found 14 points. These were applied:

- A ConTree command at the time limit raised `OperationTimedOutError` and lost the agent's work. Now the `timeout -k 5` wrapper ends it in the sandbox first.
- An error late in the loop rejected a file that could pass. Now the file is still judged.
- The limit check is now before each model call. So each of the 15 paid replies runs its tool calls (in stage 1, the 15th reply was dropped).
- `check` returns a text, and the `Check` type is deleted.
- `shell` passes `stdin=subprocess.DEVNULL` and cannot block after a kill.
- The recall fixture for `shell` is a copy with a different approach (`subprocess.run(timeout=...)`). The search still finds it.

Not applied, with the reason:

- A context manager for the session. CPython frees the temporary folder when `characterize` returns.
- Merging `llm.complete` into `llm.step`. No current defect needs it.

**Worked example.** Demo PR #1 (agno-nymous/slopgate-demo, 0584a3a to fc03fcc), dry run:

| Result | Before (old flow) | After (design D) |
|---|---|---|
| Suggestions | 0 | 0 |
| Follow-ups | 2 | 2 |
| Rejected | 0 | 0 |

- `format_total` is an exact copy of `money`, so it needs no characterization.
- `discounted` is a wrapper. Its caller `promo_total` got 9 proven tests before. With the agent, it got 7 proven tests in one run and 6 in another.

**Measured results.**

- `uv run pytest -q`: 277 passed, 16 deselected, in 3 min 36 s. Before stage 2, there were 302 tests in 9 min 41 s. The tests of the deleted flow are gone.
- Live tests (`-m live`), 6 passed:
  - `test_contree_session_hides_the_api_key_and_ends_a_hung_command`: `env` shows no `NEBIUS_` name, and `sleep 30` with a limit of 3 s returns exit 124.
  - `test_agent_proves_characterization_tests`: real Super proves `apply_discount` and `broken_rule`.
  - The wrapper, Contree-against-Local, and install tests.
- Live bench row before the review fixes: `base36_to_int` proved in 26.9 s, 7 model calls, 10,828 input tokens, $0.005. The tests killed 5 of 5 mutants.

**Known limits.**

- There is no cheap "cannot test" exit now. An untestable function costs up to 15 calls and 150,000 input tokens, about $0.05.
- The gate characterizes one function at a time. With a median of about 55 s for each function, a pull request with 10 candidates takes about 10 min.
- `characterize` itself is still not proved (step limit or token limit).
- The judge, the rewrite proof, and the repo tests still have no time limit. Ticket 33 has this work.
- With `--sandbox local`, the agent's commands run on the host, in a copy of the repo, with the secrets removed from the environment. Pull request code already ran on the host in this mode.

**Tickets 29, 30, 31, and 35.** All are wontfix, and each has a Comments entry with the reason. Ticket 10 is now blocked by 41 instead of 30 and 35.
