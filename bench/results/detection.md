# Detection benchmark

`items` is the number of distinct items with at least one TP, FP, or FN.

## Precision and recall: all

| kind | items | TP | FP | FN | precision | recall |
| --- | --- | --- | --- | --- | --- | --- |
| nesting | 59 | 105 | 72 | 0 | 0.593 | 1.0 |
| redundant_check | 42 | 30 | 35 | 33 | 0.462 | 0.476 |
| swallowed_error | 30 | 87 | 3 | 0 | 0.967 | 1.0 |
| lookup_table | 23 | 69 | 0 | 0 | 1.0 | 1.0 |
| filler_comment | 103 | 99 | 118 | 12 | 0.456 | 0.892 |
| dead | 28 | 84 | 0 | 0 | 1.0 | 1.0 |
| total | 236 | 474 | 228 | 45 | 0.675 | 0.913 |

## Precision and recall: transform

| kind | items | TP | FP | FN | precision | recall |
| --- | --- | --- | --- | --- | --- | --- |
| nesting | 16 | 48 | 0 | 0 | 1.0 | 1.0 |
| redundant_check | 20 | 24 | 9 | 21 | 0.727 | 0.533 |
| swallowed_error | 17 | 51 | 0 | 0 | 1.0 | 1.0 |
| lookup_table | 16 | 48 | 0 | 0 | 1.0 | 1.0 |
| filler_comment | 18 | 47 | 2 | 1 | 0.959 | 0.979 |
| dead | 16 | 48 | 0 | 0 | 1.0 | 1.0 |
| total | 84 | 266 | 11 | 22 | 0.96 | 0.924 |

## Precision and recall: nemotron

| kind | items | TP | FP | FN | precision | recall |
| --- | --- | --- | --- | --- | --- | --- |
| nesting | 10 | 30 | 0 | 0 | 1.0 | 1.0 |
| redundant_check | 6 | 1 | 3 | 11 | 0.25 | 0.083 |
| swallowed_error | 10 | 30 | 0 | 0 | 1.0 | 1.0 |
| lookup_table | 7 | 21 | 0 | 0 | 1.0 | 1.0 |
| filler_comment | 12 | 24 | 3 | 6 | 0.889 | 0.8 |
| dead | 10 | 30 | 0 | 0 | 1.0 | 1.0 |
| total | 50 | 136 | 6 | 17 | 0.958 | 0.889 |

## Precision and recall: two_kinds

| kind | items | TP | FP | FN | precision | recall |
| --- | --- | --- | --- | --- | --- | --- |
| nesting | 4 | 12 | 0 | 0 | 1.0 | 1.0 |
| redundant_check | 4 | 5 | 2 | 4 | 0.714 | 0.556 |
| swallowed_error | 5 | 15 | 0 | 0 | 1.0 | 1.0 |
| lookup_table | 4 | 12 | 0 | 0 | 1.0 | 1.0 |
| filler_comment | 4 | 11 | 0 | 1 | 1.0 | 0.917 |
| dead | 4 | 12 | 0 | 0 | 1.0 | 1.0 |
| total | 12 | 67 | 2 | 5 | 0.971 | 0.931 |

## False positives on clean functions

Clean item-runs: 600. Share with any kind: 0.288.

| kind | false-positive rate |
| --- | --- |
| nesting | 0.09 |
| redundant_check | 0.023 |
| swallowed_error | 0.005 |
| lookup_table | 0.0 |
| filler_comment | 0.135 |
| dead | 0.0 |
| total | 0.217 |

## Time for each function (seconds)

| mean | median | p95 | max |
| --- | --- | --- | --- |
| 2.266 | 1.618 | 6.122 | 109.93 |

8 worker processes; times include queueing.

## Tokens and cost

The Lightning tokens count all runs, including the runs of the excluded Nemotron items.

| model | use | input tokens | output tokens | USD |
| --- | --- | --- | --- | --- |
| nvidia/Nemotron-3_5-Lightning | classify | 846069 | 241400 | 0.1087 |
| nvidia/nemotron-3-super-120b-a12b | injection | 43585 | 38719 | 0.0479 |

## Stability (same kinds in all runs)

| items | share |
| --- | --- |
| all | 0.808 |
| clean | 0.825 |
| source | 0.806 |
| transform | 0.786 |
| nemotron | 0.78 |

## Counts

