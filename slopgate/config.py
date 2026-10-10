BASE_URL = "https://api.tokenfactory.nebius.com/v1/"

NESTING = 2
DUPLICATE_SCORE = 0.30
FLAG = 0.8
HOOK_FLOOR = 0.30
HOOK_K = 2

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
