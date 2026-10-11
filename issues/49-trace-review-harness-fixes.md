# 49 — Find the gate's errors in the Phoenix traces, and fix the harness

## Summary

- **Goal:** Find why the gate gives wrong or lost results on real pull requests, from the traces in Arize Phoenix. Each error gets a cause and a fix. Example: a rejection "characterization tests fail on original" on `review` (PR #32 dry run). The trace shows that the test agent's test called `llm.decide` with no key. The fix can be a rule in the agent's prompt, a fake in the sandbox, or a cheap early reject.
- **Checkable finish condition:** A table in `## Comments` lists every gate result of the traced runs that is wrong or lost. Each row has the trace id, the step, the cause, and a fix: either a merged change, or a new ticket under `issues/`. The traced runs cover at least 10 pull requests.
- **Evidence:** Before: Phoenix holds 8 `gate.review` traces (2026-10-11). Nobody has read them for errors as a set. The open gate tickets (40, 43, 44, 45, 47, 48) come from single runs and code reviews. After: the error table, with a count for each cause.
- **Constraints:** Measure, do not guess: each cause in the table points to a span in a trace. Change a model prompt only after a live comparison of the variants (about 8 tries each, as in `CLAUDE.md`). Do not post to GitHub: use `--dry-run`. The Slopgate workflow stays disabled until the user says so.

**Blocked by:** None — can start immediately.

**Status:** ready-for-agent

## Context

Ticket 32 traces every model request, sandbox command, and gate step in Phoenix. The span names are `gate.review`, `gate.function`, `gate.classify`, `gate.duplicate`, `gate.same_job`, `gate.characterize`, `gate.agent`, `gate.tests`, `gate.proof`, `sandbox.prepare`, `sandbox.run`, and `sandbox.execute`. Each span holds its input and output.

The gate has errors that the user sees on pull requests: wrong slop kinds (PR #20, ticket 36), lost reviews (ticket 46), rejections with no clear cause, and slow runs. The open tickets fix the errors that one run showed. Nobody has read many traced runs as a set yet, so the most frequent causes are not known.

## Design

1. Start Phoenix: `PHOENIX_HOST=127.0.0.1 uvx arize-phoenix serve`. Set `PHOENIX_COLLECTOR_ENDPOINT` in `.env` (see the tracing rules in `CLAUDE.md`).
2. Run the gate with tracing on, as a dry run, on at least 10 pull requests:
   - the merged pull requests of this repo from #20 to #32: `uv run --env-file .env slopgate review --pr <number> --dry-run`;
   - the pull requests of `slopgate-demo`.
3. Read the traces with the `phoenix-cli` skill. For each function that the gate looks at, record: the kind, the result (suggestion, note, rejection), the step that decided it, the tokens, and the time.
4. Mark each result as right or wrong. A result is wrong when:
   - the kind is wrong for the code;
   - a rejection comes from the harness (the sandbox, the import line, the prompt, a missing fake), not from the rewrite;
   - the agent stops at the token limit or the time limit;
   - a step takes more than 60 s.
5. Group the wrong results by cause. Count each cause.
6. For each cause: fix it in this ticket when the fix is small and clear, or write a new ticket. When a cause is already an open ticket (40, 43, 44, 45, 47, 48), add the count to that ticket and do not write a new one.
7. Re-run the gate on the same pull requests after the fixes. Compare the counts.

## Acceptance

- [ ] At least 10 pull requests have a traced gate run in Phoenix.
- [ ] `## Comments` has the error table: trace id, function, step, cause, fix or ticket.
- [ ] Each cause has a count.
- [ ] Each cause has a merged fix or a ticket under `issues/`.
- [ ] A re-run after the fixes gives the new counts.
- [ ] `uv run pytest -q` passes.

## Comments
