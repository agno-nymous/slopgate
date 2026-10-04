# 12 — Give the test writer the code the target calls

**What to build:** The prompt that asks Nemotron Super for characterization tests shows only the source of the target function. Sometimes the result of the target depends on another repo function. Then Super has to guess the behavior of that function, and its tests fail on the original code. The gate correctly rejects such tests, but the candidate is lost.

Add the source of every repo function that the target calls directly to the tests prompt. Resolve names one level deep, in the same way as the wrapper rewrites and the duplicate rewrites. Put this source under a heading such as "Code it calls". For a wrapper candidate, this source includes the wrapper and its inner function.

**Blocked by:** 05

**Status:** done

- [x] The tests prompt for a function that calls a repo helper contains the source of the helper. A seam test checks the recorded prompt.
- [x] A function with no repo callees gets the same prompt as before.
- [x] Under the `live` marker, the demo below produces the wrapper followup with real Nemotron Super and the real sandbox.

## Comments

- 2026-10-03: Found in a real run (real Super, real sandbox). In the repo, `shop/pricing.py` has `apply_discount(price, percent)`. This function raises `ValueError` outside 0..100. The PR adds the wrapper `discounted(price, percent)`. The PR also adds `shop/cart.py` with `cart_total(prices, percent)`, which calls `discounted`. Super wrote tests for `cart_total` that used `percent = -50`. Two of four tests failed on the original code. The gate rejected the candidate with "characterization tests fail on original". With correct caller tests, the same run produced the expected wrapper followup.
- 2026-10-03: Built. The function that collects the callee code (`called_code` in `slopgate/review.py`) collects the module-level repo functions that the target calls by plain name. A plain name is a name from the same file, or from `from <repo module> import <name>`. The function goes two levels deep, so the caller of a wrapper gets both the wrapper and its inner function. The tests prompt gets a "Code it calls" section only when the list is not empty. Otherwise the prompt does not change. The function does not resolve `module.func()` callees or `self.method()` callees (marked `ponytail:`).
- 2 new seam tests were added. 4 mutations each fail one test: context dropped, one level only, section always added, imports not followed. 48 offline tests pass.
- Live run, real Super plus real sandbox, on the demo repo: 6 of 9 runs produce the wrapper followup. Before this ticket, the first two real runs both failed. The ValueError guess is gone: Super now tests the out-of-range percent with `pytest.raises`. One rejection remains that was captured in detail. Super mispredicted an exact value. It asserted `cart_total([0.01], 50) == 0.0`, but `round(0.005, 2)` gives `0.01`. This is filed as ticket 13. Until ticket 13 lands, the live test (`test_real_super_proves_a_wrapper_whose_caller_depends_on_the_helper`) is flaky at about that rate.
