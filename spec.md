# Slopgate v1

Status: ready-for-agent

Context: entry for the Nebius x NVIDIA Global AI Hackathon, Coding and Agentic Engineering track. Deadline 2026-10-30, 10:00 PT. Solo build.

## Problem Statement

Coding agents now write a large share of pull requests. People cannot review them as fast as agents write them. The code has the same defects again and again:

- deep nesting where guard clauses would do
- redundant checks and `try/except` blocks that swallow errors
- one-use wrapper functions
- long `if/else` chains where a lookup table would do
- new functions that re-implement a helper that already exists in the repo

Static tools such as `ruff` and `vulture` find unused code only. They cannot see these patterns. An LLM can rewrite the code, but a reviewer cannot trust a rewrite without proof that behavior did not change.

The duplicate problem starts earlier, while the agent works. The agent does not look for an existing helper, so it writes a new one. By the time a reviewer sees the pull request, the duplicate is already part of the design.

## Solution

Slopgate has two parts. Both handle Python only.

1. **Pull request gate.** A GitHub Action reviews each pull request. It finds slop in the functions the pull request adds or changes, rewrites them with NVIDIA Nemotron models on Nebius Token Factory, and proves each rewrite in a Nebius Token Factory Sandbox. It posts only the proven rewrites, as GitHub suggested changes that the author applies in one click. Each suggestion shows complexity before and after and the test evidence.
2. **Live duplicate flag.** A Claude Code hook watches the agent while it plans and while it writes files. When the agent plans or writes a function that does the same job as an existing function, the hook adds a note to the agent's context that names the existing function. The hook never blocks the agent. When no candidate is found, the hook makes no network call and returns in milliseconds.

The safety proof works through characterization tests. These are tests that record what the original code does now, bugs included. A rewrite is kept only if those tests and the repo's own tests pass on the rewritten code.

## User Stories

### Pull request author

1. As a pull request author, I want slop in my pull request found automatically, so that I do not wait for a human reviewer to point it out.
2. As a pull request author, I want each fix as a GitHub suggested change, so that I can apply it in one click.
3. As a pull request author, I want every suggestion to state which slop pattern it fixes, so that I learn what to avoid.
4. As a pull request author, I want every suggestion to show cyclomatic complexity and nesting depth before and after, so that I see the size of the improvement.
5. As a pull request author, I want every suggestion to state how many characterization tests passed in the sandbox, so that I can trust that behavior did not change.
6. As a pull request author, I want to see the characterization tests behind a suggestion, so that I can check what was proven.
7. As a pull request author, I want rewrites that touch lines outside my diff delivered as a separate pull request into my branch, so that I can still accept them.
8. As a pull request author, I want a new function that duplicates an existing helper replaced by a call to that helper, so that the codebase keeps one version of the logic.
9. As a pull request author, I want a duplicate suggestion to state any behavior difference between my function and the helper, such as a different error on `None`, so that I decide with full information.
10. As a pull request author, I want a one-use wrapper function removed and its single caller updated, so that the call path is shorter.
11. As a pull request author, I want the gate to leave my code alone when it cannot prove a rewrite, so that I never get an unsafe suggestion.
12. As a pull request author, I want the gate to never fail or block my CI, so that it cannot stop a merge.
13. As a pull request author, I want one short summary comment per review, so that I see the result at a glance.
14. As a pull request author, I want no comment at all when my pull request has no Python changes, so that the gate adds no noise.
15. As a pull request author, I want a clear notice when the gate cannot install my repo in the sandbox, so that I know why it proved nothing.

### Repo maintainer

16. As a maintainer, I want to install the gate with one workflow file and one API key, so that setup takes minutes.
17. As a maintainer, I want the gate to work out how to install my repo and run its tests from `pyproject.toml` or `requirements*.txt`, so that most repos need no config.
18. As a maintainer, I want an optional config file that sets the install and test commands, so that unusual repos still work.
19. As a maintainer, I want to change the thresholds (complexity, nesting, duplicate score), so that I can tune noise for my codebase.
20. As a maintainer, I want rewrites to add no new classes and no new functions, so that the gate removes abstraction instead of adding it.
21. As a maintainer, I want rewrites to keep each function's signature, so that no caller breaks.
22. As a maintainer, I want the gate to skip functions whose behavior depends on time, randomness, or I/O when it cannot pin that behavior down, so that flaky tests never count as proof.
23. As a maintainer, I want the gate to reject characterization tests that miss a branch of the original function, so that weak tests never count as proof.
24. As a maintainer, I want to know the token cost of each review, so that I can predict spend.

