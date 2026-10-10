# 36 — Design: how the gate picks a slop kind, and what input the model gets

## Summary

- **Goal:** Find out why the gate names wrong slop kinds, and design the correct input and checks. Example: on PR #20, the gate named `test_followup_pull_request_failure_still_posts_the_review` as "dead" code, although vulture found no dead code in it.
- **Checkable finish condition:** The `## Design` section answers the 7 design questions, and the user approved it. After the build, the 12 PR #20 functions get no note with the real `classify` (live test), and `uv run pytest -q` passes.
- **Evidence:** Before: the gate posted 12 notes on each of 2 runs of PR #20, and 4 of 12 functions changed kind between the runs. After (2026-10-09): a dry run on the PR #20 range gave 0 notes on those functions. 2 live tests passed. `uv run pytest -q` gave 238 passed.
- **Constraints:** Measure before you choose a design. Use Ruff, vulture, and `nesting()` for the kinds that code can measure, with no model. Use Lightning only for `redundant_check` and `filler_comment`. The model gives its reason before its verdict. Remove the complexity trigger. Reject a rewrite that leaves the slop.

**Blocked by:** None — can start immediately.

**Status:** done

**Type:** brainstorm and design. The user thinks that the input that the gate gives the model is wrong.

## Context

On PR #20 (2026-10-08), the gate ran twice on the same code, once for each push. Each run posted 12 notes on test functions (ticket 17), so the pull request has 24 inline notes. 4 of the 12 functions got a different kind in the two runs. The notes were also wrong.

### Measurement (2026-10-08)

For each of the 12 functions, the gate's own checks were run, and `classify` (Lightning, the real prompt, `temperature=0`, thinking off) was asked 8 times:

| Function | Lines | Complexity | Nesting | Vulture dead code | Lightning, 8 tries |
|---|---|---|---|---|---|
| `test_copy_with_other_error_on_none` | 20 | 8 | 1 | no | dead 8 |
| `test_inline_suggestions_are_posted_as_one_comment_review` | 19 | 9 | 0 | no | nesting 8 |
| `test_pr_flag_fetches_the_pull_request_reviews_it_and_posts_to_it` | 27 | 7 | 0 | no | nesting 8 |
| `test_followup_changes_open_one_pull_request_on_the_author_branch` | 19 | 10 | 0 | no | dead 8 |
| `test_followup_pull_request_failure_still_posts_the_review` | 17 | 6 | 0 | no | dead 8 |
| `test_super_tests_reply_is_proven_or_cannot_test` | 29 | 9 | 1 | no | dead 8 |
| `test_rewrite_that_changes_behavior_is_rejected` | 12 | 6 | 0 | no | nesting 8 |
| `test_each_in_place_kind_gets_a_suggestion_naming_it` | 12 | 10 | 1 | no | lookup_table 8 |
| `test_tests_that_fail_on_original_get_one_retry_with_the_failure` | 13 | 6 | 0 | no | nesting 8 |
| `test_calls_that_do_not_evaluate_get_one_retry_with_the_error` | 14 | 7 | 0 | no | nesting 8 |
| `test_empty_block_gets_one_retry_that_names_the_error` | 12 | 6 | 0 | no | nesting 6, dead 2 |
| `test_method_prompt_has_no_calls_form_and_bare_calls_run_as_a_test_file` | 16 | 9 | 0 | no | nesting 8 |

The nesting limit is more than 2 (`NESTING`). The complexity limit is 6 or more (`COMPLEXITY`). The table shows these facts:

1. **The trigger counts `assert` as complexity.** All 12 functions reached `classify` through complexity only: none passes the nesting limit, and vulture finds no dead code. Radon adds 1 for each `assert`. A flat function with 5 asserts has complexity 6, and the same function with no asserts has complexity 1 (measured). So each test with 5 or more asserts is "complex", although it has no branches.
2. **The model's kind goes against the gate's own measurements.** Lightning said "nesting" 7 times for functions with nesting 0. It said "dead" 5 times for functions where vulture finds no dead code. The gate posts the kind with no check.
3. **The kind is stable in one run, but not across runs.** At `temperature=0`, 11 of 12 functions got the same kind 8 of 8 times. But 4 functions changed kind between the two CI runs.

## What the model gets now

`classify` in `slopgate/review.py` sends `CLASSIFY_PROMPT`:

- the six `KINDS` texts, then `- none: no kind above fits`;
- the instruction "Name the slop kind that fits the Python function below best";
- a request for bare JSON `{"kind": "<kind>"}` (`response_format: json_object`);
- the function source, with no fence.

