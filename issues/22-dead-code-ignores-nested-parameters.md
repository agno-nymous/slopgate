# 22 — Dead-code check ignores unused parameters of nested functions and lambdas

**What to build:** The dead-code check stops flagging a function because a nested function or a lambda inside it has an unused parameter.

**Blocked by:** None — can start immediately.

**Status:** ready-for-agent

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

- [ ] A function that returns `lambda texts, unused: texts` and has no other dead code is not flagged `dead`.
- [ ] A function with a nested `def inner(a, unused): return a` and no other dead code is not flagged `dead`.
- [ ] A function with an unused local variable `x = 1` is still flagged `dead`.
- [ ] Code after a `return` is still flagged `dead`.
- [ ] `uv run pytest -q` passes.

## Comments
