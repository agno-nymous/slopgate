# SWE-bench benchmark with injected slop

## Run metadata

| field | report | groundtruth | runs |
| --- | --- | --- | --- |
| models | none | injection: nvidia/nemotron-3-super-120b-a12b | tests and rewrites: nvidia/nemotron-3-super-120b-a12b, retry and summary: nvidia/Nemotron-3-Ultra-550b-a55b |
| commit | a636e72104 (tree had changes) | 548ae7bcb1 (tree had changes) | a636e72104 (tree had changes) |
| date | 2026-10-25 | 2026-10-18 | 2026-10-25 |
| seeds | none | select 10 | none |
| counts |  | redundant_check 9, swallowed_error 8, dead 6, wrapper 7, nesting 8, duplicate 6, lookup_table 1 | instances 15 |
| cost (USD) | 1.1632 |  | 1.1606 |

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
| nesting | 8 | 6 | 3 | 0 | 0 | 0 | 0 | 0.75 | 0.5 | 0.375 | 0.0 | 0 | 0 | -1.67 | 0 | 0 |
| redundant_check | 9 | 9 | 0 | 0 | 0 | 0 | 0 | 1.0 | 0.0 | 0.0 |  |  |  |  |  | 0 |
| swallowed_error | 8 | 8 | 1 | 0 | 0 | 0 | 1 | 1.0 | 0.125 | 0.125 | 0.0 | 0 | 1 | -1 | 0 | 0 |
| lookup_table | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 1.0 | 1.0 | 1.0 | 0.0 | -10 | 1 | 0 | 1 | 0 |
| dead | 6 | 6 | 5 | 0 | 0 | 0 | 0 | 1.0 | 0.833 | 0.833 | 0.0 | 0 | 0 | 0 | 0 | 0 |
| wrapper | 7 | 7 | 1 | 0 | 0 | 0 | 0 | 1.0 | 0.143 | 0.143 | 0.0 |  |  |  |  | 1 |
| duplicate | 6 | 4 | 3 | 0 | 0 | 0 | 0 | 0.667 | 0.75 | 0.5 | 0.0 |  |  |  |  | 3 |
| duplicate (exact) | 5 | 3 | 2 | 0 | 0 | 0 |  | 0.6 | 0.667 | 0.4 | 0.0 |  |  |  |  | 2 |
| duplicate (rewritten) | 1 | 1 | 1 | 0 | 0 | 0 |  | 1.0 | 1.0 | 1.0 | 0.0 |  |  |  |  | 1 |
| total | 45 | 41 | 14 | 0 | 0 | 0 | 1 | 0.911 | 0.341 | 0.311 | 0.0 | -1 | 0.2 | -0.6 | 0.1 | 4 |

## Tokens and cost

| model | use | input tokens | output tokens | USD |
| --- | --- | --- | --- | --- |
| nvidia/nemotron-3-super-120b-a12b | injection | 2622 | 1708 | 0.0023 |
| nvidia/nemotron-3-super-120b-a12b | gate | 3244115 | 197549 | 1.151 |
| nvidia/Nemotron-3-Ultra-550b-a55b | gate | 5317 | 1523 | 0.0099 |

