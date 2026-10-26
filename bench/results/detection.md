# Detection benchmark: runs.json (gate before ticket 39), all

## Run metadata

| field | report | groundtruth | runs | labels: rule | labels: definition |
| --- | --- | --- | --- | --- | --- |
| models | none | injection: nvidia/nemotron-3-super-120b-a12b | check: nvidia/Nemotron-3_5-Lightning | second_labeller: nvidia/Nemotron-3-Ultra-550b-a55b | second_labeller: nvidia/Nemotron-3-Ultra-550b-a55b |
| commit | b57be22c83 (tree had changes) | be0d670fed | be0d670fed | 58d9b5d1f3 (tree had changes) | 58d9b5d1f3 (tree had changes) |
| date | 2026-10-25 | 2026-10-09 | 2026-10-09 | 2026-10-17 | 2026-10-17 |
| seeds | split 39, bootstrap 39 | sample 37 | none | none | none |
| runs per item | 3 |  | 3 | 1 | 1 |
| counts | clean 200, source 129, transform 72, nemotron 39 |  |  |  |  |
| cost (USD) | 0.3016 |  |  |  |  |

| prompt | stage | hash |
| --- | --- | --- |
| CHECK_PROMPT | runs | `2dafaf056594` |
| DEFINITIONS | labels: definition | `029ab69e3620` |
| INJECT | groundtruth | `0a674837b4f3` |
| INJECT_PROMPT | groundtruth | `eb6823b10cc5` |
| KINDS | labels: definition | `36d181cd34ef` |
| KINDS | labels: rule | `36d181cd34ef` |
| KINDS | runs | `b86e71f5d05e` |
| LABEL_PROMPT | labels: definition | `34b76acfaa9b` |
| LABEL_PROMPT | labels: rule | `34b76acfaa9b` |
| Label | labels: definition | `a7084cceb6d8` |
| Label | labels: rule | `a7084cceb6d8` |
| RULES | runs | `ba6048530b12` |

- Source of groundtruth: backfilled on 2026-10-17 from commit be0d670fedfc4e945490ce9d731b394cc33ae2e6, the last commit that wrote groundtruth.json; the hashes are of INJECT_PROMPT and of INJECT as json with sorted keys in bench/detect.py at that commit (read with git show, parsed with ast.literal_eval); the sample seed is the literal 37 in random.Random(37) in that file
- Source of runs: backfilled on 2026-10-17 from commit be0d670fedfc4e945490ce9d731b394cc33ae2e6, the last commit that wrote runs.json (the gate before ticket 39); classify in slopgate/kinds.py at that commit calls llm.decide(LIGHTNING, ...) with CHECK_PROMPT and RULES; the hashes are of CHECK_PROMPT, RULES and KINDS (json with sorted keys) at that commit (read with git show, parsed with ast.literal_eval)
- Source of labels: rule: backfilled on 2026-10-17; the run used the same prompt text
- Source of labels: definition: backfilled on 2026-10-17; the run used the same prompt text

`items` is the number of distinct items with at least one TP, FP, or FN.

## Precision and recall: all

| kind | items | TP | FP | FN | precision | recall |
| --- | --- | --- | --- | --- | --- | --- |
| nesting | 56 | 93 | 75 | 0 | 0.554 | 1.0 |
| redundant_check | 42 | 30 | 33 | 36 | 0.476 | 0.455 |
| swallowed_error | 30 | 87 | 3 | 0 | 0.967 | 1.0 |
| lookup_table | 22 | 66 | 0 | 0 | 1.0 | 1.0 |
| dead | 28 | 84 | 0 | 0 | 1.0 | 1.0 |
| total | 156 | 360 | 111 | 36 | 0.764 | 0.909 |

## Precision and recall: transform

| kind | items | TP | FP | FN | precision | recall |
| --- | --- | --- | --- | --- | --- | --- |
| nesting | 16 | 48 | 0 | 0 | 1.0 | 1.0 |
| redundant_check | 20 | 24 | 9 | 21 | 0.727 | 0.533 |
| swallowed_error | 17 | 51 | 0 | 0 | 1.0 | 1.0 |
| lookup_table | 16 | 48 | 0 | 0 | 1.0 | 1.0 |
| dead | 16 | 48 | 0 | 0 | 1.0 | 1.0 |
| total | 72 | 219 | 9 | 21 | 0.961 | 0.912 |

