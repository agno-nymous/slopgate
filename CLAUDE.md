# Slopgate

Slopgate finds slop in Python code that coding agents write. It has two parts:

1. **The gate** (`slopgate review`): a GitHub Action that reviews each pull request. It rewrites slop with NVIDIA Nemotron models on Nebius Token Factory. It keeps a rewrite only when characterization tests and the repo's own tests pass on it in a sandbox. It posts the rewrite as a GitHub suggested change.
2. **The hook** (`slopgate hook`): a Claude Code PostToolUse hook. When the agent writes a function that copies an existing one, the hook adds a note to the agent's context. It never blocks, and it always exits 0.

`spec.md` is the full spec. `README.md` tells users how to install the gate and the hook.

## Work on this repo

- Run `/start-dev` (`.claude/skills/start-dev/SKILL.md`) to work the next ticket end to end. Add a ticket number to work a specific one.
- The tickets are in `issues/`, one file each. **`issues/ROADMAP.md` gives the next ticket and the order.** `docs/agents/issue-tracker.md` gives the ticket format and the status values.
- Do one ticket on one branch, and finish it with a pull request to `main`.
- The Slopgate workflow runs on a self-hosted runner on the user's Mac (ticket 27). It starts when a pull request opens. If the runner is offline, the job waits in the queue. Then run `uv run --env-file .env slopgate review --pr <number>` by hand.
- **The Slopgate workflow is disabled since 2026-10-08** (`gh workflow disable Slopgate`). The user turned it off until the design of ticket 36 is done, because the gate posted wrong slop kinds on PR #20. Pull requests get no `slopgate` check now: verify a gate change with a local dry run on the PR head. Turn it on again only when the user says so: `gh workflow enable Slopgate`.
- Ask the user before every commit and every push.
- Start each commit message with the ticket number: `ticket-<NN>: type(scope): message`, for example `ticket-18: feat(llm): add decide`.
- When a ticket's code is done, run a code review with the `pstack:thermo-nuclear-code-quality-review` skill before the commit (`/start-dev` step 4).
- Write tickets, ticket comments, pull request text, and replies in ASD-STE100 Simplified Technical English: one idea per sentence, short sentences, active voice, one term for one concept.
- When a ticket is done, add a `## Comments` entry with a worked example and the measured results.
- The CI has no branch protection (the repo is private on a free plan). Do not use auto-merge: it merges before the checks finish. Wait for the checks to pass, then merge.
- The `slopgate` and `slopgate-demo` repos stay private until the submission. Make both public before 2026-10-30, 10:00 PT. Before `slopgate` is public, set `runs-on: ubuntu-latest` in `.github/workflows/slopgate.yml` and remove the self-hosted runner: on a public repo, a pull request from a fork could run its code on the Mac. Also remove the `PHOENIX_COLLECTOR_ENDPOINT` env line from the workflow with the self-hosted runner.

## Commands

```bash
uv sync
PHOENIX_HOST=127.0.0.1 uvx arize-phoenix serve   # local Phoenix for traces; set PHOENIX_COLLECTOR_ENDPOINT in .env to trace
uv run pytest -q                                   # offline tests; fakes replace the models and the sandbox
uv run --extra hook --env-file .env pytest -m live -q   # live tests against Token Factory; the hook extra runs the embedding tests
uv run --env-file .env slopgate review --repo <repo> --base <ref> --head <ref> --dry-run --sandbox local
uv run --env-file .env slopgate review --pr <number>   # review a PR on this machine and post to GitHub
uv run --extra hook slopgate index --repo <repo> --ref HEAD   # base index, plus the hook's ONNX model and store
```

The live tests are marked `live` and are off by default (`addopts` in `pyproject.toml`).

## Secrets

`.env` holds `NEBIUS_API_KEY` and `NEBIUS_PROJECT_ID`. It is in `.gitignore`. Never print it, never paste a key into a file or a message, and never commit it. The user sets the GitHub secrets.

## Code map

