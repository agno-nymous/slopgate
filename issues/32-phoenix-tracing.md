# 32 — Trace every model request in Arize Phoenix

## Summary

- **Goal:** Send a trace of each gate run, hook run, and live test to Arize Phoenix. The user then sees each request to Lightning, Super, and Ultra with its full prompt, reply, model, token counts, and time. Example: on PR #20, the user opens the trace and reads the `TESTS_PROMPT` and the Super reply for `characterize`.
- **Checkable finish condition:** A dry run of the gate (`slopgate review --repo . --base <ref> --head <ref> --dry-run`) gives one trace. In it, each model request sits under the step that sent it. With tracing off, `uv run pytest -q` passes, `slopgate --help` takes 0.05 s or less, and no OpenTelemetry module is imported.
- **Evidence:** Before: to see a prompt on PR #20, the user had to rebuild it by hand in a scratch script. After (2026-10-09): a dry run on the PR #20 range gave one trace with 279 spans and 121 model requests. `uv run pytest -q` gave 221 passed. `slopgate --help` took 0.032 s. The key `NEBIUS_API_KEY` was in 0 of 538 spans.
- **Constraints:** Write the design first, and get the approval of the user before any code. Tracing is on only when `PHOENIX_COLLECTOR_ENDPOINT` is a local address. Only a local Phoenix gets traces. Put the setup in one module, `slopgate/trace.py`, and the packages in an optional `trace` extra. No span holds a secret. The hook exits 0 and makes no network call when there is no candidate.

**Blocked by:** None — can start immediately.

**Status:** done

**Priority:** high. The user set this ticket next on 2026-10-08.

## Context

Today the only way to see a prompt is to rebuild it in a scratchpad script. On PR #20 (2026-10-08), the gate rejected `characterize` because Super's tests failed on the original code. To find the cause, the prompt had to be rebuilt by hand and sent again. The rebuilt replies showed three causes:

1. Super did not replace `llm.complete`, so the tests called the real client, and `os.environ["NEBIUS_API_KEY"]` raised `KeyError` in the sandbox.
2. Super patched `slopgate.review.sandbox.run`, but `sandbox` is an argument, not a module name.
3. Super guessed the coverage marker as `"COVERAGE"`.

A trace of the real run shows the real prompt and the real reply at once. It also shows the time of each step, which ticket 23 asks for.

Facts to check in stage 1:

- `llm.py` makes every request through the `openai` client (`client().chat.completions.create`). The package `openinference-instrumentation-openai` instruments that client. Each request then becomes one LLM span with the input messages, the output, the model name, and the token counts.
- `phoenix.otel.register(project_name=..., auto_instrument=True)` (package `arize-phoenix-otel`) sets up the tracer and the instrumentation.
- Phoenix runs on the local machine, for example with `uvx arize-phoenix serve`. Its default address is `http://localhost:6006`.

## Stage 1: design

Write the design into this ticket under `## Design`. Then stop, and ask the user to approve it. Do not write code before the approval. Use the `pstack:architect` skill. If the span tree is contested, use the `pstack:interrogate` skill.

The design must answer these questions:

1. **Span tree.** Which spans exist, and which span is the parent of which? The tree must cover these units:
   - one gate run (`slopgate review`);
   - one candidate function;
   - each gate step: classify, duplicate search and the same-job decision, characterization tests (each attempt, the recorder, each sandbox run), rewrite, Ultra retry, proof, summary;
   - each model request (the LLM span from the instrumentation);
   - one hook run (`slopgate hook`) and its yes/no request;
   - one live test (`pytest -m live`).
2. **Span names.** Give the exact name of each span. Decide one naming rule and apply it everywhere. For example, a fixed name such as `gate.characterize` with the function in an attribute, or a name that holds the function, such as `characterize slopgate/review.py::broken_rule`. Give the reason for the choice: Phoenix groups and filters by name and by attribute.
3. **Span kinds.** Give the OpenInference span kind of each span (`CHAIN`, `LLM`, `TOOL`, or another kind).
4. **Attributes.** List the attributes of each span. Include at least these:
   - the repo, the base and head refs, and the pull request number;
   - the path and the qualname of the function;
   - the slop kind;
   - the name of the prompt template, for example `TESTS_PROMPT`, `NOT_PYTHON_RETRY`, `MISSED_RETRY`, or `RETRY_PROMPT`;
   - the attempt number;
   - the result: accepted, rejected with its reason, or a note.
