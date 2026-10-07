# 20 — Tests reply as one pydantic object, sent as markdown

**What to build:** The request for characterization tests has three reply forms: calls, a test file, or "cannot test". The model writes its reply as markdown. The gate parses the reply into one pydantic object and checks it before it uses it. Prose can no longer become a test file. When the calls miss branches, the gate asks once for a test file instead of rejecting the function.

**Blocked by:** 21 (it changes `strip_fence` and turns thinking off in `complete`; this ticket uses both)

**Status:** ready-for-agent

## Context

The gate proves a rewrite with characterization tests: tests that record what the original code does now, bugs included. `characterize` in `slopgate/review.py` asks Super for them with `TESTS_PROMPT`. Today the reply has two forms:

1. JSON `{"inputs": [...]}`: the arguments of calls. The gate runs each call on the original code and writes the tests from the recorded results (`record` in `slopgate/review.py`). This form is offered only for a function, not for a method.
2. Any other text: the gate uses it as a pytest file, with no check.

On PR #9 the gate examined `fake_llm`, a pytest fixture in `tests/conftest.py`. Super replied in prose ("I'm unable to write characterization tests without seeing the function…"). The gate saved the prose as `tests/test_slopgate_2.py`, and pytest failed with `SyntaxError: invalid character '’'`. In a reproduction, 2 of 3 replies were prose and 1 of 3 was `{"inputs": []}`. Ticket 17 keeps test files out of the gate, but any function that Super cannot test can cause the same failure.

## Measurement (2026-10-04 to 2026-10-06)

"Proven" means that the tests pass on the original code and cover every branch of the function. "Calls+file" offers all three forms (as for a function). "File only" offers no calls form (as for a method).

### Final fair run: markdown against a forced tool call

