# Slopgate

Slopgate finds slop in Python code that coding agents write. It has two parts:

1. **The gate** (`slopgate review`): a GitHub Action that reviews each pull request. It rewrites slop with NVIDIA Nemotron models on Nebius Token Factory. It keeps a rewrite only when characterization tests and the repo's own tests pass on it in a sandbox. It posts the rewrite as a GitHub suggested change.
2. **The hook** (`slopgate hook`): a Claude Code PostToolUse hook. When the agent writes a function that copies an existing one, the hook adds a note to the agent's context. It never blocks, and it always exits 0.

`spec.md` is the full spec. `README.md` tells users how to install the gate and the hook.

## Work on this repo

- Run `/start-dev` (`.claude/skills/start-dev/SKILL.md`) to work the next ticket end to end. Add a ticket number to work a specific one.
- The tickets are in `issues/`, one file each. **`issues/ROADMAP.md` gives the next ticket and the order.** `docs/agents/issue-tracker.md` gives the ticket format and the status values.
- Do one ticket on one branch, and finish it with a pull request to `main`.
- The Slopgate gate does not run on the pull requests of this repo in GitHub. Run it locally with `--pr` before you merge.
- Ask the user before every commit and every push.
- Write tickets, ticket comments, pull request text, and replies in ASD-STE100 Simplified Technical English: one idea per sentence, short sentences, active voice, one term for one concept.
- When a ticket is done, add a `## Comments` entry with a worked example and the measured results.
- The CI has no branch protection (the repo is private on a free plan). Do not use auto-merge: it merges before the checks finish. Wait for the checks to pass, then merge.
- The `slopgate` and `slopgate-demo` repos stay private until the submission. Make both public before 2026-10-30, 10:00 PT.

## Commands

```bash
uv sync
uv run pytest -q                                   # offline tests; fakes replace the models and the sandbox
uv run --env-file .env pytest -m live -q           # live tests against Token Factory
uv run --env-file .env slopgate review --repo <repo> --base <ref> --head <ref> --dry-run --sandbox local
uv run --env-file .env slopgate review --pr <number>   # review a PR on this machine and post to GitHub
uv run slopgate index --repo <repo> --ref HEAD     # base index, plus the hook's ONNX model and store
```

The live tests are marked `live` and are off by default (`addopts` in `pyproject.toml`).

## Secrets

`.env` holds `NEBIUS_API_KEY` and `NEBIUS_PROJECT_ID`. It is in `.gitignore`. Never print it, never paste a key into a file or a message, and never commit it. The user sets the GitHub secrets.

## Code map

| File | What it does |
|---|---|
| `slopgate/cli.py` | Command-line entry: `review`, `index`, `hook`. Imports are lazy, so `slopgate --help` takes 0.03 s. |
| `slopgate/review.py` | The gate: find candidates, classify them, write characterization tests, rewrite, prove in the sandbox. All model prompts of the gate are here. |
| `slopgate/github.py` | Posts the review, the follow-up pull request, and the summary. |
| `slopgate/sandbox.py` | `Local` (temporary folder) and `Contree` (Nebius sandbox). Each run starts from one checkpoint. |
| `slopgate/llm.py` | Token Factory client: `complete` (text) and `yes_probability` (one-token yes/no with logprobs). |
| `slopgate/embed.py` | CodeRankEmbed embeddings. The hook uses an int8 ONNX copy in `~/.cache/slopgate/`. |
| `slopgate/index.py` | Function index of a commit, in `.slopgate/<sha>.json`. |
| `slopgate/live.py` | The hook. Its store is `.slopgate/live.db` (SQLite). |
| `slopgate/diff.py`, `slopgate/functions.py` | Changed functions between two refs, and function parsing. |
| `slopgate/config.py` | Model names, thresholds, and prices. |

## Model rules

- Lightning (`nvidia/Nemotron-3_5-Lightning`), Super (`nvidia/nemotron-3-super-120b-a12b`), and Ultra (`nvidia/Nemotron-3-Ultra-550b-a55b`) are all thinking models. Super writes tests and rewrites. Ultra does the rewrite retry and the summary. Lightning names slop kinds and runs the hook's yes/no check.
- **Turn thinking off on every request:** `extra_body={"chat_template_kwargs": {"enable_thinking": False}}`. With thinking on, a complex request can spend the whole 8,192-token output limit on reasoning and return an empty or cut-off reply (`finish_reason: "length"`). A forced tool call does not turn thinking off by itself.
- **Code comes back as one ```` ```python ```` block in markdown. Never ask for code inside JSON or inside tool-call arguments.** In the fair run on 2026-10-06 (equal prompts, thinking off, 54 replies each), markdown proved 45 and a forced tool call proved 41, with 3 broken files from wrong bracket types (ticket 20).
- **Decisions** (a kind, a verdict, a reason) come back as a forced tool call whose parameters are a pydantic model (`decide`, ticket 18). The chat template shows each `Field(description=...)` to the model, so the descriptions act as instructions. Put the reason field before the verdict field. Do not use `response_format` with a JSON schema: the server enforces the shape there, but the model does not see the descriptions.
- Never offer "cannot do it" as an optional tool next to a text reply. Models choose the optional tool too often (12 of 12 false refusals in one test). Use a text line such as `CANNOT_TEST: <reason>` instead.
- A schema makes the shape of a reply certain, not its content. The sandbox proof stays the check for content.
- Frameworks were measured and rejected: DSPy (Super writes its field markers wrong, and DSPy then falls back to JSON without telling you) and Pydantic AI mixed outputs (the over-calling problem above).

## Hook rules

- The hook runs as a new process for each file write. It must exit 0 and print errors only to stderr.
- With no candidate, it makes no network call.
- The hook writes the store before it calls the model.
