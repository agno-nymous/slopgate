# 21 — Code replies: one Python block, thinking off, and reject a rewrite with no change

## Summary

- **Goal:** The gate takes model-written code safely. Thinking is off, the rewrite arrives as one Python block, and a rewrite with no change is rejected. Example: on PR #9 the gate posted a suggestion for `onnx_model` in `slopgate/embed.py` that was identical to the original.
- **Checkable finish condition:** A fake reply with prose and no Python block gives a `rejected` entry with the reason "rewrite reply is not a python block". An unchanged rewrite gives "rewrite makes no change". A reply with `finish_reason: "length"` gives "reply cut off". `uv run pytest -q` passes.
- **Evidence:** Before: with thinking on, 2 of 3 replies for `forwarded` hit the 8,192-token limit, and each took 20 to 37 s. After: 134 tests passed, 12 deselected, and the 10 live tests passed. The new live test fails with thinking on. Three gate runs on a scratch repo had 0 cut-off replies and rejected `can_edit` as "rewrite makes no change".
- **Constraints:** Code never goes inside JSON or tool-call arguments. The block ends at the first later line that is only three backticks. "No change" means the same AST and the same comments, so a rewrite that only removes a comment is not rejected. These rejections run no sandbox and no Ultra retry.

**Blocked by:** None — can start immediately.

**Status:** done

## Context

### Thinking

All three Nemotron models are thinking models. `complete` in `slopgate/llm.py` sends no `chat_template_kwargs`, so thinking is on for every text request. On 2026-10-04, a tests request for a complex function (`forwarded` in `slopgate/review.py`) used 17,000 to 34,000 characters of reasoning. 2 of 3 replies hit the 8,192-token output limit (`finish_reason: "length"`). The reply was then empty or cut off, and each request took 20 to 37 s.

With `extra_body={"chat_template_kwargs": {"enable_thinking": False}}`, a check on 2026-10-06 gave 0 reasoning characters on Lightning, Super, and Ultra, for both text and tool calls. A short rewrite took 0.7 to 0.9 s instead of 1.2 to 9.5 s. In the fair tests run (ticket 20), 120 of 120 replies with thinking off ended with `stop` or `tool_calls`, and none was cut off.

### The rewrite reply

Two model requests ask for a rewrite of a function, and both live in `slopgate/review.py`:

1. Super gets the first request (`REWRITE_PROMPT`).
2. When the rewrite fails its tests, Ultra gets one retry (`RETRY_PROMPT`). It contains the failed rewrite and the failure output.

Today the prompt says "Reply with the full rewritten function, decorators included, and nothing else." The gate takes the code from the reply with `strip_fence` in `slopgate/review.py`. Its regex, `` ```[\w-]*\n(.*?)``` ``, ends the block at the first ```` ``` ```` it finds, so code that contains ```` ``` ```` (in a docstring or a string) is cut short. When the reply has no fenced block, `strip_fence` returns the full reply text, so prose can reach the rule check and the sandbox as code.

Code never goes inside JSON or tool-call arguments. In the fair run of ticket 20, code inside tool-call arguments gave 3 broken files out of 54. Markdown gave 0.

### No change

On PR #9 the gate posted a suggestion for `onnx_model` in `slopgate/embed.py` that was identical to the original. Vulture gave a false "dead" hit (ticket 22 fixes that cause). Super returned the function unchanged, the unchanged code passed every test, and the gate accepted it. A suggestion with no change wastes the reviewer's time.

## Design

1. In `complete` (`slopgate/llm.py`), send `extra_body={"chat_template_kwargs": {"enable_thinking": False}}` on every request. When `finish_reason` is `"length"`, raise an error with the message "reply cut off". The callers already turn model errors into a `rejected` entry; check that they do, and make the reason "reply cut off".
2. New `REWRITE_PROMPT`. Ticket 19 later replaces the single instruction with a numbered list.

   ````
   Rewrite the Python function below. {instruction}

   Rules:
   - Keep the exact signature, the decorators, and the behavior, bugs included.
   - Add no new functions, no lambdas, and no new classes.
   - If every return gives True or False, keep it that way: `a and b` returns `a` itself when `a` is falsy, so wrap such a chain in bool().
   - Reply with one ```python block that holds the full rewritten function, decorators included. Put no text outside the block.

   ```python
   {source}
   ```
   ````

3. New `RETRY_PROMPT`: `REWRITE_PROMPT` plus

   ````
   This earlier rewrite failed:

   ```python
   {rewrite}
   ```

   Failure:

   {failure}
   ````

4. Change `strip_fence` to a strict extractor. It takes the text from the line after the first line that starts with ```` ```python ```` to the first later line that is only ```` ``` ```` (as CommonMark closes a fence). It returns `None` when the reply has no such pair of lines. Its other caller (`characterize`) must handle `None` too. Ticket 20 changes that caller again.
5. When `strip_fence` returns `None` for a rewrite, reject the candidate with the reason "rewrite reply is not a python block". Do not retry.
6. The rewrite makes no change when two things are equal after `textwrap.dedent`: the AST (`ast.dump(ast.parse(...))`) and the list of comments (the `COMMENT` tokens from `tokenize`). The AST alone is not enough, because `ast.dump` ignores comments, and kind `filler_comment` changes only comments. For "no change", reject the candidate with the reason "rewrite makes no change". Do not run the sandbox and do not retry with Ultra.
7. Some fake LLM replies in `tests/` return code without a fence. Wrap them in a ```` ```python ```` block.

