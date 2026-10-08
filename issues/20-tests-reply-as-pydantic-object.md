# 20 — Tests reply as one pydantic object, sent as markdown

**What to build:** The request for characterization tests has three reply forms: calls, a test file, or "cannot test". The model writes its reply as markdown. The gate parses the reply into one pydantic object and checks it before it uses it. Prose can no longer become a test file. When the calls miss branches, the gate asks once for a test file instead of rejecting the function.

**Blocked by:** 21 (it changes `strip_fence` and turns thinking off in `complete`; this ticket uses both)

**Status:** done

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

3. Replace `proposed_inputs` with `parse_tests_reply(text, function, calls_allowed) -> TestsReply`:
   1. The reply starts with `CANNOT_TEST:`: return `CannotTest`.
   2. No ```` ```python ```` block (`strip_fence` returns `None`, ticket 21), or `ast.parse` fails: raise `ValueError` with the error text. The retry text uses it as `{error}`.
   3. `calls_allowed`, and the block has no top-level `def`, `async def`, or `class`: the block is a script. Return `Calls` with each call to `{qualname}` in the script, in source order. Each item is the argument text of one call. Skip a call whose arguments use a name other than a builtin, because the recorder cannot evaluate it. If no call is left, raise `ValueError`.
   4. Otherwise: return `TestFile`.

   **Change during implementation (2026-10-08).** The first version of step 3.3 took `Calls` only when every top-level statement was a bare call. Live Super never replied in that shape for `apply_discount`. It wrote a script: the import line, `assert apply_discount(100, 20) == 80.0` lines, `try/except ValueError` blocks, and sometimes `print(...)`. Measured with thinking off, 8 tries each:

   | Parser or prompt | `apply_discount` as `Calls` | `broken_rule` |
   |---|---|---|
   | Bare calls only (first version) | 0/8 | 8/8 test file |
   | Bare calls, plus an example block of calls in the prompt | 0/8 | 8/8 `CANNOT_TEST` (wrong) |
   | Skip the import, unwrap `print` and one-call `try` | 5/8 | 8/8 test file |
   | Script: every call in a block with no `def` or `class` | 7/8 (1/8 was a pytest file) | 8/8 test file |

   The user chose the script rule. The recorder runs each call on the real code, so the values that the model predicts in the script do not matter.

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

- [x] A fake reply of prose with no block retries once, and then rejects with the reason "tests reply is not python". No test file is written to the sandbox.
- [x] A fake reply `CANNOT_TEST: fixture` rejects with "model cannot test: fixture" and makes no retry.
- [x] A fake reply with a block of three calls to the function gives `Calls` with three items, and `record` gets the same argument text as today.
- [x] A fake reply with a block that holds `def test_x(): ...` gives `TestFile`.
- [x] For a method, the prompt has no calls form, and a block of bare calls gives `TestFile`.
- [x] Fake calls that pass but miss a branch cause one retry that asks for a test file. A passing test file from that retry is used.
- [x] The rendered prompt contains the form 3 text "you do not need to see helpers or imports".
- [x] Live test (`-m live`): on `apply_discount` and on `broken_rule`, the gate proves the tests. On `fake_llm`, the reply is `CannotTest`.
- [x] `uv run pytest -q` passes.

## Comments

### 2026-10-08: done

**What was built.** The gate asks Super for characterization tests in one of three forms: calls, a test file, or `CANNOT_TEST: <reason>`. `parse_tests_reply` in `slopgate/review.py` reads the reply into one of three pydantic objects: `Calls`, `TestFile`, or `CannotTest`. Prose never becomes a test file now. A reply without a python block gets one retry, and then the function is rejected with "tests reply is not python". When recorded calls miss a branch, the gate asks once for a test file. `proposed_inputs`, `INPUTS_FORM`, `EMPTY_INPUTS_RETRY`, and the JSON fence fallback are deleted.

**Two changes to the design.**

1. `parse_tests_reply` raises `ValueError` and does not return `None`. The retry text needs the error, and `None` cannot hold it.
2. A block with no top-level `def` or `class` is a script, and every call in it is recorded (design step 3, "Change during implementation"). Calls whose arguments use a name that is not a builtin are skipped.

**Worked example (live run, Super, thinking off).** The target is `apply_discount` in `app/pricing.py`:

```python
def apply_discount(price, percent):
    if percent < 0 or percent > 100:
        raise ValueError("percent must be 0-100")
    return round(price * (100 - percent) / 100, 2)
```

Super replied with a script, not with bare calls. Part of it:

```python
from app.pricing import apply_discount

assert apply_discount(99.99, 50) == 50.0
try:
    apply_discount(100, -5)
    assert False, "Expected ValueError"
except ValueError as e:
    assert str(e) == "percent must be 0-100"
assert apply_discount(100, 0.001) == 99.9
```

Two of the predicted values are wrong. The real results are `49.99` and `100.0`. The first version of the parser read this reply as a test file. Pytest then found no tests ("no tests ran"), and the gate rejected the function. The new parser reads the script as `Calls` with 22 items, for example `'99.99, 50'` and `'100, -5'`. The recorder runs each call on the real code and writes the tests from the real results. The tests passed on the original code and covered every branch, from 1 reply in 7.3 s.

**Measured results.**

- `uv run pytest -q`: 216 passed, 15 deselected.
- Live test `test_super_tests_reply_is_proven_or_cannot_test`, 4 runs (3 before the review fixes, 1 after):

  | Function | Result | Replies | Time |
  |---|---|---|---|
  | `apply_discount` | proven 4/4 | 1 each | 3.4 to 7.3 s |
  | `broken_rule` | proven 4/4 | 1 in 3 runs, 2 in 1 run | 5.0 to 41.1 s |
  | `fake_llm` | `CannotTest` 4/4 | 1 each | 1.1 to 1.3 s |

- Parser measurement, 8 tries each: see the table in design step 3.

**Code review.** The review gave 13 findings. Fixes were applied for the argument text (`(f)(1)` gave `')(1'`), calls with names bound in the script, the error for a script with no usable call, and the structure of `characterize`. A new test calls the parser with odd call shapes. These findings were rejected:

- Force a test file after the missed-branch retry. A script in that retry then gives "no tests ran". Its calls can cover the missed branch.
- `def main()` scripts. No measured reply had this shape.
- Nested target calls. They are recorded as two calls, and a test shows this.
- Retry text for recorded calls that fail on the original code. This case is rare.
- An untagged union. The ticket asks for the tagged models.

**Known limits.**

- Sandbox runs have no time limit. A call such as `input()` or an infinite loop blocks the run. This was true before this ticket. A separate task tracks it.
- For a method, a script reply runs as a pytest file and gives "no tests ran". The one retry then asks for a corrected file.
- The `form` tags of the pydantic models are not checked, because the parser builds each model directly.