| origin | items |
| --- | --- |
| clean | 200 |
| source | 129 |
| transform | 84 |
| nemotron | 50 |

| repo | items |
| --- | --- |
| django/django | 68 |
| sympy/sympy | 78 |
| psf/requests | 27 |
| pallets/flask | 26 |
| astropy/astropy | 56 |
| scikit-learn/scikit-learn | 39 |
| sphinx-doc/sphinx | 55 |
| pytest-dev/pytest | 29 |
| pylint-dev/pylint | 19 |
| matplotlib/matplotlib | 50 |
| pydata/xarray | 14 |
| mwaskom/seaborn | 2 |

## False positives

| item | kind | runs |
| --- | --- | --- |
| astropy/astropy:astropy/coordinates/baseframe.py:BaseCoordinateFrame._get_representation_info | filler_comment | 1 |
| astropy/astropy:astropy/coordinates/builtin_frames/galactic_transforms.py:fk5_to_gal | filler_comment | 1 |
| astropy/astropy:astropy/coordinates/jparser.py:_sexagesimal | filler_comment | 3 |
| astropy/astropy:astropy/coordinates/solar_system.py:get_body | redundant_check | 3 |
| astropy/astropy:astropy/cosmology/units.py:redshift_temperature | filler_comment | 2 |
| astropy/astropy:astropy/io/fits/hdu/hdulist.py:HDUList.pop | filler_comment | 3 |
| astropy/astropy:astropy/modeling/fitting.py:model_to_fit_params | nesting | 3 |
| astropy/astropy:astropy/samp/web_profile.py:WebProfileRequestHandler._serve_cross_domain_xml | filler_comment | 2 |
| astropy/astropy:astropy/time/formats.py:TimeString.value | filler_comment | 2 |
| astropy/astropy:astropy/units/format/generic.py:Generic._format_unit_list | nesting | 3 |
| astropy/astropy:astropy/utils/iers/iers.py:LeapSeconds.from_erfa | filler_comment | 1 |
| astropy/astropy:astropy/wcs/utils.py:obsgeo_to_frame | filler_comment | 2 |
| django/django:django/contrib/postgres/fields/ranges.py:RangeField.to_python | filler_comment | 3 |
| django/django:django/contrib/postgres/fields/ranges.py:RangeField.to_python | nesting | 3 |
| django/django:django/db/backends/mysql/base.py:DatabaseWrapper.check_constraints | nesting | 3 |
| django/django:django/db/backends/mysql/base.py:DatabaseWrapper.check_constraints | redundant_check | 1 |
| django/django:django/db/backends/postgresql/base.py:DatabaseWrapper.get_connection_params | redundant_check | 1 |
| django/django:django/db/backends/postgresql/base.py:DatabaseWrapper.get_connection_params:transform:redundant_check | filler_comment | 1 |
| django/django:django/db/migrations/executor.py:MigrationExecutor.migration_plan | filler_comment | 1 |
| django/django:django/db/models/base.py:Model.clean_fields | redundant_check | 1 |
| django/django:django/db/models/base.py:Model.clean_fields:transform:nesting | filler_comment | 1 |
| django/django:django/db/models/query.py:QuerySet.__init__ | filler_comment | 2 |
| django/django:django/db/models/query.py:QuerySet._update | filler_comment | 1 |
| django/django:django/db/models/sql/query.py:Query.table_alias | filler_comment | 1 |
| django/django:django/forms/widgets.py:NullBooleanSelect.format_value:transform:lookup_table | redundant_check | 3 |
| django/django:django/template/base.py:Token.split_contents | filler_comment | 3 |
| django/django:django/template/base.py:Token.split_contents | nesting | 3 |
| django/django:django/utils/numberformat.py:format | filler_comment | 1 |
| django/django:django/utils/numberformat.py:format | nesting | 3 |
| django/django:django/utils/numberformat.py:format:transform:dead | redundant_check | 1 |
| matplotlib/matplotlib:lib/matplotlib/axes/_axes.py:Axes._convert_dx:nemotron:nesting | filler_comment | 1 |
| matplotlib/matplotlib:lib/matplotlib/figure.py:Figure.set_size_inches | filler_comment | 3 |
| matplotlib/matplotlib:lib/matplotlib/font_manager.py:findSystemFonts | nesting | 3 |
| matplotlib/matplotlib:lib/matplotlib/offsetbox.py:AnchoredOffsetbox.draw | filler_comment | 1 |
| matplotlib/matplotlib:lib/matplotlib/projections/polar.py:PolarAxes._init_axis | filler_comment | 1 |
| matplotlib/matplotlib:lib/matplotlib/transforms.py:BboxTransformTo.get_matrix | filler_comment | 1 |
| matplotlib/matplotlib:lib/matplotlib/tri/triangulation.py:Triangulation.__init__ | filler_comment | 1 |
| pallets/flask:src/flask/app.py:Flask.handle_url_build_error | nesting | 3 |
| pallets/flask:src/flask/app.py:Flask.test_cli_runner | filler_comment | 3 |
| pallets/flask:src/flask/app.py:Flask.wsgi_app | filler_comment | 1 |
| pallets/flask:src/flask/ctx.py:RequestContext.auto_pop | filler_comment | 1 |
| pallets/flask:src/flask/debughelpers.py:_dump_loader_info | nesting | 3 |
| pallets/flask:src/flask/sessions.py:SessionInterface.get_cookie_domain | filler_comment | 3 |
| pallets/flask:src/flask/templating.py:DispatchingJinjaLoader._get_source_explained | nesting | 3 |
| psf/requests:requests/adapters.py:HTTPAdapter.__setstate__ | filler_comment | 2 |
| psf/requests:requests/hooks.py:dispatch_hook | nesting | 3 |
| psf/requests:requests/models.py:RequestEncodingMixin._encode_files | filler_comment | 2 |
| psf/requests:requests/models.py:RequestEncodingMixin._encode_files | nesting | 3 |
| psf/requests:requests/models.py:Response.json | filler_comment | 1 |
| psf/requests:requests/models.py:Response.json | nesting | 3 |
| psf/requests:requests/packages/chardet/charsetgroupprober.py:CharSetGroupProber.get_confidence | nesting | 3 |
| psf/requests:requests/packages/chardet/hebrewprober.py:HebrewProber.get_charset_name | filler_comment | 3 |
| psf/requests:requests/packages/chardet/hebrewprober.py:HebrewProber.get_charset_name | redundant_check | 3 |
| psf/requests:requests/packages/chardet/sbcharsetprober.py:SingleByteCharSetProber.reset | filler_comment | 3 |
| psf/requests:requests/packages/urllib3/connection.py:HTTPConnection._new_conn | filler_comment | 1 |
| psf/requests:requests/utils.py:get_encoding_from_headers | redundant_check | 1 |
| pydata/xarray:xarray/backends/locks.py:_get_lock_maker:transform:lookup_table+filler_comment | redundant_check | 2 |
| pydata/xarray:xarray/core/duck_array_ops.py:_create_nan_agg_method | nesting | 3 |
| pylint-dev/pylint:pylint/checkers/base.py:BasicErrorChecker.visit_assign | filler_comment | 2 |
| pylint-dev/pylint:pylint/checkers/base.py:ComparisonChecker._check_logical_tautology | redundant_check | 1 |
| pylint-dev/pylint:pylint/checkers/base.py:NamingStyle.get_regex:transform:lookup_table | redundant_check | 1 |
| pylint-dev/pylint:pylint/checkers/utils.py:safe_infer | nesting | 3 |
| pytest-dev/pytest:src/_pytest/_py/path.py:LocalPath._ensuredirs | nesting | 3 |
| pytest-dev/pytest:src/_pytest/_py/path.py:LocalPath._ensuredirs | redundant_check | 2 |
| pytest-dev/pytest:src/_pytest/fixtures.py:FixtureRequest._getnextfixturedef | filler_comment | 1 |
| pytest-dev/pytest:src/_pytest/fixtures.py:FixtureRequest._getnextfixturedef | redundant_check | 1 |
| pytest-dev/pytest:src/_pytest/mark/__init__.py:KeywordMatcher.from_item | filler_comment | 2 |
| pytest-dev/pytest:src/_pytest/reports.py:TestReport.__init__ | filler_comment | 3 |
| pytest-dev/pytest:src/_pytest/tmpdir.py:pytest_configure:nemotron:nesting | redundant_check | 2 |
| pytest-dev/pytest:src/_pytest/unittest.py:UnitTestCase.collect | nesting | 3 |
| pytest-dev/pytest:src/_pytest/unittest.py:pytest_runtest_makereport | filler_comment | 1 |
| pytest-dev/pytest:src/_pytest/unittest.py:pytest_runtest_makereport | redundant_check | 1 |
| scikit-learn/scikit-learn:sklearn/ensemble/gradient_boosting.py:GradientBoostingClassifier.staged_decision_function | filler_comment | 3 |
| scikit-learn/scikit-learn:sklearn/externals/joblib/_parallel_backends.py:SafeFunction.__call__ | filler_comment | 1 |
| scikit-learn/scikit-learn:sklearn/externals/joblib/_parallel_backends.py:SafeFunction.__call__ | swallowed_error | 3 |
| scikit-learn/scikit-learn:sklearn/externals/joblib/numpy_pickle.py:NumpyPickler.save | filler_comment | 2 |
| scikit-learn/scikit-learn:sklearn/feature_extraction/text.py:CountVectorizer.inverse_transform | filler_comment | 2 |
| scikit-learn/scikit-learn:sklearn/linear_model/base.py:LinearRegression.fit | filler_comment | 2 |
| scikit-learn/scikit-learn:sklearn/metrics/classification.py:_check_targets | filler_comment | 3 |
| scikit-learn/scikit-learn:sklearn/metrics/classification.py:_check_targets | nesting | 3 |
| scikit-learn/scikit-learn:sklearn/mixture/gmm.py:_log_multivariate_normal_density_full | nesting | 3 |
| scikit-learn/scikit-learn:sklearn/model_selection/_split.py:check_cv | filler_comment | 1 |
| scikit-learn/scikit-learn:sklearn/multioutput.py:MultiOutputRegressor.score | filler_comment | 2 |
| scikit-learn/scikit-learn:sklearn/neighbors/lof.py:LocalOutlierFactor._score_samples | filler_comment | 2 |
| scikit-learn/scikit-learn:sklearn/utils/_unittest_backport.py:TestCase.assertRaises | filler_comment | 1 |
| scikit-learn/scikit-learn:sklearn/utils/estimator_checks.py:check_estimators_dtypes | filler_comment | 1 |
| scikit-learn/scikit-learn:sklearn/utils/estimator_checks.py:check_estimators_dtypes | nesting | 3 |
| sphinx-doc/sphinx:sphinx/builders/xml.py:XMLBuilder.get_outdated_docs | filler_comment | 1 |
| sphinx-doc/sphinx:sphinx/builders/xml.py:XMLBuilder.get_outdated_docs | nesting | 3 |
| sphinx-doc/sphinx:sphinx/domains/c.py:ASTDeclaration.__init__ | filler_comment | 1 |
| sphinx-doc/sphinx:sphinx/domains/c.py:Symbol.__init__ | filler_comment | 2 |
| sphinx-doc/sphinx:sphinx/domains/cpp.py:ASTFunctionParameter.get_id | filler_comment | 1 |
| sphinx-doc/sphinx:sphinx/domains/cpp.py:CPPObject.run | filler_comment | 2 |
| sphinx-doc/sphinx:sphinx/domains/std.py:ProductionList.run | filler_comment | 2 |
| sphinx-doc/sphinx:sphinx/domains/std.py:ProductionList.run | nesting | 3 |
| sphinx-doc/sphinx:sphinx/ext/autodoc/mock.py:MockFinder.find_spec | filler_comment | 2 |
| sphinx-doc/sphinx:sphinx/ext/graphviz.py:ClickableMapDefinition.parse | filler_comment | 3 |
| sphinx-doc/sphinx:sphinx/ext/intersphinx.py:resolve_reference_detect_inventory | filler_comment | 2 |
| sphinx-doc/sphinx:sphinx/util/images.py:parse_data_uri | filler_comment | 2 |
| sympy/sympy:sympy/functions/combinatorial/numbers.py:genocchi._eval_is_negative | redundant_check | 3 |
| sympy/sympy:sympy/functions/special/elliptic_integrals.py:elliptic_pi.fdiff:nemotron:dead | redundant_check | 1 |
| sympy/sympy:sympy/functions/special/spherical_harmonics.py:Ynm.fdiff | filler_comment | 3 |
| sympy/sympy:sympy/geometry/entity.py:GeometryEntity.__new__ | filler_comment | 2 |
| sympy/sympy:sympy/integrals/risch.py:splitfactor | filler_comment | 1 |
| sympy/sympy:sympy/integrals/risch.py:splitfactor | redundant_check | 3 |
| sympy/sympy:sympy/ntheory/factor_.py:udivisors:transform:nesting | redundant_check | 2 |
| sympy/sympy:sympy/ntheory/generate.py:prevprime | filler_comment | 1 |
| sympy/sympy:sympy/plotting/intervalmath/interval_arithmetic.py:interval.__pow__ | filler_comment | 3 |
| sympy/sympy:sympy/plotting/intervalmath/interval_arithmetic.py:interval.__pow__ | redundant_check | 1 |
| sympy/sympy:sympy/polys/densebasic.py:dup_deflate | redundant_check | 1 |
| sympy/sympy:sympy/polys/densetools.py:_dup_decompose | nesting | 3 |
| sympy/sympy:sympy/polys/polytools.py:Poly.trunc:nemotron:swallowed_error | filler_comment | 2 |

