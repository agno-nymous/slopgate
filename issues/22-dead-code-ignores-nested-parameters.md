# 22 — Dead-code check ignores unused parameters of nested functions and lambdas

## Summary

- **Goal:** Stop the dead-code check from flagging a function because a nested function or a lambda inside it has an unused parameter. Example: `onnx_model` in `slopgate/embed.py` has `lambda texts, normalize_embeddings: ...`, and callers must pass that parameter.
- **Checkable finish condition:** `has_dead_code` returns false for a function with `lambda texts, unused: texts` and for a function with a nested `def inner(a, unused)`. It still returns true for an unused local `x = 1` and for code after a `return`. `uv run pytest -q` passes.
- **Evidence:** Done. Before, `has_dead_code` called `onnx_model` and `fake_llm` (in `tests/conftest.py`) dead on main. After, it calls neither dead. The new test has 4 parameter sets. Before the fix, 2 failed and 2 passed. After, all 4 pass. The offline suite gave 110 passed. A live dry run gave one suggestion for `total` and none for `encoder`.
- **Constraints:** Collect the parameter names of every function and lambda in the AST with `ast.walk`, not only of the top-level function. The rest of `has_dead_code` stays the same. Known limit: a local variable with the same name as a nested parameter is also ignored. This can only miss a `dead` finding.

**Blocked by:** None — can start immediately.

**Status:** done

## Context

The gate gives a function the slop kind `dead` when vulture finds unused code inside it. The function that does this check is `has_dead_code` in `slopgate/review.py`. Vulture reports an unused parameter with type `variable`, the same type as an unused local variable. Removing a parameter changes the signature, so `has_dead_code` ignores the names of the parameters of the function under review.

It does not ignore the parameters of a nested function or of a lambda inside it. On PR #9 this gave two false hits:

1. `onnx_model` in `slopgate/embed.py` returns `SimpleNamespace(encode=lambda texts, normalize_embeddings: ...)`. The lambda must accept `normalize_embeddings`, because callers pass it, but the body does not use it. The gate asked Super to remove dead code, Super returned the function unchanged, and the gate posted an empty suggestion.
2. `fake_llm` in `tests/conftest.py` defines a nested `def complete(model, prompt, json=False)`. The fake must accept `json` to match the real signature. The gate tried to write tests for a pytest fixture, and the run failed (ticket 17 covers test files).

A parameter of a nested function or a lambda is part of an interface that callers use. Removing it breaks the callers. So the check must ignore it, the same as for the top-level function.

## Design

Collect the parameter names from every function and lambda in the function's AST, not only from the top-level node. Walk the tree with `ast.walk` and take the `args` of every `ast.FunctionDef`, `ast.AsyncFunctionDef`, and `ast.Lambda`. The rest of `has_dead_code` stays the same.

Known limit: a local variable with the same name as a nested parameter is also ignored. This is rare and only causes a missed `dead` finding, never a wrong change.

## Acceptance

- [x] A function that returns `lambda texts, unused: texts` and has no other dead code is not flagged `dead`.
- [x] A function with a nested `def inner(a, unused): return a` and no other dead code is not flagged `dead`.
- [x] A function with an unused local variable `x = 1` is still flagged `dead`.
- [x] Code after a `return` is still flagged `dead`.
- [x] `uv run pytest -q` passes.

## Comments

- 2026-10-06: Built. `has_dead_code` in `slopgate/review.py` now walks the AST of the function with `ast.walk`. It collects the parameter names of every `FunctionDef`, `AsyncFunctionDef`, and `Lambda` in the tree. Before, it collected only the parameters of the top-level function. The rest of the check did not change.
- Cause: vulture reports an unused parameter with type `variable`. The old code removed only the top-level parameters from these reports. So an unused parameter of a nested function or a lambda made the function `dead`.
- The two false hits from PR #9, measured with `has_dead_code` on the real files:

  | Function | main | this branch |
  |---|---|---|
  | `onnx_model` in `slopgate/embed.py` | dead | not dead |
  | `fake_llm` in `tests/conftest.py` | dead | not dead |

- Worked example. A demo repo adds two functions to `app/enc.py` in one commit:

  ```python
  def encoder(scale):
      return SimpleNamespace(encode=lambda texts, normalize_embeddings: [len(t) * scale for t in texts])


  def total(values):
      count = 0
      result = 0
      for v in values:
          result += v
      return result
  ```

  The lambda must accept `normalize_embeddings`, because callers pass it. `count` in `total` is real dead code. On main, `has_dead_code` flags both functions. On this branch, it flags only `total`. The live gate run (`slopgate review --dry-run --sandbox local`, real Super) took 13.0 s. It gave one suggestion: the `dead` rewrite of `total` without `count`, with 2 characterization tests passed in the sandbox. It gave no suggestion for `encoder` and made no model call for it.
- Tests: one test with 4 parameter sets in `tests/test_review.py` calls `has_dead_code` directly. It covers the 4 behavior boxes. Before the fix, the lambda case and the nested `def` case failed (`assert True is False`, 2 failed, 2 passed). After the fix, all 4 pass. The `dead` entry in `KIND_CASES` already tested an unused local and code after `return` together in one function. The new test checks each of the two alone, so a break in one check cannot hide behind the other.
- Full offline suite: 110 passed, 10 deselected (the `live` tests).
- Known limit (from the design): a local variable with the same name as a nested parameter is also ignored. This causes only a missed `dead` finding, never a wrong change.
