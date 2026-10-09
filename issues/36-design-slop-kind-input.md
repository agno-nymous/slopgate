# 36 — Design: how the gate picks a slop kind, and what input the model gets

**What to build:** A design, not code. Find out why the gate names wrong slop kinds, and design the correct input to the model and the correct checks around it. The user approves the design. Then a later ticket (or stage 2 of this ticket) builds it.

**Blocked by:** None — can start immediately.

**Status:** ready-for-agent

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

## Acceptance

- [ ] A `## Design` section answers the 7 design questions, with the measurements that support each answer.
- [ ] The measurement covers the negatives and the positives above, for the current prompt and for each design that was tried.
- [ ] The check outside test files is done: either the Comments show a posted or dry-run suggestion with a wrong kind, or they say that none was found and where the check looked.
- [ ] The user approved the design.
- [ ] A follow-up ticket for the build exists, or stage 2 is added to this ticket.

## Comments
