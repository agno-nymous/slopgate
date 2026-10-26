# Injection check

A gate miss is not a defect: a valid item that the gate does not find stays in the recall.
A `from x import *` in the module turns the name check off for that module.

items 140, not scored 22, gate misses 12, new names not ok 0, invalid 7

The `new names` column finds only reads of names that nothing binds. It does not find other changes of behavior.

| item | kinds | accept | new names | kind | reason |
|---|---|---|---|---|---|
| sphinx-doc/sphinx:sphinx/util/images.py:parse_data_uri:transform:redundant_check | redundant_check | rejects | ok | transform |  |
| sphinx-doc/sphinx:sphinx/domains/c.py:ASTDeclaration.__init__:nemotron:nesting | nesting | rejects | ok | invalid | Every branch assigns `self.symbol: Symbol = None`, so the nested ifs are a duplicated branch that a reviewer deletes, no |
| matplotlib/matplotlib:lib/matplotlib/offsetbox.py:AnchoredOffsetbox.draw:nemotron:nesting | nesting | rejects | ok | valid | Depth 3: 'if not self.get_visible():' is the last statement of the function, its branch is only 'pass', and its else wra |
| sphinx-doc/sphinx:sphinx/domains/c.py:ASTDeclaratorNameParam.describe_signature:nemotron:redundant_check | redundant_check | rejects | ok | valid | Super changed `if self.param:` to `if self.param and self.param is not None:`; the truth test before `and` already guara |
| matplotlib/matplotlib:lib/matplotlib/projections/polar.py:PolarAxes._init_axis:nemotron:redundant_check | redundant_check | rejects | ok | invalid | Super added `if hasattr(self, 'xaxis') and self.xaxis is not None: pass`. No earlier check guarantees it. |
| pallets/flask:src/flask/sessions.py:SessionInterface.make_null_session:nemotron:redundant_check | redundant_check | rejects | ok | invalid | Super added `if hasattr(self, 'null_session_class'): pass`. No earlier check guarantees it. |
| astropy/astropy:astropy/coordinates/representation.py:PhysicsSphericalRepresentation.phi:nemotron:redundant_check | redundant_check | rejects | ok | invalid | Super added `if hasattr(self, '_phi'): pass`. No earlier check guarantees it. |
| astropy/astropy:astropy/modeling/powerlaws.py:ExponentialCutoffPowerLaw1D.fit_deriv:nemotron:redundant_check | redundant_check | rejects | ok | valid | Super added `if isinstance(amplitude, (int, float)) and amplitude is not None: pass`; the isinstance test before `and` a |
| astropy/astropy:astropy/coordinates/angle_formats.py:hours_to_hms:nemotron:redundant_check | redundant_check | rejects | ok | invalid | Super added `if abs(h - int(h)) < 1e-10: pass`. No earlier check guarantees it. |
| astropy/astropy:astropy/modeling/core.py:Model._supports_unit_fitting:nemotron:redundant_check | redundant_check | rejects | ok | invalid | Super added `if hasattr(self, '_parameter_units_for_data_units'): pass`. The same test comes after it, not before it. |
| astropy/astropy:astropy/cosmology/flrw.py:LambdaCDM._dS_comoving_distance_z1z2:nemotron:redundant_check | redundant_check | rejects | ok | valid | Super added `if z1.shape == z2.shape: pass` after the try block that raises ValueError when np.broadcast_arrays cannot g |
| sympy/sympy:sympy/integrals/risch.py:splitfactor:nemotron:redundant_check | redundant_check | rejects | ok | invalid | Super added `if hasattr(q_split := ..., '__len__') and len(q_split) >= 2: pass`. No earlier check guarantees it. |
| pylint-dev/pylint:pylint/checkers/variables.py:NamesConsumer._uncertain_nodes_in_try_blocks_when_evaluating_finally_blocks:transform:nesting | nesting | keeps | ok | transform |  |
| pylint-dev/pylint:pylint/checkers/exceptions.py:ExceptionsChecker.visit_raise:transform:nesting | nesting | keeps | ok | transform |  |
| sphinx-doc/sphinx:sphinx/builders/gettext.py:should_write:transform:nesting | nesting | keeps | ok | transform |  |
| sympy/sympy:sympy/ntheory/factor_.py:udivisors:transform:nesting | nesting | keeps | ok | transform |  |
| sympy/sympy:sympy/matrices/expressions/matexpr.py:ZeroMatrix.__pow__:transform:nesting | nesting | keeps | ok | transform |  |
| django/django:django/contrib/auth/backends.py:ModelBackend._get_permissions:transform:nesting | nesting | keeps | ok | transform |  |
| matplotlib/matplotlib:lib/matplotlib/axes/_base.py:_AxesBase.redraw_in_frame:transform:nesting | nesting | keeps | ok | transform |  |
| sympy/sympy:sympy/liealgebras/type_e.py:TypeE.roots:transform:nesting | nesting | keeps | ok | transform |  |
| django/django:django/db/models/base.py:Model.clean_fields:transform:nesting | nesting | keeps | ok | transform |  |
| sympy/sympy:sympy/polys/galoistools.py:gf_add:transform:nesting | nesting | keeps | ok | transform |  |
| astropy/astropy:astropy/units/quantity_helper/function_helpers.py:einsum:transform:nesting | nesting | keeps | ok | transform |  |
| sympy/sympy:sympy/plotting/intervalmath/interval_arithmetic.py:interval.__pow__:transform:nesting | nesting | keeps | ok | transform |  |
| sphinx-doc/sphinx:sphinx/domains/cpp.py:ASTFunctionParameter.get_id:transform:redundant_check | redundant_check | keeps | ok | transform |  |
| astropy/astropy:astropy/modeling/functional_models.py:Sersic2D.input_units:transform:redundant_check | redundant_check | keeps | ok | transform |  |
| astropy/astropy:astropy/config/configuration.py:ConfigNamespace.set_temp:transform:redundant_check | redundant_check | keeps | ok | transform |  |
| pylint-dev/pylint:pylint/checkers/classes/class_checker.py:_definition_equivalent_to_call:transform:redundant_check | redundant_check | keeps | ok | transform |  |
| django/django:django/db/models/sql/query.py:Query.table_alias:transform:redundant_check | redundant_check | keeps | ok | transform |  |
| scikit-learn/scikit-learn:sklearn/externals/funcsigs.py:formatannotation:transform:redundant_check | redundant_check | keeps | ok | transform |  |
| matplotlib/matplotlib:lib/matplotlib/tri/triangulation.py:Triangulation.__init__:transform:redundant_check | redundant_check | keeps | ok | transform |  |
| astropy/astropy:astropy/utils/console.py:isatty:transform:redundant_check | redundant_check | keeps | ok | transform |  |
| pylint-dev/pylint:pylint/checkers/base.py:BasicErrorChecker.visit_assign:transform:redundant_check | redundant_check | keeps | ok | transform |  |
| django/django:django/db/backends/postgresql/base.py:DatabaseWrapper.get_connection_params:transform:redundant_check | redundant_check | keeps | ok | transform |  |
| scikit-learn/scikit-learn:sklearn/model_selection/_split.py:check_cv:transform:redundant_check | redundant_check | keeps | ok | transform |  |
| psf/requests:requests/packages/chardet/chardetect.py:description_of:transform:swallowed_error | swallowed_error | keeps | ok | transform |  |
| pydata/xarray:xarray/core/resample.py:DatasetResample.__init__:transform:swallowed_error | swallowed_error | keeps | ok | transform |  |
| django/django:django/template/defaultfilters.py:make_list:transform:swallowed_error | swallowed_error | keeps | ok | transform |  |
| astropy/astropy:astropy/coordinates/baseframe.py:BaseCoordinateFrame._get_representation_info:transform:swallowed_error | swallowed_error | keeps | ok | transform |  |
| astropy/astropy:astropy/time/formats.py:TimeString.value:transform:swallowed_error | swallowed_error | keeps | ok | transform |  |
| sphinx-doc/sphinx:sphinx/domains/std.py:ProductionList.run:transform:swallowed_error | swallowed_error | keeps | ok | transform |  |
| django/django:django/contrib/gis/gdal/prototypes/errcheck.py:check_geom_offset:transform:swallowed_error | swallowed_error | keeps | ok | transform |  |
| matplotlib/matplotlib:lib/matplotlib/figure.py:Figure.set_size_inches:transform:swallowed_error | swallowed_error | keeps | ok | transform |  |
| sympy/sympy:sympy/calculus/util.py:AccumulationBounds.intersection:transform:swallowed_error | swallowed_error | keeps | ok | transform |  |
| django/django:django/db/models/sql/compiler.py:SQLCompiler.deferred_to_columns:transform:swallowed_error | swallowed_error | keeps | ok | transform |  |
| django/django:django/contrib/auth/admin.py:UserAdmin.get_form:transform:swallowed_error | swallowed_error | keeps | ok | transform |  |
| matplotlib/matplotlib:lib/matplotlib/ticker.py:LogFormatter.label_minor:transform:swallowed_error | swallowed_error | keeps | ok | transform |  |
| sympy/sympy:sympy/ntheory/generate.py:prevprime:transform:lookup_table | lookup_table | keeps | ok | transform |  |
| matplotlib/matplotlib:lib/matplotlib/axis.py:YAxis.get_ticks_position:transform:lookup_table | lookup_table | keeps | ok | transform |  |
| pydata/xarray:xarray/backends/locks.py:_get_lock_maker:transform:lookup_table | lookup_table | keeps | ok | transform |  |
| pylint-dev/pylint:pylint/checkers/base.py:NamingStyle.get_regex:transform:lookup_table | lookup_table | keeps | ok | transform |  |
| matplotlib/matplotlib:lib/matplotlib/axis.py:XAxis.get_ticks_position:transform:lookup_table | lookup_table | keeps | ok | transform |  |
| matplotlib/matplotlib:lib/matplotlib/font_manager.py:get_fontext_synonyms:transform:lookup_table | lookup_table | keeps | ok | transform |  |
| scikit-learn/scikit-learn:sklearn/linear_model/stochastic_gradient.py:BaseSGD._get_penalty_type:transform:lookup_table | lookup_table | keeps | ok | transform |  |
| sphinx-doc/sphinx:sphinx/util/jsdump.py:encode_string:transform:lookup_table | lookup_table | keeps | ok | transform |  |
| scikit-learn/scikit-learn:sklearn/linear_model/stochastic_gradient.py:BaseSGD._get_learning_rate_type:transform:lookup_table | lookup_table | keeps | ok | transform |  |
| django/django:django/forms/widgets.py:NullBooleanSelect.format_value:transform:lookup_table | lookup_table | keeps | ok | transform |  |
| pydata/xarray:xarray/coding/times.py:_netcdf_to_numpy_timeunit:transform:lookup_table | lookup_table | keeps | ok | transform |  |
| matplotlib/matplotlib:tutorials/intermediate/imshow_extent.py:index_to_coordinate:transform:lookup_table | lookup_table | keeps | ok | transform |  |
| sphinx-doc/sphinx:sphinx/ext/autodoc/__init__.py:MethodDocumenter.merge_default_value:transform:filler_comment | filler_comment | not scored | ok | transform |  |
| sympy/sympy:sympy/polys/compatibility.py:IPolys.gf_trace_map:transform:filler_comment | filler_comment | not scored | ok | transform |  |
| django/django:django/db/models/sql/query.py:Query.get_initial_alias:transform:filler_comment | filler_comment | not scored | ok | transform |  |
| scikit-learn/scikit-learn:sklearn/gaussian_process/kernels.py:_approx_fprime:transform:filler_comment | filler_comment | not scored | ok | transform |  |
| sympy/sympy:sympy/stats/frv.py:FiniteDensity.__call__:transform:filler_comment | filler_comment | not scored | ok | transform |  |
| django/django:django/core/management/utils.py:popen_wrapper:transform:filler_comment | filler_comment | not scored | ok | transform |  |
| sphinx-doc/sphinx:sphinx/util/i18n.py:search_image_for_language:transform:filler_comment | filler_comment | not scored | ok | transform |  |
| sphinx-doc/sphinx:sphinx/writers/text.py:TextTranslator.visit_raw:transform:filler_comment | filler_comment | not scored | ok | transform |  |
| mwaskom/seaborn:seaborn/rcmod.py:set_palette:transform:filler_comment | filler_comment | not scored | ok | transform |  |
| matplotlib/matplotlib:lib/matplotlib/axis.py:Tick.contains:transform:filler_comment | filler_comment | not scored | ok | transform |  |
| sympy/sympy:sympy/polys/solvers.py:eqs_to_matrix:transform:filler_comment | filler_comment | not scored | ok | transform |  |
| sphinx-doc/sphinx:sphinx/util/logging.py:ColorizeFormatter.format:transform:filler_comment | filler_comment | not scored | ok | transform |  |
| sympy/sympy:sympy/strategies/core.py:do_one:transform:dead | dead | keeps | ok | transform |  |
| django/django:django/db/models/sql/query.py:Query.set_extra_mask:transform:dead | dead | keeps | ok | transform |  |
| sphinx-doc/sphinx:sphinx/application.py:Sphinx.add_autodoc_attrgetter:transform:dead | dead | keeps | ok | transform |  |
| pylint-dev/pylint:pylint/lint/pylinter.py:PyLinter.add_ignored_message:transform:dead | dead | keeps | ok | transform |  |
| astropy/astropy:astropy/modeling/functional_models.py:Tangent1D.inverse:transform:dead | dead | keeps | ok | transform |  |
| matplotlib/matplotlib:lib/mpl_toolkits/axes_grid1/axes_size.py:MaxExtent.get_size:transform:dead | dead | keeps | ok | transform |  |
| sympy/sympy:sympy/holonomic/holonomicerrors.py:NotHyperSeriesError.__str__:transform:dead | dead | keeps | ok | transform |  |
| scikit-learn/scikit-learn:sklearn/mixture/base.py:BaseMixture._estimate_log_prob:transform:dead | dead | keeps | ok | transform |  |
| pydata/xarray:xarray/core/nanops.py:nanargmin:transform:dead | dead | keeps | ok | transform |  |
| pylint-dev/pylint:pylint/checkers/base.py:ComparisonChecker._check_logical_tautology:transform:dead | dead | keeps | ok | transform |  |
| django/django:django/utils/numberformat.py:format:transform:dead | dead | keeps | ok | transform |  |
| django/django:django/template/defaultfilters.py:rjust:transform:dead | dead | keeps | ok | transform |  |
| sympy/sympy:sympy/concrete/expr_with_limits.py:ExprWithLimits.free_symbols:transform:nesting+swallowed_error | nesting+swallowed_error | keeps | ok | transform |  |
| sympy/sympy:sympy/ntheory/generate.py:prevprime:transform:nesting+lookup_table | nesting+lookup_table | keeps | ok | transform |  |
| sympy/sympy:sympy/polys/sqfreetools.py:dup_sqf_norm:transform:nesting+filler_comment | nesting+filler_comment | keeps | ok | transform |  |
| sympy/sympy:sympy/polys/densebasic.py:dup_deflate:transform:nesting+dead | nesting+dead | keeps | ok | transform |  |
| sympy/sympy:sympy/integrals/rde.py:order_at_oo:transform:redundant_check+swallowed_error | redundant_check+swallowed_error | keeps | ok | transform |  |
| astropy/astropy:astropy/extern/configobj/configobj.py:ConfigObj._handle_comment:transform:redundant_check+filler_comment | redundant_check+filler_comment | keeps | ok | transform |  |
| sphinx-doc/sphinx:sphinx/transforms/post_transforms/__init__.py:SphinxPostTransform.is_supported:transform:redundant_check+dead | redundant_check+dead | keeps | ok | transform |  |
| matplotlib/matplotlib:lib/matplotlib/font_manager.py:get_fontext_synonyms:transform:swallowed_error+lookup_table | swallowed_error+lookup_table | keeps | ok | transform |  |
| django/django:django/db/models/fields/__init__.py:DecimalField.formfield:transform:swallowed_error+filler_comment | swallowed_error+filler_comment | keeps | ok | transform |  |
| matplotlib/matplotlib:lib/matplotlib/backend_tools.py:SetCursorBase.set_cursor:transform:swallowed_error+dead | swallowed_error+dead | keeps | ok | transform |  |
| pydata/xarray:xarray/backends/locks.py:_get_lock_maker:transform:lookup_table+filler_comment | lookup_table+filler_comment | keeps | ok | transform |  |
| pylint-dev/pylint:pylint/checkers/base.py:NamingStyle.get_regex:transform:lookup_table+dead | lookup_table+dead | keeps | ok | transform |  |
| matplotlib/matplotlib:lib/matplotlib/transforms.py:BboxTransformTo.get_matrix:nemotron:nesting | nesting | keeps | ok | valid | Depth 3: 'if DEBUG:' holds only 'if outw == 0 or outh == 0:' and its else is only 'pass', so the two conditions can join |
| astropy/astropy:astropy/coordinates/builtin_frames/galactic_transforms.py:fk5_to_gal:nemotron:nesting | nesting | keeps | ok | valid | Depth 4: the else of 'if pmats is not None:' ends with 'return matrix_product(mat1, mat2, mat3, None)', so that branch c |
| pylint-dev/pylint:pylint/checkers/variables.py:_is_type_checking_import:nemotron:nesting | nesting | keeps | ok | valid | nesting() > 2 finds the injected kind; accept() checks this. |
| matplotlib/matplotlib:lib/matplotlib/axes/_axes.py:Axes.semilogx:nemotron:nesting | nesting | keeps | ok | valid | Depth 3: "if k not in ['base', 'subs', 'nonpositive']:" holds only "if k not in ['basex', 'subsx', 'nonposx']:", and bot |
| pytest-dev/pytest:src/_pytest/warnings.py:pytest_collection:nemotron:nesting | nesting | keeps | ok | valid | Depth 3: 'if config is not None:' is the last statement of the function and wraps 'if hook is not None:', so it can beco |
| pytest-dev/pytest:src/_pytest/tmpdir.py:pytest_configure:nemotron:nesting | nesting | keeps | ok | valid | Depth 5: 'if config is not None:' holds only "if hasattr(config, 'add_cleanup'):", which holds only "if callable(getattr |
| matplotlib/matplotlib:lib/matplotlib/axes/_axes.py:Axes._convert_dx:nemotron:nesting | nesting | keeps | ok | valid | nesting() > 2 finds the injected kind; accept() checks this. |
| django/django:django/core/checks/model_checks.py:check_all_models:nemotron:nesting | nesting | keeps | ok | valid | Depth 3: 'if model._meta.managed:' holds only 'if not model._meta.proxy:', so the two conditions can join as 'if model._ |
| sphinx-doc/sphinx:sphinx/transforms/post_transforms/code.py:setup:nemotron:swallowed_error | swallowed_error | keeps | ok | valid | Ruff BLE001/E722/S110/S112 finds the injected kind; accept() checks this. |
| sympy/sympy:sympy/polys/densearith.py:dmp_expand:nemotron:swallowed_error | swallowed_error | keeps | ok | valid | Ruff BLE001/E722/S110/S112 finds the injected kind; accept() checks this. |
| astropy/astropy:astropy/coordinates/baseframe.py:BaseCoordinateFrame.realize_frame:nemotron:swallowed_error | swallowed_error | keeps | ok | valid | Ruff BLE001/E722/S110/S112 finds the injected kind; accept() checks this. |
| sympy/sympy:sympy/polys/polytools.py:Poly.trunc:nemotron:swallowed_error | swallowed_error | keeps | ok | valid | Ruff BLE001/E722/S110/S112 finds the injected kind; accept() checks this. |
| sympy/sympy:sympy/plotting/pygletplot/managed_window.py:ManagedWindow.__init__:nemotron:swallowed_error | swallowed_error | keeps | ok | valid | Ruff BLE001/E722/S110/S112 finds the injected kind; accept() checks this. |
| sympy/sympy:sympy/geometry/plane.py:Plane.p1:nemotron:swallowed_error | swallowed_error | keeps | ok | valid | Ruff BLE001/E722/S110/S112 finds the injected kind; accept() checks this. |
| django/django:django/templatetags/l10n.py:localize:nemotron:swallowed_error | swallowed_error | keeps | ok | valid | Ruff BLE001/E722/S110/S112 finds the injected kind; accept() checks this. |
| django/django:django/utils/autoreload.py:WatchmanReloader.watched_roots:nemotron:swallowed_error | swallowed_error | keeps | ok | valid | Ruff BLE001/E722/S110/S112 finds the injected kind; accept() checks this. |
| matplotlib/matplotlib:tools/gh_api.py:get_milestones:nemotron:swallowed_error | swallowed_error | keeps | ok | valid | Ruff BLE001/E722/S110/S112 finds the injected kind; accept() checks this. |
| pylint-dev/pylint:pylint/checkers/utils.py:safe_infer:nemotron:swallowed_error | swallowed_error | keeps | ok | valid | Ruff BLE001/E722/S110/S112 finds the injected kind; accept() checks this. |
| django/django:django/forms/widgets.py:NullBooleanSelect.format_value:nemotron:lookup_table | lookup_table | keeps | ok | valid | Ruff SIM116 finds the injected kind; accept() checks this. |
| sympy/sympy:sympy/ntheory/generate.py:prevprime:nemotron:lookup_table | lookup_table | keeps | ok | valid | Ruff SIM116 finds the injected kind; accept() checks this. |
| matplotlib/matplotlib:tutorials/intermediate/imshow_extent.py:index_to_coordinate:nemotron:lookup_table | lookup_table | keeps | ok | valid | Ruff SIM116 finds the injected kind; accept() checks this. Ticket 66: the chain returned None for an unknown index, but  |
| matplotlib/matplotlib:lib/matplotlib/axis.py:YAxis.get_ticks_position:nemotron:lookup_table | lookup_table | keeps | ok | valid | Ruff SIM116 finds the injected kind; accept() checks this. |
| matplotlib/matplotlib:lib/matplotlib/axis.py:XAxis.get_ticks_position:nemotron:lookup_table | lookup_table | keeps | ok | valid | Ruff SIM116 finds the injected kind; accept() checks this. |
| matplotlib/matplotlib:lib/matplotlib/font_manager.py:get_fontext_synonyms:nemotron:lookup_table | lookup_table | keeps | ok | valid | Ruff SIM116 finds the injected kind; accept() checks this. |
| pydata/xarray:xarray/coding/times.py:_netcdf_to_numpy_timeunit:nemotron:lookup_table | lookup_table | keeps | ok | valid | Ruff SIM116 finds the injected kind; accept() checks this. |
| matplotlib/matplotlib:lib/matplotlib/font_manager.py:findSystemFonts:nemotron:filler_comment | filler_comment | not scored | ok | valid | Super added comments such as `# This checks if fontpaths is None before proceeding` above `if fontpaths is None:`; they  |
| matplotlib/matplotlib:lib/matplotlib/backends/backend_pgf.py:PdfPages._run_latex:nemotron:filler_comment | filler_comment | not scored | ok | valid | Super added comments such as `# Create a temporary directory for processing` that repeat the line before them, not the n |
| sphinx-doc/sphinx:sphinx/ext/graphviz.py:ClickableMapDefinition.parse:nemotron:filler_comment | filler_comment | not scored | ok | valid | Super added `# This checks if the href pattern matches the current line` above `if self.href_re.search(line):` and one m |
| sympy/sympy:sympy/physics/quantum/shor.py:shor:nemotron:filler_comment | filler_comment | not scored | ok | valid | Super added comments such as `# Printing the value of N for debugging/tracing` above `print("N= ", N)`; they only repeat |
| scikit-learn/scikit-learn:sklearn/linear_model/base.py:LinearRegression.fit:nemotron:filler_comment | filler_comment | not scored | ok | valid | Super replaced the why comment with `# Rescale X and y using sample weights` above `X, y = _rescale_data(X, y, sample_we |
| django/django:django/db/backends/mysql/base.py:DatabaseWrapper.check_constraints:nemotron:filler_comment | filler_comment | not scored | ok | valid | Super added comments such as `# Getting table names from introspection when none provided` above `table_names = self.int |
| matplotlib/matplotlib:lib/matplotlib/backends/backend_gtk3agg.py:FigureCanvasGTK3Agg.blit:nemotron:filler_comment | filler_comment | not scored | ok | valid | Super added end-of-line comments such as `# Calculate width of the region to blit` on `width = int(bbox.x1) - int(bbox.x |
| pydata/xarray:xarray/core/dataarray.py:DataArray.thin:nemotron:filler_comment | filler_comment | not scored | ok | valid | Super added `# Convert this DataArray to a temporary dataset for thinning operation` above `ds = self._to_temp_dataset() |
| pydata/xarray:xarray/core/duck_array_ops.py:_create_nan_agg_method:nemotron:filler_comment | filler_comment | not scored | ok | valid | Super added comments such as `# Convert input to array using asarray` above `values = asarray(values)`; they only repeat |
| django/django:django/db/models/options.py:Options.get_parent_list:nemotron:filler_comment | filler_comment | not scored | ok | valid | Super added comments such as `# Adding each found ancestor to the result set` above `result.add(ancestor)`; they only re |
| matplotlib/matplotlib:lib/matplotlib/axes/_base.py:_AxesBase.get_navigate:nemotron:dead | dead | keeps | ok | valid | Ruff F841/RUF059 or vulture finds the injected kind; accept() checks this. |
| astropy/astropy:astropy/coordinates/angles.py:Angle.dms:nemotron:dead | dead | keeps | ok | valid | Ruff F841/RUF059 or vulture finds the injected kind; accept() checks this. |
| astropy/astropy:astropy/io/misc/asdf/tags/coordinates/representation.py:RepresentationType.assert_equal:nemotron:dead | dead | keeps | ok | valid | Ruff F841/RUF059 or vulture finds the injected kind; accept() checks this. |
| sympy/sympy:sympy/strategies/rl.py:rebuild:nemotron:dead | dead | keeps | ok | valid | Ruff F841/RUF059 or vulture finds the injected kind; accept() checks this. |
| sympy/sympy:sympy/functions/special/elliptic_integrals.py:elliptic_pi.fdiff:nemotron:dead | dead | keeps | ok | valid | Ruff F841/RUF059 or vulture finds the injected kind; accept() checks this. |
| sympy/sympy:sympy/matrices/densetools.py:trace:nemotron:dead | dead | keeps | ok | valid | Ruff F841/RUF059 or vulture finds the injected kind; accept() checks this. |
| django/django:django/template/smartif.py:TokenBase.led:nemotron:dead | dead | keeps | ok | valid | Ruff F841/RUF059 or vulture finds the injected kind; accept() checks this. |
| sympy/sympy:sympy/polys/ring_series.py:rs_cos_sin:nemotron:dead | dead | keeps | ok | valid | Ruff F841/RUF059 or vulture finds the injected kind; accept() checks this. |
| matplotlib/matplotlib:lib/matplotlib/afm.py:AFM.get_kern_dist_from_name:nemotron:dead | dead | keeps | ok | valid | Ruff F841/RUF059 or vulture finds the injected kind; accept() checks this. |
| matplotlib/matplotlib:lib/matplotlib/blocking_input.py:BlockingKeyMouseInput.post_event:nemotron:dead | dead | keeps | ok | valid | Ruff F841/RUF059 or vulture finds the injected kind; accept() checks this. |