## False negatives

| item | kind | runs |
| --- | --- | --- |
| astropy/astropy:astropy/cosmology/flrw.py:LambdaCDM._dS_comoving_distance_z1z2:nemotron:redundant_check | redundant_check | 3 |
| astropy/astropy:astropy/extern/configobj/configobj.py:ConfigObj._handle_comment:transform:redundant_check+filler_comment | redundant_check | 3 |
| astropy/astropy:astropy/io/fits/util.py:_words_group | filler_comment | 1 |
| astropy/astropy:astropy/modeling/powerlaws.py:ExponentialCutoffPowerLaw1D.fit_deriv:nemotron:redundant_check | redundant_check | 3 |
| astropy/astropy:astropy/utils/console.py:isatty:transform:redundant_check | redundant_check | 3 |
| django/django:django/contrib/gis/db/models/lookups.py:GISLookup.process_rhs | filler_comment | 1 |
| django/django:django/db/backends/mysql/base.py:DatabaseWrapper.check_constraints:nemotron:filler_comment | filler_comment | 2 |
| django/django:django/db/backends/postgresql/base.py:DatabaseWrapper.get_connection_params:transform:redundant_check | redundant_check | 1 |
| django/django:django/db/models/sql/query.py:Query.table_alias:transform:redundant_check | redundant_check | 1 |
| matplotlib/matplotlib:lib/matplotlib/offsetbox.py:AnchoredOffsetbox.draw:nemotron:nesting | redundant_check | 2 |
| matplotlib/matplotlib:lib/matplotlib/tri/triangulation.py:Triangulation.__init__:transform:redundant_check | redundant_check | 2 |
| psf/requests:requests/cookies.py:MockRequest.get_full_url | filler_comment | 1 |
| pydata/xarray:xarray/core/duck_array_ops.py:_create_nan_agg_method:nemotron:filler_comment | filler_comment | 2 |
| pylint-dev/pylint:pylint/checkers/base.py:BasicErrorChecker.visit_assign:transform:redundant_check | redundant_check | 2 |
| pylint-dev/pylint:pylint/checkers/classes/class_checker.py:_definition_equivalent_to_call:transform:redundant_check | redundant_check | 2 |
| pylint-dev/pylint:pylint/checkers/utils.py:safe_infer | redundant_check | 1 |
| scikit-learn/scikit-learn:sklearn/externals/funcsigs.py:formatannotation:transform:redundant_check | redundant_check | 3 |
| scikit-learn/scikit-learn:sklearn/mixture/gaussian_mixture.py:GaussianMixture._set_parameters | filler_comment | 2 |
| scikit-learn/scikit-learn:sklearn/model_selection/_split.py:check_cv:transform:redundant_check | redundant_check | 3 |
| sphinx-doc/sphinx:sphinx/domains/c.py:ASTDeclaratorNameParam.describe_signature:nemotron:redundant_check | redundant_check | 3 |
| sphinx-doc/sphinx:sphinx/ext/graphviz.py:ClickableMapDefinition.parse:nemotron:filler_comment | filler_comment | 1 |
| sphinx-doc/sphinx:sphinx/transforms/post_transforms/__init__.py:SphinxPostTransform.is_supported:transform:redundant_check+dead | redundant_check | 1 |
| sympy/sympy:sympy/physics/quantum/shor.py:shor:nemotron:filler_comment | filler_comment | 1 |
| sympy/sympy:sympy/polys/sqfreetools.py:dup_sqf_norm:transform:nesting+filler_comment | filler_comment | 1 |

## Unlabelled kinds

| item | kind | runs |
| --- | --- | --- |

## Errors

| item | error |
| --- | --- |