5. **Grouping.** How does the user find all traces of one pull request, or of one test? Decide the session ID and the Phoenix project names (for example `slopgate-gate`, `slopgate-hook`, and `slopgate-tests`).
6. **Turn on and off.** Tracing is off unless an environment variable turns it on, for example `PHOENIX_COLLECTOR_ENDPOINT`. With tracing off, the code imports no OpenTelemetry package, makes no network call, and adds no time. `slopgate --help` must stay near 0.03 s.
7. **Hook.** The hook is a new process for each file write, and it must exit 0. Decide how the hook sends its spans without a wait, and what happens when Phoenix is not running. The hook rules stay true: no network call when there is no candidate, and the store is written before the model call.
8. **Self-hosted runner.** Decide whether the gate on the runner sends traces to a Phoenix on the same Mac, and how the workflow sets the endpoint.
9. **Privacy.** A trace holds repo code and prompts. The `slopgate` and `slopgate-demo` repos are private until the submission. Decide where traces go: only a local Phoenix, or also Phoenix Cloud. Make sure that no span holds `NEBIUS_API_KEY` or another secret.
10. **Dependencies.** Put the tracing packages in an optional extra, for example `trace`. Pip does not install uv dependency groups, so check the `setup` line of `.slopgate.toml` and the install step of `action.yml`.
11. **Ticket 23.** Decide whether the span times replace ticket 23 or only part of it.

The design also shows one sample trace as an indented tree: a gate run on one function with one tests retry and one Ultra retry.

## Stage 2: implementation

Build the design that the user approved. Put the tracing setup in one new module, for example `slopgate/trace.py`. Keep the changes to `review.py`, `cli.py`, `live.py`, and `llm.py` small: one `with` block for each step.

## Design

Status: the user approved this design on 2026-10-08, with the answers in "Questions for the user" and the rule in "Only this repo" below. Three designs were made in parallel (two on Opus, one on Sonnet) and compared. This design uses design 1 as the base. It also takes the dry-run session ID and the exit-time test from design 2. An independent reviewer (Sonnet) scored the three designs on 6 criteria and also chose design 1. The section "Rejected options" gives the reasons for the parts that were not taken.

### Measured facts

These were measured on 2026-10-08 with `arize-phoenix-otel` 0.17.2, `openinference-instrumentation-openai` 0.1.64, `opentelemetry-sdk` 1.45.1, and a local `uvx arize-phoenix serve`. The design depends on them.

- `import phoenix.otel` plus `register(...)` takes 0.7 to 0.8 s. Tracing that is on adds this time once to each process.
- The instrumentation makes one LLM span with the name `ChatCompletion` for each request. The span holds `llm.model_name`, `llm.token_count.prompt`, `llm.token_count.completion`, `llm.token_count.total`, the full input messages, the full output messages, and `llm.invocation_parameters`. `llm.py` needs no change.
- A span that starts in a `ThreadPoolExecutor` worker has no parent and no session. The hook's `classify` uses such a pool. A copy of the context (`contextvars.copy_context()`) for each task keeps the parent and the session.
- When Phoenix does not run, the exporter retries, and the process exit waits 6.1 to 7.3 s. With `OTEL_EXPORTER_OTLP_TRACES_TIMEOUT=1`, the exit waits 0.01 s. When the endpoint accepts the connection and never answers, the exit waits 1.0 s.
- `register()` with only the environment variable uses gRPC and changes the port of the URL to 4317. With `protocol="http/protobuf"`, it uses the URL as given.
- `register()` uses `batch=False` by default in 0.17.2. The design sets `batch=True`.
- A real `openai` call with a sentinel API key left the key in no span attribute and in no exported OTLP body. The key goes only into the `Authorization` header, and the instrumentation does not record headers.
- The `Local` sandbox gives the full `os.environ` to the code under test (`sandbox.shell`). That includes `NEBIUS_API_KEY` and `GH_TOKEN`. Test output goes into spans and into the `TESTS_RETRY` prompt. This is the only path found by which the key can get into a span.
- `uvx arize-phoenix serve` listens on `0.0.0.0` by default. Other machines on the network can then read the traces. `PHOENIX_HOST=127.0.0.1` prevents this.
- Phoenix filters spans by `name`, `span_kind`, and `metadata['key']` (source: `.claude/skills/phoenix-cli/references/filter-expressions.md`).

### The module `slopgate/trace.py`

The module has four public functions. Its top-level imports are from the standard library only. No OpenTelemetry type goes through its interface.

