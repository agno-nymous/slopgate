# 01 — Tracer bullet: the gate fixes one nested function

## Summary

- **Goal:** A user can run `slopgate review --dry-run` on a local git repo and get one proven fix for a deeply nested function. Example: the head commit adds `can_edit`, which has 4 levels of nested `if`. The gate prints a flat rewrite of `can_edit` as a suggestion.
- **Checkable finish condition:** `slopgate review --base <ref> --head <ref> --dry-run` on the fixture repo prints JSON with the keys `suggestions`, `followup`, and `rejected`. `suggestions` holds exactly one entry, with nesting before `4` and nesting after `<= 2`. The process exits with code 0.
- **Evidence:** Done. `uv run pytest -q` passes 5 seam tests (tests that check one step, with a fake model). The live check found all three model IDs in the Token Factory list. Radon measured `can_edit` at complexity 5 and nesting 4, and the flat rewrite at complexity 4 and nesting 0. Each of 14 one-line defects makes at least one test fail.
- **Constraints:** The LLM client is the only path to Token Factory, and tests replace it with a scripted fake. The gate flags only functions with complexity `>= 6` or nesting `> 2`. A pull request with only non-Python changes makes no LLM call. The command always exits 0, so the gate never fails CI.

**Blocked by:** None — can start immediately.

**Status:** done

## Details

The first end-to-end path of the pull request gate. The user gives a base ref and a head ref. The gate finds the new function. It asks Nemotron Super for characterization tests (tests that record what the old code does) and for a rewrite. It proves both in the local sandbox fake. It prints one suggestion as JSON. The suggestion shows the cyclomatic complexity and the nesting depth before and after the rewrite. It also shows the number of tests.

This ticket also sets up the project. It creates the package layout, the MIT license, the dependencies, the Token Factory client, the config module with all four thresholds, and the `live` pytest marker.

- [x] The command `slopgate review --base <ref> --head <ref> --dry-run` prints JSON with the keys `suggestions`, `followup`, and `rejected`.
- [x] The nested-function fixture repo gives exactly one entry in `suggestions`, for that function. The entry has nesting before `4` and nesting after `<= 2`. The complexity after the rewrite is lower than the complexity before.
- [x] Each suggestion payload has `path`, `line`, `side: "RIGHT"`, and a body with a GitHub `suggestion` block. The key `start_line` is present only for ranges of more than one line.
- [x] The static pass flags only functions with complexity `>= 6` or nesting `> 2`. A simple function in the same diff produces no entry.
- [x] A pull request that changes only non-Python files prints empty lists. The gate makes no LLM call.
- [x] Line ranges include decorators. A method gets the qualified name `Class.method`.
- [x] The LLM client is the only path to Token Factory. Tests replace the LLM client with a scripted fake.
- [x] The sandbox fake runs `pytest` with branch coverage in a temp copy of the repo.
- [x] A live test confirms that the three model IDs in the spec exist in the Token Factory model list. If the IDs differ, the test fixes the IDs in the config.
- [x] The process exits with code 0 in every case above.

## Comments

- 2026-10-02: Built the tracer bullet. The command `uv run pytest -q` passes 5 seam tests. The live test is deselected by default.
- 2026-10-02: The live check of the model IDs passed (`uv run --env-file .env pytest -m live`). All three spec IDs exist in the Token Factory model list. The config is unchanged.
- Fixture numbers (radon, measured): The nested `can_edit` function has complexity 5 and nesting 4. The flat rewrite has complexity 4 and nesting 0. The one-line `all_set(a..f)` function has complexity 6 and nesting 0. The rewrite with `all(...)` has complexity 1.
- Every assertion was mutation-checked. There were 14 one-line defects in the code. The defects were: `elif` counted as a level, thresholds removed or off by one, decorator line dropped, class prefix dropped, no re-indent, `start_line` on single-line ranges, `side` LEFT, no `*.py` filter, rewrite not spliced, and fence not stripped. Each defect makes at least one test fail.
- The review command ignores `--dry-run` for now. The review command always prints the JSON. Posting lands in ticket 06.
- The CLI catches any exception and prints it to stderr. The CLI then prints the empty result and exits 0. The gate never fails CI. Tests assert that stderr is empty. A hidden crash cannot pass as an empty result.
- A rewrite goes to `followup` as `{path, start_line, end_line, code}` when not all of its lines are in the added lines of the diff.
