| design | functions | proved | proof rate | reasons | median s | p90 s | mean calls | tokens in / out | cost $ | median sandbox s | C steps median | C broken / writes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A | 36 | 7 | 19% | fail on original 21, proved 7, cannot test 4, error 3, nondeterministic 1 | 20 | 29 | 1.7 | 75,616 / 62,828 | 0.079 | 11 | - | - |
| B | 36 | 13 | 36% | fail on original 14, proved 13, error 4, cannot test 3, nondeterministic 2 | 28 | 48 | 2.8 | 149,711 / 86,537 | 0.123 | 17 | - | - |
| C | 36 | 24 | 67% | proved 24, step limit 9, token limit 1, time limit 1, nondeterministic 1 | 55 | 100 | 14.0 | 3,585,198 / 102,925 | 1.168 | 31 | 15.0 | 0 / 72 |

C variance over 10 functions run 3 times: proved 3/3: 4, proved 2/3: 2, proved 1/3: 1, proved 0/3: 3

| function | A | B | C |
|---|---|---|---|
| slopgate@b2a2ad0:slopgate/index.py:build | cannot test | fail on original | proved / proved / step limit |
| slopgate@b2a2ad0:slopgate/live.py:seed | fail on original | proved | proved / proved / proved |
| slopgate@b2a2ad0:slopgate/live.py:matches | fail on original | error | proved / step limit / proved |
| slopgate@b2a2ad0:slopgate/review.py:find_duplicate | fail on original | proved | proved / proved / proved |
| slopgate@b2a2ad0:slopgate/review.py:characterize | cannot test | cannot test | time limit / time limit / error |
| slopgate@70c27da:slopgate/review.py:characterize | fail on original | nondeterministic | token limit / token limit / token limit |
| django/django:django/contrib/postgres/fields/ranges.py:RangeField.to_python | cannot test | cannot test | step limit / fail on original / step limit |
| django/django:django/forms/widgets.py:ClearableFileInput.value_omitted_from_data | fail on original | fail on original | proved / proved / proved |
| django/django:django/template/defaulttags.py:DebugNode.render | proved | proved | proved / proved / proved |
| django/django:django/views/generic/base.py:RedirectView.get | fail on original | fail on original | step limit / proved / step limit |
| django/django:django/utils/http.py:base36_to_int | proved | proved | proved |
| django/django:django/db/models/manager.py:BaseManager._set_creation_counter | fail on original | proved | proved |
| pytest-dev/pytest:src/_pytest/_py/path.py:LocalPath.fnmatch | error | error | step limit |
| pytest-dev/pytest:src/_pytest/cacheprovider.py:LFPluginCollSkipfiles.pytest_make_collect_report | fail on original | fail on original | step limit |
| pytest-dev/pytest:src/_pytest/_py/path.py:LocalPath._ensuredirs | fail on original | fail on original | step limit |
| pytest-dev/pytest:src/_pytest/_code/code.py:ExceptionInfo.from_exception | error | error | step limit |
| pytest-dev/pytest:src/_pytest/config/__init__.py:_get_directory | error | error | step limit |
| pytest-dev/pytest:src/_pytest/legacypath.py:Testdir.spawn_pytest | fail on original | cannot test | step limit |
| psf/requests:requests/sessions.py:Session.options | proved | proved | proved |
| psf/requests:requests/models.py:Response.iter_lines | fail on original | fail on original | proved |
| psf/requests:requests/packages/urllib3/exceptions.py:LocationParseError.__init__ | proved | proved | proved |
| psf/requests:requests/models.py:Response.json | fail on original | fail on original | proved |
| psf/requests:requests/utils.py:get_encoding_from_headers | fail on original | proved | proved |
| psf/requests:requests/packages/chardet/sbcharsetprober.py:SingleByteCharSetProber.get_confidence | fail on original | fail on original | proved |
| sympy/sympy:sympy/printing/latex.py:LatexPrinter._print_LeviCivita | fail on original | fail on original | proved |
| sympy/sympy:sympy/series/sequences.py:SeqBase.free_symbols | fail on original | fail on original | proved |
| sympy/sympy:sympy/geometry/ellipse.py:Ellipse.reflect | fail on original | fail on original | proved |
| sympy/sympy:sympy/polys/densetools.py:_dup_decompose | fail on original | fail on original | step limit |
| sympy/sympy:sympy/sets/fancysets.py:ComplexRegion._measure | proved | proved | proved |
| sympy/sympy:sympy/functions/special/spherical_harmonics.py:Ynm.fdiff | fail on original | fail on original | proved |
| pallets/flask:src/flask/app.py:Flask.wsgi_app | fail on original | proved | proved |
| pallets/flask:src/flask/helpers.py:get_load_dotenv | fail on original | proved | proved |
| pallets/flask:src/flask/json/__init__.py:JSONEncoder.default | nondeterministic | nondeterministic | nondeterministic |
| pallets/flask:src/flask/ctx.py:RequestContext.auto_pop | proved | proved | proved |
| pallets/flask:src/flask/helpers.py:make_response | cannot test | fail on original | proved |
| pallets/flask:src/flask/app.py:Flask.handle_url_build_error | proved | proved | proved |