```python
def start(project: str) -> None: ...      # record the project; the first call in a process wins; no import
def span(name: str, input=None, session: str | None = None, **metadata): ...
                                          # a context manager; tracing off -> contextlib.nullcontext()
def output(value) -> None: ...            # set output.value on the current span; off -> nothing
def bind(fn): ...                         # copy the context into a worker thread; off -> fn unchanged
```

- `start` does not import OpenTelemetry. The first `span()` call imports `phoenix.otel` and calls `register(project_name=..., protocol="http/protobuf", batch=True, auto_instrument=True, verbose=False)`. A process that opens no span imports nothing.
- `span` merges its keyword arguments into the OpenInference `metadata` of the context (`using_metadata`). All child spans get these keys, also the `ChatCompletion` spans that the instrumentation makes.
- `span` sets the span kind from the name: `TOOL` for `sandbox.*`, else `CHAIN`. A keyword argument therefore always goes into metadata. (Stage 2: an earlier `kind` parameter took the slop kind `kind="dead"` as the span kind, and the traced gate crashed with `ValueError('Invalid OpenInference span kind: dead')`.)
- `start` and the setup never raise. When the `trace` extra is not installed, when `register` fails, or when the endpoint is not a valid URL, one line goes to stderr, and the process runs without tracing.

### 1. Span tree

```
gate.review                      one gate run (cli.py)
├─ gate.index                    index.build of base and head (review.py)
├─ gate.duplicate                one function: the keyword search
│  └─ gate.same_job              one Super same-job request
│     └─ ChatCompletion
├─ gate.classify                 one function: the Lightning request
│  └─ ChatCompletion
├─ sandbox.prepare               the sandbox setup
├─ gate.function                 one candidate function
│  ├─ gate.characterize          the characterization tests
│  │  └─ gate.tests              one attempt (1 or 2)
│  │     ├─ ChatCompletion
│  │     └─ sandbox.run          the recorder, the seed 1 run, the seed 2 run
│  ├─ gate.rewrite               the Super rewrite request
│  │  └─ ChatCompletion
│  ├─ gate.proof                 one proof (attempt 1, or attempt 2 after the Ultra retry); also inline and deduplicate
│  │  └─ sandbox.run             the characterization tests, the repo tests
│  └─ gate.retry                 the Ultra retry request
│     └─ ChatCompletion
└─ gate.summary                  the Ultra summary (only without --dry-run)
   └─ ChatCompletion

hook.run                         one hook run with a candidate (live.py)
└─ ChatCompletion                one Lightning yes/no request for each candidate

test.run                         one test case (tests/conftest.py)
└─ (the gate or hook spans that the test starts, and its ChatCompletion spans)
```

`gate.rewrite`, `gate.proof`, and `gate.retry` are sibling spans. The Ultra request occurs at the end of the first proof pass, so one span for each loop pass would put the Ultra request inside the first proof. The recorder has no span of its own. It is a `sandbox.run` with the command `python slopgate_record.py`.

### 2. Span names

Rule: `<area>.<step>`, lowercase, from the fixed list above. The area is `gate`, `sandbox`, `hook`, or `test`. A name never holds a function name, an attempt number, or a template name. These go into metadata. The only other name is `ChatCompletion`, which the instrumentation sets.

Reason: Phoenix groups and filters by the exact name and by `metadata[...]`. With fixed names, `name == 'gate.tests'` finds every attempt in every run, and the time of one step can be compared across runs. A name that holds the function is different for each function. Phoenix then cannot group the spans, and its filter has no prefix match.

### 3. Span kinds

| Kind | Spans |
|---|---|
| `CHAIN` | all `gate.*` spans, `hook.run`, `test.run` |
| `TOOL` | `sandbox.prepare`, `sandbox.run` |
| `LLM` | `ChatCompletion` (from the instrumentation) |

### 4. Attributes

All Slopgate keys go into `metadata`. A child span gets the keys of its parents. An LLM span of a test retry thus holds the repo, the pull request, the function, the slop kind, the template, and the attempt.

