# SWE-bench benchmark with injected slop

## Run metadata

| field | report | groundtruth | runs |
| --- | --- | --- | --- |
| models | none | injection: nvidia/nemotron-3-super-120b-a12b | tests and rewrites: nvidia/nemotron-3-super-120b-a12b, retry and summary: nvidia/Nemotron-3-Ultra-550b-a55b |
| commit | 548ae7bcb1 (tree had changes) | 548ae7bcb1 (tree had changes) | 548ae7bcb1 (tree had changes) |
| date | 2026-10-18 | 2026-10-18 | 2026-10-18 |
| seeds | none | select 10 | none |
| counts |  | redundant_check 8, swallowed_error 7, dead 7, wrapper 8, nesting 7, duplicate 7, lookup_table 1 | instances 15 |
| cost (USD) | 0.6709 |  | 0.6677 |

| prompt | stage | hash |
| --- | --- | --- |
| AGENT_RULES | runs | `e080e3cbd1fb` |
| AGENT_TASK | runs | `d9ea2a7f8dc2` |
| DUPLICATE_PROMPT | groundtruth | `e05822b5889f` |
| HINT_TASK | runs | `17adffe7605d` |
| RETRY_PROMPT | runs | `7938a17985ab` |
| REWRITE_PROMPT | runs | `b45bcf6a7d69` |
| SAME_JOB_PROMPT | runs | `f7ca3b09a446` |


## Results

| kind | items | detected | accepted | silent_breaks | unmeasured | infrastructure_errors | rejected_for_behavior | recall | acceptance | acceptance_of_items | silent_break_rate | complexity_vs_injected | complexity_vs_original | nesting_vs_injected | nesting_vs_original | removed |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| nesting | 6 | 4 | 2 | 0 | 0 | 1 | 0 | 0.667 | 0.5 | 0.333 | 0.0 | 0 | 0 | -1.5 | 0 | 0 |
| redundant_check | 6 | 6 | 0 | 0 | 0 | 2 | 0 | 1.0 | 0.0 | 0.0 |  |  |  |  |  | 0 |
| swallowed_error | 4 | 4 | 0 | 0 | 0 | 3 | 1 | 1.0 | 0.0 | 0.0 |  |  |  |  |  | 0 |
| lookup_table | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 1.0 | 1.0 | 1.0 | 0.0 | -10 | 1 | 0 | 1 | 0 |
| dead | 3 | 3 | 2 | 0 | 0 | 4 | 0 | 1.0 | 0.667 | 0.667 | 0.0 | 0 | 0 | 0 | 0 | 0 |
| wrapper | 5 | 5 | 0 | 0 | 0 | 3 | 0 | 1.0 | 0.0 | 0.0 |  |  |  |  |  | 0 |
| duplicate | 5 | 3 | 2 | 0 | 0 | 2 | 0 | 0.6 | 0.667 | 0.4 | 0.0 |  |  |  |  | 2 |
| duplicate (exact) | 5 | 3 | 2 | 0 | 0 | 1 |  | 0.6 | 0.667 | 0.4 | 0.0 |  |  |  |  | 2 |
| duplicate (rewritten) | 0 | 0 | 0 | 0 | 0 | 1 |  |  |  |  |  |  |  |  |  | 0 |
| total | 30 | 26 | 7 | 0 | 0 | 15 | 1 | 0.867 | 0.269 | 0.233 | 0.0 | -2 | 0.2 | -0.6 | 0.2 | 2 |

## Tokens and cost

| model | use | input tokens | output tokens | USD |
| --- | --- | --- | --- | --- |
| nvidia/nemotron-3-super-120b-a12b | injection | 3378 | 2381 | 0.0032 |
| nvidia/nemotron-3-super-120b-a12b | gate | 1939146 | 91303 | 0.6639 |
| nvidia/Nemotron-3-Ultra-550b-a55b | gate | 1891 | 627 | 0.0038 |

Total USD: 0.6709. Mean seconds for each instance: 136.25, of which the gate: 134.54.
Injections dropped because the hidden tests cannot see a break: 2.

## Skipped instances

| instance | reason |
| --- | --- |

## Gate errors

