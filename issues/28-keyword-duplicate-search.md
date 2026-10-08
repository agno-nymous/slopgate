# 28 — Keyword duplicate search in the gate

**What to build:** The gate finds duplicate candidates with token Jaccard, not with CodeRankEmbed vectors. The gate then loads no embedding model and installs no torch. The exact structure-hash match stays the first step. The Super same-job check stays the final decision. The hook does not change: it keeps the hybrid score of ticket 07.

**Blocked by:** None — can start immediately. Ticket 18 also edits `find_duplicate`. Do not do the two tickets at the same time.

**Status:** done

The user chose go on 2026-10-08. Keyword search ranks copies worse than the hybrid of the hook. It finds more copies than the gate finds today, and it makes more Super calls. The Slopgate workflow was off until this ticket (`if: false` in `.github/workflows/slopgate.yml`).

## Context

### Why

`find_duplicate` in `slopgate/review.py` embeds each new module-level function with CodeRankEmbed. `index.build` in `slopgate/index.py` embeds every function of the base ref. The embedding model has these costs:

1. Memory. During the rerun of PR #15 (ticket 21), the torch fallback took 14 GB on the 16 GB Mac. The int8 ONNX model took 397 MB. The workflow now runs `uv run --extra hook`, so the gate uses ONNX. This cost is fixed already.
2. Time. `index.build` embeds every function of the base ref. On the 2,856 functions of pool B (below), the int8 ONNX model took 261 s on the M1 Mac, with a peak memory of 432 MB (measured for this ticket). The token sets of the same 2,856 functions took 0.37 s. One keyword query over them took 13 ms.
3. Install. The action installs torch and sentence-transformers, and downloads the 506 MB model on each new pull request (ticket 24). The first `slopgate index` on a machine compiles the model in 35.6 s (ticket 07).

### Recall of the gate today

The gate keeps a vector candidate only when its cosine is 0.6 or more. On the 16 copies below, the true original ranks first for all 16. But 5 originals score below 0.6: `chunks` (0.374), `strip_fence` (0.468), `tail` (0.538), `module_of` (0.557), and `duration` (0.577). The gate today finds 11 of the 16 copies. Ticket 04 warned about this floor ("The margin of 0.62 is narrow").

### The copy set

The measurement uses 16 true copies. No copy has the same structure hash as its original, so each copy needs the search. The script checks this.

- 3 copies come from the tests: `SLUG_COPY` (`tests/test_hook.py`), `TYPE_ERROR_COPY` and `RESTRUCTURED` (`tests/test_duplicates.py`). Their original is `SLUGIFY`.
- 13 copies were written for this ticket. 12 copy a module-level function of `slopgate/`. 1 is a generator copy of a `chunks` helper, like the hardest copy of ticket 07.
- Tier R: renamed names, small changes. Tier S: restructured code (loops instead of comprehensions, temporary variables, other error handling). Tier A: other calls or another approach (`subprocess.check_output` instead of `subprocess.run`, `while` and `yield` instead of a list comprehension).

The 6 copies of ticket 07 are not in the repo, so this ticket could not run them again. Numbers from ticket 07 are cited as ticket 07 numbers.

Two pools:

- Pool A: the 189 module-level functions of this repo (70 in `slopgate/`, 117 in `tests/`) plus the fixtures `SLUGIFY` and `chunks`. This is the pool that the gate searches today: module-level functions of the base ref, test functions included.
- Pool B: pool A plus 2,667 module-level functions of the Python 3.12 standard library (no `test/`, `idlelib/`, `lib2to3/`, `tkinter/`, `turtledemo/`). Total: 2,856. This pool checks that the result holds in a larger repo.

Cost: each of the 70 functions of `slopgate/` is a query against the pool without itself. None of them has a copy in the pool. The number of top-5 candidates at or above the floor is the number of Super same-job calls for a new function that has no copy.

The script is `kw/measure.py` in the scratchpad of the session that wrote this ticket. It is not in the repo. Design step 6 moves the copy set into the tests.

### Feature groups

A function becomes a set of tokens. These groups were measured, with Jaccard and no stop list, on pool A:

