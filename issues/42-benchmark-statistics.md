# 42 — Benchmark statistics: label agreement, run metadata, and pass@k

## Summary

- **Goal:** Make the benchmark numbers trustworthy enough for the submission. Example: `bench/labels.json` was drafted by Claude and accepted without a review of each row. Today nobody knows how often a second labeller would agree with it.
- **Checkable finish condition:** `bench/results/detection.md` shows the label agreement (Cohen's kappa) for each kind, a metadata block (models, prompt hashes, commit, seed, date), and "found in at least 1 of 3 runs" and "found in all 3 runs" for each kind. `uv run pytest -q` passes.
- **Evidence:** Before: `detection.md` gives one precision and one recall for each kind, with no label check and no record of the setup. After: the same report with the 3 additions above, and a test for each new function in `bench/score.py`.
- **Constraints:** The second labeller does not see the first labels. Do not change a label in `bench/labels.json` without a written reason. Ticket 10 uses the same metadata and pass@k functions, so put them in `bench/score.py`.

**Blocked by:** 37

**Status:** done

**Type:** build.

## Context

On 2026-10-09 the user shared the evals guide at https://aiengineeringfromscratch.com/guides/evals. The guide lists 6 checks for an eval. The ticket 37 benchmark does none of them.

Ticket 39 does the first 3, because its design choices need them:

1. a held-out set: choose the checks on one part of the functions, and score only on the other part;
2. a range for each number (bootstrap over functions);
3. model errors counted apart from "no kind found".

This ticket does the other 3. They do not change a design choice, but the submission (ticket 11) needs them, so do this ticket before ticket 10.

## Design

### 1. Label agreement

`bench/labels.json` has 139 decisions on real code (slop or false positive) and 56 validity decisions on Super injections. Claude drafted them. The user accepted them without a review of each row.

- A second labeller labels every row again, without the first label. Use Nemotron Ultra: it is a different model family from the first labeller. Give it the function source, the kind, the kind rule from `kinds.RULES`, and the evidence lines. Get the decision as a forced tool call (`decide`) with the reason before the decision.
- Report Cohen's kappa for each kind and in total. Kappa is the agreement corrected for the agreement that chance gives. A kappa below 0.6 means that the labels of that kind are not reliable.
- List each row where the two labellers disagree in `bench/results/label-disagreements.md`, with both reasons. The user can decide these rows. The benchmark scores with `bench/labels.json` as it is until the user changes it.

### 2. Run metadata

Each results file (`detection.json`, and later the ticket 10 results) stores:

- the model ID of each model that the run called;
- a short hash of each prompt text (`CHECK_PROMPT`, `INJECT_PROMPT`, and the rules);
- the slopgate commit (`git rev-parse HEAD`) and whether the tree had changes;
- the dataset seed, the number of items of each origin, and the number of runs for each item;
- the date and the total cost.

`detection.md` shows this block at the top. When two results files have different prompt hashes or datasets, a comparison script must say so before it prints a difference.

### 3. pass@k and pass^k

Each item runs 3 times. Report two numbers for each kind:

- **found in at least 1 of 3 runs** (pass@3): the detector can find the kind;
- **found in all 3 runs** (pass^3): the detector finds the kind every time.

For clean functions, report the same for false kinds: a false kind in at least 1 run, and a false kind in all 3 runs. A gate that posts on real pull requests needs the "all 3 runs" number to be high for real slop and low for false kinds. Put the function in `bench/score.py`, so that ticket 10 can report pass@3 and pass^3 for proven rewrites.

## Acceptance

- [x] Ultra labels each row of `bench/labels.json` without the first label, and `detection.md` gives the kappa for each kind and in total.
- [x] `bench/results/label-disagreements.md` lists each disagreement with both reasons.
- [x] `detection.json` and `detection.md` hold the metadata block.
- [x] `detection.md` gives pass@3 and pass^3 for each kind, and the two false-kind numbers for clean functions.
- [x] `tests/test_bench.py` tests kappa, the metadata, and pass@k on small fixed inputs.
- [x] `uv run pytest -q` passes.

## Comments

### 2026-10-17: done

**What was built**

- `bench/label.py` is the second labeller. Nemotron Ultra labels each row of `bench/labels.json` again with `decide` (reason before verdict). The prompt has the kind, the rule, the evidence lines, the path, and the function source. It never has the first label or its reason (a test checks this).
- The design names `kinds.RULES` and `CHECK_PROMPT`. Ticket 39 removed both. The rule text is now `kinds.KINDS[kind]`.
- Ultra labels only the rows of kinds that the gate still checks: 63 real-code rows and 46 injection rows. The 87 `filler_comment` rows have no rule, and `prepare()` does not score them.
- There are two prompt variants. "rule" gives only the one-line text of `kinds.KINDS`. "definition" adds the gate's full definition of each kind (`label.DEFINITIONS`, written from `flattenable`, `repeated_checks`, and the Ruff and vulture codes). The user asked for the second variant after the first kappa was low.
- `bench/score.py` has `kappa`, `agreement`, `metadata`, `mismatch`, `prompt_hash`, and `passes`. Ticket 10 can use them.
- Each stage writes its own metadata when it runs: `inject` writes `groundtruth.meta.json`, `run` writes `runs[-<name>].meta.json`, and each label cache holds a `metadata` key. `report` reads these files. It does not hash the code at report time. For the existing data, the meta files were written by hand from the commit that last wrote each file (see the `source` field).
- `mismatch` compares the metadata of the two runs files of the change table. `label.main` refuses a cache whose prompt hashes differ from the current prompts.
- pass@k counts an error run as a miss.

**Worked example**

Row `pallets/flask:src/flask/app.py:Flask.handle_url_build_error|nesting`. The first label is "false positive" ("Depth 3 is for/try-except-else/if rv is not None, which the handler loop needs").

- Rule prompt: Ultra says slop. It reads "nests blocks deeply" and counts two levels as deep.
- Definition prompt: Ultra says false positive: "The if statement inside the else block is at level 2, which does not exceed the threshold of more than 2 levels deep."

The two variants give a different verdict on 17 of 109 rows.

**Measured results** (`bench/results/detection.md`)

| kind | rows | kappa (rule) | kappa (definition) |
| --- | --- | --- | --- |
| nesting | 43 | 0.340 | 0.530 |
| redundant_check | 34 | 0.123 | 0.294 |
| swallowed_error | 13 | 0.0 | 0.0 |
| dead | 12 | 0.0 | 0.0 |
| lookup_table | 7 | none (all rows one label) | none |
| total | 109 | 0.348 | 0.557 |

These numbers use `bench/labels.json` after the label review below. Before the review, the totals were 0.361 and 0.573.

- Agreement in total: 0.679 (rule) and 0.780 (definition). There are 35 and 24 disagreements. `bench/results/label-disagreements.md` lists them with both reasons.
- With the rule prompt, 30 of 34 disagreements go one way: Ultra says slop where the first labeller said false positive.
- The kappa of 0.0 for `swallowed_error` and `dead` comes from 1 disagreement each. Almost all rows of these kinds have one label, so kappa is unstable.
- With the definition prompt, Ultra still calls 5 Super injections of the form `if hasattr(self, 'x'): pass` a redundant check. The definition says that a check of a new fact is not this kind.
- Ultra repeatability: two runs of the rule prompt at temperature 0 gave the same verdict on 104 of 109 rows.
- pass@3 and pass^3, current gate (`detection-t39.md`, held-out set): found 0.902 in at least 1 of 3 runs and 0.902 in all 3 runs (51 item-kinds). False kind on clean functions: 0.013 and 0.013 (80 items). The two numbers are equal because the checks are static.
- pass@3 and pass^3, gate before ticket 39 (`detection.md`): found 0.941 and 0.882 (136 item-kinds). `redundant_check` is 0.636 and 0.273, because that gate called Lightning.
- Setup differences that `detection-t39.md` now reports against `runs.json`: `CHECK_PROMPT`, `RULES`, and Lightning are in the base runs only, and the `KINDS` hash differs.
- Cost: Ultra rule run 82,714 input and 9,798 output tokens ($0.112). Ultra definition run 95,020 input and 12,486 output tokens ($0.132). One more rule run was discarded because it sent no trace (about $0.11).
- Traces (project `slopgate-bench`): `0bb01bd98fd67401f23fcbc980f838d1` (rule) and `1049dcdd4c7ba3bac462c48c877143af` (definition). Both have status OK, 109 LLM spans each, and no `finish_reason: "length"`. The median call takes 1.7 s and 2.0 s. One definition call took 27 s.
- The first label run sent no trace: `trace.start` alone opens no tracer, and `label.main` had no span. The fix adds the `bench.label` and `bench.label_row` spans.

**Label review**

The kappas were below 0.6, so two Opus subagents reviewed all 109 scored rows of `bench/labels.json` from the source. Each reviewer wrote its own verdict before it read the labels.

- The 23 rows where Ultra (definition prompt) disagreed: `labels.json` was right on 20 rows. Ultra's reasons on those rows had factual errors: wrong depth counts, missed lines, and an assignment treated as an earlier if.
- The 89 rows where the two labellers agreed: all `dead` (11), `lookup_table` (7), and `swallowed_error` (13) rows are correct.
- Most of the proposed `nesting` and `redundant_check` changes depended on the standard. The reviewers used `label.DEFINITIONS`, which describes what the gate's checks can find. Labels on that standard make the benchmark score the gate against its own rules.
- The user chose the human-reviewer standard: slop means that a reviewer wants the kind flagged, by the one-line rule in `kinds.KINDS`. `reviewed_by` in `labels.json` records this.
- Changes against the labels before the review:
  - 1 decision: `AccumulationBounds.intersection` nesting, from slop to false positive. Its reason stated a false fact: `if self.min <= other.min:` holds two ifs, so it cannot join into one `and` test.
  - 8 reasons: `numberformat.format:transform:dead` redundant_check, and 7 Nemotron nesting injections whose reason named the depth check that ticket 39 removed.
- Effect on `detection.md` (gate before ticket 39): `nesting` precision went from 0.593 to 0.576, and total precision from 0.773 to 0.767. `detection-t39.md` (held-out set) did not change.
- Ticket 66 records the injected items that change behavior or do not clearly hold their kind.

**Known limits**

- Both kappas are still below 0.6. The label review shows that most of the remaining disagreements are Ultra errors. So the low kappa says more about Ultra as a second labeller than about the labels.
- The reviewers are Claude, the same model family as the first labeller. The review is not fully independent.
- The definitions were written after the rule-prompt disagreements were read. They come from the gate's code, not from the rows. But they can still make the kappa higher than a blind second labeller would give.
- For injection rows, the prompt header says "Evidence lines from a static check", but the lines are the injection's changed lines. A change to this header makes both caches stale, so it was not done.
- The meta files for the existing data use the commit that last wrote each file. Earlier code may have made the results.
