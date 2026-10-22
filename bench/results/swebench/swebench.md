# SWE-bench benchmark with injected slop

## Run metadata

| field | report | groundtruth | runs |
| --- | --- | --- | --- |
| models | none | injection: nvidia/nemotron-3-super-120b-a12b | tests and rewrites: nvidia/nemotron-3-super-120b-a12b, retry and summary: nvidia/Nemotron-3-Ultra-550b-a55b |
| commit | 1890fa62d2 (tree had changes) | 548ae7bcb1 (tree had changes) | 1890fa62d2 (tree had changes) |
| date | 2026-10-21 | 2026-10-18 | 2026-10-21 |
| seeds | none | select 10 | none |
| counts |  | redundant_check 8, swallowed_error 7, dead 7, wrapper 8, nesting 7, duplicate 7, lookup_table 1 | instances 15 |
| cost (USD) | 0.7918 |  | 0.7888 |

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
| nesting | 7 | 5 | 3 | 0 | 0 | 0 | 0 | 0.714 | 0.6 | 0.429 | 0.0 | 0 | 0 | -1.67 | -0.33 | 0 |
| redundant_check | 8 | 8 | 0 | 0 | 0 | 0 | 0 | 1.0 | 0.0 | 0.0 |  |  |  |  |  | 0 |
| swallowed_error | 7 | 7 | 0 | 0 | 0 | 0 | 1 | 1.0 | 0.0 | 0.0 |  |  |  |  |  | 0 |
| lookup_table | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 1.0 | 1.0 | 1.0 | 0.0 | -10 | 1 | 0 | 1 | 0 |
| dead | 6 | 6 | 4 | 0 | 0 | 1 | 0 | 1.0 | 0.667 | 0.667 | 0.0 | 0 | 0 | 0 | 0 | 0 |
| wrapper | 7 | 7 | 2 | 0 | 0 | 1 | 0 | 1.0 | 0.286 | 0.286 | 0.0 |  |  |  |  | 2 |
| duplicate | 6 | 4 | 3 | 0 | 0 | 1 | 0 | 0.667 | 0.75 | 0.5 | 0.0 |  |  |  |  | 3 |
| duplicate (exact) | 5 | 3 | 2 | 0 | 0 | 1 |  | 0.6 | 0.667 | 0.4 | 0.0 |  |  |  |  | 2 |
| duplicate (rewritten) | 1 | 1 | 1 | 0 | 0 | 0 |  | 1.0 | 1.0 | 1.0 | 0.0 |  |  |  |  | 1 |
| total | 42 | 38 | 13 | 0 | 0 | 3 | 1 | 0.905 | 0.342 | 0.31 | 0.0 | -1.25 | 0.12 | -0.62 | 0 | 5 |

## Tokens and cost

| model | use | input tokens | output tokens | USD |
| --- | --- | --- | --- | --- |
| nvidia/nemotron-3-super-120b-a12b | injection | 3378 | 2381 | 0.0032 |
| nvidia/nemotron-3-super-120b-a12b | gate | 2270502 | 113722 | 0.7835 |
| nvidia/Nemotron-3-Ultra-550b-a55b | gate | 3051 | 680 | 0.0051 |

Total USD: 0.7918. Mean seconds for each instance: 233.39, of which the gate: 229.73.
Injections dropped because the hidden tests cannot see a break: 2.

## Skipped instances

| instance | reason |
| --- | --- |

## Gate errors

| instance | errors |
| --- | --- |
| psf__requests-3362 |  https://coverage.readthedocs.io usage: pytest.py [options] [file_or_dir] [file_or_dir] [...] pytest.py: error: unrecognized arguments: --continue-on-collection-errors   inifile: None   rootdir: /repo |

## Items