## Precision and recall: nemotron

| kind | items | TP | FP | FN | precision | recall |
| --- | --- | --- | --- | --- | --- | --- |
| nesting | 7 | 21 | 0 | 0 | 1.0 | 1.0 |
| redundant_check | 5 | 1 | 1 | 11 | 0.5 | 0.083 |
| swallowed_error | 10 | 30 | 0 | 0 | 1.0 | 1.0 |
| lookup_table | 6 | 18 | 0 | 0 | 1.0 | 1.0 |
| dead | 10 | 30 | 0 | 0 | 1.0 | 1.0 |
| total | 36 | 100 | 1 | 11 | 0.99 | 0.901 |

## Precision and recall: two_kinds

| kind | items | TP | FP | FN | precision | recall |
| --- | --- | --- | --- | --- | --- | --- |
| nesting | 3 | 9 | 0 | 0 | 1.0 | 1.0 |
| redundant_check | 2 | 5 | 0 | 1 | 1.0 | 0.833 |
| swallowed_error | 4 | 12 | 0 | 0 | 1.0 | 1.0 |
| lookup_table | 3 | 9 | 0 | 0 | 1.0 | 1.0 |
| dead | 4 | 12 | 0 | 0 | 1.0 | 1.0 |
| total | 8 | 47 | 0 | 1 | 1.0 | 0.979 |

## False positives on clean functions

Clean item-runs: 600. Share with any kind: 0.153.

| kind | false-positive rate |
| --- | --- |
| nesting | 0.09 |
| redundant_check | 0.023 |
| swallowed_error | 0.005 |
| lookup_table | 0.0 |
| dead | 0.0 |
| total | 0.115 |

## Label agreement (Cohen's kappa)

The "rule" prompt gives Ultra the one-line rule from `kinds.KINDS`. The "definition" prompt adds the gate's full definition from `bench/label.py`.

A kappa below 0.6 means the labels of that kind are not reliable, and kappa is unstable when almost all rows of a kind have the same label.

| kind | rows (rule) | agreement (rule) | kappa (rule) | rows (definition) | agreement (definition) | kappa (definition) |
| --- | --- | --- | --- | --- | --- | --- |
| nesting | 43 | 0.628 | 0.306 | 43 | 0.744 | 0.481 |
| redundant_check | 34 | 0.471 | 0.123 | 34 | 0.618 | 0.261 |
| swallowed_error | 13 | 0.923 | 0.0 | 13 | 0.923 | 0.0 |
| lookup_table | 7 | 1.0 |  | 7 | 1.0 |  |
| dead | 12 | 0.917 | 0.0 | 12 | 0.917 | 0.0 |
| total | 109 | 0.67 | 0.336 | 109 | 0.761 | 0.522 |

## Found in at least 1 of 3 runs and in all 3 runs

An error run counts as a miss.

| kind | found | found ≥1 of 3 | found 3 of 3 | clean items | false kind ≥1 of 3 | false kind 3 of 3 |
| --- | --- | --- | --- | --- | --- | --- |
| nesting | 31 items | 1.0 | 1.0 | 200 | 0.09 | 0.09 |
| redundant_check | 22 items | 0.636 | 0.273 | 200 | 0.035 | 0.015 |
| swallowed_error | 29 items | 1.0 | 1.0 | 200 | 0.005 | 0.005 |
| lookup_table | 22 items | 1.0 | 1.0 | 200 | 0.0 | 0.0 |
| dead | 28 items | 1.0 | 1.0 | 200 | 0.0 | 0.0 |
| total | 132 item-kinds | 0.939 | 0.879 | 200 | 0.125 | 0.11 |

## Time for each function (seconds)

| mean | median | p95 | max |
| --- | --- | --- | --- |
| 2.063 | 1.471 | 5.573 | 109.93 |

8 worker processes; times include queueing.

## Tokens and cost

| model | use | input tokens | output tokens | USD |
| --- | --- | --- | --- | --- |
| nvidia/nemotron-3-super-120b-a12b | injection | 43585 | 38719 | 0.0479 |
| nvidia/Nemotron-3-Ultra-550b-a55b | second labeller (rule) | 85810 | 10150 | 0.1163 |
| nvidia/Nemotron-3-Ultra-550b-a55b | second labeller (definition) | 98581 | 12952 | 0.1374 |

