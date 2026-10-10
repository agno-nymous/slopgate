# Detection benchmark: runs.json (gate before ticket 39), all

`items` is the number of distinct items with at least one TP, FP, or FN.

## Precision and recall: all

| kind | items | TP | FP | FN | precision | recall |
| --- | --- | --- | --- | --- | --- | --- |
| nesting | 59 | 105 | 72 | 0 | 0.593 | 1.0 |
| redundant_check | 43 | 30 | 35 | 36 | 0.462 | 0.455 |
| swallowed_error | 30 | 87 | 3 | 0 | 0.967 | 1.0 |
| lookup_table | 23 | 69 | 0 | 0 | 1.0 | 1.0 |
| dead | 28 | 84 | 0 | 0 | 1.0 | 1.0 |
| total | 160 | 375 | 110 | 36 | 0.773 | 0.912 |

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
| nesting | 10 | 30 | 0 | 0 | 1.0 | 1.0 |
| redundant_check | 6 | 1 | 3 | 11 | 0.25 | 0.083 |
| swallowed_error | 10 | 30 | 0 | 0 | 1.0 | 1.0 |
| lookup_table | 7 | 21 | 0 | 0 | 1.0 | 1.0 |
| dead | 10 | 30 | 0 | 0 | 1.0 | 1.0 |
| total | 40 | 112 | 3 | 11 | 0.974 | 0.911 |

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

## Time for each function (seconds)

| mean | median | p95 | max |
| --- | --- | --- | --- |
| 2.073 | 1.491 | 5.513 | 109.93 |

8 worker processes; times include queueing.

## Tokens and cost

| model | use | input tokens | output tokens | USD |
| --- | --- | --- | --- | --- |
| nvidia/nemotron-3-super-120b-a12b | injection | 43585 | 38719 | 0.0479 |

## Stability (same kinds in all runs)

| items | share |
| --- | --- |
| all | 0.943 |
| clean | 0.98 |
| source | 0.946 |
| transform | 0.847 |
| nemotron | 0.925 |

## Counts

| origin | items |
| --- | --- |
| clean | 200 |
| source | 129 |
| transform | 72 |
| nemotron | 40 |

| repo | items |
| --- | --- |
| django/django | 64 |
| sympy/sympy | 74 |
| psf/requests | 27 |
| pallets/flask | 26 |
| astropy/astropy | 56 |
| scikit-learn/scikit-learn | 37 |
| sphinx-doc/sphinx | 50 |
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
| pytest-dev/pytest:src/_pytest/tmpdir.py:pytest_configure:nemotron:nesting | redundant_check | 2 |
| pytest-dev/pytest:src/_pytest/unittest.py:UnitTestCase.collect | nesting | 3 |
| pytest-dev/pytest:src/_pytest/unittest.py:pytest_runtest_makereport | redundant_check | 1 |
| scikit-learn/scikit-learn:sklearn/externals/joblib/_parallel_backends.py:SafeFunction.__call__ | swallowed_error | 3 |
| scikit-learn/scikit-learn:sklearn/metrics/classification.py:_check_targets | nesting | 3 |
| scikit-learn/scikit-learn:sklearn/mixture/gmm.py:_log_multivariate_normal_density_full | nesting | 3 |
| scikit-learn/scikit-learn:sklearn/utils/estimator_checks.py:check_estimators_dtypes | nesting | 3 |
| sphinx-doc/sphinx:sphinx/builders/xml.py:XMLBuilder.get_outdated_docs | nesting | 3 |
| sphinx-doc/sphinx:sphinx/domains/std.py:ProductionList.run | nesting | 3 |
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