### Coding agent user (live flag)

25. As a developer who uses a coding agent, I want the agent told when it writes a function that duplicates an existing one, so that it reuses the existing one.
26. As a developer who uses a coding agent, I want the agent told when a step in its plan is already done by an existing function, so that it changes the plan before it writes code.
27. As a developer who uses a coding agent, I want the note to name the existing function, its file, and a confidence score, so that the agent can act on it.
28. As a developer who uses a coding agent, I want the hook to never block a write, so that it cannot stop my agent's work.
29. As a developer who uses a coding agent, I want the hook to add no visible delay when it finds no candidate, so that it feels as fast as grep.
30. As a developer who uses a coding agent, I want functions that the agent wrote earlier in the session to be checked too, so that it does not re-write its own helper.
31. As a developer who uses a coding agent, I want the code search model to run on my laptop CPU with modest memory, so that I need no GPU and no code leaves my machine for the search step.
32. As a developer who uses a coding agent, I want to build the index with one command, so that setup is simple.
33. As a developer who uses a coding agent, I want the index refreshed after `git pull`, so that new teammates' functions are found.
34. As a developer who uses a coding agent, I want to choose the classifier backend (Nemotron by default, Jev optional), so that I can trade speed against cost.

### Hackathon judge

35. As a judge, I want a public demo repo with real gate reviews on its pull requests, so that I can see the gate work without installing it.
36. As a judge, I want benchmark numbers (detection recall, complexity change, acceptance rate, silent-break rate), so that I can judge accuracy, not just a demo.
37. As a judge, I want to see which Nemotron model does which job and why, so that I can judge the use of Token Factory.
38. As a judge, I want to see the sandbox checkpoint-and-fork pattern explained, so that I can judge the use of Sandboxes.

## Implementation Decisions

### Entry points (the two test seams)

```
▸ `slopgate review` — command-line entry of the pull request gate
  - Does: takes a repo, a base ref, and a head ref; runs the full gate; posts the review, or with `--dry-run` prints the exact review payload as JSON.
  - Impact: behavior — the GitHub Action, the benchmark, and the tests all call this one entry.

▸ `slopgate hook` — command-line entry of the live duplicate flag
  - Does: reads one Claude Code hook event as JSON on stdin and prints either a note for the agent or nothing.
  - Impact: performance — this runs on every agent file write, so the no-candidate path must stay local and fast.

▸ `slopgate index` — command-line entry that builds the function index
  - Does: indexes every function of the repo at a git ref.
  - Impact: behavior — both entry points above read this index.
```

The `--dry-run` JSON has three parts: `suggestions` (GitHub review comment payloads), `followup` (file edits for the follow-up pull request), and `rejected` (candidate kind plus reason).

### Modules