## Stability (same kinds in all runs)

| items | share |
| --- | --- |
| all | 0.945 |
| clean | 0.98 |
| source | 0.946 |
| transform | 0.847 |
| nemotron | 0.944 |

## Counts

| origin | items |
| --- | --- |
| clean | 200 |
| source | 129 |
| transform | 72 |
| nemotron | 39 |

| repo | items |
| --- | --- |
| django/django | 64 |
| sympy/sympy | 74 |
| psf/requests | 27 |
| pallets/flask | 26 |
| astropy/astropy | 56 |
| scikit-learn/scikit-learn | 37 |
| sphinx-doc/sphinx | 49 |
| pytest-dev/pytest | 29 |
| pylint-dev/pylint | 19 |
| matplotlib/matplotlib | 46 |
| pydata/xarray | 12 |
| mwaskom/seaborn | 1 |

## False positives

| item | kind | runs |
| --- | --- | --- |
| astropy/astropy:astropy/coordinates/solar_system.py:get_body | redundant_check | 3 |
| astropy/astropy:astropy/modeling/fitting.py:model_to_fit_params | nesting | 3 |
| astropy/astropy:astropy/units/format/generic.py:Generic._format_unit_list | nesting | 3 |
| django/django:django/contrib/postgres/fields/ranges.py:RangeField.to_python | nesting | 3 |
| django/django:django/db/backends/mysql/base.py:DatabaseWrapper.check_constraints | nesting | 3 |
| django/django:django/db/backends/mysql/base.py:DatabaseWrapper.check_constraints | redundant_check | 1 |
| django/django:django/db/backends/postgresql/base.py:DatabaseWrapper.get_connection_params | redundant_check | 1 |
| django/django:django/db/models/base.py:Model.clean_fields | redundant_check | 1 |
| django/django:django/forms/widgets.py:NullBooleanSelect.format_value:transform:lookup_table | redundant_check | 3 |
| django/django:django/template/base.py:Token.split_contents | nesting | 3 |
| django/django:django/utils/numberformat.py:format | nesting | 3 |
| django/django:django/utils/numberformat.py:format:transform:dead | redundant_check | 1 |
| matplotlib/matplotlib:lib/matplotlib/font_manager.py:findSystemFonts | nesting | 3 |
| pallets/flask:src/flask/app.py:Flask.handle_url_build_error | nesting | 3 |
| pallets/flask:src/flask/debughelpers.py:_dump_loader_info | nesting | 3 |
| pallets/flask:src/flask/templating.py:DispatchingJinjaLoader._get_source_explained | nesting | 3 |
| psf/requests:requests/hooks.py:dispatch_hook | nesting | 3 |
| psf/requests:requests/models.py:RequestEncodingMixin._encode_files | nesting | 3 |
| psf/requests:requests/models.py:Response.json | nesting | 3 |
| psf/requests:requests/packages/chardet/charsetgroupprober.py:CharSetGroupProber.get_confidence | nesting | 3 |
| psf/requests:requests/packages/chardet/hebrewprober.py:HebrewProber.get_charset_name | redundant_check | 3 |
| psf/requests:requests/utils.py:get_encoding_from_headers | redundant_check | 1 |
| pydata/xarray:xarray/backends/locks.py:_get_lock_maker:transform:lookup_table+filler_comment | redundant_check | 2 |
| pydata/xarray:xarray/core/duck_array_ops.py:_create_nan_agg_method | nesting | 3 |
| pylint-dev/pylint:pylint/checkers/base.py:ComparisonChecker._check_logical_tautology | redundant_check | 1 |
| pylint-dev/pylint:pylint/checkers/base.py:NamingStyle.get_regex:transform:lookup_table | redundant_check | 1 |
| pylint-dev/pylint:pylint/checkers/utils.py:safe_infer | nesting | 3 |
| pytest-dev/pytest:src/_pytest/_py/path.py:LocalPath._ensuredirs | nesting | 3 |
| pytest-dev/pytest:src/_pytest/_py/path.py:LocalPath._ensuredirs | redundant_check | 2 |
| pytest-dev/pytest:src/_pytest/fixtures.py:FixtureRequest._getnextfixturedef | redundant_check | 1 |
| pytest-dev/pytest:src/_pytest/unittest.py:UnitTestCase.collect | nesting | 3 |
| pytest-dev/pytest:src/_pytest/unittest.py:pytest_runtest_makereport | redundant_check | 1 |
| scikit-learn/scikit-learn:sklearn/externals/joblib/_parallel_backends.py:SafeFunction.__call__ | swallowed_error | 3 |
| scikit-learn/scikit-learn:sklearn/metrics/classification.py:_check_targets | nesting | 3 |
| scikit-learn/scikit-learn:sklearn/mixture/gmm.py:_log_multivariate_normal_density_full | nesting | 3 |
| scikit-learn/scikit-learn:sklearn/utils/estimator_checks.py:check_estimators_dtypes | nesting | 3 |
| sphinx-doc/sphinx:sphinx/builders/xml.py:XMLBuilder.get_outdated_docs | nesting | 3 |
| sphinx-doc/sphinx:sphinx/domains/std.py:ProductionList.run | nesting | 3 |
| sympy/sympy:sympy/calculus/util.py:AccumulationBounds.intersection | nesting | 3 |
| sympy/sympy:sympy/functions/combinatorial/numbers.py:genocchi._eval_is_negative | redundant_check | 3 |
| sympy/sympy:sympy/functions/special/elliptic_integrals.py:elliptic_pi.fdiff:nemotron:dead | redundant_check | 1 |
| sympy/sympy:sympy/integrals/risch.py:splitfactor | redundant_check | 3 |
| sympy/sympy:sympy/ntheory/factor_.py:udivisors:transform:nesting | redundant_check | 2 |
| sympy/sympy:sympy/plotting/intervalmath/interval_arithmetic.py:interval.__pow__ | redundant_check | 1 |
| sympy/sympy:sympy/polys/densebasic.py:dup_deflate | redundant_check | 1 |
| sympy/sympy:sympy/polys/densetools.py:_dup_decompose | nesting | 3 |

