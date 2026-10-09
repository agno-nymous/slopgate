# 32 — Trace every model request in Arize Phoenix

**What to build:** Send a trace of each gate run, each hook run, and each live test to Arize Phoenix. In Phoenix, the user sees each request to Lightning, Super, and Ultra: the full prompt, the full reply, the model, the token counts, and the time. Each request sits under the gate step that sent it, so the user can see which prompt belongs to which function and which retry. The ticket has two stages. Stage 1 designs the span tree and the names. The user approves the design before stage 2 writes code.

**Blocked by:** None — can start immediately.

**Status:** ready-for-agent

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

## Acceptance

- [ ] Stage 1: the `## Design` section answers questions 1 to 11 and holds a sample trace. The user approved it before any code was written.
- [ ] With tracing off: `uv run pytest -q` passes, `slopgate --help` takes 0.05 s or less, and a test shows that no OpenTelemetry module is imported.
- [ ] With a local Phoenix running: one dry run of the gate (`slopgate review --repo . --base <ref> --head <ref> --dry-run`) gives one trace. In it, each model request is an LLM span under the step that sent it. The span holds the full prompt, the full reply, the model, and the token counts.
- [ ] A rejected function shows its reason on its span. Example: `characterize` with "characterization tests fail on original".
- [ ] One live test run (`pytest -m live -k test_super_tests_reply`) gives one trace for each test case, grouped as the design says.
- [ ] One hook run with a candidate gives one trace, and the hook still exits 0 when Phoenix is not running.
- [ ] No span holds `NEBIUS_API_KEY`. A test checks this.
- [ ] `README.md` tells how to start Phoenix and turn tracing on.
- [ ] `CLAUDE.md` gets the new module in the code map and the tracing command.

## Comments