| Feature group | Ranked first | Worst rank | What it adds |
|---|---|---|---|
| Lexical tokens: the regex of `live.tokens` over the raw source | 16/16 | 1 | Everything below, plus Python keywords and single punctuation characters. The punctuation and the keywords carry the shape of the code. A renamed copy keeps its shape. |
| Identifier sub-tokens only (snake_case and camelCase split) | 10/16 | 175 | Little alone. A renamed copy changes most identifiers. |
| AST groups: called names, attribute names, builtin calls, string-literal words, numbers, local imports | 15/16 | 16 | The "what it does" words, with no names of local variables. |
| AST groups without string-literal words | 14/16 | 135 | String-literal words are the strongest AST group. |
| AST groups without numbers, or without local imports | 15/16 | 16 | Nothing on this set. |
| AST groups without attribute names, or without called names | 15/16 | 3 | Each of the two groups adds noise when the other is present. |
| AST groups plus AST node kinds | 15/16 | 9 | Node kinds are in almost every function (`Name`, `Call`, `Load` in 98 to 100%). |
| AST groups plus identifier sub-tokens | 15/16 | 3 | Slightly better than AST groups alone. |
| Lexical tokens of the code after `ast.unparse`, with annotations removed | 15/16 | 3 | Worse. The `->` annotation is in 90% of repo functions and in no copy, but removing it did not help. |

Only the lexical tokens of `live.tokens` ranked all 16 originals first. This is the tokenizer that the hook uses already.

### Stop list

Document frequency over pool A. The top lexical tokens:

- All 189 functions: `:` `(` `)` `def` 100%, `,` 97%, `.` 96%, `=` 91%, `"` 91%, `[` `]` 86%, `{` 69%, `}` 68%, `/` 59%, `repo` 59%, `-` 57%, `return` 56%, `test` 56%, `+` 54%, `in` 54%, `assert` 54%, `llm` 49%, `py` 49%, `capsys` 49%, `make` 47%, `fake` 47%, `is` 46%, `app` 44%, `1` 42%.
- The 72 functions that are not tests: `:` `(` `)` `def` 100%, `,` 94%, `-` 93%, `return` 93%, `.` 92%, `>` 90%, `=` 88%, `"` 79%, `[` `]` 75%, `str` 71%, `if` 68%, `in` 68%, `for` 64%, `{` `}` 54%, `none` 47%, `f` 44%, `path` 42%.

20 lexical tokens are in more than 50% of the functions of pool A. 52 tokens are in more than 25%.

Stop lists were measured with each feature group. The stop lists were: tokens in more than 50%, 25%, or 10% of the pool, plus `self`, `cls`, `args`, `kwargs`, and the Python keywords. Every stop list made the result worse. For lexical Jaccard:

| Stop list | Ranked first | Worst rank | Smallest lead | Lowest original score |
|---|---|---|---|---|
| None | 16/16 | 1 | 0.004 | 0.379 |
| Tokens in more than 50% of pool A, plus the generic words | 16/16 | 1 | 0.008 | 0.133 |
| Tokens in more than 25% | 14/16 | 140 | -0.154 | 0.00 |
| Tokens in more than 10% | 14/16 | 140 | -0.125 | 0.00 |

The cause: a short copy shares the common tokens with its original. Without them, the token set of the copy holds mostly its renamed identifiers. The score of the true original then falls, and the floor must fall with it. With the 50% stop list, the floor for 16/16 falls from 0.37 to 0.13, and the Super calls per new function rise from 1.49 to 4.29.

The proposed stop list is empty.

### Scoring

Measured on pool A, lexical tokens, no stop list:

| Scoring | Ranked first | In top 5 | Worst rank |
|---|---|---|---|
| Jaccard | 16/16 | 16/16 | 1 |
| BM25 (k1 1.2, b 0.75) | 13/16 | 15/16 | 54 |
| TF-IDF cosine (sublinear tf) | 11/16 | 13/16 | 7 |

IDF weighting gives the most weight to rare tokens. In a renamed copy, the rare tokens are the new names, and the original does not contain them. The same result held for every feature group: Jaccard was best in each.

### Result

Lexical Jaccard is the keyword design: the tokens of `live.tokens`, no stop list, Jaccard, top 5, floor 0.30.

Summary. "Found" counts the copies whose original is in the top 5 and at or above the floor. That is the rule of the gate. "Super calls" is the mean number of same-job calls for a new function with no copy.