## Acceptance

- [x] `complete` sends `chat_template_kwargs: {"enable_thinking": False}` (a test checks the request that the fake client gets).
- [x] A fake reply with `finish_reason: "length"` gives a `rejected` entry with the reason "reply cut off".
- [x] A fake LLM reply with prose and no python block gives one `rejected` entry with the reason "rewrite reply is not a python block". No sandbox run happens.
- [x] A fake reply whose code contains a line with ```` ``` ```` inside a string gives the full function, not a cut-off one.
- [x] A fake LLM reply that returns the original function unchanged gives one `rejected` entry with the reason "rewrite makes no change". No sandbox run happens, and no Ultra retry happens.
- [x] A rewrite that only removes a comment is not rejected as "no change".
- [x] The rendered `REWRITE_PROMPT` and `RETRY_PROMPT` contain the source inside a ```` ```python ```` block.
- [x] Live test (`-m live`): one `complete` call on Super, and one on Ultra, return a reply with no reasoning content.
- [x] `uv run pytest -q` passes.

## Comments

### 2026-10-07: done

**What was built.**

- `complete` in `slopgate/llm.py` sends `chat_template_kwargs: {"enable_thinking": False}` on every request. When `finish_reason` is `"length"`, it raises `llm.CutOff("reply cut off")`.
- The trial loop in `review()` catches `llm.CutOff` once per candidate. A cut-off reply in the tests request, the rewrite, or the Ultra retry gives the rejected reason "reply cut off". The next candidate then runs.
- `classify` and `find_duplicate` also catch `llm.CutOff`. Before this ticket, a cut-off JSON reply failed `json.loads` and was caught as `ValueError`. Without the new catch, `CutOff` would stop the whole review.
- `REWRITE_PROMPT` and `RETRY_PROMPT` use the texts in the Design. The source and the failed rewrite are in ```` ```python ```` blocks.
- `strip_fence` is strict. It returns the lines between the first line that starts with ```` ```python ```` and the first later line that is only ```` ``` ````. When the reply has no such pair, it returns `None`.
- The rewrite loop rejects a reply with no python block ("rewrite reply is not a python block"). It also rejects a rewrite that has the same AST and the same comments as the original ("rewrite makes no change"). Both checks run on the Super reply and on the Ultra retry reply. Neither check runs the sandbox or starts a retry.
- `characterize` uses the raw reply when `strip_fence` returns `None`. Ticket 20 changes this caller again.

**Design change: first closing fence, not last.** The Design said that the block ends at the last line that is only ```` ``` ````. A live run showed that this rule is wrong. For `total`, Super replied with a ```` ```python ```` test file, then about 1,500 characters of prose, then a ```` ```json ```` block. The last-fence rule put the prose into the test file. The tests failed with `SyntaxError: invalid character '—' (U+2014)`, in 4 of 4 runs. The user approved the change to the first closing fence, which is how CommonMark closes a fence. A markdown renderer also ends the block at that line, so a model cannot put a bare ```` ``` ```` line inside a code block. A ```` ``` ```` inside a string on a code line still comes through whole.

**Worked example.** This is a scratch repo with one commit that adds `app/perms.py`:

```python
def can_edit(user_active, is_owner, locked, archived):
    if user_active:
        if is_owner:
            if not locked:
                if not archived:
                    return True
                else:
                    return False
            ...

def total(prices, tax):
    count = 0
    result = 0
    for p in prices:
        # add the price to the result
        result = result + p
        ...
```

