# SWE-bench benchmark with injected slop

## Run metadata

| field | report | groundtruth | runs |
| --- | --- | --- | --- |
| models | none | injection: nvidia/nemotron-3-super-120b-a12b | tests and rewrites: nvidia/Nemotron-3.5-Super-VL, retry and summary: nvidia/Nemotron-3-Ultra-550b-a55b |
| commit | 865b1713a5 (tree had changes) | 548ae7bcb1 (tree had changes) | 865b1713a5 (tree had changes) |
| date | 2026-10-30 | 2026-10-18 | 2026-10-30 |
| seeds | none | select 10 | none |
| counts |  | redundant_check 9, swallowed_error 8, dead 6, wrapper 7, nesting 8, duplicate 6, lookup_table 1 | instances 15 |
| cost (USD) | 0.8216 |  | 0.8191 |

| prompt | stage | hash |
| --- | --- | --- |
| AGENT_RULES | runs | `e080e3cbd1fb` |
| AGENT_TASK | runs | `3a947e7f3a27` |
| DUPLICATE_PROMPT | groundtruth | `e05822b5889f` |
| HINT_TASK | runs | `17adffe7605d` |
| RETRY_PROMPT | runs | `7938a17985ab` |
| REWRITE_PROMPT | runs | `b45bcf6a7d69` |
| SAME_JOB_PROMPT | runs | `f7ca3b09a446` |


## Results

| kind | items | detected | accepted | silent_breaks | unmeasured | infrastructure_errors | rejected_for_behavior | recall | acceptance | acceptance_of_items | silent_break_rate | complexity_vs_injected | complexity_vs_original | nesting_vs_injected | nesting_vs_original | removed |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| nesting | 8 | 6 | 4 | 0 | 0 | 0 | 0 | 0.75 | 0.667 | 0.5 | 0.0 | 0.75 | 0.75 | -1.75 | 0 | 0 |
| redundant_check | 9 | 9 | 0 | 0 | 0 | 0 | 0 | 1.0 | 0.0 | 0.0 |  |  |  |  |  | 0 |
| swallowed_error | 8 | 8 | 4 | 0 | 0 | 0 | 1 | 1.0 | 0.5 | 0.5 | 0.0 | 0.25 | 1.25 | -0.25 | 0.75 | 0 |
| lookup_table | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 1.0 | 1.0 | 1.0 | 0.0 | -11 | 0 | -1 | 0 | 0 |
| dead | 6 | 6 | 5 | 0 | 0 | 0 | 0 | 1.0 | 0.833 | 0.833 | 0.0 | 0 | 0 | 0 | 0 | 0 |
| wrapper | 7 | 7 | 3 | 0 | 0 | 0 | 0 | 1.0 | 0.429 | 0.429 | 0.0 |  |  |  |  | 3 |
| duplicate | 6 | 4 | 3 | 0 | 0 | 0 | 0 | 0.667 | 0.75 | 0.5 | 0.0 |  |  |  |  | 3 |
| duplicate (exact) | 5 | 3 | 2 | 0 | 0 | 0 |  | 0.6 | 0.667 | 0.4 | 0.0 |  |  |  |  | 2 |
| duplicate (rewritten) | 1 | 1 | 1 | 0 | 0 | 0 |  | 1.0 | 1.0 | 1.0 | 0.0 |  |  |  |  | 1 |
| total | 45 | 41 | 20 | 0 | 0 | 0 | 1 | 0.911 | 0.488 | 0.444 | 0.0 | -0.5 | 0.57 | -0.64 | 0.21 | 6 |

## Tokens and cost

| model | use | input tokens | output tokens | USD |
| --- | --- | --- | --- | --- |
| nvidia/nemotron-3-super-120b-a12b | injection | 2622 | 1708 | 0.0023 |
| nvidia/Nemotron-3.5-Super-VL | gate | 2296334 | 136201 | 0.8115 |
| nvidia/Nemotron-3-Ultra-550b-a55b | gate | 4153 | 1210 | 0.0078 |