## Ideas to examine (the user's hypothesis: the input is wrong)

These are hypotheses, not decisions. Test each one with a measurement.

1. **The kind texts are fix instructions, not detection rules.** `KINDS` also feeds the rewrite prompt. "It nests blocks deeply. Flatten it with guard clauses…" tells the model how to fix, not how to decide that the slop is there. The model may then match on the look of the code.
2. **The prompt asks for the best fit.** "Name the slop kind that fits … best" pushes the model to name a kind. `none` is last and has no definition of when to use it.
3. **The model does not see what the gate measured.** The gate knows that the nesting depth is 0 and that vulture finds nothing. The model does not get these facts, so it guesses them.
4. **The model does not know why the function was sent.** It does not know that the trigger was complexity 6, or that most of that complexity comes from asserts.
5. **The model does not know the file is a test.** A test with many asserts is normal test code, not slop.
6. **There is no reason field.** CLAUDE.md says decisions go through `decide`, a forced tool call with the reason before the verdict (ticket 18). `classify` still uses bare JSON, so the model gives a verdict with no reasoning.
7. **The trigger is wrong for tests**, and maybe for code too. Asserts and `and` chains count as complexity.
8. **The gate trusts the model over its own checks.** For the kinds that the gate can measure (nesting, dead code, an if/elif chain), the model's kind is not checked.

## Possible problem outside test files (inferred, not seen yet)

The same path runs for normal code. A flat function with complexity 6 can go to Lightning, get "nesting", and Super then gets the instruction "flatten it". If the rewrite keeps the behavior, the gate posts it as a proven "nesting" fix. The proof checks that the behavior is the same. It does not check that the slop was there. Check this on the demo repo and on old pull requests.

## Design questions

1. Which kinds can the gate measure without a model, and which need a model?
2. For each kind that needs a model, what input does the model need: a detection rule, the measured facts, the file type, the trigger?
3. Should the model reply with a reason first (`decide`), and with which fields?
4. What is the correct trigger? Should asserts count?
5. When the model's kind goes against a measurement, which one wins?
6. How do notes on test files fit: keep them, keep only the measured kinds, or remove them?
7. How do the notes stop repeating on each push?

## How to measure

- **Negatives:** the 12 functions above. The correct answer for each is "no note", unless a person finds real slop in it.
- **Positives:** functions with known slop of each kind, for example the `KIND_CASES` in `tests/test_review.py` and the demo repo.
- Compare each design against the current prompt with 8 tries for each function. Count false kinds on the negatives and missed kinds on the positives. A design that removes the false kinds but misses real slop is not better.

## Design

### Measurement (2026-10-09)

**Dataset: 60 functions.**

- 12 negatives: the PR #20 functions above, from the PR head `70c27da`.
- 9 positives: the 5 slop functions of `KINDS_SOURCE` in `tests/test_review.py` and the 4 functions of demo PR #1 (commit `441d235`, before the applied suggestions).
- 12 hand-written functions: 7 have simple slop that the current trigger misses (for example a bare `except Exception: return None` with complexity 2), or two kinds at once. 5 are clean code that looks like slop (a narrow `except`, a why-comment, guard clauses, a range chain, nesting 2).
- 27 real functions: every function in `slopgate/*.py` on `main` that passes the current trigger (complexity 6 or more, or nesting more than 2). Nobody labelled these. The gate's own detectors decide the measurable kinds. A person read the model-only kinds.

Each design ran 8 times on each function, at `temperature=0`, with thinking off. That gives 264 labelled tries with 136 expected kinds, 152 tries on functions with no slop, and 216 tries on real code.

