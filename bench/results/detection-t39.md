# Detection benchmark: runs-t39.json, held_out

## Run metadata

| field | report | groundtruth | runs | base runs | labels: rule | labels: definition |
| --- | --- | --- | --- | --- | --- | --- |
| models | none | injection: nvidia/nemotron-3-super-120b-a12b | none | check: nvidia/Nemotron-3_5-Lightning | second_labeller: nvidia/Nemotron-3-Ultra-550b-a55b | second_labeller: nvidia/Nemotron-3-Ultra-550b-a55b |
| commit | 58d9b5d1f3 (tree had changes) | be0d670fed | c31b3c5800 | be0d670fed | 58d9b5d1f3 (tree had changes) | 58d9b5d1f3 (tree had changes) |
| date | 2026-10-17 | 2026-10-09 | 2026-10-10 | 2026-10-09 | 2026-10-17 | 2026-10-17 |
| seeds | split 39, bootstrap 39 | sample 37 | none | none | none | none |
| runs per item | 3 |  | 3 | 3 | 1 | 1 |
| counts | clean 80, source 52, transform 29, nemotron 14 |  |  |  |  |  |
| cost (USD) | 0.2925 |  |  |  |  |  |

| prompt | stage | hash |
| --- | --- | --- |
| CHECK_PROMPT | base runs | `2dafaf056594` |
| DEFINITIONS | labels: definition | `029ab69e3620` |
| INJECT | groundtruth | `0a674837b4f3` |
| INJECT_PROMPT | groundtruth | `eb6823b10cc5` |
| KINDS | base runs | `b86e71f5d05e` |
| KINDS | labels: definition | `36d181cd34ef` |
| KINDS | labels: rule | `36d181cd34ef` |
| KINDS | runs | `36d181cd34ef` |
| LABEL_PROMPT | labels: definition | `34b76acfaa9b` |
| LABEL_PROMPT | labels: rule | `34b76acfaa9b` |
| Label | labels: definition | `a7084cceb6d8` |
| Label | labels: rule | `a7084cceb6d8` |
| RULES | base runs | `ba6048530b12` |

- Source of groundtruth: backfilled on 2026-10-17 from commit be0d670fedfc4e945490ce9d731b394cc33ae2e6, the last commit that wrote groundtruth.json; the hashes are of INJECT_PROMPT and of INJECT as json with sorted keys in bench/detect.py at that commit (read with git show, parsed with ast.literal_eval); the sample seed is the literal 37 in random.Random(37) in that file
- Source of runs: backfilled on 2026-10-17 from commit c31b3c580064743a9bd02290f57159a46c099fc7, the last commit that wrote runs-t39.json (the gate of ticket 39); slopgate/kinds.py at that commit does not import llm, so the gate called no model; the hash is of KINDS (json with sorted keys) at that commit (read with git show, parsed with ast.literal_eval)
- Source of base runs: backfilled on 2026-10-17 from commit be0d670fedfc4e945490ce9d731b394cc33ae2e6, the last commit that wrote runs.json (the gate before ticket 39); classify in slopgate/kinds.py at that commit calls llm.decide(LIGHTNING, ...) with CHECK_PROMPT and RULES; the hashes are of CHECK_PROMPT, RULES and KINDS (json with sorted keys) at that commit (read with git show, parsed with ast.literal_eval)
- Source of labels: rule: backfilled on 2026-10-17; the run used the same prompt text
- Source of labels: definition: backfilled on 2026-10-17; the run used the same prompt text

## Setup differences

The base result and this result differ in the setup below. Read the change table with this in mind.

- prompt CHECK_PROMPT: 2dafaf056594 against missing
- prompt KINDS: b86e71f5d05e against 36d181cd34ef
- prompt RULES: ba6048530b12 against missing
- models: {'check': 'nvidia/Nemotron-3_5-Lightning'} against {}

## Change against the gate before ticket 39

Each cell is the value and its 95% range from 1000 bootstrap resamples of whole functions.

