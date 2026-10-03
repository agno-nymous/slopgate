# 01 — Tracer bullet: the gate fixes one nested function

**What to build:** The first end-to-end path of the pull request gate. A user runs `slopgate review --dry-run` on a local git repo with a base ref and a head ref. The head commit adds a function with 4 levels of nested `if`. The gate finds the function, asks Nemotron Super for characterization tests and a rewrite, proves both with the local sandbox fake, and prints one suggestion as JSON. The suggestion shows cyclomatic complexity and nesting depth before and after, and the test count.

This ticket also sets up the project: package layout, MIT license, dependencies, the Token Factory client, the config module with all four thresholds, and the `live` pytest marker.

**Blocked by:** None — can start immediately.

**Status:** ready-for-agent

- [ ] `slopgate review --base <ref> --head <ref> --dry-run` prints JSON with the keys `suggestions`, `followup`, and `rejected`.
- [ ] On the nested-function fixture repo, `suggestions` has exactly one entry for that function, with nesting before `4` and after `<= 2`, and complexity after lower than before.
- [ ] Each suggestion payload has `path`, `line`, `side: "RIGHT"`, and a body with a GitHub `suggestion` block; `start_line` is present only for multi-line ranges.
- [ ] The static pass flags only functions with complexity `>= 6` or nesting `> 2`; a simple function in the same diff produces no entry.
- [ ] A pull request that changes only non-Python files prints empty lists and makes no LLM call.
- [ ] Line ranges include decorators, and a method gets the qualified name `Class.method`.
- [ ] The LLM client is the only path to Token Factory, and tests replace it with a scripted fake.
- [ ] The sandbox fake runs `pytest` with branch coverage in a temp copy of the repo.
- [ ] A live test confirms that the three model IDs in the spec exist in the Token Factory model list. If they differ, it fixes the IDs in the config.
- [ ] The process exits with code 0 in every case above.