Both ways got the same prompt text. Only the reply channel was different: a ```` ```python ```` block, or a forced tool call (`tool_choice` names the tool) whose parameters are the pydantic union. Thinking was off in both (`enable_thinking: False`). The run used 5 demo functions (`money`, `apply_discount`, `can_checkout`, `shipping_label`, `format_total`), 4 complex Slopgate functions (`broken_rule`, `forwarded`, `import_line`, `structure_hash`), and `fake_llm`, 3 runs each.

| | Markdown | Tool call |
|---|---|---|
| Calls+file, simple | **15/15** | 13/15 |
| Calls+file, complex | **5/12** | 3/12 |
| File only, simple | 15/15 | 15/15 |
| File only, complex | 10/12 | 10/12 |
| **Total proven** | **45/54** | **41/54** |
| Broken syntax | **0** | 3 (wrong bracket type: `money(1234.567]`, and `]` closing `(` in a test file) |
| Wrong refusals | **0** | 3 (`forwarded`: "requires AST nodes") |
| `fake_llm` (a fixture: "cannot test" is correct) | **6/6 `cannot_test`** | 1/6 |
| Mean time | 2.2–10.3 s | 1.5–4.1 s |

Decision: the model replies in markdown, and the gate parses the reply into the pydantic object. Decisions without code use a tool call (ticket 18).

### Earlier findings that shaped the prompt

1. **Thinking cuts replies off.** Super is a thinking model. With thinking on, a test request for `forwarded` used 17,000 to 34,000 characters of reasoning. 2 of 3 replies hit the 8,192-token output limit (`finish_reason: "length"`) and were empty or cut off. Mean time was 20 to 25 s. Ticket 21 turns thinking off in `complete`.
2. **The old refusal wording invites false refusals.** "Use this form if you cannot write tests from the code shown" gave refusals such as "missing definitions for `BOOL_CALLS`" and "the imports are not shown". The tests run the real code, so the model never needs to see helpers or imports. The new wording (form 3 below) removed these refusals.
3. **On complex functions, calls miss branches.** When calls were allowed, 13 of 24 complex replies chose calls that did not cover every branch. With a test file, 20 of 24 complex replies were proven. So the gate asks for a test file when calls miss branches (design step 4).
4. **Optional tools refuse too often.** Pydantic AI with the forms as optional tools (`tool_choice: "auto"`) refused 12 of 12 complex test-file requests with false reasons. Do not offer "cannot test" as an optional tool.
5. **A JSON schema in `response_format` alone does not reach the model.** 40 of 46 test files were an empty string.

## Design

1. Add the models to `slopgate/review.py`. The model never sees these classes. The gate's parser fills them in.

   ```python
   class Calls(BaseModel):
       form: Literal["calls"]
       calls: list[str]          # the argument text of each call, e.g. "[10], 50"

   class TestFile(BaseModel):
       form: Literal["test_file"]
       code: str

   class CannotTest(BaseModel):
       form: Literal["cannot_test"]
       reason: str

   TestsReply = Annotated[Calls | TestFile | CannotTest, Field(discriminator="form")]
   ```

   A union with a `form` tag allows exactly one form. Three optional fields would allow a reply with two forms or with none.

2. New `TESTS_PROMPT`. This is the text of the fair run. For a method, leave out form 1 and renumber. Keep the callee section (`CALLEES`) after it, as today.

   ````
   Write characterization tests for the Python function below. The tests must record what the code does now, bugs included.

   Reply in one of these forms:

   1. Calls. Use this form if calls with plain-value arguments (literals and builtins only) cover every branch. Write one call to `{qualname}` per statement, for example `apply_discount([10], 50)`. Do not predict results: each call runs on the code, and its return value or exception is recorded.
   2. Test file. Use this form for all other functions. Write one pytest file. Import the target with exactly this line: from {module} import {name}. Call the function as `{qualname}`. Cover every branch.
   3. Cannot test. The tests run the real code, so you do not need to see helpers or imports. Use this form only when no test can call the function, for example a pytest fixture.

   For the calls form or the test file form, reply with one ```python block and no other text. For the cannot test form, reply with one line: CANNOT_TEST: <reason>

   File: {path}

   ```python
   {source}
   ```
   ````

3. Replace `proposed_inputs` with `parse_tests_reply(text, function, calls_allowed) -> TestsReply | None`:
   1. The reply starts with `CANNOT_TEST:`: return `CannotTest`.
   2. No ```` ```python ```` block (`strip_fence` returns `None`, ticket 21), or `ast.parse` fails: return `None`.
   3. `calls_allowed`, and every top-level statement is an expression that calls `{qualname}` by name: return `Calls`. Each item is the text between the outer parentheses of one call (`ast.get_source_segment` of the call, without the name and the parentheses). This is the same text that `record` takes today.
   4. Otherwise: return `TestFile`.

4. In `characterize`, handle each result as below. Each retry text is appended to the request, as the retries are today. The function makes at most 2 model requests in total, as today.
   - `CannotTest`: reject the function with the reason "model cannot test: <reason>". Do not retry.
   - `None`, or `Calls` with an empty list: retry with

     ```
     Your reply had no ```python block, or the block did not parse: {error}. Reply again in one of the forms above.
     ```

     If the second reply also fails, reject with the reason "tests reply is not python".
   - `Calls` that `record` cannot run: retry with the new `INPUTS_RETRY`:

     ````
     Your calls could not run on the unchanged code above. Each argument must be a literal or a builtin: quote every string, and use no bare names. Reply again with one ```python block of calls.

     Earlier calls:

     ```python
     {calls}
     ```

     Failure:

     {failure}
     ````

   - `Calls` that pass but miss branches (new; today the gate rejects here): retry with

     ````
     Your calls miss {missed} branches of the function. Write a test file instead: reply with one ```python block that holds one pytest file. Import the target with exactly this line: from {module} import {name}. Cover every branch.
     ````

   - `TestFile` that fails on the original code: retry with the new `TESTS_RETRY`:

     ````
     Your earlier test file failed on the unchanged code above, so some expected values are wrong. Reply with the corrected file in one ```python block: keep the inputs where you can, and change each expected value to what the code actually returns or raises.

     Earlier test file:

     ```python
     {tests}
     ```

     Failure:

     {failure}
     ````

5. Send the tests request through `complete` with thinking off (ticket 21). Do not send it as a JSON schema or a tool call. The measurement above shows why.

## Acceptance

- [ ] A fake reply of prose with no block retries once, and then rejects with the reason "tests reply is not python". No test file is written to the sandbox.
- [ ] A fake reply `CANNOT_TEST: fixture` rejects with "model cannot test: fixture" and makes no retry.
- [ ] A fake reply with a block of three calls to the function gives `Calls` with three items, and `record` gets the same argument text as today.
- [ ] A fake reply with a block that holds `def test_x(): ...` gives `TestFile`.
- [ ] For a method, the prompt has no calls form, and a block of bare calls gives `TestFile`.
- [ ] Fake calls that pass but miss a branch cause one retry that asks for a test file. A passing test file from that retry is used.
- [ ] The rendered prompt contains the form 3 text "you do not need to see helpers or imports".
- [ ] Live test (`-m live`): on `apply_discount` and on `broken_rule`, the gate proves the tests. On `fake_llm`, the reply is `CannotTest`.
- [ ] `uv run pytest -q` passes.

## Comments