| kind | base precision | new precision | difference precision | base recall | new recall | difference recall | base FP rate | new FP rate | difference FP rate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| nesting | 0.56 [0.35, 0.759] | 0.923 [0.75, 1.0] | 0.363 [0.174, 0.556] | 1.0 [1.0, 1.0] | 0.857 [0.636, 1.0] | -0.143 [-0.364, 0.0] | 0.113 [0.046, 0.186] | 0.013 [0.0, 0.042] | -0.1 [-0.169, -0.039] |
| redundant_check | 0.316 [0.043, 0.667] | 1.0 [1.0, 1.0] (992 resamples) | 0.684 [0.333, 0.95] (992 resamples) | 0.25 [0.037, 0.5] | 0.625 [0.25, 1.0] | 0.375 [0.0, 0.778] | 0.004 [0.0, 0.014] | 0.0 [0.0, 0.0] | -0.004 [-0.014, 0.0] |
| swallowed_error | 1.0 [1.0, 1.0] | 1.0 [1.0, 1.0] | 0.0 [0.0, 0.0] | 1.0 [1.0, 1.0] | 1.0 [1.0, 1.0] | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] |
| lookup_table | 1.0 [1.0, 1.0] (998 resamples) | 1.0 [1.0, 1.0] (998 resamples) | 0.0 [0.0, 0.0] (998 resamples) | 1.0 [1.0, 1.0] (998 resamples) | 1.0 [1.0, 1.0] (998 resamples) | 0.0 [0.0, 0.0] (998 resamples) | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] |
| dead | 1.0 [1.0, 1.0] | 1.0 [1.0, 1.0] | 0.0 [0.0, 0.0] | 1.0 [1.0, 1.0] | 1.0 [1.0, 1.0] | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] | 0.0 [0.0, 0.0] |
| total | 0.746 [0.63, 0.849] | 0.979 [0.925, 1.0] | 0.233 [0.138, 0.342] | 0.882 [0.799, 0.958] | 0.902 [0.789, 0.984] | 0.02 [-0.078, 0.109] | 0.117 [0.048, 0.189] | 0.013 [0.0, 0.042] | -0.104 [-0.174, -0.042] |

`items` is the number of distinct items with at least one TP, FP, or FN.

## Precision and recall: all

| kind | items | TP | FP | FN | precision | recall |
| --- | --- | --- | --- | --- | --- | --- |
| nesting | 15 | 36 | 3 | 6 | 0.923 | 0.857 |
| redundant_check | 8 | 15 | 0 | 9 | 1.0 | 0.625 |
| swallowed_error | 7 | 21 | 0 | 0 | 1.0 | 1.0 |
| lookup_table | 10 | 30 | 0 | 0 | 1.0 | 1.0 |
| dead | 12 | 36 | 0 | 0 | 1.0 | 1.0 |
| total | 48 | 138 | 3 | 15 | 0.979 | 0.902 |

## Precision and recall: transform

| kind | items | TP | FP | FN | precision | recall |
| --- | --- | --- | --- | --- | --- | --- |
| nesting | 7 | 21 | 0 | 0 | 1.0 | 1.0 |
| redundant_check | 5 | 15 | 0 | 0 | 1.0 | 1.0 |
| swallowed_error | 5 | 15 | 0 | 0 | 1.0 | 1.0 |
| lookup_table | 8 | 24 | 0 | 0 | 1.0 | 1.0 |
| dead | 7 | 21 | 0 | 0 | 1.0 | 1.0 |
| total | 29 | 96 | 0 | 0 | 1.0 | 1.0 |

## Precision and recall: nemotron

| kind | items | TP | FP | FN | precision | recall |
| --- | --- | --- | --- | --- | --- | --- |
| nesting | 3 | 3 | 0 | 6 | 1.0 | 0.333 |
| redundant_check | 3 | 0 | 0 | 9 |  | 0.0 |
| swallowed_error | 2 | 6 | 0 | 0 | 1.0 | 1.0 |
| lookup_table | 2 | 6 | 0 | 0 | 1.0 | 1.0 |
| dead | 5 | 15 | 0 | 0 | 1.0 | 1.0 |
| total | 14 | 30 | 0 | 15 | 1.0 | 0.667 |

## Precision and recall: two_kinds

| kind | items | TP | FP | FN | precision | recall |
| --- | --- | --- | --- | --- | --- | --- |
| nesting | 2 | 6 | 0 | 0 | 1.0 | 1.0 |
| redundant_check | 0 | 0 | 0 | 0 |  |  |
| swallowed_error | 1 | 3 | 0 | 0 | 1.0 | 1.0 |
| lookup_table | 1 | 3 | 0 | 0 | 1.0 | 1.0 |
| dead | 2 | 6 | 0 | 0 | 1.0 | 1.0 |
| total | 3 | 18 | 0 | 0 | 1.0 | 1.0 |

## False positives on clean functions

Clean item-runs: 240. Share with any kind: 0.05.

| kind | false-positive rate |
| --- | --- |
| nesting | 0.013 |
| redundant_check | 0.0 |
| swallowed_error | 0.0 |
| lookup_table | 0.0 |
| dead | 0.0 |
| total | 0.013 |

