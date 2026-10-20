# 67 — An agent installs the test environment from the repo's own instructions

## Summary

- **Goal:** Build a working test environment for a repo that the guess install in `sandbox.commands()` cannot build. A Nemotron agent reads the README, CONTRIBUTING, tox.ini, noxfile, setup.cfg, pyproject.toml, requirements files, CI workflows, and Makefile. It runs install commands in a ConTree session and writes one install script. The gate replays the script on a new image and checks that the repo's tests collect. Example: `sphinx-doc/sphinx` at 2021-01 installs with exit 0 on `python:3.10-slim`, but its conftest fails with `TypeError: required field "lineno" missing from alias`.
- **Checkable finish condition:** On the 15 SWE-bench instances of ticket 10, plus about 6 more Lite instances, the `install` stage of `bench/swebench.py` reports the install success rate (by the gate's collection check) for the guess install, the agent with Lightning, and the agent with Super, 3 tries each, with time, tokens, and USD. The chosen model gets more instances to a working environment than the guess install, and the benchmark `run` and `report` stages are made again with it.
- **Evidence:** Before: ticket 10, run of 2026-10-18 with the plain `Contree()` install. 5 of 15 instances fail the install (setuptools-scm, ticket 58). 4 of 15 install with exit 0, but the tests cannot run (Python 3.10 is too new: sphinx-7975, sphinx-8506, sphinx-8627, requests-3362). Only 6 of 15 have a working environment, and the gate accepts 7 of 26 detected items (7 of 17 on the 6 working environments). On the SWE-bench images, it accepts 18 of 43. After: the `install` stage report and the new benchmark report.
- **Constraints:** The gate never trusts the agent: it replays the script on a new image and runs its own collection check. The agent runs only on `Contree`, and only when the guess install or the collection check fails. The `.slopgate.toml` `setup` line still wins. Follow the model rules in `CLAUDE.md`: thinking off, and a text line `CANNOT_INSTALL: <reason>` instead of an optional refusal tool. Choose Lightning or Super by the rule in section 8, which is written before the runs.

**Blocked by:** 58, 59

**Status:** ready-for-agent

**Type:** feature.

## Context

The user asked for this feature on 2026-10-18, during ticket 10: an NVIDIA Lightning agent that installs the environment from the README. Today the gate guesses an install. When the install fails, the gate posts `NO_ENVIRONMENT`. When the install passes but the environment is broken, the gate does not see it. The test agent then stops at the step limit with "characterization tests fail on original", and the Super tokens are lost.

Tickets 58 (setuptools-scm version) and 59 (Python of the commit date) are the deterministic fixes. They go first. If the guesses in section 0 hold, they fix all 9 failed instances without a model call. The agent handles what is left: missing test extras, compiler or apt builds, Python older than 3.8, and custom setups.

An Opus design agent wrote the design below on 2026-10-18. Nothing in it ran live yet. Section 9 lists the probes that come first.

## Design

### Who it is for

- **The PR author on a repo that the guess install cannot build.** Today the gate posts `NO_ENVIRONMENT` and proves nothing. With the agent, the gate installs the repo the way a developer does, then proves rewrites as usual.
- **The maintainer.** The gate prints the verified install script in the PR summary. The maintainer can review it and put it in `.slopgate.toml`. Then the next PR needs no agent.
- **The next engineer on slopgate.** One new function (`install`), one new check (`collect_error`), and two prompts. `converse` gets three parameters. No new class, no cache, no new sandbox method.

### Data shape

The agent produces one artifact: the text of `.slopgate/setup.sh` in its session. It is either a POSIX shell script or one line `# CANNOT_INSTALL: <reason>`. The gate replays that script with the existing `sandbox.prepare(repo, head, setup, image)` on a new image. The result is the same `checkpoint` type that `review()` uses today. So the install script is the same thing as the `setup` string that `commands()` returns and that `.slopgate.toml` overrides. One concept, one path.

### 0. Measured start point, and the deterministic fixes that go first

Coordinator data, ticket 10 run with the plain `Contree()` install (`bench/results/swebench/runs.json`, 15 instances):

- 5 of 15 (all `pytest-dev`) fail the install: `LookupError: setuptools-scm was unable to detect version for /repo`. The sandbox gets `git archive`, which has no `.git`. This is also a defect for real users (ticket 58).
- 3 of 15 install with exit 0, but the environment does not work on `python:3.10-slim`. `sphinx-7975` and `sphinx-8627`: the conftest fails with `required field "lineno" missing from alias` (old sphinx needs Python 3.9 or older). `requests-3362`: the date-pinned 2016 pytest runs `from UserDict import DictMixin` on Python 3.10. Characterization then fails "on original" at the step limit, and Super tokens are lost.
- 6 of 15 environments work (final run 2 of ticket 10; sphinx-8506 also has the conftest error). Acceptance: 7 of 26 detected items (on the SWE-bench image: 18 of 43).

All 8 failures have a deterministic cause. Fix them without a model first, then measure what is left for the agent.

**Fix A: the setuptools-scm version (ticket 58).** In `commands()`, if `pyproject.toml`, `setup.py`, or `setup.cfg` at the ref names `setuptools_scm`, `setuptools-scm`, or `hatch-vcs`, put `export SETUPTOOLS_SCM_PRETEND_VERSION=<v> && ` in front of the setup. `<v>` is `git describe --tags --abbrev=0 <ref>` on the host with a leading `v` removed, else `0.0.0`. The host has the history, so the version is real. Not chosen: uploading `.git`. It makes the archive much larger and sends the whole history to the sandbox for one string. Limit: the variable also applies to a dependency that builds from an sdist with setuptools-scm. Most dependencies come as wheels. The `_FOR_<DIST>` form is not in 2019 setuptools-scm versions. A `.slopgate.toml` `setup` line still wins.

**Fix B: the Python of the commit date.** Done in ticket 59 (2026-10-19), with changes: the floor is 3.6 (uv installs into 3.6 and 3.7 with `pip install --ignore-requires-python uv`), the Python must be released 90 days before the merge-base date, and 3.6 gets a non-editable uv install, then `pip install --no-deps -e .`. Ticket 59 has the measurement. The original text follows. Replace the fixed `OLD_COMMIT_IMAGE = "python:3.10-slim"` with the newest Python minor that was released before the merge-base date, from 3.8 to 3.12. Release dates: 3.8 2019-10-14, 3.9 2020-10-05, 3.10 2021-10-04, 3.11 2022-10-24, 3.12 2023-10-02. In `config.py`: `PYTHONS = [("3.8", "2019-10-14"), ...]`, and `commands()` returns `f"python:{version}-slim"`. Floor 3.8: the `uv` package needs Python 3.8 or later, and the pinned install uses uv. This gives 3.8 for `sphinx-7975` (2020-07) and 3.9 for `sphinx-8627` (2021-01), both older than the `ast` change of 3.10. For `requests-3362` (2016) it gives 3.8, where `collections.MutableMapping` still exists, so the old pytest probably does not reach the `UserDict` fallback (a guess, to verify). Ticket 53's working cases keep 3.10 (seaborn 2022-06, pylint 2022-03) or move to 3.9 (flask 2021-05). Rerun those 3 to confirm.

**Fix C: the collection check before any characterization** (`collect_error`, section 4). Inferred from the error texts: the 4 broken environments above fail `pytest --collect-only` with a nonzero exit. A conftest that does not import and a pytest that does not start both stop collection. Without this check, the exit code of the install is the only check, and the `|| pip install -e .` fallback in `pinned_install` hides a failed pinned install.

Then the agent handles only what is left after A, B, and C: missing test extras (tox.ini or nox sessions), packages that need a compiler or apt libraries, commits that need Python older than 3.8, and custom setups. Step 2 of the work order measures how many instances are left. If A, B, and C make 15 of 15 work, the agent waits for the external repos in section 8.

### 1. Session to checkpoint (ConTree SDK evidence)

SDK: `.venv/lib/python3.13/site-packages/contree_sdk`.

- `ContreeImageSync.session()` returns `ContreeSessionSync(self)` (`sdk/objects/image/_sync.py`).
- `_ContreeSessionBase._copy_self` returns `self` (`sdk/objects/session/_base.py`). `_ImageLikeBase._await` sets `new_self.uuid = UUID(result.image)` after each run (`sdk/objects/image_like/_base.py`). So each `session.run(..., disposable=False).wait()` moves `session.uuid` to the new image. The session object always names the image after its last command.
- `client.images.use(uuid)` returns `ContreeImageSync(client, uuid, None)` with no API call (`_use_image`, `sdk/managers/images/_base.py`). `strict=True` checks that it exists.
- `image.tag_as(tag)` tags an image. `client.images.use("name:tag", strict=True)` finds it or raises `NotFoundError`. A tag like `slopgate-env:ab12` parses to the tag `slopgate-env:ab12` (`utils/oci.py`, same path as `python:3.12-slim`).

Exact calls to make a checkpoint from the agent's session:

```python
session = checkpoint.session()            # in ContreeSession.__init__ today
session.run(shell=..., cwd="/repo", disposable=False, ...).wait()   # each execute
installed = client.images.use(session.uuid)   # a separate image object for later runs
```

Do not use the session object itself as a checkpoint. Its `_copy_self` returns `self`, so the 8 worker threads of `review()` would share and overwrite one `_request` and `_state`.

**Recommendation: replay, not the session image.** The gate takes the script, not the session image:

1. The gate checks the environment on a new image. Probe commands, partial installs, and edits that the agent made in the session do not exist there. The agent cannot pass by state that the script does not make.
2. The script is the reproducible artifact. It goes into the PR summary as a `.slopgate.toml` `setup` suggestion.
3. It reuses `sandbox.prepare` with no change to its interface.

Cost: one more install run (the time of the last good install in the session; guess 0.5 to 3 min, to be measured). If the eval shows replay time is the main cost, `client.images.use(session.uuid)` is the measured fallback, with the same `collect_error` check.

### 2. When the agent runs

Recommendation: **only when there is no usable environment.** That is, when `sandbox.prepare` with the `commands()` setup raises, or when it builds but `collect_error` fails. Only on `Contree` (`sandbox.pins` is true). `Local` runs commands on the host, so an install there would change the gate's own venv.

Order in `review()`:

1. `commands()` setup (the `.slopgate.toml` `setup` line, the lock, the date pin, or `pip install -e .`), as today.
2. On `Contree`: `collect_error(sandbox, checkpoint, test)`.
3. If step 1 raised or step 2 failed: `install(...)`. If it returns a checkpoint, use it.
4. If the agent fails too: `NO_ENVIRONMENT`, with both reasons. Do not characterize on an environment whose tests do not collect. The ticket 10 run shows that this only spends Super tokens to the step limit (sphinx and requests above).
5. Risk of step 4: a repo where one optional test module never collects gets no review at all. Step 2 of the work order measures this "false trigger" count first. If it is not 0, relax the check before the gate uses it to block.

Why not always: the guess install is 14 to 25 s (ticket 53 traces) and it works on maintained repos. The agent adds minutes and model cost to every PR, and it replaces a deterministic install with a model-written one.

Why also on a failed collect check, not only a failed install: `pinned_install` ends in `|| pip install -e .`, which hides a failed pinned install. Ticket 53 measured this: xarray 2019 "built" with numpy 2, then every import failed (`np.unicode_`). Only a check after the install catches that.

Cost per review with candidates (guesses until the eval measures them):

| Path | Extra time | Extra model cost |
|---|---|---|
| Guess works, check passes | one collect run, 5 to 40 s | 0 |
| Agent runs | 3 to 10 min (steps plus installs plus replay) | Super about $0.05 to $0.20, Lightning about $0.01 to $0.04 (200k to 600k cumulative input tokens at `PRICES`) |

A repo where the check fails on every PR (a "false trigger") pays the agent every time. The eval counts this (section 8). The `.slopgate.toml` suggestion is the fix for the maintainer.

### 3. Base image

Recommendation: **one image, `python:3.12-slim` (the `Contree` default), and the agent chooses the Python version with uv.**

- `Contree.prepare` installs `uv` next to pytest and coverage: `pip install -q pytest coverage uv`.
- If the repo needs another Python, the agent runs `uv venv --seed --python 3.X /venv`.
- `Contree.prepare` passes `env={"PATH": VENV_PATH}, preserve_env=True`, with `VENV_PATH = "/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"`. Then `python` is the `/venv` Python in the session, in the replay, and in every later `Contree.run`. If `/venv` does not exist, the entry does nothing. Precedent: `bench/swebench.py` `build()` sets `TESTBED_PATH` the same way, and the later `hidden` runs use it.
- The guess install uses the image of Fix B (the Python of the commit date). The agent session and the replay use the default image, so a `.slopgate.toml` `setup` line with `/venv` also works. The agent learns the commit date from the task and can choose the same Python, or an older one with `uv venv`.

What the image gives (from the code): root, Debian with `apt-get`, pip, and network access. `prepare` downloads packages today, and the SDK has no network field in `InstanceSpawnRequest`. No compiler and no git: a package with no wheel fails to build (ticket 53: pillow 9.2 on 3.12) unless the agent picks an older Python or runs `apt-get install -y build-essential`.

Not chosen: letting the agent pick the image. That needs a second session and a decision call before the first command. uv gives the same choice inside one session.

Probes before code (stage 0, all are guesses now):

- `uv python install 3.7 3.8 3.9` works from ConTree. This needs download access to GitHub. uv support for 3.7 is uncertain.
- `uv venv --seed --python 3.8 /venv` and `/venv/bin/python -m pip --version`.
- A PATH that `prepare` preserves still holds after session commands that run without `preserve_env`. If it does not, pass `env={"PATH": VENV_PATH}` on every `ContreeSession.execute` and `Contree.run`.
- `apt-get update && apt-get install -y build-essential` works, and how long it takes.

### 4. The success check (gate side)

```python
def collect_error(sandbox, checkpoint, test) -> str | None:
    if not re.match(r"(python -m )?pytest\b", test):
        return None
    code, output = sandbox.run(checkpoint, {}, f"python -m coverage --version && {test} --collect-only")
    return None if code == 0 else f"tests do not collect:\n{tail(output)}"
```

- Exit 0 from `pytest --collect-only` means at least one test was collected (no tests gives 5) and there was no collection error (gives 2, or 1 with `--continue-on-collection-errors`). That is version independent. It needs no parsing of the summary line, which changed across pytest versions. Exit codes on 2019 pytest with `--continue-on-collection-errors` are a guess. The offline tests use the installed pytest, and stage 0 checks one old pytest.
- `python -m coverage --version` proves that the characterization agent can run coverage.
- A non-pytest test override (for example `make test`) skips the check.
- Not in the check: a full suite run. The baseline already runs the suite in parallel with characterization. A full run here would add up to `SANDBOX_TIMEOUT` before any work starts. The eval records whether the baseline is comparable (`pytest_result` not None) and the pass ratio, as a second metric.
- Known gap: collection passes but every test fails at fixture time (flask 2025 `monkeypatch.notset`, ticket 53). The baseline metric in the eval shows how often this happens. If it happens often, add a short run to the check.

The gate never trusts the agent: the check runs on the replayed image, and the agent's own check runs only inform the agent.

### 5. The tool loop

Reuse `converse`, `llm.step`, `EXECUTE`, and `shown`. Changes to `converse`:

```python
def limit(steps, began, tokens, max_steps, max_seconds, max_tokens) -> str | None
def converse(session, system: str, task: str, max_steps: int, max_seconds: int, model: str = SUPER, max_tokens: int = AGENT_TOKENS) -> str | None
```

`system` replaces `test_path` (it was used only to format `AGENT_RULES`). `characterize` and `harden` pass `AGENT_RULES.format(test_path=test_path)`. Behavior stays the same for them.

Limits (`config.py`, guesses to tune from the eval):

- `INSTALL_STEPS = 30`. The test agent has 15 for one file. Install needs reads, 2 or 3 install tries with fixes, the check, and the script.
- `INSTALL_SECONDS = 900`. One pip install of the xarray or sphinx dependencies can take 1 to 3 min.
- `INSTALL_TOKENS = 600_000` cumulative input tokens. The context grows each step, so 30 steps pass 150k early.
- Command timeout: the time left, as `converse` does today.
- `INSTALL_MODEL = LIGHTNING` as a placeholder (the user's choice). The eval decides (section 8).
- Thinking off: `llm.step` already sends `enable_thinking: False`.

The agent ends by writing `.slopgate/setup.sh` with a heredoc. The gate reads it with `session.read(SCRIPT)` after the loop, however the loop ended. This works when the model never sends a reply without a tool call (ticket 62: Super almost never does). There is no optional "cannot do it" tool. The agent writes the line `# CANNOT_INSTALL: <reason>` to the same file instead.

Context window: `shown()` lets one output reach 80,000 characters, about 20k tokens. A few long pip logs can pass the context window before any limit and end the loop as `agent error`. The rules tell the agent to use `-q` and `| tail -n 60`. The eval counts `agent error` stops. If they occur, add an output cap for this agent. Stage 0 gets the context window of Lightning and Super on Token Factory, and checks that Lightning returns tool calls with `EXECUTE` at all.

Prompts:

```python
SCRIPT = ".slopgate/setup.sh"

INSTALL_RULES = """You install the test environment of a Python repository in a sandbox, as a developer does on a new machine. You are root. The sandbox has network access, apt-get, pip, and uv.

Rules:
- Each command runs in a new shell in /repo, the root of the repository. cd, export, and source do not carry over to the next command.
- First read the files that tell how to install and test: README, CONTRIBUTING, tox.ini, noxfile.py, setup.cfg, setup.py, pyproject.toml, requirements*.txt, requirements/, .github/workflows/*.yml, Makefile. Read many files in one command, for example: head -n 80 README* tox.ini setup.cfg
- Keep output short: use pip install -q, and add | tail -n 60 to long commands.
- Install into the Python that the command python runs. If the repository needs a different Python version, make a virtual environment: uv venv --seed --python <version> /venv. /venv/bin is first on PATH in every command, so python is then the Python of /venv.
- Install pytest and coverage into that Python. Use a pytest version that works with the tests of the repository.
- /repo has no .git folder. If the build reads its version from git (setuptools-scm, hatch-vcs, versioneer), set SETUPTOOLS_SCM_PRETEND_VERSION in the install command.
- Do not change the files of the repository. Do not change the code or the tests to make them pass.
- Do not start servers or background processes.
- Write the install script with the execute tool and a heredoc: mkdir -p .slopgate && cat > {script} <<'EOF' ... EOF
- The script runs in one shell in /repo, and it stops at the first command that fails. Put only the commands that install in it: no reads and no checks.
- If you cannot install the environment, write one line to {script}: # CANNOT_INSTALL: <reason>. Then stop."""

INSTALL_TASK = """Install the test environment of this repository, so that this command runs its tests:

{test}

The repository is at a commit of {date}. A package version released after that date can break it. This command installs only versions released before that date:

uv pip install --python "$(command -v python)" --exclude-newer {date} <packages>

The default install of the gate failed:

{failure}

When you stop, the gate checks your script. It copies the repository into a new sandbox that has only pytest, coverage, and uv on the system Python. It runs {script} in /repo. Then it runs this check:

{check}

The check passes when the command exits with 0: pytest collects the tests with no error, and coverage runs. Run the check yourself after each install. Then run the tests: most of them must pass. Stop when your script is written and the check passes."""
```

`{check}` is the same string that `collect_error` runs. `{failure}` is the tail of the `InstallError` or of the collect output.

The gate function:

```python
def install(repo, head, sandbox, test: str, since: str, failure: str, model: str = INSTALL_MODEL) -> tuple[object | None, str | None, str | None]:
    # returns (checkpoint, script, reason); reason is None on success
```

1. `base = sandbox.prepare(repo, head, None)` (default image, uv installed).
2. `stop = converse(sandbox.session(base), INSTALL_RULES.format(script=SCRIPT), INSTALL_TASK.format(...), INSTALL_STEPS, INSTALL_SECONDS, model, INSTALL_TOKENS)` inside a `gate.install` span.
3. `script = session.read(SCRIPT)`. None gives `no script: agent stopped (<stop>)`. A `# CANNOT_INSTALL:` line gives that reason.
4. `checkpoint = sandbox.prepare(repo, head, f"set -e\n{script}")`. `InstallError` gives `script fails on a new sandbox: <tail>`.
5. `reason = collect_error(sandbox, checkpoint, test)`. Return `(checkpoint if reason is None else None, script, reason)`.

`review()` puts `result["environment"] = {"source": "agent", "script": script}` on success, and `{"source": "default"}` otherwise. The agent reason also goes into the `could not build test environment` notice when both paths fail.

### 6. Caching

Recommendation: **no cache in v1.**

- The durable recipe is the `.slopgate.toml` `setup` suggestion. `github.summary` adds one paragraph when `result["environment"]["source"] == "agent"`: the script in a TOML block (`[sandbox]` with `setup = '''...'''`), labeled as written by a model, for the maintainer to review before committing. It is one store, owned and reviewed by the maintainer, with no new infrastructure.
- A shared cache adds a trust problem (section 7). A tagged ConTree image built from a fork PR can carry a pytest plugin or a `sitecustomize.py` in site-packages that makes tests pass. Every later PR that hits the cache would then accept rewrites without proof. This shows up as silent breaks.

If the eval shows that repeat agent runs cost too much, the v2 cache is:

- The key is the sha256 of the default image name plus the `git ls-tree` blob SHAs of the dependency files (`pyproject.toml`, `setup.py`, `setup.cfg`, `tox.ini`, `noxfile.py`, `uv.lock`, `requirements*.txt`, `requirements/`) **at the installed commit (head)**.
- Write it only from trusted refs: a push to the base branch, or a same-repo PR. Never from a fork PR. Use `checkpoint.tag_as(f"slopgate-env:{key[:16]}")`.
- Read it with `client.images.use(tag, strict=True)`, then `prepare` with an `rm -rf /repo` prefix and the stored script (it installs quickly, because the packages are already there), then `collect_error`.
- Guesses to probe first: whether a tag can be moved to a new image, and how long untagged images last. The bench reuses `hidden_uuid` across stages, which shows days, not more.

### 7. Security

- Secrets: unchanged. `Contree` runs get only the env that the gate passes (none), and `shell()` drops `NEBIUS_*`, `PHOENIX_*`, `OTEL_*`, `GH_TOKEN`, `GITHUB_TOKEN` for `Local`.
- Prompt injection: the PR author controls the README, CONTRIBUTING, and workflows that the agent reads. The worst case is commands in the sandbox and a bad script. A PR author can already run any code in the sandbox through `setup.py` or `conftest.py`, and a `conftest.py` can already make the tests pass. So for the PR's own review, the agent adds no new class of risk. The replay and `collect_error` stop a script that leaves no tests to collect.
- New surface: anything that one PR's install leaves for another PR. v1 shares nothing between PRs, so there is no such surface. The v2 cache rule (trusted refs only) keeps it closed.
- Host safety: no agent on `Local`. The guard is `sandbox.pins`, with a one-line comment on why.
- Cost abuse: bounded by `INSTALL_STEPS`, `INSTALL_SECONDS`, and `INSTALL_TOKENS`.
- The summary labels the script as model-written. A maintainer who copies it into `.slopgate.toml` reviews it first.
- Network: allowed, as for pip today. The tests themselves can also reach the network in ConTree, as today. This is not new.

### 8. Evaluation

Least new code: one stage `install` in `bench/swebench.py` (`python -m bench.swebench install`), modeled on `run()`. It uses `ProcessPoolExecutor(WORKERS)`, so `llm.usage` is per process, and it calls `trace.start("slopgate-bench")` (project memory: trace every live run).

Instances:

- The 15 `INSTANCES`, at `base_commit`, from `dataset()` and `checkout()`.
- Extra Lite instances for repos that failed in earlier tickets or that need compilers. Pick by hand from `LITE` and record the ids in the ticket: the oldest `psf/requests` (2014, ticket 59), `pydata/xarray` 2019 (ticket 53), `sympy/sympy` 2016 (ticket 59), and one each of `scikit-learn`, `matplotlib`, and `astropy`. Leave out Django, because it uses `runtests.py`, not pytest. Add their test dirs to `TESTS`.

For each instance:

1. **Calibration.** Run `collect_error` on the SWE-bench image (`images.use(hidden_uuid)` for selected instances), with both the bench command (`TESTS[repo]`) and the production default `python -m pytest -q -rfE`. If the official environment fails the check, the check is too strict.
2. **Default.** `commands(clone, base, commit_date(clone, base))`, then `Contree().prepare`, then `collect_error` with both commands. Record built, check result, and seconds.
3. **Agent**, 3 attempts each with `LIGHTNING` and with `SUPER`: `install(clone, base, Contree(), test, date, failure, model=m)`. Pass the default's failure text, or "the default install was not tried" when it passed. Record success, reason, stop, steps (`len(llm.usage[used:])`), tokens and USD (`usage_of`, `cost`), seconds, whether the script uses `/venv` or `apt-get`, and the `agent error` stops.
4. **Secondary.** On each good checkpoint, run the suite once. Record whether `pytest_result` is comparable and the pass ratio.

Output: `results/swebench/install.json` and `.md`, with `metadata(...)` and the prompts `INSTALL_RULES` and `INSTALL_TASK`.

Metrics: default success, agent success per model (pooled and **per instance across the 3 attempts**), success on the subset where the default fails, false triggers (the default builds, the check fails with the production command), time, tokens, and USD per install, the stop reason counts (step limit with no script is the "probes forever" mode that Ultra showed in ticket 41), and filler commands (`echo`, `true`, `pwd`) per ticket 62.

Decision rule, fixed before any run: use Lightning if its successful attempts are at least Super's minus 3 (of about 63 attempts per model), and no instance goes from 3 of 3 with Super to 0 of 3 with Lightning. Otherwise use Super. If both are below the default on the default-fails subset, the agent does not ship.

Then the end-to-end run: wire the chosen model, run `run` and `report` again, and compare with the ticket 10 run that uses the plain `Contree()` install. Compare `infrastructure_errors` (`no_environment`), `acceptance`, `acceptance_of_items`, and `silent_break_rate`. Keep the old `runs.json` and `swebench.md` under a new name before the rerun. The hidden tests stay on the SWE-bench image, so the judge does not change.

Rough size (guess): about 66 agent attempts per model, at 5 to 10 min, with 8 workers, is about 1.5 h per model. That is about $10 to $15 for Super and $2 to $3 for Lightning, plus ConTree time (not measured: `ContreeSession.execute` drops `result.cost`).

### 9. Files, signatures, tests, order

Files:

- `slopgate/config.py`: `PYTHONS` replaces `OLD_COMMIT_IMAGE` (Fix B). `INSTALL_MODEL`, `INSTALL_STEPS`, `INSTALL_SECONDS`, `INSTALL_TOKENS`.
- `slopgate/sandbox.py`: `commands()` adds the scm export (Fix A) and picks the image by date (Fix B), with the same return shape `(setup, test, image)`. `Contree.prepare` installs `uv` too and passes `env={"PATH": VENV_PATH}, preserve_env=True`. Add the constant `VENV_PATH`.
- `slopgate/review.py`: `limit(..., max_tokens)`, `converse(session, system, task, max_steps, max_seconds, model=SUPER, max_tokens=AGENT_TOKENS)`, `SCRIPT`, `INSTALL_RULES`, `INSTALL_TASK`, `collect_error(sandbox, checkpoint, test) -> str | None`, `install(repo, head, sandbox, test, since, failure, model=INSTALL_MODEL) -> tuple[checkpoint | None, str | None, str | None]`, and the new prepare block in `review()` (section 2).
- `slopgate/github.py`: `summary` adds the `.slopgate.toml` suggestion. `publish` shows the agent reason in the notice.
- `bench/swebench.py`: stage `install`, `EXTRA` ids, more `TESTS` entries.
- `README.md` and `CLAUDE.md` code map: one line each on the install agent and `.slopgate.toml`.
- A new ticket in `issues/` (STE100) with the stage 0 probes and the eval results.

Offline tests (`tests/test_review.py`, with `Local`, `scripted()`, `agent_reply`, `tool_call`, and `write_command` as the agent tests use them today):

- `test_collect_error_passes_a_repo_whose_tests_collect` / `..._names_an_import_error` / `..._names_a_repo_with_no_tests`. These use real pytest on `make_repo` repos.
- `test_install_returns_the_checkpoint_of_the_replayed_script`. The agent writes a script that creates a module that the tests import. Assert that the module exists in the returned checkpoint.
- `test_install_rejects_a_session_install_that_the_script_does_not_repeat`. The agent creates the module with a session command, but the script is `true`. Assert the reason starts with `tests do not collect`. This proves that the gate does not trust the session.
- `test_install_reports_the_cannot_install_line` and `test_install_without_a_script_names_the_stop_reason`.
- `test_install_task_gives_the_date_the_failure_and_the_check` (the rendered prompt).
- `test_review_uses_the_agent_environment_when_the_default_install_fails`. Use a `Local` subclass with `pins = True`, and monkeypatch `review.commands` to return a failing setup, so nothing installs into the gate's venv.
- `test_review_keeps_the_default_environment_when_the_agent_fails`. The default builds, the check fails, the agent fails, and the review still proves the rewrite.
- `test_review_on_local_runs_no_agent`. The existing `test_install_failure_is_one_notice_with_last_20_lines` keeps passing unchanged.
- `tests/test_github.py`: the summary shows the TOML block only for `source == "agent"`.
- The existing `characterize` agent tests pass unchanged after the `converse` change.

Order (each unit ends in a check):

0. Stage 0 probes in a scratchpad script (no repo change): uv Pythons, `/venv`, PATH preservation through session commands, `apt-get`, Lightning tool calls with `EXECUTE`, the context window of both models, and the collect exit code on one 2019 pytest. Write the results into the ticket.
1. Deterministic fixes, one commit each, with offline tests in the style of `test_old_commit_installs_the_versions_of_its_date_on_the_old_image`: Fix A (scm version; test: a repo with `setuptools_scm` in `pyproject.toml` gets the export with its tag), Fix B (image by date; test: dates 2016, 2020-07, 2021-01, 2022-06, 2024 give 3.8, 3.8, 3.9, 3.10, default), Fix C (`collect_error` in `review()`, `NO_ENVIRONMENT` when it fails; tests with real pytest on `make_repo` repos).
2. Run the calibration and default part of the `install` stage on the 15 instances plus the extra ones. This gives the default success rate after A, B, and C, and the false trigger count, before any agent code. Then rerun `run` and `report`: this is the deterministic result for ticket 10, with no agent. If false triggers are not 0, fix the check first.
3. `converse` and `limit` parameters. Check: `uv run pytest -q` passes unchanged. Then `install`, the prompts, the config, the `Contree.prepare` change, and the offline tests.
4. The agent part of the `install` stage: Lightning and Super, 3 attempts each. Apply the decision rule and set `INSTALL_MODEL`.
5. Wire into `review()` and `github.py`, with tests. Then a dry run on one instance where the default failed, on the PR head (project memory: verify the gate on the PR head).
6. The end-to-end `run` and `report` rerun, compared with the ticket 10 baseline.
7. Only if step 6 shows that repeat agent cost matters: the v2 cache, with the trusted-ref rule.

## Acceptance

- [ ] The stage 0 probes ran: uv-managed Python 3.7 and 3.8 in ConTree, `PATH` in session commands, `--collect-only` exit codes on 2019 pytest, and whether Lightning makes tool calls.
- [ ] `collect_error` runs before any characterization. When it fails and the agent fails, the gate posts `NO_ENVIRONMENT` without a Super call.
- [ ] The `install` stage reports the guess install, Lightning, and Super on the same instances, 3 tries each.
- [ ] The model choice follows the rule in section 8.
- [ ] The PR summary shows the verified install script as a `.slopgate.toml` `setup` suggestion.
- [ ] `run` and `report` are made again with the agent install, and the numbers are compared with ticket 10.
- [ ] Offline tests cover the replay, the collection check, and the `CANNOT_INSTALL` line.
