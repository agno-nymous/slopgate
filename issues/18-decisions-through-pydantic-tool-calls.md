# 18 — Model decisions through pydantic tool calls

**What to build:** A new model call, `decide`, sends a prompt with one tool whose parameters are a pydantic model. It forces the model to call that tool, and it returns the arguments as a parsed pydantic object. The gate's duplicate check uses it with a `SameJob` model.

**Blocked by:** None — can start immediately.

**Status:** ready-for-agent

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

- [ ] `decide` with a fake client returns a `SameJob` object for a valid tool call, and `None` for a reply with no tool call or with a missing field.
- [ ] The request that `decide` sends has one tool, whose parameters hold each field description, a `tool_choice` that names it, and `chat_template_kwargs: {"enable_thinking": False}`.
- [ ] `find_duplicate` skips a candidate when `decide` returns `None`, and returns the helper when `same_job` is true.
- [ ] Live test (`-m live`): `decide(SUPER, ..., SameJob)` and `decide(LIGHTNING, ..., SameJob)` each return `same_job=True` for a renamed copy of `apply_discount`.
- [ ] `uv run pytest -q` passes.

## Comments
