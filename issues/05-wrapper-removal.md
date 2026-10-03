# 05 — Wrapper removal

**What to build:** The gate removes a one-use wrapper function: a module-level function with a single caller that only passes its arguments on to another call. The characterization tests target the wrapper's single caller, because the caller's behavior is what must not change. The rewrite deletes the wrapper and changes the caller to make the inner call directly. The edit can span two files, so it goes into `followup`.

**Blocked by:** 01

**Status:** done

- [x] On a fixture with a one-use wrapper, `followup` holds edits that delete the wrapper and update its caller, and the caller's characterization tests pass on the result.
- [x] A wrapper with two or more callers is not removed.
- [x] A wrapper whose caller is a method is not removed (methods are out of scope for this kind).
- [x] The rule check confirms that the wrapper is gone and that no other function or class was added.
- [x] When the wrapper and its caller are in different files, both file edits appear in `followup`.

## Comments

- 2026-10-03: Built. Wrapper detection is static (no LLM): a module-level function whose body is only `return <call>` that passes every parameter once, unchanged. It runs before the duplicate search, because Super would likely call a wrapper a duplicate of its inner function. The rewrite is mechanical (no LLM, no Ultra retry); the caller's characterization tests and the repo's tests must pass on it.
- Left alone silently: two or more uses, a method or nested-def caller, an aliased import or attribute access of the wrapper, decorated or async wrappers, `*args`/`**kwargs` (marked `ponytail:`), keyword arguments reordered at the call site when an argument contains a call (inlining would change evaluation order), and a non-constant default the call site omits (inlining would evaluate it per call).
- The rule check (wrapper gone, exactly one fewer def or class) can only fail on a broken rewrite, so it is proven by mutation: skipping the deletion yields `rule: wrapper not deleted`, adding a def yields `rule: adds a function or class`.
- 11 wrapper tests; 45 offline tests pass in total; live 6 passed. 12 mutations each fail at least one test (10 by the delegate, plus the two evaluation guards added in review).
- Found while reviewing: vulture reports unused function arguments as typ `variable`, so ticket 03's `dead` kind fires on any function that ignores an argument, and the rewrite then cannot remove it (signature rule). Fixed in its own commit.
