# Slopgate

Slopgate reviews each Python pull request for slop: deep nesting, repeated checks, swallowed errors, one-use wrappers, long if/elif chains, filler comments, dead code, and new functions that copy an existing helper. It rewrites each finding with NVIDIA Nemotron models on Nebius Token Factory. It keeps a rewrite only if characterization tests of the original code and the repo's own tests pass on it in a Nebius Token Factory Sandbox.

## Add Slopgate to a repo

1. Add two repository secrets: `NEBIUS_API_KEY` and `NEBIUS_PROJECT_ID` (from https://tokenfactory.nebius.com/project/api-keys).
2. Add this workflow as `.github/workflows/slopgate.yml`:

```yaml
name: Slopgate
on: pull_request
permissions:
  contents: write
  pull-requests: write
jobs:
  slopgate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: agno-nymous/slopgate@main
        with:
          nebius-api-key: ${{ secrets.NEBIUS_API_KEY }}
          nebius-project-id: ${{ secrets.NEBIUS_PROJECT_ID }}
```

Checkout needs full history (`fetch-depth: 0`), because Slopgate compares the pull request head with its base.

To let Slopgate open follow-up pull requests, turn on **Settings > Actions > General > Workflow permissions > Allow GitHub Actions to create and approve pull requests**. Without it, the review is still posted, and the summary links to the pushed `slopgate/<head branch>` branch instead.

## What a pull request gets

- One review with event `COMMENT`. Each rewrite that edits only lines the pull request added is a suggested change, with its slop kinds, complexity and nesting before and after, and the number of characterization tests that passed.
- One follow-up pull request on branch `slopgate/<head branch>` for every other proven rewrite. It targets the author's branch. Pull requests from forks get no follow-up branch, because the workflow token cannot push to a fork.
- A short summary by Nemotron Ultra with the accepted and rejected counts and the token cost.

Slopgate never fails CI. A pull request without findings gets no comment. If the sandbox cannot install the repo, the pull request gets one notice comment.

The sandbox runs `pip install -e .` (or `pip install -r requirements.txt`) and `python -m pytest -q`. To change either, add `.slopgate.toml`:

```toml
[sandbox]
setup = "pip install -e '.[test]'"
test = "python -m pytest -q tests/unit"
```

GitHub does not start workflows for pull requests that the workflow token opens, so CI does not run on the follow-up pull request until someone pushes to it.

## Review a pull request on your machine

`slopgate review --pr <number>` reviews one pull request from a local clone and posts the review to GitHub. It does not need a workflow run. It fetches the base and head commits of the pull request from `origin`. It does not change your working tree. Log in with `gh auth login` first. Set `NEBIUS_API_KEY` and `NEBIUS_PROJECT_ID` in the environment. Add `--sandbox local` to run the tests on your machine. Add `--dry-run` to print the result and post nothing.

```sh
slopgate review --pr 12
```

## Flag copies while Claude Code writes

`slopgate hook` checks each Python file that Claude Code writes or edits. When a new module-level function does the same job as an existing function, the hook adds a note to the agent's context. The note names the existing function, its file, and a confidence. The hook never blocks a write and always exits 0.

1. Install Slopgate with the `hook` extra in the environment where Claude Code runs:

   ```sh
   pip install 'slopgate[hook] @ git+https://github.com/agno-nymous/slopgate'
   ```

2. Index the repo once. The first run on a machine also compiles the embedding model to `~/.cache/slopgate/` (about 30 s). Later hook runs load it in about 0.3 s.

   ```sh
   slopgate index --ref HEAD
   ```

3. Add the hook to `.claude/settings.json` in the repo:

   ```json
   {
     "hooks": {
       "PostToolUse": [
         {
           "matcher": "Write|Edit|MultiEdit",
           "hooks": [{ "type": "command", "command": "slopgate hook", "timeout": 30 }]
         }
       ]
     }
   }
   ```

4. Export `NEBIUS_API_KEY` in the shell that starts Claude Code. The hook asks Nemotron Lightning only when a local search finds a likely copy.

The hook keeps the functions of the working tree in `.slopgate/live.db`. Each write updates the rows of its own file, so the agent's earlier functions are found too. Functions under `tests/` and functions named `test_*` are never checked or matched.

Files that change outside Claude Code, for example after `git pull`, stay out of date until the next write or the next `slopgate index`. To index after every pull, add `.git/hooks/post-merge` and make it executable:

```sh
#!/bin/sh
slopgate index --ref HEAD >/dev/null
```

## Trace model requests in Phoenix (development of this repo only)

Tracing sends each model request of the gate, the hook, and the live tests to a local Arize Phoenix. Use tracing only for work on this repo. Other repos do not trace.

1. Start Phoenix. It listens on this machine only.

   ```sh
   PHOENIX_HOST=127.0.0.1 uvx arize-phoenix serve
   ```

   The UI runs at http://127.0.0.1:6006.

2. Run `uv sync`. It installs the trace packages in the `dev` group (the `trace` extra).

3. Turn on tracing in this repo only. Add this line to the `.env` file of this repo:

   ```sh
   PHOENIX_COLLECTOR_ENDPOINT=http://127.0.0.1:6006
   ```

   The gate and the live tests read `.env` with `--env-file .env`.

   For the hook, add the same variable to the `env` block of `.claude/settings.local.json` in this repo. Claude Code gives that block only to sessions in this repo.

   Do not export the variable in a shell profile. Then every repo with the hook would send traces. Only a local endpoint is accepted.

Traces go to these Phoenix projects: `slopgate-gate`, `slopgate-hook`, and `slopgate-tests`. All gate runs of one pull request are one Phoenix session. All hook runs of one Claude Code session are one Phoenix session. In one pytest run, all cases of one test are one Phoenix session.

Example commands:

```sh
uv run --env-file .env slopgate review --repo . --base origin/main --head HEAD --dry-run
uv run --env-file .env pytest -m live -q -k test_super_tests_reply
```

To turn tracing off, remove the `PHOENIX_COLLECTOR_ENDPOINT` line from `.env` and from `.claude/settings.local.json`.

## Detection benchmark (development of this repo only)

The detection benchmark measures how well the gate finds slop kinds (`classify` in `slopgate/kinds.py`) on code from 12 SWE-bench Lite repos. It runs no sandbox and writes no rewrite. It uses 200 clean functions, and copies of other functions with injected slop: code transforms and Nemotron Super injections.

Run it with one command:

```sh
uv run --env-file .env python -m bench.detect
```

The command clones the repos into `~/.cache/slopgate/bench/` and skips each stage that is already done. To run one stage only, add `sample`, `inject`, `run`, or `report`. A person records a decision for each kind that the gate finds on a clean function in `bench/labels.json`. The same file records whether each Nemotron injection contains its kind. The report leaves out the invalid injections.

The results are in [`bench/results/detection.md`](bench/results/detection.md) and [`bench/results/detection.json`](bench/results/detection.json). Ticket 37 explains them.
