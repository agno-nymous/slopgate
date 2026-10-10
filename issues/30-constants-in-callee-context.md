# 30 — Give the test writer the constants the target reads

## Summary

- **Goal:** Show the test writer the constants that the function reads. Example: `find_duplicate` reads `DUPLICATE_SCORE = 0.30`. Super did not see the value, guessed `0.8`, and 4 of 5 tests failed on PR #17.
- **Checkable finish condition:** An offline test with a fake model checks the recorded prompt: for a function that reads the imported constant `LIMIT`, the "Code it calls" section holds `LIMIT = 30`. `uv run pytest -q` passes. A live measurement on `find_duplicate` at commit b2a2ad0 (8 runs before and 8 after) records how many runs assert `0.8` and how many give proven tests.
- **Evidence:** Not built yet. Before: on PR #17 (2026-10-08), the same error came back in two gate runs. After: the live measurement of 8 runs before and 8 after the change.
- **Constraints:** Extend `called_code` in `slopgate/review.py`. Add a name only when it is a module-level assignment with a plain name target, found in the same file or through `from <repo module> import <name>`. Do not add functions, classes, parameters, or local variables. Add each constant once, under the `# <path>` heading of its file. Show an assignment of more than 20 lines as `NAME = ...  # <n> lines, not shown`. A function that reads no constant gets the same prompt as before.

**Blocked by:** None — can start immediately.

**Status:** wontfix

## Context

On PR #17 (2026-10-08), the gate wrote tests for `find_duplicate` in `slopgate/review.py`. The function calls `index.search(pool, function.source, DUPLICATE_SCORE, 5)`. `DUPLICATE_SCORE` comes from `from slopgate.config import ...` and is `0.30`. Super did not see the value. It asserted the call `search([], 'def empty(): pass', 0.8, 5)`, and 4 of 5 tests failed on the original code. The same error came back in two gate runs.

CoverUp gives the model a tool that returns the definition of any name in the excerpt, constants included. Its authors write that without the imports and these definitions, "LLMs often make incorrect assumptions about symbols in the code" ([Pizzorno and Berger 2025](https://arxiv.org/html/2403.16218v3)). Slopgate gets the same result without a tool call: it adds the definitions to the prompt before it sends it.

## Design

1. Extend `called_code` in `slopgate/review.py`. For the target and for each callee that it finds, collect each name that the function body reads (`ast.Name` with `ast.Load`).
2. A name is a repo constant when it resolves to a module-level `ast.Assign` or `ast.AnnAssign` with a plain name target. The name resolves in the same file, or through `from <repo module> import <name>`, in the same way as callee names now.
3. Do not add a name that is a function, a class, or a parameter or local variable of the function.
4. Add each constant once, under the `# <path>` heading of its file, as the source lines of the assignment.
5. If the assignment has more than 20 lines, add only `NAME = ...  # <n> lines, not shown`. Long prompt strings and tables then do not fill the prompt.
6. A target that reads no repo constant gets the same prompt as before.

## Acceptance

- [ ] A function that reads an imported constant (`from pkg.config import LIMIT`) gets `LIMIT = 30` in the "Code it calls" section. A seam test checks the recorded prompt.
- [ ] A constant from the same file is added. A constant that a callee reads is added.
- [ ] A local variable or a parameter with the same name as a module constant is not added.
- [ ] An assignment of more than 20 lines appears as one `... not shown` line.
- [ ] A function that reads no constant gets the same prompt as before.
- [ ] `uv run pytest -q` passes.
- [ ] Live measurement: run `characterize` on `find_duplicate` at commit b2a2ad0, 8 runs before and 8 runs after the change. Record how many runs assert `0.8` and how many runs give proven tests.

## How to verify by hand

1. Call `called_code(".", "b2a2ad0", <find_duplicate function>)` in a Python shell.
2. Check that the output contains `DUPLICATE_SCORE = 0.30`.

## Comments

### 2026-10-10 — wontfix: replaced by ticket 41

Ticket 41 replaced the Super call in `characterize` with an agent loop in a sandbox session. The agent can read any file of the repo with `cat` or `grep`, so it can find a constant without help. `called_code` is deleted.

Measured in ticket 41: the agent proved `find_duplicate` at b2a2ad0 (the example of this ticket) in 2 of 3 runs. The old flow did not prove it in run 2. Design B of ticket 41 built the design of this ticket (constants in the prompt) and proved 8 of 36 functions in run 2, against 24 of 36 for the agent.
