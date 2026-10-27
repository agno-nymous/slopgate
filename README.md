# Slopgate

Slopgate reviews each Python pull request for slop: deep nesting, repeated checks, swallowed errors, one-use wrappers, long if/elif chains, dead code, and new functions that copy an existing helper. It rewrites each finding with NVIDIA Nemotron models on Nebius Token Factory. It keeps a rewrite only if characterization tests of the original code and the repo's own tests pass on it in a Nebius Token Factory Sandbox.

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
- An inline note on each function with slop that Slopgate did not rewrite. The note gives the slop kinds and the fix, and says that Slopgate changed nothing.
- A short summary by Nemotron Ultra with the counts of suggestions, follow-up changes and notes, and the token cost.

Slopgate never fails CI. A pull request without findings gets no comment. If the sandbox cannot install the repo, the pull request gets one notice comment.

### How Slopgate installs your repository

The sandbox is a ConTree Linux container (Debian, root, network access) with Python 3.12, or an older Python for an old commit (rule 3). Slopgate installs pytest, coverage, and uv first. Then it installs your repository. Slopgate uses the first rule that applies:

1. `setup` in `.slopgate.toml`. The sandbox uses Python 3.12 and runs only your `setup`. This override also replaces the old Python and the date pins of the other rules.
2. `uv.lock` with `pyproject.toml`: the locked versions of all dependency groups, then the project itself.
3. `pyproject.toml` or `setup.py`: `pip install -e .`. For a commit from before 2023-10-02, the sandbox installs the dependency versions released before the commit date. It uses the newest Python that was released at least 90 days before the commit (3.6 to 3.11).
4. Only `requirements*.txt`: `pip install -r` for each file.
5. None of these: no install.

If the pinned install of rule 2 or 3 fails, the sandbox falls back to `pip install -e .`. If the repository takes its version from git (setuptools-scm, hatch-vcs), the sandbox has no `.git`, so Slopgate sets the version from the last tag. This export applies to rules 2 and 3. A `setup` override must set `SETUPTOOLS_SCM_PRETEND_VERSION` itself.

After the install, Slopgate runs the `test` command once with `--collect-only` (only when `test` is a pytest command). If no test collects, or the conftest does not import, the gate stops and posts one notice. It writes no test and rewrites nothing. The check passes while at least one test collects. A test module that does not import (for example, a missing optional test dependency) does not stop the gate.

If this install fails, put the install in `.slopgate.toml`. The `setup` text is one shell script. Join commands with `&&`: the sandbox reads only the exit code of the last command, so it can miss an earlier failure. Slopgate then runs `python -m pytest -q -rfE`, or your `test` command:

```toml
[sandbox]
setup = "pip install -e '.[test]'"
test = "python -m pytest -q tests/unit"
```

Two examples of `setup`:

- Test extras: `pip install -e '.[test]'`
- System libraries and extras: `apt-get update && apt-get install -y build-essential libfreetype6-dev && pip install -e '.[test]'`

Slopgate runs the `test` command once on the original code. A test that fails there does not reject a rewrite. The `test` command must be one pytest run. Do not chain commands with `&&`: a failure in the first run stops the second run, and Slopgate cannot see that. Do not use `-x`. Keep `f` and `E` in `-r` (pytest 5.4 and later show them by default). If a run cannot be compared, every failing test rejects the rewrite.

GitHub does not start workflows for pull requests that the workflow token opens, so CI does not run on the follow-up pull request until someone pushes to it.

## Review a pull request on your machine

`slopgate review --pr <number>` reviews one pull request from a local clone and posts the review to GitHub. It does not need a workflow run. It fetches the base and head commits of the pull request from `origin`. It does not change your working tree. Log in with `gh auth login` first. Set `NEBIUS_API_KEY` and `NEBIUS_PROJECT_ID` in the environment. Add `--sandbox local` to run the tests on your machine. Add `--dry-run` to print the result and post nothing.

```sh
slopgate review --pr 12
```

## Try Slopgate on your machine

The [showcase site](docs/demo/index.html) shows recorded reviews, and its try-it page runs the gate on one function in your browser with your own key. To run Slopgate yourself, you need two Nebius keys, `uv`, and `git`. The keys stay on your machine. A dry run posts nothing to GitHub.

1. Get `NEBIUS_API_KEY` and `NEBIUS_PROJECT_ID` from https://tokenfactory.nebius.com/project/api-keys. Install `uv` from https://docs.astral.sh/uv/.

2. Set the keys in your shell:

   ```sh
   export NEBIUS_API_KEY=...
   export NEBIUS_PROJECT_ID=...
   ```

3. Clone a repository that has a pull request or two commits with Python changes. This example is the demo repository of Slopgate:

   ```sh
   git clone https://github.com/agno-nymous/slopgate-demo
   cd slopgate-demo
   ```

4. Review the changes between a base commit and a head commit. `--base` and `--head` take any git ref:

   ```sh
   uvx --from git+https://github.com/agno-nymous/slopgate slopgate review --repo . --base 0584a3a --head 441d235 --dry-run
   ```

The command prints the review as JSON: `suggestions`, `followup`, `rejected`, and `notes`. The recordings on the showcase page are this output.

A review of this example took 84 s in one run and 210 s in another. It cost $0.019 in Token Factory tokens (the Phoenix trace of the 210 s run). A larger pull request costs more, because each changed function gets a test agent run in a ConTree sandbox.

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

## Gate benchmark on SWE-bench (development of this repo only)

The gate benchmark runs the whole gate (`slopgate review`) on SWE-bench Lite instances with injected slop. The gate builds its own sandbox with its normal install, as it does for a user. The hidden tests run on the SWE-bench Docker image of each instance in ConTree. The benchmark injects one slop kind into each of up to 3 functions whose body the instance's hidden tests run. It keeps an injection only if a `raise` at the start of the function breaks a hidden test. Then it runs the gate on the injected commit. The hidden tests (the files of the instance's test patch) are deleted from the commit, so the gate never sees them. After the gate, the benchmark runs the hidden tests on each accepted rewrite.

Run it with one command:

```sh
uv run --env-file .env python -m bench.swebench
```

The command skips each stage that is already done. To run one stage only, add `select`, `run`, `report`, or `install`. `select` writes the ground truth (kind, function, file) before the gate runs. It also saves the injected commit of each instance as a git bundle in [`bench/results/swebench/heads/`](bench/results/swebench/heads/). On a machine with no local clones, `run` clones each repo from GitHub and gets the injected commit from its bundle. The hidden tests use ConTree checkpoints of the Nebius project that ran `select`. So a rerun from a fresh clone works only with a key of that project. `run` skips each instance that `runs.json` already holds, so delete that file first: `rm bench/results/swebench/runs.json && uv run --env-file .env python -m bench.swebench run`.

The results are in [`bench/results/swebench/swebench.md`](bench/results/swebench/swebench.md) and [`bench/results/swebench/swebench.json`](bench/results/swebench/swebench.json). They give the detection recall, the complexity change, the acceptance rate, the silent-break rate, and the token cost, for each slop kind and in total. [`bench/results/swebench/image-sandbox/`](bench/results/swebench/image-sandbox/swebench.md) holds an earlier run in which the gate also used the SWE-bench image. Ticket 10 explains them.
