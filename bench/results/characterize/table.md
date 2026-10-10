| design | functions | proved | proof rate | reasons | median s | p90 s | mean calls | tokens in / out | cost $ | median sandbox s | agent steps median | agent broken / writes | kill rate | median asserts |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A | 36 | 7 | 19% | fail on original 20, proved 7, cannot test 3, error 3, no reply 1, missed branches 1, nondeterministic 1 | 19 | 31 | 1.7 | 75,956 / 63,408 | 0.080 | 11 | - | - | 97% (29/30) | 10 |
| B | 36 | 8 | 22% | fail on original 16, proved 8, cannot test 5, error 4, missed branches 2, nondeterministic 1 | 35 | 68 | 3.0 | 207,346 / 141,672 | 0.190 | 22 | - | - | 97% (30/31) | 12.0 |
| C | 36 | 19 | 53% | proved 19, step limit 14, token limit 2, nondeterministic 1 | 56 | 89 | 14.1 | 3,435,409 / 108,629 | 1.128 | 34 | 15.0 | 0 / 70 | 87% (71/82) | 7 |
| D | 36 | 24 | 67% | proved 24, step limit 7, token limit 3, error 1, nondeterministic 1 | 55 | 100 | 13.4 | 2,875,259 / 113,506 | 0.965 | 40 | 15.0 | 2 / 80 | 86% (88/102) | 4.5 |

Kill rate on the 5 functions that A, B, C, D all proved in run 0: A 100% (17/17), B 100% (17/17), C 94% (16/17), D 94% (16/17)

C variance over 10 functions run 3 times: proved 3/3: 1, proved 2/3: 3, proved 1/3: 2, proved 0/3: 4

D variance over 10 functions run 3 times: proved 3/3: 6, proved 2/3: 1, proved 1/3: 0, proved 0/3: 3

| function | A | B | C | D |
|---|---|---|---|---|
| slopgate@b2a2ad0:slopgate/index.py:build | cannot test | cannot test | proved / step limit / proved | proved / proved / proved |
| slopgate@b2a2ad0:slopgate/live.py:seed | fail on original | fail on original | step limit / proved / proved | proved / proved / proved |
| slopgate@b2a2ad0:slopgate/live.py:matches | fail on original | fail on original | proved / step limit / step limit | proved / proved / proved |
| slopgate@b2a2ad0:slopgate/review.py:find_duplicate | proved | proved | step limit / step limit / step limit | token limit / proved / proved |
| slopgate@b2a2ad0:slopgate/review.py:characterize | cannot test | cannot test | token limit / step limit / step limit | step limit / token limit / step limit |
| slopgate@70c27da:slopgate/review.py:characterize | fail on original | fail on original | token limit / step limit / token limit | token limit / token limit / token limit |
| django/django:django/contrib/postgres/fields/ranges.py:RangeField.to_python | cannot test | cannot test | step limit / step limit / step limit | step limit / step limit / step limit |
| django/django:django/forms/widgets.py:ClearableFileInput.value_omitted_from_data | fail on original | fail on original | step limit / proved / step limit | proved / proved / proved |
| django/django:django/template/defaulttags.py:DebugNode.render | fail on original | fail on original | proved / proved / proved | proved / proved / proved |
| django/django:django/views/generic/base.py:RedirectView.get | proved | fail on original | proved / proved / step limit | proved / proved / proved |
| django/django:django/utils/http.py:base36_to_int | proved | proved | proved | proved |
| django/django:django/db/models/manager.py:BaseManager._set_creation_counter | fail on original | fail on original | proved | proved |
| pytest-dev/pytest:src/_pytest/_py/path.py:LocalPath.fnmatch | fail on original | error | step limit | token limit |
| pytest-dev/pytest:src/_pytest/cacheprovider.py:LFPluginCollSkipfiles.pytest_make_collect_report | fail on original | fail on original | step limit | step limit |
| pytest-dev/pytest:src/_pytest/_py/path.py:LocalPath._ensuredirs | error | error | step limit | step limit |
| pytest-dev/pytest:src/_pytest/_code/code.py:ExceptionInfo.from_exception | error | error | step limit | step limit |
| pytest-dev/pytest:src/_pytest/config/__init__.py:_get_directory | error | error | step limit | step limit |
| pytest-dev/pytest:src/_pytest/legacypath.py:Testdir.spawn_pytest | fail on original | cannot test | step limit | error |
| psf/requests:requests/sessions.py:Session.options | proved | proved | proved | proved |
| psf/requests:requests/models.py:Response.iter_lines | no reply | fail on original | proved | proved |
| psf/requests:requests/packages/urllib3/exceptions.py:LocationParseError.__init__ | proved | proved | proved | proved |
| psf/requests:requests/models.py:Response.json | fail on original | fail on original | proved | proved |
| psf/requests:requests/utils.py:get_encoding_from_headers | proved | proved | proved | proved |
| psf/requests:requests/packages/chardet/sbcharsetprober.py:SingleByteCharSetProber.get_confidence | missed branches | missed branches | proved | proved |
| sympy/sympy:sympy/printing/latex.py:LatexPrinter._print_LeviCivita | fail on original | fail on original | step limit | proved |
| sympy/sympy:sympy/series/sequences.py:SeqBase.free_symbols | fail on original | fail on original | proved | proved |
| sympy/sympy:sympy/geometry/ellipse.py:Ellipse.reflect | fail on original | fail on original | proved | proved |
| sympy/sympy:sympy/polys/densetools.py:_dup_decompose | fail on original | missed branches | step limit | proved |
| sympy/sympy:sympy/sets/fancysets.py:ComplexRegion._measure | fail on original | fail on original | proved | proved |
| sympy/sympy:sympy/functions/special/spherical_harmonics.py:Ynm.fdiff | fail on original | fail on original | proved | proved |
| pallets/flask:src/flask/app.py:Flask.wsgi_app | fail on original | proved | proved | proved |
| pallets/flask:src/flask/helpers.py:get_load_dotenv | fail on original | proved | proved | proved |
| pallets/flask:src/flask/json/__init__.py:JSONEncoder.default | nondeterministic | nondeterministic | nondeterministic | nondeterministic |
| pallets/flask:src/flask/ctx.py:RequestContext.auto_pop | proved | proved | proved | proved |
| pallets/flask:src/flask/helpers.py:make_response | fail on original | cannot test | step limit | step limit |
| pallets/flask:src/flask/app.py:Flask.handle_url_build_error | fail on original | fail on original | step limit | proved |
