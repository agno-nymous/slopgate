# 12 — Give the test writer the code the target calls

**What to build:** The prompt that asks Nemotron Super for characterization tests shows only the target function's source. When the target's result depends on another repo function, Super has to guess that function's behavior, and its tests then fail on the original code. The gate correctly rejects such tests, but the candidate is lost.

Add the source of every repo function that the target calls directly (one level, resolved like the wrapper and duplicate rewrites resolve names) to the tests prompt, under a heading such as "Code it calls". For a wrapper candidate, this includes the wrapper and its inner function.

**Blocked by:** 05

**Status:** ready-for-agent

- [ ] The tests prompt for a function that calls a repo helper contains the helper's source; a seam test checks the recorded prompt.
- [ ] A function with no repo callees gets the same prompt as before.
- [ ] Under the `live` marker, the demo below produces the wrapper followup with real Nemotron Super and the real sandbox.

## Comments

- 2026-10-03: Found in a real run (real Super, real sandbox). Repo: `shop/pricing.py` has `apply_discount(price, percent)`, which raises `ValueError` outside 0..100. The PR adds the wrapper `discounted(price, percent)` and `shop/cart.py` with `cart_total(prices, percent)`, which calls `discounted`. Super wrote tests for `cart_total` that used `percent = -50`; two of four failed on the original, so the gate rejected the candidate with "characterization tests fail on original". With correct caller tests, the same run produced the expected wrapper followup.