- **Function model.** Parses a Python file into functions and methods with qualified name, line range (decorators included), source, and a structure hash. The structure hash removes the docstring and renames the function, arguments, and local names to placeholders, so copies that differ only in names get the same hash.
- **Metrics.** Cyclomatic complexity from `radon`, maximum nesting depth (`if`, `for`, `while`, `try`, `with`, `match` each add one level), and line count. Works on indented method source.
- **Diff mapping.** Maps a base-to-head git diff to the changed functions at head, with the set of added line numbers per function. Only added or modified Python files count.
- **Index.** Stores per function: the function record and the structure hash. The gate searches it by token Jaccard. The index stores no vectors. The hook store of the live flag holds the CodeRankEmbed vectors. The index is saved in a `.slopgate/` folder in the repo, which git ignores.
- **Embedder.** CodeRankEmbed (`nomic-ai/CodeRankEmbed`, 137M parameters, MIT license) runs on the local CPU for the live flag only. The hook compiles the model once per machine to `~/.cache/slopgate/` as int8 ONNX.
- **LLM client.** One function sends a prompt to a Token Factory model and returns text, with an optional JSON mode. One more function sends one step of the test agent's tool loop. Temperature 0. Every LLM call goes through it, so tests replace it with a fake.
- **Triage.** Static checks find the kinds, with no model call. The kinds are `nesting`, `redundant_check`, `swallowed_error`, `wrapper`, `lookup_table`, `dead`, and `duplicate`. Ruff finds `swallowed_error`, `lookup_table`, and `dead`. Vulture also finds `dead`. `nesting` is a nesting depth of more than 2, with an `if` that a guard clause or a merged condition can make flat. `redundant_check` is an `if` whose condition an earlier check in the same function already decides (an AST check). The wrapper and duplicate searches find `wrapper` and `duplicate`.
- **Duplicate search.** For each new module-level function: an exact structure-hash match needs no model call. Otherwise, keyword search (token Jaccard) over an index built at the base ref, with a score floor of 0.30 and the top 5 results. Nemotron Super then decides whether the candidate does the same job and states any behavior difference. The function itself and other changed functions are excluded.
- **Proof.** Each candidate gets its proof in a thread pool of 8. For each candidate:
  1. A test agent writes characterization tests (ticket 41). Nemotron Super gets one `execute` tool on a sandbox session that starts from the checkpoint. It reads files, runs the code and the tests, sees the failures and the missed branches, and writes the test file with a heredoc. The agent loop runs on the runner, outside the sandbox. It stops after 15 model calls, 120 s, or 150,000 input tokens. Each test file imports its target through exactly one import line.
  2. The tests run twice on the original code. Both runs must pass with identical output, and branch coverage of the target function must be complete.
  3. For a duplicate, the same tests run against the existing helper by swapping that one import line. This is the differential test that proves equivalence.
  4. Nemotron Super rewrites the code. A rule check runs before any sandbox time is spent. It requires: the code parses, the signature is unchanged (or, for `wrapper` and `duplicate`, the function is gone), no new class, and no more functions than before.
  5. The rewrite runs against the characterization tests.
  6. If the rewrite breaks a rule, leaves the slop, or fails the characterization tests, Nemotron Ultra retries once with the failing output.
  7. After all candidates are done, the repo's own tests run once on all accepted rewrites together. If this run fails, each rewrite runs alone. The gate rejects a rewrite that fails alone, with the reason "rewrite fails repo tests". If two rewrites pass alone but fail together, the gate keeps the first rewrite. It rejects the second rewrite with the reason "rewrite conflicts with another rewrite". The repo's own tests also run once on the original code, in parallel with the characterization tests. A repo test that fails on the original code does not reject a rewrite. A failing run counts as the same only if it ran the same number of tests and each failed test also failed on the original code. If a run cannot be compared (the run stopped early, or a failure has no line in the summary), every failing test rejects the rewrite.

  For a wrapper, the characterization tests target the wrapper's single caller. For a duplicate, callers are rewritten to call the existing helper. A wrapper or a duplicate runs the repo's own tests in its own proof, not in step 7.
- **Sandbox runner.** The runner installs the repo once per pull request in a ConTree sandbox from `python:3.12-slim`, by uploading a tar file of the ref. It keeps the installed state as a checkpoint, and every trial starts from that checkpoint. At most 8 trials run at the same time. Install and test commands come from an optional `.slopgate.toml`, then `pyproject.toml`, then `requirements*.txt`. An install failure raises an error that carries the last 20 output lines.
- **GitHub output.** A rewrite goes inline as a suggested change only when it edits one file and every replaced line is in the diff's added lines. All other rewrites go into a follow-up pull request on branch `slopgate/<head branch>` that targets the author's branch. The review is posted with event `COMMENT`, never `REQUEST_CHANGES`. Nemotron Ultra writes one summary per review. Posting uses the `gh` CLI.
- **Live flag hook.** On a file write (Claude Code `PostToolUse` on `Write` and `Edit`), the hook:
  1. parses the new functions;
  2. checks for a hash match;
  3. runs keyword and vector search;
  4. calls the classifier only when a candidate passes the score floor;
  5. adds the new functions to the index.

  On plan submission (`PreToolUse` on `ExitPlanMode`), it splits the plan into steps, searches the summaries, and makes one batched classifier call. The note goes into the agent's context and never blocks.