| Span | Keys that the span adds to `metadata` | `input.value` / `output.value` |
|---|---|---|
| `gate.review` | `repo`, `base`, `head`, `pr`, `sandbox` | in: `<pr or repo> <base>..<head>`; out: the result JSON |
| `gate.duplicate` | `path`, `qualname` | out: the match, or null |
| `gate.same_job` | `helper` (`path::qualname`), `score`, `prompt` = `SAME_JOB_PROMPT` | — |
| `gate.classify` | `path`, `qualname`, `prompt` = `CLASSIFY_PROMPT` | out: the slop kind, or null |
| `sandbox.prepare` | — | in: the setup command; an `InstallError` sets the ERROR status |
| `gate.function` | `path`, `qualname`, `slop_kind` | out: the entry that this function added to the result, for example `{"rejected": [{"reason": "characterization tests fail on original: ..."}]}` |
| `gate.characterize` | — | out: the failure, or `passed` |
| `gate.tests` | `attempt` (1, 2), `prompt` (`TESTS_PROMPT`, `NOT_PYTHON_RETRY`, `INPUTS_RETRY`, `MISSED_RETRY`, `TESTS_RETRY`) | out: the failure that caused the retry |
| `gate.rewrite` | `prompt` = `REWRITE_PROMPT` | — |
| `gate.proof` | `attempt` (1 = Super rewrite, 2 = Ultra retry) | out: the failure, or `passed` |
| `gate.retry` | `prompt` = `RETRY_PROMPT` | — |
| `sandbox.run` | — | in: `{cmd, files}`; out: `{exit_code, output}` |
| `gate.summary` | `prompt` = `SUMMARY_PROMPT` | — |
| `hook.run` | `path` (the written file) | out: the note that the agent sees |
| `test.run` | `test` (the pytest node ID) | in: the node ID |

`gate.function` gets its output in a `finally` block. The block records what this function added to `result`. Thus every exit path shows its result: a suggestion, a follow-up, a rejection with its reason, `reply cut off`, and `internal error`. The 8 places that append to `result` do not change. An exception that goes through a span sets the ERROR status on that span. Example: `llm.CutOff` makes `gate.tests` red.

### 5. Grouping

- Projects: `slopgate-gate`, `slopgate-hook`, and `slopgate-tests`. The first `start` call in a process sets the project. A live test that runs the gate thus stays in `slopgate-tests`, under its `test.run` span.
- Gate session ID: `<owner>/<repo>#<number>` when the pull request is known (`--pr`, or `GITHUB_EVENT_PATH` on the runner). All runs of one pull request are then one Phoenix session. A dry run with `--base` and `--head` uses `<repo folder>@<first 12 characters of head>`, so repeated dry runs of one head are one session.
- Hook session ID: the `session_id` of the Claude Code hook payload. All hook traces of one agent session are then one Phoenix session.
- Test session ID: `<test name> <pytest start time>`, for example `test_super_tests_reply 2026-10-08 14:03:11`. One `pytest -m live -k test_super_tests_reply` run is one session with one trace for each test case.

### 6. Turn on and off

Tracing is on only when `PHOENIX_COLLECTOR_ENDPOINT` is set, is not empty, and has a local host (`localhost`, `127.0.0.1`, or `::1`). Phoenix uses the same variable, so one variable turns tracing on and gives the address. When tracing is off, `span` returns `contextlib.nullcontext()`, and `output` and `bind` do nothing. No OpenTelemetry module is imported, and there is no network call. `cli.py` imports `trace` only in the `review` and `hook` branches, so `slopgate --help` does not change.

**Only this repo.** Slopgate traces only the work on this repo, not the repos where Slopgate is installed. Do not export `PHOENIX_COLLECTOR_ENDPOINT` in a shell profile. Set it only in these places:

- The gate and the live tests: in this repo's `.env`. Every command here loads it with `--env-file .env`. Other repos do not read it.
- The hook: in the `env` block of this repo's `.claude/settings.local.json`. Claude Code gives that block only to sessions in this repo.
- The runner: in the repository variable `vars.PHOENIX_COLLECTOR_ENDPOINT` of this repo (question 8).

Other installs (`pip install slopgate`, `action.yml`) do not install the `trace` extra. Thus they cannot trace, also when the variable is set.

A test in `tests/test_trace.py` proves the off state. A subprocess without the variable runs `slopgate review --dry-run` on a small repo, opens a span, and calls `output` and `bind`. Then it checks that `sys.modules` holds no module from `opentelemetry`, `phoenix`, or `openinference`. The test uses a subprocess because other tests in the same process can import these modules.

### 7. Hook

- `hook()` returns `""` before the span when there is no candidate. The result is the same as today, because `note(classify(root, []))` is `""`. With no candidate, the hook imports nothing and makes no network call.
- `hook.run` starts after the store write. The rule "the store is written before the model call" stays true.
- The spans go out through a `BatchSpanProcessor` in a background thread. At exit, the SDK sends the remaining spans. `trace.py` sets `OTEL_EXPORTER_OTLP_TRACES_TIMEOUT=1` (with `setdefault`), so the exit waits at most about 1 s when Phoenix does not run or does not answer. The export error goes to stderr. The hook exits 0.
- `classify` wraps its function with `trace.bind`, so the yes/no spans keep `hook.run` as the parent and keep the session.
- A test in `tests/test_trace.py` starts tracing in a subprocess with the endpoint on a closed local port. It checks exit 0 and a time less than 4 s. The time includes the cold import of `phoenix.otel` (up to 1.1 s). Measured: 0.92 s to 1.92 s with the 1 s timeout, and 8.70 s without it, so the test finds a lost timeout.