| Method | Pool | Ranked first | Found | Smallest lead | Floor | Super calls per new function |
|---|---|---|---|---|---|---|
| Cosine, query prefix (gate today) | A | 16/16 | 11/16 | 0.055 | 0.60 | 0.10 |
| Hybrid 0.5 x cosine + 0.5 x Jaccard (hook) | A | 16/16 | 16/16 | 0.129 | 0.39 | 1.13 |
| Lexical Jaccard (this ticket) | A | 16/16 | 16/16 | 0.004 | 0.30 | 3.54 |
| Cosine, floor lowered to 16/16 | A | 16/16 | 16/16 | 0.055 | 0.37 | 3.23 |
| Cosine, query prefix (gate today) | B | 16/16 | 11/16 | 0.020 | 0.60 | 0.10 |
| Hybrid (hook) | B | 16/16 | 16/16 | 0.005 | 0.39 | 1.20 |
| Cosine, floor lowered to 16/16 | B | 16/16 | 16/16 | 0.020 | 0.37 | 3.81 |
| Lexical Jaccard (this ticket) | B | 15/16 | 16/16 | -0.085 | 0.30 | 3.91 |

The hybrid floor and the lowered cosine floor are the lowest score of a true original, rounded down. They are fitted to these 16 copies, so their costs are a lower bound.

Ticket 07 measured 6 other copies in 139 functions. There, the smallest lead was 0.17 for the hybrid, 0.07 for cosine only, and 0.05 for Jaccard only.

Floor sweep for lexical Jaccard:

| Floor | Found, pool A | Super calls, pool A | Found, pool B | Super calls, pool B |
|---|---|---|---|---|
| 0.25 | 16/16 | 4.63 | 16/16 | 4.79 |
| 0.30 | 16/16 | 3.54 | 16/16 | 3.91 |
| 0.35 | 16/16 | 2.03 | 16/16 | 2.44 |
| 0.37 | 16/16 | 1.49 | 16/16 | 1.74 |

The lowest score of a true original is 0.379 (`module_of`). The floor 0.30 keeps a margin of 0.079 below it. The floor 0.30 is also the hook floor.

Per copy, lexical Jaccard, pool A:

| Original | Tier | Rank | Score | Best wrong match | Lead |
|---|---|---|---|---|---|
| `slugify` (`SLUG_COPY`) | S | 1 | 0.760 | 0.278 (`index`) | 0.482 |
| `slugify` (`TYPE_ERROR_COPY`) | S | 1 | 0.720 | 0.286 (`index`) | 0.434 |
| `slugify` (`RESTRUCTURED`) | S | 1 | 0.680 | 0.297 (`load`) | 0.383 |
| `chunks` | A | 1 | 0.423 | 0.359 (`removal_edit`) | 0.064 |
| `duration` | S | 1 | 0.486 | 0.400 (`plural`) | 0.086 |
| `plural` | S | 1 | 0.538 | 0.433 (`duration`) | 0.105 |
| `tail` | S | 1 | 0.533 | 0.429 (`removal_edit`) | 0.105 |
| `module_of` | S | 1 | 0.379 | 0.375 (`slugify`) | 0.004 |
| `strip_fence` | S | 1 | 0.442 | 0.327 (`apply`) | 0.115 |
| `proposed_inputs` | S | 1 | 0.600 | 0.368 (`returns`) | 0.232 |
| `pooled` | S | 1 | 0.552 | 0.333 (`module_of`) | 0.218 |
| `tokens` | R | 1 | 0.766 | 0.354 (`suggested_code`) | 0.412 |
| `apply` | R | 1 | 0.659 | 0.362 (`strip_fence`) | 0.297 |
| `shell` | A | 1 | 0.617 | 0.432 (`git`) | 0.185 |
| `git` | A | 1 | 0.690 | 0.600 (`archive`) | 0.090 |
| `complexity` | R | 1 | 0.609 | 0.308 (`models`) | 0.301 |

On pool B, two rows change. `module_of` ranks 4th: `strip_quotes` and two other standard-library functions score above 0.379. `chunks` stays first, but its lead falls to 0.023 (`_strip_padding`, 0.400). On pool B, the hybrid also has a small lead on `module_of`: 0.005.

### What the measurements say