- **Classifier.** The default is Nemotron Lightning, limited to a one-token yes/no answer, with the token log-probability as confidence. The flag threshold is 0.8. Jev is an optional backend behind the same interface.

### Models

| Job | Model |
|---|---|
| Hook yes/no duplicate check | `nvidia/Nemotron-3_5-Lightning` |
| Characterization tests, rewrites, duplicate check | `nvidia/nemotron-3-super-120b-a12b` |
| Retry and review summary | `nvidia/Nemotron-3-Ultra-550b-a55b` |

Check these IDs against the Token Factory model list in the first ticket.

### Constraints

- Python 3.12. MIT license.
- Token Factory base URL `https://api.tokenfactory.nebius.com/v1/`, key in `NEBIUS_API_KEY`.
- Thresholds: complexity 6, nesting 2, duplicate score 0.30, flag 0.8. All four are in one config module.
- Duplicate and wrapper handling apply only to module-level functions. Methods get in-place rewrites only.
- Credit budget: about $50 of Token Factory credit in total.

## Testing Decisions

- A good test drives a seam with real input and checks external output: the JSON from `slopgate review --dry-run`, or the stdout of `slopgate hook`. It never asserts on internal functions or data structures.
- **Seam 1 tests** use fixture git repos with a base commit and a head commit that adds known slop:
  - a 4-level nested function
  - a one-use wrapper
  - a copy of an existing helper with a different `None` behavior
  - a function that uses `random`
  - a method inside a class
  - a change outside the diff
  - a repo that fails to install
  - a pull request with no Python changes

  They assert which suggestions appear, their before and after numbers, which candidates are rejected and why, and that every outcome exits with code 0.
- **Seam 2 tests** feed recorded Claude Code hook payloads. They assert that a duplicate write produces a note that names the existing function, and that a unique write produces empty output with no LLM call. They also assert that a plan step that matches an existing function produces a note, and that a function written earlier in the same session is found.
- **Fakes at three external boundaries:**
  - The LLM fake returns scripted replies.
  - The sandbox fake runs `pytest` with `coverage` in a local temp directory, so pass/fail behavior is real.
  - GitHub needs no fake, because `--dry-run` prints the payload.
- The same seam tests run against real Token Factory and ConTree under a `live` pytest marker. The default run skips them.
- Prior art: none. This is a new repo.

## Out of Scope

- Languages other than Python.
- Whole-repo audit mode.
- A GitHub App or a hosted webhook service.
- Blocking the coding agent or failing CI.
- Merging two existing duplicates into a new shared helper.
- Agents other than Claude Code for the live flag.
- Duplicate or wrapper handling for methods.

## Further Notes

- **Benchmark.** It injects slop into 30 to 50 SWE-bench commits and runs them on the preloaded SWE-bench sandbox images through `slopgate review --dry-run`. It reports detection recall, complexity change, acceptance rate, and silent-break rate: the share of accepted rewrites that fail SWE-bench's hidden tests. It runs as a Nebius Serverless Job. It also compares Jev against Nemotron as the live-flag classifier, and that comparison feeds the hackathon feedback section.
- **Submission needs:** a public repo with the MIT license visible, a README covering setup and how Nemotron, Token Factory, and Sandboxes are used, a demo repo with real reviews, and a video of at most 3 minutes.
- **Unconfirmed facts.** Sandbox runs are reported as free during the beta, but this is unconfirmed. Hackathon credit is $25 (code `NEBIUS-DEVPOST-GLOBAL26`) plus $25 from the Builders Program.
- **SDK detail to confirm.** The exact ConTree call that starts a run from a saved session state needs a short spike in the sandbox ticket.