### 8. Self-hosted runner

Yes. The gate on the runner sends traces to a Phoenix on the same Mac. Add one line to the `env` of the review step in `.github/workflows/slopgate.yml`:

```yaml
          PHOENIX_COLLECTOR_ENDPOINT: ${{ vars.PHOENIX_COLLECTOR_ENDPOINT }}
```

The repository variable is not set by default. The expression then gives `""`, and tracing stays off. To turn tracing on, run `gh variable set PHOENIX_COLLECTOR_ENDPOINT --body http://127.0.0.1:6006`. To turn it off, run `gh variable delete PHOENIX_COLLECTOR_ENDPOINT`. These need no commit. `uv run` installs the `dev` group, which holds the trace packages. Before the repo is public (`runs-on: ubuntu-latest`), remove this line together with the self-hosted runner.

### 9. Privacy

- Only a local Phoenix gets traces. `start` refuses an endpoint whose host is not local. It writes one line to stderr and keeps tracing off. Phoenix Cloud thus cannot get private code by mistake. The user can remove this rule after the repos are public.
- Start Phoenix with `PHOENIX_HOST=127.0.0.1`, so that other machines on the network cannot read it. Measured: the UI and the HTTP port 6006 then listen on `127.0.0.1` only. The gRPC port 4317 still listens on all interfaces, and Phoenix has no setting to change its host. Port 4317 only receives spans. It cannot be used to read traces.
- `sandbox.shell` removes the variables that start with `NEBIUS_`, `PHOENIX_`, or `OTEL_`, and `GH_TOKEN` and `GITHUB_TOKEN`, from the environment of the `Local` sandbox. The `Local` sandbox then agrees with `Contree`, which never had the key. This also stops model-written tests in `Local` from calling the real client with the real key (cause 1 on PR #20).
- A test in `tests/test_trace.py` proves that no span holds the key. A stub HTTP server answers `/v1/chat/completions` and stores the bodies of `/v1/traces`. A subprocess sets `NEBIUS_API_KEY` to a sentinel value, makes one model request in a worker thread through `trace.bind`, and runs `env` in the `Local` sandbox. The test then checks these facts: the sentinel is in no exported body; the prompt text is in the bodies (a control); and there is exactly one root span.

### 10. Dependencies

```toml
[project.optional-dependencies]
trace = ["arize-phoenix-otel>=0.17.2", "openinference-instrumentation-openai>=0.1.64"]

[dependency-groups]
dev = ["numpy", "slopgate[trace]"]
```

If uv does not accept `slopgate[trace]` in a group, the `dev` group lists the two packages. `.slopgate.toml` does not change (`pip install -e . numpy`): the sandbox does not need tracing, and the trace tests skip there with `pytest.importorskip`. `action.yml` does not change: a GitHub-hosted runner has no local Phoenix, and the local-host rule refuses a remote one.

### 11. Ticket 23

Span times replace the measurement part of ticket 23. A traced run shows the time of `gate.index`, `sandbox.prepare`, each test attempt, each proof, each sandbox run, and each model request. Ticket 25 needs these times. Span times do not replace the `Slowest:` line in the pull request comment, and they give nothing on a run without tracing. Proposal: change the blocker of ticket 25 from 23 to 32, and reduce ticket 23 to the `Slowest:` line.

### Sample trace

A gate run on one function, with one test retry and one Ultra retry. The times are examples, not measurements. Each span shows only the keys that it adds. Each child also holds the keys of its parents.

```
gate.review  CHAIN  41.9 s  session agno-nymous/slopgate#20
│ metadata {repo: ".", base: "3909996", head: "70c27da", pr: "agno-nymous/slopgate#20", sandbox: "contree"}
├─ gate.index  CHAIN  0.4 s
├─ gate.duplicate  CHAIN  0.1 s  +{path: "slopgate/review.py", qualname: "broken_rule"}  out: null
├─ gate.classify  CHAIN  1.2 s  +{path, qualname, prompt: "CLASSIFY_PROMPT"}  out: "nesting"
│  └─ ChatCompletion  LLM  nvidia/Nemotron-3_5-Lightning  412 -> 9 tokens
├─ sandbox.prepare  TOOL  9.8 s  in: "apt-get ... && pip install -e . numpy"
└─ gate.function  CHAIN  28.1 s  +{path: "slopgate/review.py", qualname: "broken_rule", slop_kind: "nesting"}
   │ out: {"suggestions": [{"path": "slopgate/review.py", "line": 319, ...}]}
   ├─ gate.characterize  CHAIN  14.4 s  out: "passed"
   │  ├─ gate.tests  CHAIN  7.3 s  +{attempt: 1, prompt: "TESTS_PROMPT"}
   │  │  │ out: "characterization tests fail on original: ..."
   │  │  ├─ ChatCompletion  LLM  nvidia/nemotron-3-super-120b-a12b  1830 -> 640 tokens
   │  │  ├─ sandbox.run  TOOL  2.0 s  cmd "PYTHONHASHSEED=1 python -m coverage run ..."  exit 1
   │  │  └─ sandbox.run  TOOL  1.8 s  cmd "PYTHONHASHSEED=2 python -m coverage run ..."  exit 1
   │  └─ gate.tests  CHAIN  7.1 s  +{attempt: 2, prompt: "TESTS_RETRY"}
   │     ├─ ChatCompletion  LLM  nvidia/nemotron-3-super-120b-a12b  2950 -> 655 tokens
   │     ├─ sandbox.run  TOOL  2.1 s  cmd "PYTHONHASHSEED=1 ..."  exit 0
   │     └─ sandbox.run  TOOL  1.7 s  cmd "PYTHONHASHSEED=2 ..."  exit 0
   ├─ gate.rewrite  CHAIN  3.0 s  +{prompt: "REWRITE_PROMPT"}
   │  └─ ChatCompletion  LLM  nvidia/nemotron-3-super-120b-a12b  520 -> 210 tokens
   ├─ gate.proof  CHAIN  1.9 s  +{attempt: 1}  out: "rewrite fails characterization tests: ..."
   │  └─ sandbox.run  TOOL  1.9 s  files {tests/test_slopgate_0.py, slopgate/review.py}  exit 1
   ├─ gate.retry  CHAIN  4.6 s  +{prompt: "RETRY_PROMPT"}
   │  └─ ChatCompletion  LLM  nvidia/Nemotron-3-Ultra-550b-a55b  1240 -> 230 tokens
   └─ gate.proof  CHAIN  4.1 s  +{attempt: 2}  out: "passed"
      ├─ sandbox.run  TOOL  1.9 s  the characterization tests  exit 0
      └─ sandbox.run  TOOL  2.2 s  cmd "python -m pytest -q"  exit 0
```

The `ChatCompletion` span under `gate.tests` attempt 2 holds `{repo, base, head, pr, sandbox, path, qualname, slop_kind, attempt: 2, prompt: "TESTS_RETRY"}`. The filter `span_kind == 'LLM' and metadata['prompt'] == 'TESTS_RETRY'` finds it without the tree.

### Changes in each file

| File | Change |
|---|---|
| `slopgate/trace.py` | New. About 55 lines. |
| `slopgate/review.py` | One `with` for each step. About 21 lines added and 8 lines changed. About 145 lines get only a new indent (`git diff -w` hides them). The template name goes into a `template` variable beside `retry`. The slop kind uses the metadata key `slop_kind`. |
| `slopgate/sandbox.py` | One `with` in `Local.run` and one in `Contree.run`, which is 2 places instead of 9 call sites. The environment filter in `shell`. About 5 lines added. |
| `slopgate/cli.py` | `trace.start` in the `review` and `hook` branches, and `gate.review` around the review and the publish. The event file is read before the review, so the session ID is known. About 7 lines added. |
| `slopgate/live.py` | The early return, `hook.run`, and `trace.bind`. About 6 lines added. |
| `slopgate/github.py` | `gate.summary`. 1 line added. |
| `slopgate/llm.py` | No change. |
| `tests/conftest.py` | `trace.start("slopgate-tests")` and an autouse fixture with `test.run`. About 8 lines added. |
| `tests/test_trace.py` | New. Three tests: no import when off, no key in a span, quick exit when Phoenix does not run. |
| `pyproject.toml`, `.github/workflows/slopgate.yml`, `README.md`, `CLAUDE.md` | The extra and the group, one env line, a tracing section, the code map row and the command. |

One behavior changes in `cli.py`: a run without `--dry-run`, without `--pr`, and without `GITHUB_EVENT_PATH` now fails before the review, not after it. The error is the same `KeyError`.

### Rejected options

- **Template names found by string match on the prompt (design 2).** No call site would pass a name. But the match depends on the text of the templates, and `RETRY_PROMPT` contains `REWRITE_PROMPT`, so a special rule is necessary. An explicit name is easier to read and cannot match the wrong template.
- **No attempt span, only decorators on existing functions (design 2).** This changes about 10 lines of `review.py` and no indent. But the ticket asks for a span for each attempt. Without it, the sandbox runs of attempt 1 and attempt 2 are siblings, and the reader must use the order in time to separate them. Decorators also read metadata from parameter names, so a renamed parameter loses its metadata without an error.
- **Decorators on the steps that are already functions, to reduce the new indent.** A reviewer proposed this. Most of the new indent comes from loop bodies (the candidate loop, the attempt loop, and the proof loop), and decorators cannot wrap a loop body. The new indent also causes no merge conflict: `issues/ROADMAP.md` makes the tickets that edit `review.py` go one at a time, each from `main`.
- **`opentelemetry-instrumentation-threading` (design 2).** It needs no change in `live.py`, but it adds a dependency for one thread pool. `trace.bind` is one line.
- **A proxy object around the sandbox, and redaction of the key in span text (design 3).** The environment filter in `sandbox.shell` removes the key at its source. Redaction only hides the key in spans, and the key still reaches the code under test and the `TESTS_RETRY` prompt. No other path for the key was found, so a second redaction layer is not added.
- **A name that holds the function, for example `characterize slopgate/review.py::broken_rule`.** Phoenix cannot group such names (see question 2).
- **A separate switch such as `SLOPGATE_TRACE=1`.** Two variables must then agree. Phoenix's own variable does both jobs.

### Answers of the user (2026-10-08)

1. Only a local Phoenix gets traces. Keep the local-only rule.
2. Reduce ticket 23 to the `Slowest:` line. Ticket 25 waits for ticket 32, not for ticket 23.
3. Do the environment filter in `sandbox.shell` in this ticket.

## Acceptance

- [x] Stage 1: the `## Design` section answers questions 1 to 11 and holds a sample trace. The user approved it before any code was written.
- [x] With tracing off: `uv run pytest -q` passes, `slopgate --help` takes 0.05 s or less, and a test shows that no OpenTelemetry module is imported.
- [x] With a local Phoenix running: one dry run of the gate (`slopgate review --repo . --base <ref> --head <ref> --dry-run`) gives one trace. In it, each model request is an LLM span under the step that sent it. The span holds the full prompt, the full reply, the model, and the token counts.
- [x] A rejected function shows its reason on its span. Example: `characterize` with "characterization tests fail on original".
- [x] One live test run (`pytest -m live -k test_super_tests_reply`) gives one trace for each test case, grouped as the design says.
- [x] One hook run with a candidate gives one trace, and the hook still exits 0 when Phoenix is not running.
- [x] No span holds `NEBIUS_API_KEY`. A test checks this.
- [x] `README.md` tells how to start Phoenix and turn tracing on.
- [x] `CLAUDE.md` gets the new module in the code map and the tracing command.

## Comments

### 2026-10-09 — done

**What was built.** The new module `slopgate/trace.py` sends a trace of each gate run, each hook run with a candidate, and each test case to a local Arize Phoenix. It has four functions: `start`, `span`, `output`, and `bind`. Tracing is on only when `PHOENIX_COLLECTOR_ENDPOINT` is a local address and the `trace` extra is installed. With tracing off, no OpenTelemetry module is imported. The `openinference-instrumentation-openai` package makes one LLM span for each model request, so `llm.py` did not change. Each step span puts its keys (`path`, `qualname`, `slop_kind`, `prompt`, `attempt`) into the OpenInference metadata, and every child span, also each LLM span, gets them. The `Local` sandbox no longer gives `NEBIUS_*`, `PHOENIX_*`, `OTEL_*`, `GH_TOKEN`, or `GITHUB_TOKEN` to the code under test. The official Phoenix skills (`phoenix-tracing`, `phoenix-cli`, `phoenix-evals`, from `Arize-ai/phoenix` commit `a944a14`) are in `.claude/skills/`.

**Worked example.** Command: `PHOENIX_COLLECTOR_ENDPOINT=http://127.0.0.1:6006 uv run --env-file .env slopgate review --repo . --base 19d7331 --head 70c27da --dry-run` (the range of PR #20, Contree sandbox). The result: 2 rejections and 12 notes, the same counts that the gate posted on PR #20. Phoenix got one trace with 279 spans and one root, `gate.review`, in the session `ticket-32-phoenix-tracing@70c27da340ae`. Part of the trace for the rejected function:

```
gate.function {qualname: characterize, slop_kind: dead}
│ out: {"rejected": [{"function": "characterize", "reason": "characterization tests fail on original: ..."}]}
└─ gate.characterize  out: characterization tests fail on original: ...
   ├─ gate.tests {attempt: 1, prompt: TESTS_PROMPT}
   │  ├─ ChatCompletion LLM nemotron-3-super  1882 -> 2721 tokens
   │  ├─ sandbox.run TOOL  exit_code 1  ".FFFFFFFFFFF..."
   │  └─ sandbox.run TOOL  exit_code 1
   └─ gate.tests {attempt: 2, prompt: TESTS_RETRY}
      ├─ ChatCompletion LLM nemotron-3-super  5425 -> 2375 tokens
      ├─ sandbox.run TOOL  exit_code 1
      └─ sandbox.run TOOL  exit_code 1
```

Each `ChatCompletion` span holds the full prompt, the full reply, the model, and the token counts. The second Super request holds `metadata.prompt = TESTS_RETRY` and `metadata.attempt = 2`, so the Phoenix filter `span_kind == 'LLM' and metadata['prompt'] == 'TESTS_RETRY'` finds it.

**Measured results.**

- The trace shows where the review time goes. The run took 3 min 33 s. It sent 121 model requests (110,867 prompt tokens, 12,497 completion tokens). 102 of them are Super same-job requests (`gate.same_job`) for 22 functions. Tickets 25 and 36 can use this.
- `uv run pytest -q`: 221 passed, 15 deselected. `tests/test_trace.py` has 5 tests: no OpenTelemetry import when off, no key in any exported span, a quick exit when Phoenix does not run, refusal of a remote endpoint, and the same review result with tracing on and off.
- `slopgate --help`: 0.032 s (median of 21 runs), the same as `main`. A top-level `pathlib` import first made it 0.039 s; `os.path` replaced it.
- Exit with Phoenix not running: 8.70 s without `OTEL_EXPORTER_OTLP_TRACES_TIMEOUT=1`, and 0.92 s to 1.92 s with it.
- Live test (`pytest -m live -k test_super_tests_reply`): 3 passed, 3 traces, one for each test case, all in the session `test_super_tests_reply_is_proven_or_cannot_test <start time>`.
- Hook with a copy of `slugify`: one trace, `hook.run` with one Lightning `ChatCompletion` child (the parent stays correct through the thread pool), session `hook-check`. With Phoenix not running: exit 0 in 2.32 s, with one export error line on stderr.
- `NEBIUS_API_KEY`: 0 hits in the 538 spans of the `slopgate-gate` project. The test with a sentinel key also gives 0 hits in the raw OTLP bodies.

**Defect found in stage 2.** The first traced gate run crashed with `ValueError('Invalid OpenInference span kind: dead')` and gave an empty result. The design passed the slop kind as `kind=`, and `span` used `kind` as the span kind. With tracing off, `span` returns before it reads `kind`, so the offline tests passed. Fix: `span` now sets the span kind from the name (`TOOL` for `sandbox.*`, else `CHAIN`), and the slop kind uses the key `slop_kind`. The test `test_traced_review_matches_untraced_review` fails with the defect and passes with the fix.

**Code review (Opus, thermo-nuclear).** Applied: the span kind comes from the name (finding 1); `register` errors and an invalid endpoint URL turn tracing off with one stderr line, and do not stop the gate (findings 2 and 3); one debug print removed (5); one repeated expression removed in `Contree.run` (6); the README text about sessions agrees with the code (7). Rejected: build the dry-run session ID only when tracing is on (4). One `git rev-parse` takes milliseconds, and a gate run takes minutes. The test time limit stays at 4 s, not 2 s, because the cold import of `phoenix.otel` takes up to 1.1 s; the design text now says this.

**Known limits.**

- `gate.tests` and `gate.proof` set no output when they end early (a `return` or a `break`). `gate.characterize` and `gate.function` show the result.
- The gRPC port 4317 of Phoenix listens on all interfaces. Phoenix has no setting for its host. The port only receives spans.
- The session ID of a dry run uses the folder name, so a worktree gives a different name than the main checkout.
- The Ultra retry (`gate.retry`) did not occur in the live runs. The offline tests cover its code path only with tracing off.