Total USD: 1.1632. Mean seconds for each instance: 250.91, of which the gate: 240.36.
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
| pallets__flask-4992:src/flask/app.py:Flask.auto_find_instance_path:dead | True | dead | followup |  | write of `Flask.auto_find_instance_path`. nesting 1 -> 1, complexity 2 -> 2. 2 characterization tests passed in sandbox. |
| pallets__flask-4992:src/flask/scaffold.py:_path_is_relative_to_impl:wrapper | True | wrapper | rejected |  | no test file: agent stopped (no tool call) |
| pallets__flask-4992:src/flask/config.py:Config.get_namespace:nesting | True | nesting | followup |  | ting`) rewrite of `Config.get_namespace`. nesting 3 -> 2, complexity 5 -> 5. 1 characterization tests passed in sandbox. |
| pytest-dev__pytest-7432:src/_pytest/_code/code.py:TracebackEntry.getsource:dead | True | dead | rejected |  | getstatementrange_ast FAILED tests/test_slopgate_0.py::test_getsource_normal_case_no_astcache - Typ... 6 failed in 0.82s |
| pytest-dev__pytest-7432:src/_pytest/compat.py:_iscoroutinefunction_impl:wrapper | True | wrapper | rejected |  | e - Attr... FAILED tests/test_slopgate_1.py::test_is_generator_gen_false - AttributeError... 3 failed, 4 passed in 0.04s |
| pytest-dev__pytest-7432:src/_pytest/main.py:wrap_session_alt:duplicate | True | duplicate | rejected |  | OR testing/python/metafunc.py 92 failed, 2431 passed, 118 skipped, 9 xfailed, 23 warnings, 2 errors in 126.64s (0:02:06) |
| sphinx-doc__sphinx-8627:sphinx/util/matching.py:_translate_pattern_impl:wrapper | True | wrapper | followup |  | ned into its single caller `compile_matchers` in sphinx/util/matching.py. 5 characterization tests of the caller passed. |
| sphinx-doc__sphinx-8627:sphinx/util/typing.py:_stringify_py37_alt:duplicate | False | nesting | missed |  |  |
| sphinx-doc__sphinx-8627:sphinx/locale/__init__.py:_TranslationProxy.__new__:redundant_check | True | redundant_check | rejected |  | step limit: characterization tests miss branches: 1 |
| pytest-dev__pytest-5227:src/_pytest/mark/evaluate.py:MarkEvaluator._istrue:nesting | True | nesting | rejected |  |  FAILED testing/python/metafunc.py 4 failed, 2133 passed, 123 skipped, 10 xfailed, 1 warnings, 1 error in 104.85 seconds |
| pytest-dev__pytest-5227:src/_pytest/terminal.py:TerminalReporter._get_progress_information_message:redundant_check | True | redundant_check | rejected |  | step limit: characterization tests miss branches: 1 |
| pytest-dev__pytest-5227:src/_pytest/junitxml.py:pytest_unconfigure:swallowed_error | True | swallowed_error | rejected |  | cessful_unregister FAILED tests/test_slopgate_0.py::test_xml_exists_unregister_raises 2 failed, 2 passed in 0.04 seconds |
| sphinx-doc__sphinx-8506:sphinx/config.py:eval_config_file_alt:duplicate | False |  | missed |  |  |
| sphinx-doc__sphinx-8506:sphinx/environment/collectors/asset.py:DownloadFileCollector.process_doc:nesting | False |  | missed |  |  |
| sphinx-doc__sphinx-8506:sphinx/deprecation.py:_ModuleWrapper.__getattr__:redundant_check | True | redundant_check | rejected |  |  FAILED tests/test_slopgate_0.py::test_getattr_broken_contains - AssertionErro... 1 failed, 3 passed, 1 warning in 0.04s |
| pytest-dev__pytest-7220:src/_pytest/config/__init__.py:PytestPluginManager._getconftestmodules:redundant_check | True | redundant_check | rejected |  | step limit: characterization tests miss branches: 1 |
| pytest-dev__pytest-7220:src/_pytest/runner.py:pytest_terminal_summary:swallowed_error | True | swallowed_error | followup |  |  rewrite of `pytest_terminal_summary`. nesting 4 -> 3, complexity 11 -> 11. 10 characterization tests passed in sandbox. |
| pytest-dev__pytest-7220:src/_pytest/capture.py:_get_multicapture:dead | True | dead | followup |  |  (`dead`) rewrite of `_get_multicapture`. nesting 1 -> 1, complexity 5 -> 5. 7 characterization tests passed in sandbox. |
| pytest-dev__pytest-8365:src/_pytest/main.py:pytest_runtestloop:swallowed_error | True | swallowed_error | rejected |  | rewrite leaves the slop: swallowed_error |
| pytest-dev__pytest-8365:src/_pytest/assertion/rewrite.py:rewrite_asserts:dead | True | dead | followup |  | te (`dead`) rewrite of `rewrite_asserts`. nesting 0 -> 0, complexity 1 -> 1. 2 characterization tests passed in sandbox. |
| pytest-dev__pytest-8365:src/_pytest/compat.py:_get_real_func_impl:wrapper | True | wrapper | rejected |  | =========== FAILED tests/test_slopgate_1.py::test_exception_path - AttributeError: module... 1 failed, 4 passed in 0.03s |
| psf__requests-3362:requests/adapters.py:HTTPAdapter.cert_verify:nesting | True | nesting | rejected |  | rule: signature changed |
| psf__requests-3362:requests/cookies.py:merge_cookies:redundant_check | True | redundant_check | rejected |  |  once. Called 0 times.  /usr/local/lib/python3.6/unittest/mock.py:824: AssertionError 3 failed, 3 passed in 0.08 seconds |
| psf__requests-3362:requests/models.py:PreparedRequest.prepare_cookies:swallowed_error | True | swallowed_error | rejected |  | rule: signature changed |
| pallets__flask-5063:src/flask/cli.py:_find_best_app_impl:wrapper | True | wrapper | rejected |  | ================ FAILED tests/test_slopgate_0.py::test_locate_app_success_with_app_name_none 1 failed, 5 passed in 0.12s |
| pallets__flask-5063:src/flask/scaffold.py:_path_is_relative_to_alt:duplicate | True | duplicate | followup |  | `_path_is_relative_to_alt` does the same job as `_path_is_relative_to` in src/flask/scaffold.py (exact structural copy). |
| pallets__flask-5063:src/flask/ctx.py:AppContext.pop:nesting | False |  | missed |  |  |
| pylint-dev__pylint-5859:pylint/reporters/reports_handler_mix_in.py:ReportsHandlerMixIn.register_report:swallowed_error | True | swallowed_error | rejected |  | rewrite leaves the slop: swallowed_error |
| pylint-dev__pylint-5859:pylint/message/message_definition_store.py:MessageDefinitionStore.register_message:dead | True | dead | followup |  | MessageDefinitionStore.register_message`. nesting 0 -> 0, complexity 1 -> 1. 2 characterization tests passed in sandbox. |
| pylint-dev__pylint-5859:pylint/config/find_default_config_files.py:_find_default_config_files_impl:wrapper | True | wrapper | rejected |  | ns_none_when_no_match FAILED tests/test_slopgate_0.py::test_find_pylintrc_handles_empty_iterator - ... 3 failed in 0.40s |
| pytest-dev__pytest-5692:src/_pytest/terminal.py:MoreQuietAction.__init__:dead | True | dead | followup |  | `) rewrite of `MoreQuietAction.__init__`. nesting 0 -> 0, complexity 1 -> 1. 5 characterization tests passed in sandbox. |
| pytest-dev__pytest-5692:src/_pytest/skipping.py:_check_xfail_no_run_impl:wrapper | True | wrapper | rejected |  | ==== FAILED tests/test_slopgate_1.py::test_xfail_evaluator_set - AttributeError: <... 1 failed, 6 passed in 0.12 seconds |
| pytest-dev__pytest-5692:src/_pytest/pathlib.py:register_cleanup_lock_removal_alt:duplicate | True | duplicate | followup |  | e unlinking. Differential tests that fail on the helper: test_register_cleanup_lock_removal_alt_returns_register_result. |
| sphinx-doc__sphinx-7975:sphinx/registry.py:SphinxComponentRegistry.load_extension:nesting | True | nesting | followup |  | SphinxComponentRegistry.load_extension`. nesting 5 -> 3, complexity 8 -> 8. 10 characterization tests passed in sandbox. |
| sphinx-doc__sphinx-7975:sphinx/util/nodes.py:apply_source_workaround:redundant_check | True | redundant_check | rejected |  | AILED tests/test_slopgate_2.py::test_other_node_no_workaround_needed - Recur... 11 failed, 2 passed in 120.91s (0:02:00) |
| sphinx-doc__sphinx-7975:sphinx/transforms/__init__.py:SphinxSmartQuotes.apply:swallowed_error | True | swallowed_error | rejected |  | ception - Attribut... FAILED tests/test_slopgate_1.py::test_apply_exception - AttributeError: can't... 8 failed in 0.19s |
| pydata__xarray-4248:xarray/core/ops.py:inject_binary_ops_alt:duplicate | True | duplicate | followup |  | `inject_binary_ops_alt` does the same job as `inject_binary_ops` in xarray/core/ops.py (exact structural copy). |
| pydata__xarray-4248:xarray/core/variable.py:Variable._inplace_binary_op:nesting | True | nesting | rejected |  | rule: does not parse |
| pydata__xarray-4248:xarray/core/merge.py:_get_priority_vars_and_indexes:redundant_check | True | redundant_check | rejected |  | step limit: characterization tests miss branches: 1 |
| pylint-dev__pylint-7993:pylint/message/message_id_store.py:MessageIdStore.check_msgid_and_symbol:redundant_check | True | nesting, redundant_check | rejected |  | =========== FAILED tests/test_slopgate_2.py::test_existing_msgid_only_no_symbol - pylint.... 1 failed, 8 passed in 0.13s |
| pylint-dev__pylint-7993:pylint/config/_pylint_config/utils.py:should_retry_after_invalid_input:swallowed_error | True | swallowed_error | rejected |  | rule: adds a class |
| pylint-dev__pylint-7993:pylint/checkers/base/name_checker/naming_style.py:NamingStyle.get_regex:lookup_table | True | lookup_table | followup |  | le`) rewrite of `NamingStyle.get_regex`. nesting 1 -> 1, complexity 12 -> 2. 1 characterization tests passed in sandbox. |
| mwaskom__seaborn-3190:seaborn/_core/scales.py:Continuous.tick:nesting | True | nesting | followup |  | `nesting`) rewrite of `Continuous.tick`. nesting 4 -> 2, complexity 8 -> 8. 18 characterization tests passed in sandbox. |
| mwaskom__seaborn-3190:seaborn/palettes.py:_parse_cubehelix_args:redundant_check | True | redundant_check | rejected |  | step limit: characterization tests miss branches: 1 |
| mwaskom__seaborn-3190:seaborn/_core/properties.py:ObjectProperty.get_mapping:swallowed_error | True | swallowed_error | rejected |  | ate_0.py::TestObjectPropertyGetMapping::test_get_mapping_with_invalid_values_type 2 failed, 9 passed, 1 warning in 1.57s |