| Design | Model | False kinds | Missed kinds (of 136) | Tries with no slop that got a kind (of 152) | Real code: wrong measurable kinds | Real code: model-only kinds | Time per function |
|---|---|---|---|---|---|---|---|
| A: the current prompt (one kind, bare JSON) | Lightning | 168 | 61 | 132 | 190 | 13 | 0.7 s |
| B: ticket 19 (`decide`, one list of kinds, fix texts) | Lightning | 868 | 16 | 150 | 320 | 622 | 1.1 s |
| C0: detection rules, one evidence line for each finding, all kinds in one call | Lightning | 28 | 81 | 0 | 0 | 3 | 0.9 s |
| C: C0 plus the measured facts (nesting, complexity, asserts, test file) | Lightning | 14 | 86 | 0 | 3 | 5 | 0.9 s |
| D: code measures nesting, if/elif chains, dead code; one call for the other kinds | Lightning | 34 | 33 | 6 | 0 | 27 | 1.4 s |
| D | Super | 15 | 13 | 11 | 0 | 33 | 1.0 s |
| E: as D, but one call for each kind, with a `reason` field before the evidence lines | Lightning | 3 | 4 | 0 | 0 | 51 | 2.2 s |
| **E2: E, and code also measures `swallowed_error`** | **Lightning** | **3** | **12** | **0** | **0** | **21** | **2.2 s** |
| E2 | Super | 4 | 12 | 4 | 0 | 9 (8 errors) | 2.2 s |
| F: E2, and `redundant_check` must quote two lines (the earlier check and the repeated check) | Lightning | 8 | 15 | 5 | 0 | 18 | 2.3 s |
| F | Super | 14 | 11 | 10 | 0 | 0 | 1.3 s |
| G: F plus two examples in each prompt (one simple, one complex) | Lightning | 15 | 12 | 0 | 0 | 30 (10 errors) | 3.8 s |
| G | Super | 14 | 8 | 8 | 0 | 0 | 1.3 s |

The time is for calls in series. E2 sends at most 2 calls for each function, and they can run in parallel.

Design A gave the same kind as the PR #20 table on all 12 negatives, so the dataset reproduces the problem.

**What the numbers show:**

1. **A list of kinds alone makes the result worse (B).** Lightning names all 5 kinds for almost every function. A tool call fixes the shape of the reply, not its content.
2. **Detection rules and a quoted evidence line remove the false kinds (C0).** Each rule says when a kind is present, not how to fix it. The gate drops a finding when its evidence line is not a line of the function. But Lightning then misses 81 of 136 kinds.
3. **The measured facts do not help (C).** Missed kinds went from 81 to 86.
4. **Code is better than a model for the measurable kinds.** Lightning said `dead` for 24 of the 27 real functions. Vulture finds no dead code in any of them. Lightning said `nesting` for functions with nesting 0, and `lookup_table` for a range chain (`weight < 1`, `weight < 5`). Code never makes these mistakes.
5. **One call for each kind is better than one call for all kinds (E against D).** In one call, Lightning reports every `if` line as `redundant_check` and drops the other kinds.
6. **Lightning cannot judge `except` clauses (E).** It called `except SyntaxError` a broad catch in 3 real functions. The code check in E2 removes this mistake. It also misses the "try block around code that cannot raise" case (8 of the 12 missed kinds in E2).
7. **The two-line evidence (F) and the examples (G) did not make Lightning better.** On Super, the examples reduced the missed kinds from 11 to 8. But Super then reported a plain range chain as `redundant_check` 8 of 8 times. Its reason was wrong ("each later elif is always true").
8. **The trigger misses simple slop.** 7 of the 12 hand-written slop functions never reach `classify` today, because their complexity is below 6.

**Outside test files.** The wrong kind also reaches normal code. On PR #17 (2026-10-07), the gate posted a "proven" `dead` rewrite of `test_search_returns_best_top_above_floor`. Vulture finds no dead code in it, so the kind came from Lightning. The rewrite changed the test data from `"a b c d e f g h i j {extra}"` to `"a b c d e f f g h i j {extra}"`, and the proof passed. That was before ticket 17, so the function went through the rewrite path that normal code uses. With design A, Lightning names `dead` for 24 of the 27 real functions in `slopgate/`.

**Battle-tested tools on the same dataset.** Ruff 0.14 (MIT) and mypy 1.18 (MIT) ran on the 60 functions, with no model call.

- Ruff, with the rules SIM116 (`lookup_table`), BLE001, E722, S110, S112 (`swallowed_error`), F841, RUF059 (`dead`), and PLR1702 with `max-nested-blocks = 2` (`nesting`), agrees with the hand-written AST checks of design E2 on 55 of 60 functions. One run on the whole repo takes 0.11 s.
- The 5 differences:
  - Ruff RUF059 finds `output` unused in `code, output = sandbox.run(...)` in `review.characterize`. Vulture and the AST check miss it. Ruff is better here.
  - Ruff BLE001 flags `except Exception as error:` in `cli.main` and `review.review`. Both handlers print or record the error on purpose. A rewrite that narrows them can change behavior that the proof does not test.
  - Ruff SIM102 flags a collapsible `if` in `discount`. It is not a Slopgate kind.
  - Neither finds a try block around code that cannot raise (`add_try_cannot_raise`).
