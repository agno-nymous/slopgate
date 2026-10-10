# 18 — Model decisions through pydantic tool calls

## Summary

- **Goal:** Get model decisions (a kind, a yes/no verdict, a reason) as a forced tool call that parses into a pydantic object. Example: the duplicate check returns `SameJob(difference='', same_job=True)` for a renamed copy of `apply_discount`.
- **Checkable finish condition:** `uv run pytest -q` passes. The live test `test_decide_finds_a_renamed_copy_of_apply_discount` passes for Super and for Lightning, and each returns `same_job=True`. `decide` returns `None` for a reply with no tool call or with a missing field.
- **Evidence:** Done. Before, decisions used JSON mode, which checks that the reply is valid JSON but not that it has the right fields. On 2026-10-04, a JSON schema in `response_format` proved 2 of 15 and 3 of 15 runs, and a forced tool call proved 15 of 15. After: the live test passed with Super in 1.31 s and 1.84 s and Lightning in 0.67 s and 0.78 s. The offline suite gave 144 passed.
- **Constraints:** Decisions use a tool call. Code stays in a ```` ```python ```` block in markdown, never inside JSON. Thinking is off for `decide`. `classify` stays on `complete(..., json=True)` until ticket 19. `slopgate/llm.py` has no runtime pydantic import, because the hook imports it.

**Blocked by:** None — can start immediately.

**Status:** done

## Context

Slopgate gets two kinds of model replies:

1. **Decisions:** a kind name, a yes/no verdict, a short reason. These come back as a tool call (this ticket).
2. **Code:** tests and rewrites. These come back as a ```` ```python ```` block in markdown (tickets 20 and 21). Code never goes inside JSON, because the model must escape each newline and quote there, and it fails (see the measurement below).

Today the decision replies use `complete(model, prompt, json=True)` in `slopgate/llm.py`. That sets `response_format={"type": "json_object"}`. JSON mode makes sure that the reply is valid JSON, but not that it has the correct fields or types. The prompt describes the shape in words, and the caller catches a missing key.

## Measurement (2026-10-04): how the schema reaches the model

Super got the same tests request in four ways, on 5 demo functions, 3 runs each. Ticket 20 has the full table. The ways that matter here:

| Way | What the model sees | Result |
|---|---|---|
| `response_format` with a JSON schema | Nothing. The server enforces the shape, but the field descriptions are not in the prompt. | 2/15 and 3/15 proven. 40 of 46 test files were an empty string. |
| `response_format`, plus the schema JSON pasted in the prompt | The schema, as prompt text | 15/15 for short fields |
| **Forced tool call** (`tools=[...]`, `tool_choice` names the tool) | The chat template writes the tool definition, with every field `description`, into the prompt | 15/15 for short fields, no empty fields, mean 2.1 s (the fastest way) |

So a tool call is the correct way. Each `Field(description=...)` acts as an instruction to the model, and the same text defines the shape. No schema text is pasted into the prompt by hand.

A forced tool call was checked on Lightning and on Super on 2026-10-04, with `SameJob` and `SlopKinds` (ticket 19). Both models returned valid objects in 1.3 to 4.5 s.

A forced tool call does not turn thinking off by itself. On 2026-10-06, with the default setting, the models wrote 121 (Super), 379 (Lightning), and 1,016 (Ultra) characters of reasoning before the tool call. With `chat_template_kwargs: {"enable_thinking": False}`, all three wrote 0 characters and replied in 0.8 to 1.2 s, with correct objects. So `decide` turns thinking off explicitly. Whether thinking makes the duplicate check more accurate is not measured. If the duplicate check gives too many wrong answers later, turn thinking on for that call only.

## Design

1. Add `decide(model, prompt, schema)` to `slopgate/llm.py`:
   - The tool is `{"type": "function", "function": {"name": schema.__name__, "description": <the schema's description>, "parameters": schema.model_json_schema()}}`. Put the tool description in the class docstring of the pydantic model. Pydantic copies the docstring into the schema `description`. Here the docstring is prompt text, not code documentation.
   - Call `client().chat.completions.create(model=model, messages=[...], temperature=0, tools=[tool], tool_choice={"type": "function", "function": {"name": schema.__name__}}, extra_body={"chat_template_kwargs": {"enable_thinking": False}})`.
   - Record token usage in `usage`, as `complete` does.
   - Return `schema.model_validate_json(message.tool_calls[0].function.arguments)`. Return `None` when there is no tool call or when validation raises `ValidationError`.