| File | What it does |
|---|---|
| `slopgate/cli.py` | Command-line entry: `review`, `index`, `hook`. Imports are lazy, so `slopgate --help` takes 0.03 s. |
| `slopgate/review.py` | The gate: find candidates, write characterization tests with an agent loop in a sandbox session (`characterize`, ticket 41), run the tests against boundary mutants and give the survivors to a hint round of the agent (`harden`, ticket 51), rewrite, prove in the sandbox. `broken_rule` rejects a rewrite that changes the operator of a comparison on the same two operands (ticket 51). The duplicate checks and the proofs of the candidates run in a thread pool (`WORKERS` in `config.py`). The repo suite runs once for all accepted rewrites. The repo suite runs once on the original code too (`baseline`, ticket 48), and a test that fails there does not reject a rewrite. All model prompts of the gate are here. |
| `slopgate/kinds.py` | The slop kinds: `classify` (Ruff, vulture, and the `flattenable` and `repeated_checks` AST checks; no model call), the fix texts, and `leftover` (the check that a rewrite removes the slop). |
| `slopgate/github.py` | Posts the review, the follow-up pull request, and the summary. |
| `slopgate/sandbox.py` | `Local` (temporary folder) and `Contree` (Nebius sandbox). Each run starts from one checkpoint. `session(checkpoint)` gives the test agent a session that keeps files between commands. `commands` chooses the install and the image. For a repo that uses setuptools-scm or hatch-vcs and has no `.git_archival.txt` with `describe-name:`, it sets `SETUPTOOLS_SCM_PRETEND_VERSION` to the last tag (ticket 58). Only `Contree` pins (`Contree.pins`): the repo lock (`uv.lock`), or for a merge-base from before Python 3.12 the dependency versions of its date on the Python of its date (`old_python`: the newest minor released 90 days before, 3.6 at the least; ticket 59), or else `pip install -e .`. For an old commit, `atomicwrites` is out of the date limit, and the build of a setuptools-scm repo uses setuptools ≤ max(commit date, `SETUPTOOLS_EDITABLE`) (ticket 68). `Contree.prepare` gets the image with `images.oci`, which imports a missing tag from Docker Hub. |
| `slopgate/llm.py` | Token Factory client: `complete` (text), `decide` (forced tool call, returns a pydantic object), `step` (one call of the test agent's tool loop), and `yes_probability` (one-token yes/no with logprobs). |
| `slopgate/embed.py` | CodeRankEmbed embeddings for the hook only. Compiles to int8 ONNX in `~/.cache/slopgate/`. |
| `slopgate/index.py` | Function index of a commit, in `.slopgate/<sha>.json`, and keyword search over it. |
| `slopgate/live.py` | The hook. Its store is `.slopgate/live.db` (SQLite). |
| `slopgate/diff.py`, `slopgate/functions.py` | Changed functions between two refs, `old_function` (the same function at the merge-base, so the gate keeps only kinds that the pull request adds), the `.py` files of a commit that decode (`python_sources`), function parsing, `dedent` (by the indent of the `def` line; use it, not `textwrap.dedent`), token sets of functions, and the test-file rule (`is_test_file`, `pytest_patterns`) that the gate and the hook share. |
| `slopgate/trace.py` | Phoenix tracing: start, span, output, bind. Off unless PHOENIX_COLLECTOR_ENDPOINT is a local address; with tracing off it imports no OpenTelemetry module. |
| `slopgate/config.py` | Model names, thresholds, and prices. |

## Model rules

- Lightning (`nvidia/Nemotron-3_5-Lightning`), Super (`nvidia/nemotron-3-super-120b-a12b`), and Ultra (`nvidia/Nemotron-3-Ultra-550b-a55b`) are all thinking models. Super runs the test agent and writes rewrites. Ultra does the rewrite retry and the summary. Lightning runs only the hook's yes/no check. The static checks (Ruff, vulture, `flattenable`, and `repeated_checks`) find all slop kinds of the gate except `duplicate`, which Super decides. They call no model.
- **Turn thinking off on every request:** `extra_body={"chat_template_kwargs": {"enable_thinking": False}}`. With thinking on, a complex request can spend the whole output limit on reasoning and return an empty or cut-off reply (`finish_reason: "length"`). A forced tool call does not turn thinking off by itself.
- `complete` sends `max_tokens=32768` (`MAX_OUTPUT_TOKENS`). The server default is 8,192 output tokens, and one long test file passed it on PR #17.
- **Code comes back as one ```` ```python ```` block in markdown. Never ask for code inside JSON or inside tool-call arguments.** In the fair run on 2026-10-06 (equal prompts, thinking off, 54 replies each), markdown proved 45 and a forced tool call proved 41, with 3 broken files from wrong bracket types (ticket 20).
- **Exception: the characterization test agent** (`characterize`, ticket 41). Super gets one `execute` tool in a sandbox session and writes the test file with a heredoc. It can run the code, read files, and see the failures and the missed branches. On 36 functions (2026-10-10), it proved 24 and the old markdown flow proved 7. 2 of 80 heredoc writes were broken. A plain tool loop proved more than Deep Agents (19), so the gate uses no agent framework. Ultra as the test agent proved 4 of 24 runs on 8 functions (Super: 22 of 24, 2026-10-12): Ultra probed with `python -c` for 15 steps and wrote no test file. The agent rules forbid package installs: the judge runs on a fresh copy, so an installed package is missing there (ticket 55: `RangeField.to_python` went from 0 of 9 to 3 of 3). After round 1 passes, the gate runs the tests against boundary mutants of each comparison (`==` to `>=`, and so on). If a mutant survives, a new agent conversation gets the surviving changes and adds tests (ticket 51). The gate uses that file only if it kills more mutants and loses no kill. On 37 functions (2026-10-17), the kill rate of real boundary mutants went from 70% to 87%, and the hint round ran on 7 of 31 proved functions for 24 s to 60 s each.
- **Decisions** (a kind, a verdict, a reason) come back as a forced tool call whose parameters are a pydantic model (`decide`, ticket 18). The chat template shows each `Field(description=...)` to the model, so the descriptions act as instructions. Put the reason field before the verdict field. Do not use `response_format` with a JSON schema: the server enforces the shape there, but the model does not see the descriptions.
- Never offer "cannot do it" as an optional tool next to a text reply. Models choose the optional tool too often (12 of 12 false refusals in one test). Use a text line such as `CANNOT_TEST: <reason>` instead (the tests prompt used this line until ticket 41).
- A schema makes the shape of a reply certain, not its content. The sandbox proof stays the check for content.
- Frameworks were measured and rejected: DSPy (Super writes its field markers wrong, and DSPy then falls back to JSON without telling you) and Pydantic AI mixed outputs (the over-calling problem above).

## Hook rules

- The hook runs as a new process for each file write. It must exit 0 and print errors only to stderr.
- With no candidate, it makes no network call.
- The hook writes the store before it calls the model.

## Tracing rules

- Set `PHOENIX_COLLECTOR_ENDPOINT` only in this repo's `.env` and `.claude/settings.local.json`. Never set it in a shell profile.
- A thread pool that sends model requests wraps its function with `trace.bind`. Otherwise its spans lose their parent.
- A script that calls `review` functions directly must call `trace.start(<project>)` first. Setting `PHOENIX_COLLECTOR_ENDPOINT` alone sends no trace, and the CLI is the only caller of `trace.start`.
- The sandbox environment drops `NEBIUS_*`, `PHOENIX_*`, `OTEL_*`, `GH_TOKEN`, `GITHUB_TOKEN`.