| instance | errors |
| --- | --- |
| pytest-dev__pytest-5227 | his is an issue with the package mentioned above, not pip. hint: See above for details.  [notice] A new release of pip is available: 23.0.1 -> 26.2.1 [notice] To update, run: pip install --upgrade pip |
| pytest-dev__pytest-7220 | his is an issue with the package mentioned above, not pip. hint: See above for details.  [notice] A new release of pip is available: 23.0.1 -> 26.2.1 [notice] To update, run: pip install --upgrade pip |
| pytest-dev__pytest-7432 | his is an issue with the package mentioned above, not pip. hint: See above for details.  [notice] A new release of pip is available: 23.0.1 -> 26.2.1 [notice] To update, run: pip install --upgrade pip |
| pytest-dev__pytest-5692 | his is an issue with the package mentioned above, not pip. hint: See above for details.  [notice] A new release of pip is available: 23.0.1 -> 26.2.1 [notice] To update, run: pip install --upgrade pip |
| pytest-dev__pytest-8365 | his is an issue with the package mentioned above, not pip. hint: See above for details.  [notice] A new release of pip is available: 23.0.1 -> 26.2.1 [notice] To update, run: pip install --upgrade pip |

## Items

| item | detected | gate kinds | outcome | silent break | reason |
| --- | --- | --- | --- | --- | --- |
| pytest-dev__pytest-5227:src/_pytest/mark/evaluate.py:MarkEvaluator._istrue:nesting | True | nesting | no_environment |  |  boolean expression. Slopgate could not build the test environment, so it could not prove a rewrite and changed nothing. |
| pytest-dev__pytest-5227:src/_pytest/terminal.py:TerminalReporter._get_progress_information_message:redundant_check | True | redundant_check | no_environment |  |  the repeated check. Slopgate could not build the test environment, so it could not prove a rewrite and changed nothing. |
| pytest-dev__pytest-5227:src/_pytest/junitxml.py:pytest_unconfigure:swallowed_error | True | swallowed_error | no_environment |  | ive the same result. Slopgate could not build the test environment, so it could not prove a rewrite and changed nothing. |
| pytest-dev__pytest-7220:src/_pytest/config/__init__.py:PytestPluginManager._getconftestmodules:redundant_check | True | redundant_check | no_environment |  |  the repeated check. Slopgate could not build the test environment, so it could not prove a rewrite and changed nothing. |
| pytest-dev__pytest-7220:src/_pytest/runner.py:pytest_terminal_summary:swallowed_error | True | swallowed_error | no_environment |  | ive the same result. Slopgate could not build the test environment, so it could not prove a rewrite and changed nothing. |
| pytest-dev__pytest-7220:src/_pytest/capture.py:_get_multicapture:dead | True | dead | no_environment |  | iables. Remove them. Slopgate could not build the test environment, so it could not prove a rewrite and changed nothing. |
| pytest-dev__pytest-7432:src/_pytest/_code/code.py:TracebackEntry.getsource:dead | True | dead | no_environment |  | iables. Remove them. Slopgate could not build the test environment, so it could not prove a rewrite and changed nothing. |
| pytest-dev__pytest-7432:src/_pytest/compat.py:_iscoroutinefunction_impl:wrapper | True | wrapper | no_environment |  | o its single caller. Slopgate could not build the test environment, so it could not prove a rewrite and changed nothing. |
| pytest-dev__pytest-7432:src/_pytest/main.py:wrap_session_alt:duplicate | True | duplicate | no_environment |  | py. Call it instead. Slopgate could not build the test environment, so it could not prove a rewrite and changed nothing. |
| pytest-dev__pytest-5692:src/_pytest/terminal.py:MoreQuietAction.__init__:dead | True | dead | no_environment |  | iables. Remove them. Slopgate could not build the test environment, so it could not prove a rewrite and changed nothing. |
| pytest-dev__pytest-5692:src/_pytest/skipping.py:_check_xfail_no_run_impl:wrapper | True | wrapper | no_environment |  | o its single caller. Slopgate could not build the test environment, so it could not prove a rewrite and changed nothing. |
| pytest-dev__pytest-5692:src/_pytest/pathlib.py:register_cleanup_lock_removal_alt:duplicate | True | duplicate | no_environment |  | py. Call it instead. Slopgate could not build the test environment, so it could not prove a rewrite and changed nothing. |
| pytest-dev__pytest-8365:src/_pytest/main.py:pytest_runtestloop:swallowed_error | True | swallowed_error | no_environment |  | ive the same result. Slopgate could not build the test environment, so it could not prove a rewrite and changed nothing. |
| pytest-dev__pytest-8365:src/_pytest/assertion/rewrite.py:rewrite_asserts:dead | True | dead | no_environment |  | iables. Remove them. Slopgate could not build the test environment, so it could not prove a rewrite and changed nothing. |
| pytest-dev__pytest-8365:src/_pytest/compat.py:_get_real_func_impl:wrapper | True | wrapper | no_environment |  | o its single caller. Slopgate could not build the test environment, so it could not prove a rewrite and changed nothing. |
| pallets__flask-4992:src/flask/app.py:Flask.auto_find_instance_path:dead | True | dead | followup |  | write of `Flask.auto_find_instance_path`. nesting 1 -> 1, complexity 2 -> 2. 3 characterization tests passed in sandbox. |
| pallets__flask-4992:src/flask/scaffold.py:_path_is_relative_to_impl:wrapper | True | wrapper | rejected |  | Assertio... FAILED tests/test_slopgate_2.py::test_find_package_virtualenv_other - Asserti... 3 failed, 2 passed in 0.09s |
| pallets__flask-4992:src/flask/config.py:Config.get_namespace:nesting | True | nesting | followup |  | ting`) rewrite of `Config.get_namespace`. nesting 3 -> 2, complexity 5 -> 5. 9 characterization tests passed in sandbox. |
| psf__requests-3362:requests/packages/urllib3/util/retry.py:Retry._is_read_error:dead | True | dead | rejected |  | cs.io/en/7.16.2/messages.html#warning-no-data-collected   self._warn("No data was collected.", slug="no-data-collected") |
| psf__requests-3362:requests/utils.py:_unquote_unreserved_impl:wrapper | True | wrapper | rejected |  | cs.io/en/7.16.2/messages.html#warning-no-data-collected   self._warn("No data was collected.", slug="no-data-collected") |
| psf__requests-3362:requests/api.py:request_alt:duplicate | True | duplicate | rejected |  | py", line 392, in import_plugin     raise new_exc ImportError: Error importing plugin "main": No module named 'UserDict' |
| pallets__flask-5063:src/flask/cli.py:_find_best_app_impl:wrapper | True | wrapper | rejected |  | nd_best_app FAILED tests/test_slopgate_0.py::test_locate_app_no_exception_path - Attribut... 2 failed, 4 passed in 0.19s |
| pallets__flask-5063:src/flask/scaffold.py:_path_is_relative_to_alt:duplicate | True | duplicate | followup |  | `_path_is_relative_to_alt` does the same job as `_path_is_relative_to` in src/flask/scaffold.py (exact structural copy). |
| pallets__flask-5063:src/flask/ctx.py:AppContext.pop:nesting | False |  | missed |  |  |
| sphinx-doc__sphinx-8627:sphinx/util/matching.py:_translate_pattern_impl:wrapper | True | wrapper | rejected |  | cs.io/en/7.16.2/messages.html#warning-no-data-collected   self._warn("No data was collected.", slug="no-data-collected") |
| sphinx-doc__sphinx-8627:sphinx/util/typing.py:_stringify_py37_alt:duplicate | False | nesting | missed |  |  |
| sphinx-doc__sphinx-8627:sphinx/locale/__init__.py:_TranslationProxy.__new__:redundant_check | True | redundant_check | rejected |  | cs.io/en/7.16.2/messages.html#warning-no-data-collected   self._warn("No data was collected.", slug="no-data-collected") |
| sphinx-doc__sphinx-7975:sphinx/registry.py:SphinxComponentRegistry.load_extension:nesting | True | nesting | rejected |  | cs.io/en/7.16.2/messages.html#warning-no-data-collected   self._warn("No data was collected.", slug="no-data-collected") |
| sphinx-doc__sphinx-7975:sphinx/util/nodes.py:apply_source_workaround:redundant_check | True | redundant_check | rejected |  | cs.io/en/7.16.2/messages.html#warning-no-data-collected   self._warn("No data was collected.", slug="no-data-collected") |
| sphinx-doc__sphinx-7975:sphinx/transforms/__init__.py:SphinxSmartQuotes.apply:swallowed_error | True | swallowed_error | rejected |  | cs.io/en/7.16.2/messages.html#warning-no-data-collected   self._warn("No data was collected.", slug="no-data-collected") |
| sphinx-doc__sphinx-8506:sphinx/config.py:eval_config_file_alt:duplicate | False |  | missed |  |  |
| sphinx-doc__sphinx-8506:sphinx/environment/collectors/asset.py:DownloadFileCollector.process_doc:nesting | False |  | missed |  |  |
| sphinx-doc__sphinx-8506:sphinx/deprecation.py:_ModuleWrapper.__getattr__:redundant_check | True | redundant_check | rejected |  | cs.io/en/7.16.2/messages.html#warning-no-data-collected   self._warn("No data was collected.", slug="no-data-collected") |
| pylint-dev__pylint-5859:pylint/reporters/reports_handler_mix_in.py:ReportsHandlerMixIn.register_report:swallowed_error | True | swallowed_error | rejected |  | rewrite leaves the slop: swallowed_error |
| pylint-dev__pylint-5859:pylint/message/message_definition_store.py:MessageDefinitionStore.register_message:dead | True | dead | followup |  | MessageDefinitionStore.register_message`. nesting 0 -> 0, complexity 1 -> 1. 2 characterization tests passed in sandbox. |
| pylint-dev__pylint-5859:pylint/config/find_default_config_files.py:_find_default_config_files_impl:wrapper | True | wrapper | rejected |  | ns_none_when_no_match FAILED tests/test_slopgate_0.py::test_find_pylintrc_handles_empty_iterator - ... 3 failed in 0.33s |
| pydata__xarray-4248:xarray/core/ops.py:inject_binary_ops_alt:duplicate | True | duplicate | followup |  | `inject_binary_ops_alt` does the same job as `inject_binary_ops` in xarray/core/ops.py (exact structural copy). |
| pydata__xarray-4248:xarray/core/variable.py:Variable._inplace_binary_op:nesting | True | nesting | rejected |  | rule: adds a class |
| pydata__xarray-4248:xarray/core/merge.py:_get_priority_vars_and_indexes:redundant_check | True | redundant_check | rejected |  | step limit: characterization tests miss branches: 1 |
| pylint-dev__pylint-7993:pylint/message/message_id_store.py:MessageIdStore.check_msgid_and_symbol:redundant_check | True | nesting, redundant_check | rejected |  | step limit: characterization tests miss branches: 1 |
| pylint-dev__pylint-7993:pylint/config/_pylint_config/utils.py:should_retry_after_invalid_input:swallowed_error | True | swallowed_error | rejected |  | before_exit FAILED tests/test_slopgate_1.py::test_decorator_called_once_flag_logic - asse... 3 failed, 5 passed in 0.11s |
| pylint-dev__pylint-7993:pylint/checkers/base/name_checker/naming_style.py:NamingStyle.get_regex:lookup_table | True | lookup_table | followup |  | e`) rewrite of `NamingStyle.get_regex`. nesting 1 -> 1, complexity 12 -> 2. 14 characterization tests passed in sandbox. |
| mwaskom__seaborn-3190:seaborn/_core/scales.py:Continuous.tick:nesting | True | nesting | followup |  | (`nesting`) rewrite of `Continuous.tick`. nesting 4 -> 2, complexity 8 -> 8. 9 characterization tests passed in sandbox. |
| mwaskom__seaborn-3190:seaborn/palettes.py:_parse_cubehelix_args:redundant_check | True | redundant_check | rejected |  | step limit: characterization tests miss branches: 1 |
| mwaskom__seaborn-3190:seaborn/_core/properties.py:ObjectProperty.get_mapping:swallowed_error | True | swallowed_error | rejected |  | =========== FAILED tests/test_slopgate_0.py::test_get_mapping_asarray_exception - assert ... 1 failed, 9 passed in 1.30s |