2. Update the `fake_llm` fixture in `tests/conftest.py` so that it also fakes `decide`. Keep the `json` parameter of `complete` for now: `classify` still uses it. Ticket 19 removes it.
3. Add the model in `slopgate/review.py`:

   ```python
   class SameJob(BaseModel):
       """Report whether the new function does the same job as the existing helper."""

       difference: str = Field(description="The behavior difference between the two functions, or an empty string when they behave the same.")
       same_job: bool = Field(description="True if callers of the new function could call the existing helper instead and get the same behavior.")
   ```

   The model writes the fields in schema order. `difference` comes first, so the model states the difference before it gives the verdict. This order is not measured.
4. `find_duplicate` in `slopgate/review.py` calls `llm.decide(SUPER, SAME_JOB_PROMPT.format(...), SameJob)`. When `decide` returns `None`, go to the next candidate, as the `except` does today. The new `SAME_JOB_PROMPT`:

   ````
   Decide whether the new Python function does the same job as the existing helper, so that callers of the new function could call the helper instead.

   Reply by calling the tool `SameJob`.

   New function, in {path}:

   ```python
   {source}
   ```

   Existing helper, in {helper_path}:

   ```python
   {helper_source}
   ```
   ````
5. `classify` stays on `complete(..., json=True)` until ticket 19 changes it. If you do ticket 19 in the same branch, skip that step.

## Acceptance

- [x] `decide` with a fake client returns a `SameJob` object for a valid tool call, and `None` for a reply with no tool call or with a missing field.
- [x] The request that `decide` sends has one tool, whose parameters hold each field description, a `tool_choice` that names it, and `chat_template_kwargs: {"enable_thinking": False}`.
- [x] `find_duplicate` skips a candidate when `decide` returns `None`, and returns the helper when `same_job` is true.
- [x] Live test (`-m live`): `decide(SUPER, ..., SameJob)` and `decide(LIGHTNING, ..., SameJob)` each return `same_job=True` for a renamed copy of `apply_discount`.
- [x] `uv run pytest -q` passes.

## Comments

### 2026-10-07 — done

**What was built.** `llm.decide(model, prompt, schema)` sends one forced tool call. The tool parameters are the JSON schema of a pydantic model. The tool description is the class docstring. Thinking is off. `decide` returns the parsed object. It returns `None` when the reply has no tool call or when the arguments fail validation. `find_duplicate` now calls `decide(SUPER, ..., SameJob)` and does not parse JSON by hand. `SAME_JOB_PROMPT` puts each source in a ```` ```python ```` block. `classify` still uses `complete(..., json=True)`. Ticket 19 changes it.

`llm.py` has no runtime pydantic import. `decide` catches `ValueError`, which is the base class of pydantic's `ValidationError`. The hook imports `llm`, and a pydantic import takes 47 ms, while the full hook import takes 33 ms (measured by the code review). `pydantic>=2` is now a direct dependency in `pyproject.toml`.

**Worked example (live, 2026-10-07).** The new function adds a check that the helper does not have:

```python
def discounted(price, percent):
    if percent > 100:
        raise ValueError('percent above 100')
    return round(price * (1 - percent / 100), 2)
```

The helper is `apply_discount(price, percent)`, which returns `round(price * (1 - percent / 100), 2)`. `decide` gave these objects:

- Super, 1.60 s: `SameJob(difference='The new function raises ValueError for percent > 100, while the helper does not validate input.', same_job=False)`
- Lightning, 0.75 s: `SameJob(difference='The new function checks if percent > 100 and raises ValueError, while the existing helper does not perform this validation.', same_job=False)`

For a renamed copy of `apply_discount` (the live test), both models gave `SameJob(difference='', same_job=True)`.

**Measured results.**

- Live test `test_decide_finds_a_renamed_copy_of_apply_discount`: 2 passed. Super took 1.31 s and 1.84 s in two runs. Lightning took 0.67 s and 0.78 s.
- Offline, after the rebase on ticket 21: `uv run pytest -q` gives 144 passed, 14 deselected, in 240 s.
- Super took 1.75 s and Lightning 0.76 s in a third live run, after the rebase.
- New offline tests: `tests/test_llm.py` (the parse result, `None` for no tool call and for a missing field, the request shape) and `test_candidate_without_a_verdict_is_skipped` in `tests/test_duplicates.py`.

**Known limits.**

- The live checks use one copy and one function that differs. The accuracy of the duplicate check on real pull requests is not measured.
- The effect of the field order (`difference` before `same_job`) is not measured.
- The `fake_llm` fake of `decide` returns the queued object (a `SameJob` or `None`). It does not parse JSON. `tests/test_llm.py` tests the parse against a fake client.
- A cut-off tool call (`finish_reason: "length"`) has incomplete arguments. `decide` then returns `None`, and `find_duplicate` goes to the next candidate. `decide` does not raise `CutOff`.