- Keyword search ranks copies worse than the hybrid. Its smallest lead is 0.004 on pool A, against 0.129 for the hybrid. On pool B, it ranks one original 4th, below three wrong matches.
- Keyword search finds more copies than the gate finds today: 16 of 16 against 11 of 16. The cause is the floor of the gate (0.6), not the vectors.
- At the same recall (16 of 16), keyword search and cosine make about the same number of Super calls: 3.5 to 3.9 for keyword search at 0.30, and 3.2 to 3.8 for cosine at 0.37. Only the hybrid is cheaper: 1.1 to 1.2. The gate today makes 0.10 calls, because its floor drops 5 of the 16 copies.
- So the choice is between keyword search (no model, 3.5 to 3.9 calls) and the hybrid in the gate (the ONNX model, 261 s of index time on 2,856 functions, 1.1 to 1.2 calls).
- Each same-job prompt holds two functions. For `slopgate/`, that is about 1,900 characters, or about 500 tokens (estimated at 4 characters per token). The money cost is small. The time is about 1 s per call (the decide calls of ticket 18 took 0.8 to 1.2 s). `find_duplicate` stops at the first "same job" answer.
- More candidates give Super more chances to say "same job" by mistake. The differential test in the sandbox still proves each duplicate rewrite, so a wrong "same job" costs sandbox time, not a wrong suggestion.

## Design

1. Move `tokens` from `slopgate/live.py` to `slopgate/functions.py`. `live.py` imports it from there. Do not change the function.
2. `index.build` stores no vector and does not import `slopgate.embed`. A record keeps `path`, `qualname`, `start`, `end`, `source`, and `hash`. An old index file that has a `vector` key still loads. The gate ignores the key.
3. `live.seed` computes the vectors that the hook store needs with `embed.encode` on the record sources. `slopgate index` keeps its output and its behavior for the hook.
4. `index.search(index, source, floor, top)` scores each record by the Jaccard of `tokens(source)` and the tokens of the record source. It returns the top `top` records at or above `floor`, best first. Tokenize each pool function once per review, not once per query.
5. `find_duplicate` keeps the hash match first. Then it calls `index.search(pool, function.source, DUPLICATE_SCORE, 5)`, and then the Super same-job check, as today. Set `DUPLICATE_SCORE = 0.30` in `slopgate/config.py`.
6. Add the 16 copies of the table to the tests as an offline parametrized test. Each case holds the original and the copy as strings. The pool is every module-level function of `slopgate/` and `tests/` at test time, with the fixture original in place of the repo function of the same name. A second case uses pool B (the same pool plus the module-level functions of the standard library).
7. Move `sentence-transformers`, `transformers`, and `einops` from `dependencies` to the `hook` extra in `pyproject.toml`. In `action.yml`, remove the PyTorch index URL and the cache step for `~/.cache/huggingface`. In `.github/workflows/slopgate.yml`, run `uv run slopgate review` without `--extra hook`, and remove the comment about the torch fallback.
8. Change the tests that count `embed` calls in the gate path (`test_index_is_written_once_and_loaded_after`, `test_unrelated_helper_below_floor_costs_no_llm_call`, `test_real_encode_prefixes_queries_only`). Replace the live test `test_restructured_copy_is_found_by_real_vector_search` with an offline test.
9. In `spec.md`, change the duplicate search line: "Otherwise, keyword search (token Jaccard) over an index built at the base ref, with a score floor of 0.30 and the top 5 results." Change the threshold "duplicate score 0.6" to 0.30. Update the code map in `CLAUDE.md` and the install steps in `README.md`.
10. Set ticket 24 to `wontfix`. The gate downloads no model after this ticket.

## Acceptance