## False negatives

| item | kind | runs |
| --- | --- | --- |
| astropy/astropy:astropy/cosmology/flrw.py:LambdaCDM._dS_comoving_distance_z1z2:nemotron:redundant_check | redundant_check | 3 |
| astropy/astropy:astropy/extern/configobj/configobj.py:ConfigObj._handle_comment:transform:redundant_check+filler_comment | redundant_check | 3 |
| astropy/astropy:astropy/modeling/powerlaws.py:ExponentialCutoffPowerLaw1D.fit_deriv:nemotron:redundant_check | redundant_check | 3 |
| astropy/astropy:astropy/utils/console.py:isatty:transform:redundant_check | redundant_check | 3 |
| django/django:django/db/backends/postgresql/base.py:DatabaseWrapper.get_connection_params:transform:redundant_check | redundant_check | 1 |
| django/django:django/db/models/sql/query.py:Query.table_alias:transform:redundant_check | redundant_check | 1 |
| matplotlib/matplotlib:lib/matplotlib/offsetbox.py:AnchoredOffsetbox.draw:nemotron:nesting | redundant_check | 2 |
| matplotlib/matplotlib:lib/matplotlib/tri/triangulation.py:Triangulation.__init__:transform:redundant_check | redundant_check | 2 |
| pylint-dev/pylint:pylint/checkers/base.py:BasicErrorChecker.visit_assign:transform:redundant_check | redundant_check | 2 |
| pylint-dev/pylint:pylint/checkers/classes/class_checker.py:_definition_equivalent_to_call:transform:redundant_check | redundant_check | 2 |
| pylint-dev/pylint:pylint/checkers/utils.py:safe_infer | redundant_check | 1 |
| scikit-learn/scikit-learn:sklearn/externals/funcsigs.py:formatannotation:transform:redundant_check | redundant_check | 3 |
| scikit-learn/scikit-learn:sklearn/model_selection/_split.py:check_cv:transform:redundant_check | redundant_check | 3 |
| sphinx-doc/sphinx:sphinx/domains/c.py:ASTDeclaratorNameParam.describe_signature:nemotron:redundant_check | redundant_check | 3 |
| sphinx-doc/sphinx:sphinx/transforms/post_transforms/__init__.py:SphinxPostTransform.is_supported:transform:redundant_check+dead | redundant_check | 1 |
| sympy/sympy:sympy/calculus/util.py:AccumulationBounds.intersection | redundant_check | 3 |

## Unlabelled kinds

| item | kind | runs |
| --- | --- | --- |

## Errors

| item | error |
| --- | --- |
