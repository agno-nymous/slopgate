# Default install of the test environment

## Run metadata

| field | report |
| --- | --- |
| models | none |
| commit | 1890fa62d2 (tree had changes) |
| date | 2026-10-21 |
| seeds | none |
| counts | instances 28, built 18, collects 18, false_triggers 0, calibrated 15, calibration_production 15, calibration_bench 15 |

| prompt | stage | hash |
| --- | --- | --- |


## Results

- Instances: 28. Default built: 18. Default succeeds (built, and the tests collect): 18.
- False triggers (built, and the tests do not collect): 0.
- Calibration on the SWE-bench image, 15 instances: the production command passes on 15, the bench command on 15.
- Mean seconds for each instance: 32.9.

## Instances

| instance | python | built | collects | calibration production | calibration bench | seconds | reason |
| --- | --- | --- | --- | --- | --- | --- | --- |
| pytest-dev__pytest-5227 | 3.7 | True | True | pass | pass | 29.7 |  |
| pytest-dev__pytest-7220 | 3.8 | True | True | pass | pass | 33.1 |  |
| pytest-dev__pytest-8365 | 3.9 | True | True | pass | pass | 28.7 |  |
| pytest-dev__pytest-5692 | 3.7 | True | True | pass | pass | 31.5 |  |
| pytest-dev__pytest-7432 | 3.8 | True | True | pass | pass | 32.7 |  |
| sphinx-doc__sphinx-8627 | 3.8 | True | True | pass | pass | 35.0 |  |
| sphinx-doc__sphinx-8506 | 3.8 | True | True | pass | pass | 33.1 |  |
| sphinx-doc__sphinx-7975 | 3.8 | True | True | pass | pass | 33.4 |  |
| pylint-dev__pylint-7993 | 3.10 | True | True | pass | pass | 36.6 |  |
| pylint-dev__pylint-5859 | 3.10 | True | True | pass | pass | 28.9 |  |
| psf__requests-3362 | 3.6 | True | True | pass | pass | 24.4 |  |
| pallets__flask-4992 | 3.11 | True | True | pass | pass | 21.7 |  |
| pallets__flask-5063 | 3.11 | True | True | pass | pass | 22.6 |  |
| pydata__xarray-4248 | 3.8 | True | True | pass | pass | 45.9 |  |
| mwaskom__seaborn-3190 | 3.10 | True | True | pass | pass | 32.7 |  |
| psf__requests-1963 | 3.6 | False | False |  |  | 15.7 |  output. ERROR: Command errored out with exit status 1: python setup.py egg_info Check the logs for full command output. |
| pydata__xarray-3364 | 3.7 | True | True |  |  | 20.6 |  |
| sympy__sympy-11400 | 3.6 | True | True |  |  | 77.9 |  |
| scikit-learn__scikit-learn-10297 | 3.6 | False | False |  |  | 26.3 | "'"');f.close();exec(compile(code, __file__, '"'"'exec'"'"'))' develop --no-deps Check the logs for full command output. |
| matplotlib__matplotlib-18869 | 3.9 | False | False |  |  | 38.0 | reetype-2.6.1     [end of output]  note: This error originates from a subprocess, and is likely not a problem with pip.  |
| astropy__astropy-6938 | 3.6 | False | False |  |  | 20.6 |  output. ERROR: Command errored out with exit status 1: python setup.py egg_info Check the logs for full command output. |
| scikit-learn__scikit-learn-10508 | 3.6 | False | False |  |  | 26.3 | "'"');f.close();exec(compile(code, __file__, '"'"'exec'"'"'))' develop --no-deps Check the logs for full command output. |
| scikit-learn__scikit-learn-11040 | 3.6 | False | False |  |  | 26.0 | "'"');f.close();exec(compile(code, __file__, '"'"'exec'"'"'))' develop --no-deps Check the logs for full command output. |
| matplotlib__matplotlib-22711 | 3.10 | False | False |  |  | 38.0 | reetype-2.6.1     [end of output]  note: This error originates from a subprocess, and is likely not a problem with pip.  |
| matplotlib__matplotlib-23299 | 3.10 | False | False |  |  | 34.5 | reetype-2.6.1     [end of output]  note: This error originates from a subprocess, and is likely not a problem with pip.  |
| astropy__astropy-12907 | 3.10 | False | False |  |  | 28.6 | code: 1 ╰─> See above for output.  note: This error originates from a subprocess, and is likely not a problem with pip.  |
| astropy__astropy-14182 | 3.10 | False | False |  |  | 26.5 | code: 1 ╰─> See above for output.  note: This error originates from a subprocess, and is likely not a problem with pip.  |
| sympy__sympy-12171 | 3.6 | True | True |  |  | 72.2 |  |
