# SWE-bench benchmark with injected slop

## Run metadata

| field | report | groundtruth | runs |
| --- | --- | --- | --- |
| models | none | injection: nvidia/nemotron-3-super-120b-a12b | tests and rewrites: nvidia/nemotron-3-super-120b-a12b, retry and summary: nvidia/Nemotron-3-Ultra-550b-a55b |
| commit | 548ae7bcb1 (tree had changes) | 548ae7bcb1 (tree had changes) | 548ae7bcb1 (tree had changes) |
| date | 2026-10-18 | 2026-10-18 | 2026-10-18 |
| seeds | none | select 10 | none |
| counts |  | redundant_check 8, swallowed_error 7, dead 7, wrapper 6, duplicate 7, nesting 8, lookup_table 2 | instances 15 |
| cost (USD) | 1.2434 |  | 1.2416 |

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
| nesting | 8 | 8 | 4 | 0 | 0 | 0 | 0 | 1.0 | 0.5 | 0.5 | 0.0 | 0 | 0 | -1.5 | -0.25 | 0 |
| redundant_check | 8 | 8 | 0 | 0 | 0 | 0 | 0 | 1.0 | 0.0 | 0.0 |  |  |  |  |  | 0 |
| swallowed_error | 7 | 7 | 0 | 0 | 0 | 0 | 0 | 1.0 | 0.0 | 0.0 |  |  |  |  |  | 0 |
| lookup_table | 2 | 2 | 2 | 0 | 0 | 0 | 0 | 1.0 | 1.0 | 1.0 | 0.0 | -10 | 1 | 0 | 1 | 0 |
| dead | 7 | 7 | 5 | 0 | 0 | 0 | 0 | 1.0 | 0.714 | 0.714 | 0.0 | -0.2 | -0.2 | -0.2 | -0.2 | 0 |
| wrapper | 6 | 6 | 2 | 0 | 0 | 0 | 0 | 1.0 | 0.333 | 0.333 | 0.0 |  |  |  |  | 2 |
| duplicate | 7 | 5 | 5 | 0 | 0 | 0 | 0 | 0.714 | 1.0 | 0.714 | 0.0 |  |  |  |  | 5 |
| duplicate (exact) | 6 | 5 | 5 | 0 | 0 | 0 |  | 0.833 | 1.0 | 0.833 | 0.0 |  |  |  |  | 5 |
| duplicate (rewritten) | 1 | 0 | 0 | 0 | 0 | 0 |  | 0.0 |  | 0.0 |  |  |  |  |  | 0 |
| total | 45 | 43 | 18 | 0 | 0 | 0 | 0 | 0.956 | 0.419 | 0.4 | 0.0 | -1.91 | 0.09 | -0.64 | 0 | 7 |

## Tokens and cost

| model | use | input tokens | output tokens | USD |
| --- | --- | --- | --- | --- |
| nvidia/nemotron-3-super-120b-a12b | injection | 2266 | 1222 | 0.0018 |
| nvidia/nemotron-3-super-120b-a12b | gate | 3636444 | 156791 | 1.232 |
| nvidia/Nemotron-3-Ultra-550b-a55b | gate | 5560 | 1357 | 0.0096 |

Total USD: 1.2434. Mean seconds for each instance: 228.63, of which the gate: 224.19.

## Skipped instances

| instance | reason |
| --- | --- |

## Gate errors

| instance | errors |
| --- | --- |

## Items