## Label agreement (Cohen's kappa)

The "rule" prompt gives Ultra the one-line rule from `kinds.KINDS`. The "definition" prompt adds the gate's full definition from `bench/label.py`.

A kappa below 0.6 means the labels of that kind are not reliable, and kappa is unstable when almost all rows of a kind have the same label.

| kind | rows (rule) | agreement (rule) | kappa (rule) | rows (definition) | agreement (definition) | kappa (definition) |
| --- | --- | --- | --- | --- | --- | --- |
| nesting | 18 | 0.833 | 0.675 | 18 | 0.778 | 0.556 |
| redundant_check | 15 | 0.533 | 0.222 | 15 | 0.667 | 0.359 |
| swallowed_error | 2 | 1.0 |  | 2 | 1.0 |  |
| lookup_table | 2 | 1.0 |  | 2 | 1.0 |  |
| dead | 5 | 1.0 |  | 5 | 1.0 |  |
| total | 42 | 0.762 | 0.54 | 42 | 0.786 | 0.581 |

## Found in at least 1 of 3 runs and in all 3 runs

An error run counts as a miss.

| kind | found | found ≥1 of 3 | found 3 of 3 | clean items | false kind ≥1 of 3 | false kind 3 of 3 |
| --- | --- | --- | --- | --- | --- | --- |
| nesting | 14 items | 0.857 | 0.857 | 80 | 0.013 | 0.013 |
| redundant_check | 8 items | 0.625 | 0.625 | 80 | 0.0 | 0.0 |
| swallowed_error | 7 items | 1.0 | 1.0 | 80 | 0.0 | 0.0 |
| lookup_table | 10 items | 1.0 | 1.0 | 80 | 0.0 | 0.0 |
| dead | 12 items | 1.0 | 1.0 | 80 | 0.0 | 0.0 |
| total | 51 item-kinds | 0.902 | 0.902 | 80 | 0.013 | 0.013 |

## Time for each function (seconds)

| mean | median | p95 | max |
| --- | --- | --- | --- |
| 0.094 | 0.079 | 0.186 | 0.595 |

8 worker processes; times include queueing.

## Tokens and cost

| model | use | input tokens | output tokens | USD |
| --- | --- | --- | --- | --- |
| nvidia/nemotron-3-super-120b-a12b | injection | 43585 | 38719 | 0.0479 |
| nvidia/Nemotron-3-Ultra-550b-a55b | second labeller (rule) | 82714 | 9798 | 0.1121 |
| nvidia/Nemotron-3-Ultra-550b-a55b | second labeller (definition) | 95020 | 12486 | 0.1325 |

## Stability (same kinds in all runs)

| items | share |
| --- | --- |
| all | 1.0 |
| clean | 1.0 |
| source | 1.0 |
| transform | 1.0 |
| nemotron | 1.0 |

## Counts

| origin | items |
| --- | --- |
| clean | 80 |
| source | 52 |
| transform | 29 |
| nemotron | 14 |

| repo | items |
| --- | --- |
| django/django | 30 |
| sympy/sympy | 23 |
| psf/requests | 8 |
| pallets/flask | 13 |
| astropy/astropy | 28 |
| scikit-learn/scikit-learn | 19 |
| sphinx-doc/sphinx | 18 |
| pytest-dev/pytest | 12 |
| matplotlib/matplotlib | 14 |
| pylint-dev/pylint | 4 |
| pydata/xarray | 6 |

## False positives

| item | kind | runs |
| --- | --- | --- |
| pytest-dev/pytest:src/_pytest/unittest.py:UnitTestCase.collect | nesting | 3 |

## False negatives

| item | kind | runs |
| --- | --- | --- |
| astropy/astropy:astropy/cosmology/flrw.py:LambdaCDM._dS_comoving_distance_z1z2:nemotron:redundant_check | redundant_check | 3 |
| matplotlib/matplotlib:lib/matplotlib/offsetbox.py:AnchoredOffsetbox.draw:nemotron:nesting | nesting | 3 |
| matplotlib/matplotlib:lib/matplotlib/offsetbox.py:AnchoredOffsetbox.draw:nemotron:nesting | redundant_check | 3 |
| sphinx-doc/sphinx:sphinx/domains/c.py:ASTDeclaration.__init__:nemotron:nesting | nesting | 3 |
| sphinx-doc/sphinx:sphinx/domains/c.py:ASTDeclaratorNameParam.describe_signature:nemotron:redundant_check | redundant_check | 3 |

## Unlabelled kinds

| item | kind | runs |
| --- | --- | --- |

## Errors

| item | error |
| --- | --- |
