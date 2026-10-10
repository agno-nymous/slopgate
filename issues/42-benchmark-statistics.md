# 42 — Benchmark statistics: label agreement, run metadata, and pass@k

## Summary

- **Goal:** Make the benchmark numbers trustworthy enough for the submission. Example: `bench/labels.json` was drafted by Claude and accepted without a review of each row. Today nobody knows how often a second labeller would agree with it.
- **Checkable finish condition:** `bench/results/detection.md` shows the label agreement (Cohen's kappa) for each kind, a metadata block (models, prompt hashes, commit, seed, date), and "found in at least 1 of 3 runs" and "found in all 3 runs" for each kind. `uv run pytest -q` passes.
- **Evidence:** Before: `detection.md` gives one precision and one recall for each kind, with no label check and no record of the setup. After: the same report with the 3 additions above, and a test for each new function in `bench/score.py`.
- **Constraints:** The second labeller does not see the first labels. Do not change a label in `bench/labels.json` without a written reason. Ticket 10 uses the same metadata and pass@k functions, so put them in `bench/score.py`.

**Blocked by:** 37

**Status:** ready-for-agent

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

- [ ] Ultra labels each row of `bench/labels.json` without the first label, and `detection.md` gives the kappa for each kind and in total.
- [ ] `bench/results/label-disagreements.md` lists each disagreement with both reasons.
- [ ] `detection.json` and `detection.md` hold the metadata block.
- [ ] `detection.md` gives pass@3 and pass^3 for each kind, and the two false-kind numbers for clean functions.
- [ ] `tests/test_bench.py` tests kappa, the metadata, and pass@k on small fixed inputs.
- [ ] `uv run pytest -q` passes.

## Comments