| item | detected | gate kinds | outcome | silent break | reason |
| --- | --- | --- | --- | --- | --- |
| pytest-dev__pytest-5227:src/_pytest/fixtures.py:FixtureManager.getfixtureclosure:nesting | True | nesting | rejected |  | ==== FAILED tests/test_slopgate_0.py::test_getfixtureclosure_merge_avoids_duplicates 1 failed, 11 passed in 0.12 seconds |
| pytest-dev__pytest-5227:src/_pytest/python.py:Module._inject_setup_module_fixture:redundant_check | True | redundant_check | rejected |  | resent FAILED tests/test_slopgate_1.py::test_inject_setup_module_fixture_with_alternative_names 5 failed in 0.12 seconds |
| pytest-dev__pytest-5227:src/_pytest/runner.py:pytest_runtest_protocol:swallowed_error | True | swallowed_error | rejected |  | nfo ============================ FAILED tests/test_slopgate_2.py::test_exception_path 1 failed, 1 passed in 0.04 seconds |
| sphinx-doc__sphinx-8506:sphinx/config.py:eval_config_file_alt:duplicate | False |  | missed |  |  |
| sphinx-doc__sphinx-8506:sphinx/util/inventory.py:InventoryFile.load_v2:nesting | True | nesting | rejected |  | FAILED tests/test_slopgate_1.py::test_load_v2_regex_no_match - ValueError: in... 5 failed, 1 passed, 7 warnings in 0.09s |
| sphinx-doc__sphinx-8506:sphinx/domains/__init__.py:Index.__init__:redundant_check | True | redundant_check | rejected |  | characterization tests miss branches: 1 |
| pytest-dev__pytest-5692:src/_pytest/capture.py:CaptureManager.item_capture:dead | True | dead | rejected |  | ================ FAILED tests/test_slopgate_0.py::test_exception - AssertionError: assert False 1 failed in 0.03 seconds |
| pytest-dev__pytest-5692:src/_pytest/fixtures.py:_get_parametrized_fixture_keys_impl:wrapper | True | wrapper | rejected |  | tributeErro... FAILED tests/test_slopgate_1.py::test_reorder_items_scopenum_loop - Attribute... 4 failed in 0.11 seconds |
| pytest-dev__pytest-5692:src/_pytest/mark/structures.py:get_unpacked_marks_alt:duplicate | True | duplicate | followup |  | unpacked_marks_alt` does the same job as `get_unpacked_marks` in src/_pytest/mark/structures.py (exact structural copy). |
| pallets__flask-4992:src/flask/scaffold.py:Scaffold.context_processor:dead | True | dead | rejected |  | sts/test_slopgate_1.py !!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!! 1 error in 0.16s |
| pallets__flask-4992:src/flask/app.py:Flask.add_url_rule:nesting | True | nesting | rejected |  | step limit: characterization tests miss branches: 1 |
| pallets__flask-4992:src/flask/wrappers.py:Request.endpoint:redundant_check | True | redundant_check | rejected |  | characterization tests miss branches: 1 |
| sphinx-doc__sphinx-8627:sphinx/util/typing.py:_is_system_TypeVar_impl:wrapper | True | wrapper | rejected |  | AILED tests/test_slopgate_2.py::test_typevar_fallback - AssertionError: asse... 1 failed, 8 passed, 13 warnings in 0.08s |
| sphinx-doc__sphinx-8627:sphinx/util/inspect.py:safe_getattr_alt:duplicate | False | swallowed_error | missed |  |  |
| sphinx-doc__sphinx-8627:sphinx/pycode/__init__.py:ModuleAnalyzer.for_file:nesting | True | nesting | followup |  | g`) rewrite of `ModuleAnalyzer.for_file`. nesting 3 -> 2, complexity 4 -> 4. 4 characterization tests passed in sandbox. |
| sphinx-doc__sphinx-7975:sphinx/registry.py:SphinxComponentRegistry.preload_builder:nesting | True | nesting | followup |  | SphinxComponentRegistry.preload_builder`. nesting 3 -> 1, complexity 4 -> 4. 4 characterization tests passed in sandbox. |
| sphinx-doc__sphinx-7975:sphinx/util/nodes.py:NodeMatcher.match:redundant_check | True | nesting, redundant_check | rejected |  | step limit: characterization tests miss branches: 1 |
| sphinx-doc__sphinx-7975:sphinx/locale/__init__.py:init_console:swallowed_error | True | swallowed_error | rejected |  | rule: does not parse |
| pytest-dev__pytest-7220:src/_pytest/_code/code.py:TracebackEntry.getsource:redundant_check | True | redundant_check | rejected |  | miss - A... FAILED tests/test_slopgate_0.py::test_syntax_error_path - AssertionError: exp... 4 failed, 1 passed in 0.13s |
| pytest-dev__pytest-7220:src/_pytest/pytester.py:linecomp:swallowed_error | True | swallowed_error | rejected |  | rewrite makes no change |
| pytest-dev__pytest-7220:src/_pytest/config/__init__.py:Config._get_override_ini_value:dead | True | dead | followup |  | rite of `Config._get_override_ini_value`. nesting 3 -> 2, complexity 5 -> 4. 7 characterization tests passed in sandbox. |
| pytest-dev__pytest-7432:src/_pytest/_code/code.py:TracebackEntry.statement:dead | True | dead | followup |  | `) rewrite of `TracebackEntry.statement`. nesting 0 -> 0, complexity 2 -> 2. 2 characterization tests passed in sandbox. |
| pytest-dev__pytest-7432:src/_pytest/config/__init__.py:_prepareconfig_impl:wrapper | True | wrapper | rejected |  | _hook - AttributeE... FAILED tests/test_slopgate_2.py::test_main_valueerror_then_return_ret - Attri... 5 failed in 0.36s |
| pytest-dev__pytest-7432:src/_pytest/capture.py:_readline_workaround_alt:duplicate | True | duplicate | followup |  | _readline_workaround_alt` does the same job as `_readline_workaround` in src/_pytest/capture.py (exact structural copy). |
| pallets__flask-5063:src/flask/cli.py:_find_best_app_impl:wrapper | True | wrapper | rejected |  | ================ FAILED tests/test_slopgate_1.py::test_locate_app_success_with_none_app_name 1 failed, 4 passed in 0.13s |
| pallets__flask-5063:src/flask/scaffold.py:_path_is_relative_to_alt:duplicate | True | duplicate | followup |  | `_path_is_relative_to_alt` does the same job as `_path_is_relative_to` in src/flask/scaffold.py (exact structural copy). |
| pallets__flask-5063:src/flask/blueprints.py:Blueprint.__init__:nesting | True | nesting | followup |  | esting`) rewrite of `Blueprint.__init__`. nesting 3 -> 1, complexity 4 -> 4. 6 characterization tests passed in sandbox. |
| pytest-dev__pytest-8365:src/_pytest/helpconfig.py:pytest_addoption:swallowed_error | True | swallowed_error | rejected |  | rewrite leaves the slop: swallowed_error |
| pytest-dev__pytest-8365:src/_pytest/cacheprovider.py:pytest_report_header:dead | True | dead | followup |  | dead`) rewrite of `pytest_report_header`. nesting 2 -> 2, complexity 5 -> 5. 6 characterization tests passed in sandbox. |
| pytest-dev__pytest-8365:src/_pytest/pathlib.py:_rm_rf_impl:wrapper | True | wrapper | followup |  | ined into its single caller `ensure_reset_dir` in src/_pytest/pathlib.py. 3 characterization tests of the caller passed. |
| psf__requests-3362:requests/packages/urllib3/connectionpool.py:HTTPConnectionPool._validate_conn:dead | True | dead | followup |  | e of `HTTPConnectionPool._validate_conn`. nesting 0 -> 0, complexity 1 -> 1. 1 characterization tests passed in sandbox. |
| psf__requests-3362:requests/packages/urllib3/util/url.py:_split_first_impl:wrapper | True | wrapper | followup |  |  its single caller `parse_url` in requests/packages/urllib3/util/url.py. 17 characterization tests of the caller passed. |
| psf__requests-3362:requests/api.py:request_alt:duplicate | True | duplicate | followup |  | `request_alt` does the same job as `request` in requests/api.py (exact structural copy). |
| pylint-dev__pylint-7993:pylint/checkers/typecheck.py:TypeChecker.visit_extslice:redundant_check | True | redundant_check | rejected |  | step limit: characterization tests miss branches: 1 |
| pylint-dev__pylint-7993:pylint/checkers/base_checker.py:BaseChecker.add_message:swallowed_error | True | swallowed_error | rejected |  | ts/test_slopgate_1.py::TestBaseCheckerAddMessage::test_add_message_different_exception_types 2 failed, 2 passed in 0.23s |
| pylint-dev__pylint-7993:pylint/checkers/base/name_checker/naming_style.py:NamingStyle.get_regex:lookup_table | True | lookup_table | followup |  | le`) rewrite of `NamingStyle.get_regex`. nesting 1 -> 1, complexity 12 -> 2. 1 characterization tests passed in sandbox. |
| pylint-dev__pylint-5859:pylint/message/message_definition.py:MessageDefinition.check_msgid:swallowed_error | True | swallowed_error | rejected |  | rewrite leaves the slop: swallowed_error |
| pylint-dev__pylint-5859:pylint/checkers/base.py:NamingStyle.get_regex:lookup_table | True | lookup_table | followup |  | e`) rewrite of `NamingStyle.get_regex`. nesting 1 -> 1, complexity 12 -> 2. 13 characterization tests passed in sandbox. |
| pylint-dev__pylint-5859:pylint/message/message_id_store.py:MessageIdStore.check_msgid_and_symbol:dead | True | dead | followup |  | `MessageIdStore.check_msgid_and_symbol`. nesting 2 -> 2, complexity 7 -> 7. 10 characterization tests passed in sandbox. |
| mwaskom__seaborn-3190:seaborn/_core/properties.py:IntervalProperty.get_mapping:nesting | True | nesting | followup |  | ewrite of `IntervalProperty.get_mapping`. nesting 3 -> 2, complexity 6 -> 6. 7 characterization tests passed in sandbox. |
| mwaskom__seaborn-3190:seaborn/_core/scales.py:PseudoAxis.update_units:redundant_check | True | nesting, redundant_check | rejected |  | token limit: characterization tests miss branches: 1 |
| mwaskom__seaborn-3190:seaborn/palettes.py:light_palette:swallowed_error | True | swallowed_error | rejected |  | fo ============================ FAILED tests/test_slopgate_2.py::test_light_palette_basic - ValueError 1 failed in 1.33s |
| pydata__xarray-4248:xarray/core/utils.py:_maybe_cast_to_cftimeindex_alt:duplicate | True | duplicate | followup |  | t_to_cftimeindex_alt` does the same job as `_maybe_cast_to_cftimeindex` in xarray/core/utils.py (exact structural copy). |
| pydata__xarray-4248:xarray/coding/cftimeindex.py:assert_all_valid_date_type:nesting | True | nesting | rejected |  | rule: changes a comparison |
| pydata__xarray-4248:xarray/ufuncs.py:_skip_signature:redundant_check | True | redundant_check | rejected |  | AILED tests/test_slopgate_2.py::test_isinstance_false_second - RecursionErro... 1 failed, 6 passed, 9 warnings in 16.07s |
