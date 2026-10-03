# 01 — Tracer bullet: the gate fixes one nested function

**What to build:** The first end-to-end path of the pull request gate. A user runs `slopgate review --dry-run` on a local git repo with a base ref and a head ref. The head commit adds a function with 4 levels of nested `if`. The gate finds the function, asks Nemotron Super for characterization tests and a rewrite, proves both with the local sandbox fake, and prints one suggestion as JSON. The suggestion shows cyclomatic complexity and nesting depth before and after, and the test count.

This ticket also sets up the project: package layout, MIT license, dependencies, the Token Factory client, the config module with all four thresholds, and the `live` pytest marker.

**Blocked by:** None — can start immediately.

**Status:** done

- [x] `slopgate review --base <ref> --head <ref> --dry-run` prints JSON with the keys `suggestions`, `followup`, and `rejected`.
- [x] On the nested-function fixture repo, `suggestions` has exactly one entry for that function, with nesting before `4` and after `<= 2`, and complexity after lower than before.
- [x] Each suggestion payload has `path`, `line`, `side: "RIGHT"`, and a body with a GitHub `suggestion` block; `start_line` is present only for multi-line ranges.
- [x] The static pass flags only functions with complexity `>= 6` or nesting `> 2`; a simple function in the same diff produces no entry.
- [x] A pull request that changes only non-Python files prints empty lists and makes no LLM call.
- [x] Line ranges include decorators, and a method gets the qualified name `Class.method`.
- [x] The LLM client is the only path to Token Factory, and tests replace it with a scripted fake.
- [x] The sandbox fake runs `pytest` with branch coverage in a temp copy of the repo.
- [x] A live test confirms that the three model IDs in the spec exist in the Token Factory model list. If they differ, it fixes the IDs in the config.
- [x] The process exits with code 0 in every case above.

## Comments

- 2026-10-02: Built the tracer bullet. `uv run pytest -q` passes 5 seam tests; the live test is deselected by default.
- 2026-10-02: Live model-ID check passed (`uv run --env-file .env pytest -m live`). All three spec IDs exist in the Token Factory model list, so the config is unchanged.
- Fixture numbers (radon, measured): nested `can_edit` complexity 5, nesting 4; flat rewrite complexity 4, nesting 0. One-line `all_set(a..f)` complexity 6, nesting 0; rewrite with `all(...)` complexity 1.
- Every assertion was mutation-checked: 14 one-line defects in the code (elif counted as a level, thresholds removed or off by one, decorator line dropped, class prefix dropped, no re-indent, `start_line` on single-line ranges, `side` LEFT, no `*.py` filter, rewrite not spliced, fence not stripped) each make at least one test fail.
- `review` ignores `--dry-run` for now and always prints the JSON. Posting lands in ticket 06.
- The CLI catches any exception, prints it to stderr, prints the empty result, and exits 0, so the gate never fails CI. Tests assert stderr is empty so a hidden crash cannot pass as an empty result.
- A rewrite whose lines are not all in the diff's added lines goes to `followup` as `{path, start_line, end_line, code}`.
