# Install agent

## Run metadata

| field | report |
| --- | --- |
| models | install agent: nvidia/Nemotron-3_5-Lightning, nvidia/nemotron-3-super-120b-a12b |
| commit | 1890fa62d2 (tree had changes) |
| date | 2026-10-20 |
| seeds | none |
| counts | attempts 24, successes 0 |
| cost (USD) | 1.4883 |

| prompt | stage | hash |
| --- | --- | --- |
| INSTALL_RULES | report | `1f912070f8e9` |
| INSTALL_TASK | report | `27e3147b0954` |


## Models

| model | attempts | successes | 3 of 3 | at least 1 | 0 | mean seconds | mean steps | tokens in | tokens out | USD | /venv scripts | apt-get scripts |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| nvidia/Nemotron-3_5-Lightning | 12 | 0 | 0 | 0 | 4 | 176.09 | 28.75 | 3586877 | 19089 | 0.2199 | 0 | 0 |
| nvidia/nemotron-3-super-120b-a12b | 12 | 0 | 0 | 0 | 4 | 158.05 | 26.25 | 4120453 | 35620 | 1.2684 | 0 | 0 |

## Failure reasons: nvidia/Nemotron-3_5-Lightning

- 10 x no script: agent stopped (step limit)
- 2 x no script: agent stopped (agent error: ApiStatusCodeError(re

## Failure reasons: nvidia/nemotron-3-super-120b-a12b

- 4 x no script: agent stopped (token limit)
- 3 x no script: agent stopped (step limit)
- 1 x Unable to install due to vendored urllib3 compatibility with
- 1 x distutils missing in Python 3.12 and cannot be installed via
- 1 x Python 3.6 required but not available
- 1 x no script: agent stopped (agent error: ApiStatusCodeError(re
- 1 x need imp module unavailable in Python 3.12

## Instances

| instance | default | Nemotron-3_5-Lightning k/3 | nemotron-3-super-120b-a12b k/3 |
| --- | --- | --- | --- |
| psf__requests-1963 | fail | 0/3 | 0/3 |
| scikit-learn__scikit-learn-10297 | fail | 0/3 | 0/3 |
| matplotlib__matplotlib-18869 | fail | 0/3 | 0/3 |
| astropy__astropy-6938 | fail | 0/3 | 0/3 |

## Decision

- Collapse (Super 3 of 3, Lightning 0 of 3): none.
- The agent ships only if at least one model gets an instance to success that the default failed: no.
- Chosen model: nvidia/Nemotron-3_5-Lightning.