| item | detected | gate kinds | outcome | silent break | reason |
| --- | --- | --- | --- | --- | --- |
| pallets__flask-4992:src/flask/app.py:Flask.auto_find_instance_path:dead | True | dead | followup |  | write of `Flask.auto_find_instance_path`. nesting 1 -> 1, complexity 2 -> 2. 2 characterization tests passed in sandbox. |
| pallets__flask-4992:src/flask/scaffold.py:_path_is_relative_to_impl:wrapper | True | wrapper | rejected |  | x_lib_python FAILED tests/test_slopgate_2.py::test_installed_to_virtualenv_sitepackages_root 3 failed, 2 passed in 0.08s |
| pallets__flask-4992:src/flask/config.py:Config.get_namespace:nesting | True | nesting | followup |  | ting`) rewrite of `Config.get_namespace`. nesting 3 -> 2, complexity 5 -> 5. 8 characterization tests passed in sandbox. |
| sphinx-doc__sphinx-8627:sphinx/util/matching.py:_translate_pattern_impl:wrapper | True | wrapper | followup |  | ned into its single caller `compile_matchers` in sphinx/util/matching.py. 3 characterization tests of the caller passed. |
| sphinx-doc__sphinx-8627:sphinx/util/typing.py:_stringify_py37_alt:duplicate | False | nesting | missed |  |  |
| sphinx-doc__sphinx-8627:sphinx/locale/__init__.py:_TranslationProxy.__new__:redundant_check | True | redundant_check | rejected |  | step limit: characterization tests miss branches: 1 |
| sphinx-doc__sphinx-7975:sphinx/registry.py:SphinxComponentRegistry.load_extension:nesting | True | nesting | followup |  | `SphinxComponentRegistry.load_extension`. nesting 5 -> 3, complexity 8 -> 8. 8 characterization tests passed in sandbox. |
| sphinx-doc__sphinx-7975:sphinx/util/nodes.py:apply_source_workaround:redundant_check | True | redundant_check | rejected |  | time limit: characterization tests miss branches: 2 |
| sphinx-doc__sphinx-7975:sphinx/transforms/__init__.py:SphinxSmartQuotes.apply:swallowed_error | True | swallowed_error | rejected |  | rewrite makes no change |
| pytest-dev__pytest-5227:src/_pytest/mark/evaluate.py:MarkEvaluator._istrue:nesting | True | nesting | followup |  | g`) rewrite of `MarkEvaluator._istrue`. nesting 6 -> 4, complexity 10 -> 10. 9 characterization tests passed in sandbox. |
| pytest-dev__pytest-5227:src/_pytest/terminal.py:TerminalReporter._get_progress_information_message:redundant_check | True | redundant_check | rejected |  | token limit: characterization tests miss branches: 1 |
| pytest-dev__pytest-5227:src/_pytest/junitxml.py:pytest_unconfigure:swallowed_error | True | swallowed_error | rejected |  | rewrite leaves the slop: swallowed_error |
| sphinx-doc__sphinx-8506:sphinx/config.py:eval_config_file_alt:duplicate | False |  | missed |  |  |
| sphinx-doc__sphinx-8506:sphinx/environment/collectors/asset.py:DownloadFileCollector.process_doc:nesting | False |  | missed |  |  |
| sphinx-doc__sphinx-8506:sphinx/deprecation.py:_ModuleWrapper.__getattr__:redundant_check | True | redundant_check | rejected |  | step limit: characterization tests miss branches: 1 |
| psf__requests-3362:requests/packages/urllib3/util/retry.py:Retry._is_read_error:dead | True | dead | no_environment |  | iables. Remove them. Slopgate could not build the test environment, so it could not prove a rewrite and changed nothing. |
| psf__requests-3362:requests/utils.py:_unquote_unreserved_impl:wrapper | True | wrapper | no_environment |  | o its single caller. Slopgate could not build the test environment, so it could not prove a rewrite and changed nothing. |
| psf__requests-3362:requests/api.py:request_alt:duplicate | True | duplicate | no_environment |  | py. Call it instead. Slopgate could not build the test environment, so it could not prove a rewrite and changed nothing. |
| pytest-dev__pytest-8365:src/_pytest/main.py:pytest_runtestloop:swallowed_error | True | swallowed_error | rejected |  | rewrite leaves the slop: swallowed_error |
| pytest-dev__pytest-8365:src/_pytest/assertion/rewrite.py:rewrite_asserts:dead | True | dead | followup |  | te (`dead`) rewrite of `rewrite_asserts`. nesting 0 -> 0, complexity 1 -> 1. 1 characterization tests passed in sandbox. |
| pytest-dev__pytest-8365:src/_pytest/compat.py:_get_real_func_impl:wrapper | True | wrapper | rejected |  | =========== FAILED tests/test_slopgate_1.py::test_method_get_not_callable - TypeError: 'i... 1 failed, 4 passed in 0.03s |
| pallets__flask-5063:src/flask/cli.py:_find_best_app_impl:wrapper | True | wrapper | rejected |  | =========== FAILED tests/test_slopgate_0.py::test_locate_app_success_no_app_name - Attrib... 1 failed, 4 passed in 0.12s |
| pallets__flask-5063:src/flask/scaffold.py:_path_is_relative_to_alt:duplicate | True | duplicate | followup |  | `_path_is_relative_to_alt` does the same job as `_path_is_relative_to` in src/flask/scaffold.py (exact structural copy). |
| pallets__flask-5063:src/flask/ctx.py:AppContext.pop:nesting | False |  | missed |  |  |
| pytest-dev__pytest-7432:src/_pytest/_code/code.py:TracebackEntry.getsource:dead | True | dead | rejected |  | r - AttributeError... FAILED tests/test_slopgate_0.py::test_getsource_astcache_key_none - Attribute... 5 failed in 0.14s |
| pytest-dev__pytest-7432:src/_pytest/compat.py:_iscoroutinefunction_impl:wrapper | True | wrapper | rejected |  | sts/test_slopgate_1.py !!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!! 1 error in 0.07s |
| pytest-dev__pytest-7432:src/_pytest/main.py:wrap_session_alt:duplicate | True | duplicate | rejected |  | OR testing/python/metafunc.py 92 failed, 2431 passed, 118 skipped, 9 xfailed, 23 warnings, 2 errors in 111.44s (0:01:51) |
| pytest-dev__pytest-7220:src/_pytest/config/__init__.py:PytestPluginManager._getconftestmodules:redundant_check | True | redundant_check | rejected |  |  you need more quota, you can request it at https://tokenfactory.nebius.com'}"): characterization tests miss branches: 1 |
| pytest-dev__pytest-7220:src/_pytest/runner.py:pytest_terminal_summary:swallowed_error | True | swallowed_error | rejected |  | rewrite leaves the slop: swallowed_error |
| pytest-dev__pytest-7220:src/_pytest/capture.py:_get_multicapture:dead | True | dead | rejected |  | eError: ... FAILED tests/test_slopgate_0.py::test_get_multicapture_tee_sys - AttributeErr... 3 failed, 2 passed in 0.05s |
| mwaskom__seaborn-3190:seaborn/_core/scales.py:Continuous.tick:nesting | True | nesting | rejected |  | _different_instance ERROR tests/test_slopgate_1.py::TestContinuousTick::test_tick_all_none_parameters 18 errors in 1.38s |
| mwaskom__seaborn-3190:seaborn/palettes.py:_parse_cubehelix_args:redundant_check | True | redundant_check | rejected |  | time limit: characterization tests miss branches: 1 |
| mwaskom__seaborn-3190:seaborn/_core/properties.py:ObjectProperty.get_mapping:swallowed_error | True | swallowed_error | rejected |  |  FAILED tests/test_slopgate_0.py::test_get_mapping_non_finite_handling - Value... 2 failed, 6 passed, 1 warning in 1.34s |
| pydata__xarray-4248:xarray/core/ops.py:inject_binary_ops_alt:duplicate | True | duplicate | followup |  | `inject_binary_ops_alt` does the same job as `inject_binary_ops` in xarray/core/ops.py (exact structural copy). |
| pydata__xarray-4248:xarray/core/variable.py:Variable._inplace_binary_op:nesting | True | nesting | rejected |  | rule: adds a class |
| pydata__xarray-4248:xarray/core/merge.py:_get_priority_vars_and_indexes:redundant_check | True | redundant_check | rejected |  | time limit: characterization tests miss branches: 1 |
| pylint-dev__pylint-5859:pylint/reporters/reports_handler_mix_in.py:ReportsHandlerMixIn.register_report:swallowed_error | True | swallowed_error | rejected |  | =========== FAILED tests/test_slopgate_2.py::test_report_is_enabled - AssertionError: ass... 1 failed, 7 passed in 0.06s |
| pylint-dev__pylint-5859:pylint/message/message_definition_store.py:MessageDefinitionStore.register_message:dead | True | dead | followup |  | MessageDefinitionStore.register_message`. nesting 0 -> 0, complexity 1 -> 1. 1 characterization tests passed in sandbox. |
| pylint-dev__pylint-5859:pylint/config/find_default_config_files.py:_find_default_config_files_impl:wrapper | True | wrapper | followup |  | gle caller `find_pylintrc` in pylint/config/find_default_config_files.py. 4 characterization tests of the caller passed. |
| pytest-dev__pytest-5692:src/_pytest/terminal.py:MoreQuietAction.__init__:dead | True | dead | followup |  | `) rewrite of `MoreQuietAction.__init__`. nesting 0 -> 0, complexity 1 -> 1. 3 characterization tests passed in sandbox. |
| pytest-dev__pytest-5692:src/_pytest/skipping.py:_check_xfail_no_run_impl:wrapper | True | wrapper | rejected |  | ============== FAILED tests/test_slopgate_1.py::test_pytest_runtest_setup_branches - Attribu... 1 failed in 0.04 seconds |
| pytest-dev__pytest-5692:src/_pytest/pathlib.py:register_cleanup_lock_removal_alt:duplicate | True | duplicate | followup |  | r_cleanup_lock_removal_alt` does the same job as `register_cleanup_lock_removal` in src/_pytest/pathlib.py (score 0.59). |
| pylint-dev__pylint-7993:pylint/message/message_id_store.py:MessageIdStore.check_msgid_and_symbol:redundant_check | True | nesting, redundant_check | rejected |  | time limit: characterization tests miss branches: 1 |
| pylint-dev__pylint-7993:pylint/config/_pylint_config/utils.py:should_retry_after_invalid_input:swallowed_error | True | swallowed_error | rejected |  | time limit: characterization tests fail on original: ..Killed |
| pylint-dev__pylint-7993:pylint/checkers/base/name_checker/naming_style.py:NamingStyle.get_regex:lookup_table | True | lookup_table | followup |  | e`) rewrite of `NamingStyle.get_regex`. nesting 1 -> 1, complexity 12 -> 2. 13 characterization tests passed in sandbox. |