- mypy (`--check-untyped-defs`, `redundant-expr`, `truthy-bool`, `--warn-unreachable`, `--strict-equality`) finds 0 of 3 redundant checks: the parameters have no types, so mypy cannot narrow them. On a typed copy, it finds the repeated `is not None` in `total`, but not `if price > 0` after `if price <= 0`: mypy does not track value ranges. So mypy is not used.
- No battle-tested tool checks `redundant_check` on untyped code or `filler_comment`. A model checks these two kinds.

**Sources for the design.** Other tools check most of these kinds with code: Ruff [SIM116](https://docs.astral.sh/ruff/rules/if-else-block-instead-of-dict-lookup/) (an if chain that should be a dict lookup), Ruff [S110](https://docs.astral.sh/ruff/rules/try-except-pass) (try-except-pass), and mypy [`redundant-expr`](https://mypy.readthedocs.io/en/stable/error_code_list2.html) (a condition that is always true). [slopguards](https://pypi.org/project/slopguards/) checks swallowed exceptions and comments that restate the code. The study [Reducing False Positives in Static Bug Detection with LLMs](https://arxiv.org/abs/2601.18844v1) reports that a static check plus a model removes most false positives. A word-overlap check for filler comments was also measured: it separates the comments of this dataset, but its stop-word list was tuned on 3 functions, so it is not used.

### Answers to the design questions

1. **Which kinds can the gate measure?** Battle-tested tools measure 4 kinds:
   - `nesting`: the existing `nesting()` in `slopgate/functions.py`, depth more than `NESTING`. It agrees with Ruff PLR1702 on 60 of 60 functions. PLR1702 is a Ruff preview rule, so its behavior can change.
   - `lookup_table`: Ruff SIM116.
   - `swallowed_error`: Ruff BLE001, E722, S110, S112. The user chose option A on 2026-10-09: the gate keeps a BLE001 or E722 hit only when the handler body does not use the caught error.
   - `dead`: Ruff F841 and RUF059, plus vulture (Ruff's check for unreachable code is a preview rule).

   `redundant_check` and `filler_comment` need a model.
2. **What does the model get?** One call for each model kind. The call has the detection rule of that kind (not the fix text), the file path, and the source in a fence. The model is asked about a kind only when code finds the syntax for it: 2 or more conditions for `redundant_check`, and a `#` comment for `filler_comment`. Measured facts and examples are not sent: they did not help (points 3 and 7).
3. **Reason first?** Yes. The tool is `Check`, with `reason` (what the model checked and why each line matches or not), then `lines` (each line that matches the rule, copied exactly). The gate keeps a finding only when each evidence line is a line of the function and has the right syntax (`#` for `filler_comment`; `if`, `elif`, `while`, `and`, `or`, or `assert` for `redundant_check`).
4. **The trigger.** Remove the complexity trigger. Each kind has its own check: the code detector, or the syntax check before the model call. Asserts then have no effect.
5. **Model against measurement.** The measurement wins, because the model is never asked about a measured kind. After the rewrite, the gate also checks that the slop is gone. For a measured kind, its detector must not find it in the rewrite. For a model kind, the rewrite must not have the evidence lines. A rewrite that leaves the slop is rejected. With this check, a false kind costs one rejected rewrite, not a wrong suggestion as on PR #17.
6. **Test files.** Keep notes on test files, with the same detection. Design E2 gave no note on the 12 PR #20 functions (0 of 96 tries).
7. **Repeated notes.** Before `publish` posts, it reads the review comments on the pull request. It skips each new comment whose path and first line match an existing comment.

### Stage 2: the build

The user asked to build the change in this ticket. Ticket 19 (several kinds per function) is part of this build, because the new `classify` returns a list.

1. A registry in `slopgate/review.py` gives each kind its fix text, plus a detector (code) or a detection rule and a syntax check (model). Ruff is a gate dependency, pinned to one version. The gate runs it as `python -m ruff check --isolated` on the file text from stdin, with only the rules of question 1.
2. `classify(function)` returns the kinds with their evidence lines. It sends one `llm.decide(LIGHTNING, prompt, Check)` call for each model kind whose syntax check passes. The calls run in parallel, and each worker is wrapped with `trace.bind`.
3. The loop in `review` collects all kinds of a function (the measured kinds plus the model kinds). The complexity trigger goes away.
4. One rewrite for all kinds, with a numbered list of fix texts and the evidence lines (ticket 19, step 4). After the proof, the check of question 5 runs.
5. The suggestion body, the notes, and the `rejected` and follow-up entries name every kind.
6. `publish` skips comments that already exist on the pull request.
7. Remove the `json` parameter of `complete` and `CLASSIFY_PROMPT`.

## Acceptance

- [x] A `## Design` section answers the 7 design questions, with the measurements that support each answer.
- [x] The measurement covers the negatives and the positives above, for the current prompt and for each design that was tried.
- [x] The check outside test files is done: either the Comments show a posted or dry-run suggestion with a wrong kind, or they say that none was found and where the check looked.
- [x] The user approved the design.
- [x] A follow-up ticket for the build exists, or stage 2 is added to this ticket.

### Stage 2 acceptance

- [x] The 12 PR #20 functions get no note, with the real `classify` and Lightning (live test).
- [x] A function with deep nesting and filler comments gets both kinds and one rewrite request, whose prompt has both fix texts as a numbered list.
- [x] A Ruff BLE001 hit whose handler uses the caught error gives no `swallowed_error`.
- [x] A rewrite that keeps an evidence line, or that a detector still flags, is rejected with a reason that names the kind.
- [x] A function with no kind makes no model call.
- [x] `publish` does not post a comment whose path and first line already exist on the pull request.
- [x] `uv run pytest -q` passes.

## Comments

### 2026-10-09 — done

**What was built.** The gate now finds slop kinds in two ways. Battle-tested tools measure 4 kinds with no model: Ruff 0.14 (`lookup_table`, `swallowed_error`, `dead`), vulture (`dead`), and the existing `nesting()` (`nesting`). Lightning checks the other 2 kinds (`redundant_check`, `filler_comment`) with one forced tool call (`Check`) for each kind. Each reply gives a `reason` first, then the evidence lines. The gate keeps an evidence line only when it is a line of the function and has the syntax of its kind (a COMMENT token, or a condition keyword). The complexity trigger is removed, so asserts have no effect. A function can have several kinds (ticket 19), and it gets one rewrite with a numbered list of fixes. Before the sandbox runs, the gate rejects a rewrite that still has a slop kind ("rewrite leaves the slop: <kind>"). `publish` skips a comment whose path and first line already exist on the pull request. The detection code is in the new file `slopgate/kinds.py`.

**Worked example (dry run on demo PR #1, `441d235`).** The input is `can_checkout` (nesting 4) and `shipping_label` (an if/elif chain of 6 branches). The gate gave:

- `Slopgate (`nesting`) rewrite of `can_checkout`.` The rewrite has 4 guard clauses, nesting 4 -> 1. 16 characterization tests passed in the sandbox.
- `Slopgate (`lookup_table`) rewrite of `shipping_label`.` Ruff SIM116 found the chain. The rewrite is a dict with `.get(zone, "International")`. 10 characterization tests passed.
- The duplicate `format_total` and the wrapper `discounted` got follow-ups, as before. 0 rejected.

**Measured results.**

- The design measurement is in `## Design` above: 13 designs, 60 functions, 8 tries each.
- Dry run on the PR #20 range (`19d7331..70c27da`): 0 notes. The gate posted 12 notes on each of the 2 runs of PR #20. Two non-test functions got kinds: `parse_tests_reply` (`nesting`, `redundant_check`) and `characterize` (`nesting`, `redundant_check`, `dead`: the unused `output` that Ruff RUF059 finds). Both were rejected, because the characterization tests failed on the original code (tickets 30 and 35).
- Live tests `test_classify_finds_no_kind_in_the_pr_20_test_functions` and `test_classify_finds_filler_comments_in_clamp_all`: 2 passed, in 6.4 s.
- Ruff with the selected rules checks the whole repo in 0.11 s.
- `uv run pytest -q`: 238 passed, 17 deselected, in 5 min 30 s.

**Known limits.**

- A try block around code that cannot raise is not found. Ruff does not check it, and the model check was removed because Lightning called `except SyntaxError` a broad catch in 3 real functions.
- Lightning can still name `redundant_check` for nested `if` blocks. The first dry run of demo PR #1 gave `can_checkout` the kinds `nesting` and `redundant_check`. The second run gave `nesting` only. The rewrite was correct both times.
- 12 of the 60 functions in the dataset were written for this ticket, so the numbers can favor these examples.
- Code with type hints could also use mypy `redundant-expr` for repeated `None` checks. This is not done.
- `publish` reads the existing comments with one more `gh api` call for each review.
