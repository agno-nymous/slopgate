BASE_URL = "https://api.tokenfactory.nebius.com/v1/"

NESTING = 2
DUPLICATE_SCORE = 0.30
FLAG = 0.8
HOOK_FLOOR = 0.30
HOOK_K = 2
WORKERS = 8

LIGHTNING = "nvidia/Nemotron-3_5-Lightning"
SUPER = "nvidia/nemotron-3-super-120b-a12b"
ULTRA = "nvidia/Nemotron-3-Ultra-550b-a55b"

# The server default is 8,192 output tokens; a full test file for a large function can pass it.
MAX_OUTPUT_TOKENS = 32768

# USD per million tokens (input, output)
PRICES = {LIGHTNING: (0.06, 0.24), SUPER: (0.30, 0.90), ULTRA: (1.0, 3.0)}

# Limits of the characterization agent for each function, as measured in ticket 41 (tokens: cumulative input tokens).
AGENT_STEPS = 15
AGENT_SECONDS = 120
AGENT_TOKENS = 150_000

HINT_MUTANTS = 8
HINT_STEPS = 8
HINT_SECONDS = 90
MUTANT_SECONDS = 60

# Seconds for one sandbox run (the check, the rewrite proof, the repo tests). The slowest normal run in ticket 33 took 159 s:
# this repo's own test suite in ConTree.
SANDBOX_TIMEOUT = 600

# A commit from before Python 3.12 runs on an older Python with the dependencies of its own time (ticket 53). On 3.12 the old pytest
# fails in the assertion rewriter, and some old packages have no wheel.
OLD_COMMIT_BEFORE = "2023-10-02T00:00:00+00:00"
# setuptools 64.0 (2022-08-11) is the first with `build_editable`.
SETUPTOOLS_EDITABLE = "2022-08-12T00:00:00+00:00"
# Release dates of the Python minors. An old commit gets the newest one released 90 days before its date, so its dependencies have
# wheels for it (ticket 59). 3.6 is the floor: uv cannot install into an older Python.
PYTHON_LAG_DAYS = 90
PYTHONS = [("3.6", "2016-12-23"), ("3.7", "2018-06-27"), ("3.8", "2019-10-14"), ("3.9", "2020-10-05"), ("3.10", "2021-10-04"), ("3.11", "2022-10-24")]
