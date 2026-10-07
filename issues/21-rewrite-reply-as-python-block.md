# 21 — Code replies: one Python block, thinking off, and reject a rewrite with no change

**What to build:** Three changes to the requests that return code:

1. `complete` turns thinking off and rejects a reply that was cut off.
2. The rewrite prompt asks for exactly one ```` ```python ```` block. The gate takes the code with a strict extractor and rejects a reply that has no such block.
3. The gate rejects a rewrite that is the same code as the original.

**Blocked by:** None — can start immediately.

**Status:** ready-for-agent

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

4. Change `strip_fence` to a strict extractor. It takes the text from the line after the first line that starts with ```` ```python ```` to the last line that is only ```` ``` ````. It returns `None` when the reply has no such pair of lines. Its other caller (`characterize`) must handle `None` too. Ticket 20 changes that caller again.
5. When `strip_fence` returns `None` for a rewrite, reject the candidate with the reason "rewrite reply is not a python block". Do not retry.
6. The rewrite makes no change when two things are equal after `textwrap.dedent`: the AST (`ast.dump(ast.parse(...))`) and the list of comments (the `COMMENT` tokens from `tokenize`). The AST alone is not enough, because `ast.dump` ignores comments, and kind `filler_comment` changes only comments. For "no change", reject the candidate with the reason "rewrite makes no change". Do not run the sandbox and do not retry with Ultra.
7. Some fake LLM replies in `tests/` return code without a fence. Wrap them in a ```` ```python ```` block.

## Acceptance

- [ ] `complete` sends `chat_template_kwargs: {"enable_thinking": False}` (a test checks the request that the fake client gets).
- [ ] A fake reply with `finish_reason: "length"` gives a `rejected` entry with the reason "reply cut off".
- [ ] A fake LLM reply with prose and no python block gives one `rejected` entry with the reason "rewrite reply is not a python block". No sandbox run happens.
- [ ] A fake reply whose code contains a line with ```` ``` ```` inside a string gives the full function, not a cut-off one.
- [ ] A fake LLM reply that returns the original function unchanged gives one `rejected` entry with the reason "rewrite makes no change". No sandbox run happens, and no Ultra retry happens.
- [ ] A rewrite that only removes a comment is not rejected as "no change".
- [ ] The rendered `REWRITE_PROMPT` and `RETRY_PROMPT` contain the source inside a ```` ```python ```` block.
- [ ] Live test (`-m live`): one `complete` call on Super, and one on Ultra, return a reply with no reasoning content.
- [ ] `uv run pytest -q` passes.

## Comments
