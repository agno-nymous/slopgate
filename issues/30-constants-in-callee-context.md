# 30 — Give the test writer the constants the target reads

**What to build:** The "Code it calls" section of the tests prompt (ticket 12) shows the functions that the target calls. It does not show the module-level constants that the target reads. Then Super guesses their values, and its tests fail on the original code. Add the assignment of each repo constant that the target or one of its callees reads to the same section.

**Blocked by:** None — can start immediately.

**Status:** ready-for-agent

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