- [x] `python -c "import slopgate.review, slopgate.index, sys; assert 'slopgate.embed' not in sys.modules"` passes.
- [x] A review with a duplicate candidate makes no `embed` call. A test makes `embed.encode` raise, and the gate still finds the duplicate.
- [x] Recall gate, pool A: for each of the 16 copies, `index.search` returns the original in the top 5 at or above `DUPLICATE_SCORE`.
- [x] Recall gate, pool B: the same, for all 16 copies.
- [x] The Comments record how many of the 16 originals rank first on pool A and on pool B. This ticket measured 16/16 and 15/16. Rank 1 is not a gate, because the gate sends all top-5 candidates above the floor to Super.
- [x] The Comments record the Super calls per new function with no copy, on pool A at floor 0.30. This ticket measured 3.54. More than 5 is not possible (top 5).
- [x] A renamed exact copy still gives zero LLM calls (the existing test stays).
- [x] `uv sync` with no extra installs no `torch`. With `--extra hook`, the hook tests pass.
- [x] `spec.md`, `CLAUDE.md`, `README.md`, and ticket 24 match the Design.
- [x] `uv run pytest -q` passes.
- [x] The Slopgate workflow runs again: `.github/workflows/slopgate.yml` gets back `if: ${{ !startsWith(github.head_ref, 'slopgate/') }}`, and a new pull request shows the `slopgate` check.
- [x] Live run: `slopgate review --base 74fcd0d --head 22635c3 --dry-run` on this repo. Record the time, the peak memory (`/usr/bin/time -l`), and the duplicate result. Ticket 21 measured 320 s and 397 MB with ONNX.

## Comments

### 2026-10-08 — Done

**What was built.** The gate finds duplicate candidates with keyword search. `index.search` scores each base-index record by the Jaccard of the token sets of `tokens`. It returns the top 5 records at or above `DUPLICATE_SCORE` (0.30). The exact structure-hash match stays first. The Super same-job check stays the final decision. The base index stores no vectors, and `slopgate.review` and `slopgate.index` do not import `slopgate.embed`. `tokens` moved to `slopgate/functions.py`. `live.seed` now computes the vectors of the hook store with `embed.encode`. `sentence-transformers`, `transformers`, and `einops` moved to the `hook` extra. A new dependency group `dev = ["numpy"]` keeps the hook tests runnable with a plain `uv run pytest -q`, because `live.matches` needs numpy. The Slopgate workflow runs again, without `--extra hook`.

**Worked example.** The copy `make_slug` (`TYPE_ERROR_COPY`) in `app/posts.py` raises `TypeError` where `slugify` raises `ValueError`. The structure hashes differ, so the gate runs keyword search. `slugify` is the first result. Super says "same job", and the gate gives a follow-up that names `slugify` in `app/text.py`. The test `test_copy_is_found_when_the_embedding_model_fails` makes `embed.encode` raise, and the gate gives the same follow-up.

**The copy set.** The 13 copies of this ticket were not in the repo. New copies were written, one for each row of the "Per copy" table, with the same tier. They are in `tests/test_recall.py`. Each case asserts that the copy has a different structure hash than its original. The 12 repo originals are read from the repo at test time.

**Measured results.**

- Pools: pool A has 198 functions (71 in `slopgate/`, 125 in `tests/`, 2 fixtures). Pool B has 3,060 (2,862 from the Python 3.12.10 standard library). The ticket counted 2,667 standard-library functions. The filter of the ticket script is not known.
- Recall gate: 16 of 16 originals are in the top 5 at or above 0.30 on pool A, and 16 of 16 on pool B.
- Rank 1: 16 of 16 on pool A, and 15 of 16 on pool B. On pool B, `chunks` ranks 3rd (0.385, below `_strip_padding` at 0.414 and one other function).
- Smallest lead on pool A: 0.016 (`chunks`), then 0.029 (`module_of`). Lowest original score: 0.385 (`chunks`).
- Super calls per new function with no copy, pool A, floor 0.30: 3.58 (mean over the 71 functions of `slopgate/`). The ticket measured 3.54 over 70. The new function `jaccard` is the 71st.
- Time: one query on pool B takes 11 ms. The pool B build takes 1.15 s (0.85 s parse, 0.30 s tokens). The 32 recall cases run in 1.99 s.
- Live run `slopgate review --base 74fcd0d --head 22635c3 --dry-run` on this repo, Contree sandbox: 311 s, peak memory 88 MB (`maximum resident set size` 88,211,456). Ticket 21 measured 320 s and 397 MB with ONNX. The result had 0 suggestions, 0 follow-ups, and 10 rejected entries. No entry was a duplicate.
- Duplicate result of the live run: the range adds 12 new module-level functions (1 in `slopgate/`, 11 in `tests/`). Keyword search sent 35 candidates to Super. Super said "same job" for none. 5 test functions fill the top 5 with other tests at 0.33 to 0.61.
- `uv run pytest -q`: 174 passed, 10 deselected, in 240 s. `uv run --extra hook pytest -q`: 174 passed.
- `uv sync` with no extra installs no `torch` and no `sentence-transformers`.