`review()` ran 3 times with real Lightning, Super, and the Contree sandbox. The results were the same in all 3 runs:

- `can_edit`: rejected, "rewrite makes no change". Lightning gave the kind `dead`, and `can_edit` has no dead code. Super returned the function unchanged, which is correct for that instruction. The gate made no sandbox run and no Ultra call. Before this ticket, the gate posted such a rewrite as an empty suggestion. Tickets 18 and 19 fix the wrong kind.
- `total`: 1 suggestion, with 9 characterization tests passed in the sandbox. The suggestion removed `count` and the three comments that restate the code:

  ```python
  def total(prices, tax):
      result = 0
      for p in prices:
          result = result + p
          result = result + p * tax
      return result
  ```

With the same prompt, the kind `nesting`, and thinking off, Super gave `can_edit` a flat rewrite in 3 of 3 direct calls.

**Measured results.**

- `uv run pytest -q`: 134 passed, 12 deselected (230 s).
- `pytest -m live -q`: 10 passed, 2 skipped (the 2 skipped tests need `onnxruntime`, which is not installed), 133 deselected (106 s).
- New live test `test_complete_replies_without_reasoning`, on Super and Ultra: 2 passed in 2.9 s. With `enable_thinking: True`, the same test fails on both models. With thinking on, Super fills both `reasoning` and `reasoning_content`, so the test checks both fields.
- 3 gate runs on the scratch repo: 0 cut-off replies. Each run made 6 model calls (1 Lightning, 5 Super) and no Ultra call.
- The new test `test_cut_off_classify_reply_skips_the_function_and_the_review_goes_on` fails when the `llm.CutOff` catch in `classify` is removed.

**Known limits.**

- `characterize` accepts only a ```` ```python ```` block. If Super puts the JSON `inputs` reply only in a ```` ```json ```` block, or the tests in an untagged fence, the raw text with the fences goes on as the reply. That reply then fails and uses the one retry. Ticket 20 replaces this path.
- If the Ultra retry is cut off, the reason is "reply cut off". The reason of the earlier Super failure is lost.
- A docstring line that is only ```` ``` ```` ends the block, so that rewrite fails the rule check ("does not parse").

### 2026-10-07: gate crash on the review of PR #15

**Problem.** The Slopgate check of PR #15 was green, but the review did not run. After 8.5 min, the gate stopped with `JSONDecodeError('Expecting property name enclosed in double quotes: line 2 column 65416 (char 65416)')` and printed an empty result.

**Cause (measured).** The Contree sandbox cuts command output at 65,535 characters. Commands that print 70,000, 100,000, and 200,000 characters each gave 65,535 characters. `characterize` printed the full coverage report with `coverage json -o -`. For this repo, that report is 120,171 characters (12 files). The JSON was cut at character 65,416, and 65,416 plus about 119 characters of pytest output and marker is 65,535. `review()` does not catch the error, so the gate lost the whole review. `cli.py` exits 0 on purpose, because the gate must never fail CI (spec, user story 12).

**Fix.** The sandbox now prints only the missed branches of the function's file, as one short JSON line (`MISSED` in `slopgate/review.py`). The size of this line does not depend on the size of the repo.

**Test.** `test_review_survives_a_sandbox_that_cuts_output_at_65535_characters` cuts each sandbox output at 65,535 characters, like Contree. The repo imports a module with 6,000 executed lines. With the old code, the test fails with the same `JSONDecodeError` at character 65,416. With the fix, the test passes.

**Memory of the gate.** During the rerun of the gate on the refs of PR #15, the process took 14 GB on the 16 GB Mac and used 6.7 GB of swap. The venv had no `onnxruntime`, so `embed.load` used the torch model. The torch model embeds up to 8,192 tokens per function (`max_seq_length` in the model config) in padded batches. The int8 ONNX model cuts each function at 512 tokens and embeds one function at a time. The workflow now runs `uv run --extra hook`, and `CLAUDE.md` gives the same commands.

**Rerun with the fix and ONNX** (`slopgate review --base 74fcd0d --head 22635c3 --dry-run`, measured with `/usr/bin/time -l`):

- The review finished, with no crash. The run took 320 s. The failed CI run took 8.5 min before it stopped.
- The peak resident memory was 397 MB. The torch run was at 14 GB when it was stopped.
- The result was 0 suggestions and 10 rejected. Two functions (`strip_fence`, and one test function) were rejected with "rewrite makes no change". Seven of the 10 candidates are test functions, which ticket 17 handles.
