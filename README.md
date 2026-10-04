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

- One review with event `COMMENT`. Each rewrite that edits only lines the pull request added is a suggested change, with the slop kind, complexity and nesting before and after, and the number of characterization tests that passed.
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