**Rebase on ticket 18.** Ticket 18 merged first. `find_duplicate` now asks Super through `llm.decide` with `SameJob`, after the keyword search. After the rebase and the review fixes, `uv run pytest -q` gave 182 passed, 12 deselected. The live run gave 341 s, peak memory 83 MB, 0 suggestions, 0 follow-ups, and no duplicate.

**Code review.** A thermo-nuclear review gave 11 findings. These were applied: a test that the gate imports no hook-only module, a test of the `seed` alignment of records and vectors, a test that `index.build` loads the file, a unit test of `index.search` for `top` and `floor`, one `jaccard` in `slopgate/functions.py` for the gate and the hook, and `numpy` in the `hook` extra. The ticket status changed to `needs-live-check`. These were rejected:

- Freeze the recall pools. Design step 6 builds the pool at test time. A new function that pushes an original out of the top 5 is a real loss of recall, so the test must fail.
- Give the fake `decide` its own reply queue. The fake comes from ticket 18. A reply of the wrong type fails at once.
- Put `@cache` on `tokens`. Design step 1 says: do not change the function.
- Run `find_duplicate` in parallel. Tickets 23 and 25 own the gate time.

**Fixes from the gate review of PR #17.**

1. Sandbox setup. `pip install -e .` does not install the uv `dev` group, so `tests/test_hook.py` could not import numpy, and the repo tests failed in the sandbox. `.slopgate.toml` now installs `numpy` too. The PyTorch index is gone. The next gate run passed one rewrite in the sandbox.
2. Moved helper (a defect from before this ticket). The duplicate pool kept base helpers that the pull request moved or deleted. The moved `tokens` matched its old copy in `live.py`, and the follow-up imported it from a module that no longer defines it. The pool now keeps a base record only when its path and name exist at head. Two tests (a move and a delete) failed before the fix and pass after it.
3. Empty inputs (a defect from before this ticket). For a function that takes objects, Super often replied `{"inputs": []}`. The gate recorded zero calls and rejected the candidate with "no tests ran". Live Super, 8 tries per function: `find_duplicate` gave an empty list 6 times, `characterize` 8 times, `seed` 1 time. A prompt rule against an empty list did not help (8 of 8 still empty). One retry with a request for a pytest file gave a test file in 19 of 19 cases. The gate now does that retry and runs no sandbox for an empty list.

After these fixes, `uv run pytest -q` gave 186 passed, 12 deselected.

4. Runner sleep. The gate run on commit 8ca2676 was cancelled after 10 min. The Mac went to idle sleep 39 s into the job, and the runner stopped renewing the job. The gate step now runs under `caffeinate -i`.

**Workflow check.** The `slopgate` check ran on PR #17 and passed on commit d0c6675 (4 min 35 s, 10 rejected, 0 accepted). The moved `tokens` rejection is gone. `find_duplicate` got a pytest file after the empty-inputs retry, but that file failed on the original code. `matches` gave an empty list twice and was rejected with no sandbox run. The other rejections come from generated tests that mock badly, from test files (ticket 17), and from one cut-off reply.

**Other test changes.** At the floor 0.30, the new callers in the wrapper fixtures (`invoice_total`, `fee_total`, `total`) score 0.35 to 0.53 against `compute_tax`. Each costs one Super same-job call. 17 tests in `tests/test_wrappers.py` and `tests/test_github.py` now queue one "not the same job" reply for each call.

**Known limits.**

- Test functions are similar to each other. On the live run, they caused 30 of the 35 Super calls. Ticket 17 (test files get review notes only) can remove test functions from the duplicate search.
- `chunks` on pool B ranks 3rd, with a lead of -0.029. Keyword search ranks copies worse than the hybrid score of the hook.
- `slopgate index` now embeds the pooled functions on each run, also when the index file of the ref exists already. Before, the vectors were in the index file. A new ref embedded all functions before too.
- The live test `test_real_super_proves_a_wrapper_whose_caller_depends_on_the_helper` was not run. Its caller can now get a real Super same-job call.