Total USD: 0.8216. Mean seconds for each instance: 239.41, of which the gate: 225.45.
Injections dropped because the hidden tests cannot see a break: 2.

## Skipped instances

| instance | reason |
| --- | --- |

## Gate errors

| instance | errors |
| --- | --- |

## Items

| item | detected | gate kinds | outcome | silent break | reason |
| --- | --- | --- | --- | --- | --- |
| sphinx-doc__sphinx-8627:sphinx/util/matching.py:_translate_pattern_impl:wrapper | True | wrapper | followup |  | ned into its single caller `compile_matchers` in sphinx/util/matching.py. 3 characterization tests of the caller passed. |
| sphinx-doc__sphinx-8627:sphinx/util/typing.py:_stringify_py37_alt:duplicate | False | nesting | missed |  |  |
| sphinx-doc__sphinx-8627:sphinx/locale/__init__.py:_TranslationProxy.__new__:redundant_check | True | redundant_check | rejected |  | characterization tests miss branches: 1 |
| pallets__flask-4992:src/flask/app.py:Flask.auto_find_instance_path:dead | True | dead | followup |  | write of `Flask.auto_find_instance_path`. nesting 1 -> 1, complexity 2 -> 2. 2 characterization tests passed in sandbox. |
| pallets__flask-4992:src/flask/scaffold.py:_path_is_relative_to_impl:wrapper | True | wrapper | rejected |  | me_parent_greater_than_lib FAILED tests/test_slopgate_2.py::TestFindPackage::test_folder_less_than_lib 8 failed in 0.66s |
| pallets__flask-4992:src/flask/config.py:Config.get_namespace:nesting | True | nesting | followup |  | ting`) rewrite of `Config.get_namespace`. nesting 3 -> 2, complexity 5 -> 5. 7 characterization tests passed in sandbox. |
| sphinx-doc__sphinx-7975:sphinx/registry.py:SphinxComponentRegistry.load_extension:nesting | True | nesting | followup |  | `SphinxComponentRegistry.load_extension`. nesting 5 -> 3, complexity 8 -> 8. 8 characterization tests passed in sandbox. |
| sphinx-doc__sphinx-7975:sphinx/util/nodes.py:apply_source_workaround:redundant_check | True | redundant_check | rejected |  | e_2.py::TestNonSpecialNodeNoSourceNoRawsource::test_non_special_node_no_source_no_rawsource 6 failed, 14 passed in 0.27s |
| sphinx-doc__sphinx-7975:sphinx/transforms/__init__.py:SphinxSmartQuotes.apply:swallowed_error | True | swallowed_error | rejected |  | no test file: agent stopped (step limit) |
| pytest-dev__pytest-7432:src/_pytest/_code/code.py:TracebackEntry.getsource:dead | True | dead | rejected |  | ck_to_lineno_plus_one FAILED tests/test_slopgate_0.py::test_getsource_returns_source_slice - assert... 6 failed in 0.10s |
| pytest-dev__pytest-7432:src/_pytest/compat.py:_iscoroutinefunction_impl:wrapper | True | wrapper | rejected |  | OR testing/python/metafunc.py 92 failed, 2431 passed, 118 skipped, 9 xfailed, 23 warnings, 2 errors in 116.14s (0:01:56) |
| pytest-dev__pytest-7432:src/_pytest/main.py:wrap_session_alt:duplicate | True | duplicate | rejected |  | OR testing/python/metafunc.py 92 failed, 2431 passed, 118 skipped, 9 xfailed, 23 warnings, 2 errors in 112.15s (0:01:52) |
| sphinx-doc__sphinx-8506:sphinx/config.py:eval_config_file_alt:duplicate | False |  | missed |  |  |
| sphinx-doc__sphinx-8506:sphinx/environment/collectors/asset.py:DownloadFileCollector.process_doc:nesting | False |  | missed |  |  |
| sphinx-doc__sphinx-8506:sphinx/deprecation.py:_ModuleWrapper.__getattr__:redundant_check | True | redundant_check | rejected |  | characterization tests miss branches: 1 |
| pytest-dev__pytest-5227:src/_pytest/mark/evaluate.py:MarkEvaluator._istrue:nesting | True | nesting | rejected |  | ult_returned_true FAILED tests/test_slopgate_1.py::test_string_condition_uses_globals 9 failed, 4 passed in 0.13 seconds |
| pytest-dev__pytest-5227:src/_pytest/terminal.py:TerminalReporter._get_progress_information_message:redundant_check | True | redundant_check | rejected |  | step limit: characterization tests miss branches: 1 |
| pytest-dev__pytest-5227:src/_pytest/junitxml.py:pytest_unconfigure:swallowed_error | True | swallowed_error | followup |  | _error`) rewrite of `pytest_unconfigure`. nesting 2 -> 2, complexity 3 -> 5. 3 characterization tests passed in sandbox. |
| pytest-dev__pytest-7220:src/_pytest/config/__init__.py:PytestPluginManager._getconftestmodules:redundant_check | True | redundant_check | rejected |  | step limit: characterization tests miss branches: 1 |
| pytest-dev__pytest-7220:src/_pytest/runner.py:pytest_terminal_summary:swallowed_error | True | swallowed_error | rejected |  | rewrite leaves the slop: swallowed_error |
| pytest-dev__pytest-7220:src/_pytest/capture.py:_get_multicapture:dead | True | dead | followup |  |  (`dead`) rewrite of `_get_multicapture`. nesting 1 -> 1, complexity 5 -> 5. 6 characterization tests passed in sandbox. |
| pallets__flask-5063:src/flask/cli.py:_find_best_app_impl:wrapper | True | wrapper | rejected |  | ========== FAILED tests/test_slopgate_0.py::TestLocateApp::test_import_success_app_name_none 1 failed, 4 passed in 0.12s |
| pallets__flask-5063:src/flask/scaffold.py:_path_is_relative_to_alt:duplicate | True | duplicate | followup |  | `_path_is_relative_to_alt` does the same job as `_path_is_relative_to` in src/flask/scaffold.py (exact structural copy). |
| pallets__flask-5063:src/flask/ctx.py:AppContext.pop:nesting | False |  | missed |  |  |
| psf__requests-3362:requests/adapters.py:HTTPAdapter.cert_verify:nesting | True | nesting | rejected |  | Conn object at 0x7ffff5f022b0>.cert_file  tests/test_slopgate_0.py:87: AssertionError 1 failed, 9 passed in 0.03 seconds |
| psf__requests-3362:requests/cookies.py:merge_cookies:redundant_check | True | redundant_check | rejected |  | step limit: characterization tests miss branches: 1 |
| psf__requests-3362:requests/models.py:PreparedRequest.prepare_cookies:swallowed_error | True | swallowed_error | followup |  | ite of `PreparedRequest.prepare_cookies`. nesting 2 -> 2, complexity 4 -> 4. 5 characterization tests passed in sandbox. |
| pytest-dev__pytest-8365:src/_pytest/main.py:pytest_runtestloop:swallowed_error | True | swallowed_error | rejected |  | failed - A... FAILED tests/test_slopgate_2.py::test_items_loop_shouldstop_raises_interrupted 5 failed, 4 passed in 0.14s |
| pytest-dev__pytest-8365:src/_pytest/assertion/rewrite.py:rewrite_asserts:dead | True | dead | followup |  | te (`dead`) rewrite of `rewrite_asserts`. nesting 0 -> 0, complexity 1 -> 1. 4 characterization tests passed in sandbox. |
| pytest-dev__pytest-8365:src/_pytest/compat.py:_get_real_func_impl:wrapper | True | wrapper | followup |  | nlined into its single caller `get_real_method` in src/_pytest/compat.py. 6 characterization tests of the caller passed. |
| pylint-dev__pylint-5859:pylint/reporters/reports_handler_mix_in.py:ReportsHandlerMixIn.register_report:swallowed_error | True | swallowed_error | followup |  | of `ReportsHandlerMixIn.register_report`. nesting 1 -> 0, complexity 2 -> 1. 4 characterization tests passed in sandbox. |
| pylint-dev__pylint-5859:pylint/message/message_definition_store.py:MessageDefinitionStore.register_message:dead | True | dead | followup |  | MessageDefinitionStore.register_message`. nesting 0 -> 0, complexity 1 -> 1. 5 characterization tests passed in sandbox. |
| pylint-dev__pylint-5859:pylint/config/find_default_config_files.py:_find_default_config_files_impl:wrapper | True | wrapper | rejected |  | pylintrc - Attribu... FAILED tests/test_slopgate_0.py::test_returns_none_when_no_config_files - Att... 4 failed in 0.38s |
| pytest-dev__pytest-5692:src/_pytest/terminal.py:MoreQuietAction.__init__:dead | True | dead | followup |  | `) rewrite of `MoreQuietAction.__init__`. nesting 0 -> 0, complexity 1 -> 1. 2 characterization tests passed in sandbox. |
| pytest-dev__pytest-5692:src/_pytest/skipping.py:_check_xfail_no_run_impl:wrapper | True | wrapper | followup |  | nto its single caller `pytest_runtest_setup` in src/_pytest/skipping.py. 10 characterization tests of the caller passed. |
| pytest-dev__pytest-5692:src/_pytest/pathlib.py:register_cleanup_lock_removal_alt:duplicate | True | duplicate | followup |  | r_cleanup_lock_removal_alt` does the same job as `register_cleanup_lock_removal` in src/_pytest/pathlib.py (score 0.59). |
| pydata__xarray-4248:xarray/core/ops.py:inject_binary_ops_alt:duplicate | True | duplicate | followup |  | `inject_binary_ops_alt` does the same job as `inject_binary_ops` in xarray/core/ops.py (exact structural copy). |
| pydata__xarray-4248:xarray/core/variable.py:Variable._inplace_binary_op:nesting | True | nesting | followup |  | rewrite of `Variable._inplace_binary_op`. nesting 3 -> 1, complexity 1 -> 1. 5 characterization tests passed in sandbox. |
| pydata__xarray-4248:xarray/core/merge.py:_get_priority_vars_and_indexes:redundant_check | True | redundant_check | rejected |  | step limit: characterization tests miss branches: 1 |
| mwaskom__seaborn-3190:seaborn/_core/scales.py:Continuous.tick:nesting | True | nesting | followup |  | nesting`) rewrite of `Continuous.tick`. nesting 4 -> 2, complexity 8 -> 11. 14 characterization tests passed in sandbox. |
| mwaskom__seaborn-3190:seaborn/palettes.py:_parse_cubehelix_args:redundant_check | True | redundant_check | rejected |  | characterization tests miss branches: 1 |
| mwaskom__seaborn-3190:seaborn/_core/properties.py:ObjectProperty.get_mapping:swallowed_error | True | swallowed_error | followup |  |  rewrite of `ObjectProperty.get_mapping`. nesting 2 -> 2, complexity 7 -> 7. 8 characterization tests passed in sandbox. |
| pylint-dev__pylint-7993:pylint/message/message_id_store.py:MessageIdStore.check_msgid_and_symbol:redundant_check | True | nesting, redundant_check | rejected |  | step limit: characterization tests miss branches: 1 |
| pylint-dev__pylint-7993:pylint/config/_pylint_config/utils.py:should_retry_after_invalid_input:swallowed_error | True | swallowed_error | rejected |  | time limit: characterization tests fail on original: .F.....Killed |
| pylint-dev__pylint-7993:pylint/checkers/base/name_checker/naming_style.py:NamingStyle.get_regex:lookup_table | True | lookup_table | followup |  | e`) rewrite of `NamingStyle.get_regex`. nesting 1 -> 0, complexity 12 -> 1. 13 characterization tests passed in sandbox. |
