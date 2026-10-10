# Detection benchmark: runs-t39.json, held_out

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

## Time for each function (seconds)

| mean | median | p95 | max |
| --- | --- | --- | --- |
| 0.094 | 0.079 | 0.186 | 0.595 |

8 worker processes; times include queueing.

## Tokens and cost

| model | use | input tokens | output tokens | USD |
| --- | --- | --- | --- | --- |
| nvidia/nemotron-3-super-120b-a12b | injection | 43585 | 38719 | 0.0479 |

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
