# 05 — Wrapper removal

## Summary

- **Goal:** The gate removes a function that only passes its arguments on to another call and has one caller. Example: a wrapper `f(a, b)` whose body is `return g(a, b)`. The gate deletes `f` and changes its caller to call `g` directly.
- **Checkable finish condition:** On the wrapper fixture, `followup` holds edits that delete the wrapper and update its caller. The characterization tests of the caller (tests that record what the old code does) pass on the result. A wrapper with two or more callers, or with a method as its caller, gets no edit.
- **Evidence:** Done. There are 11 wrapper tests. In total, 45 offline tests and 6 live tests passed. Each of 12 planted bugs makes at least one test fail. When a planted bug skips the deletion, the result is `rule: wrapper not deleted`.
- **Constraints:** Detection is static and uses no LLM. The behavior of the caller must not change. The rewrite adds no other function or class. Methods are out of scope. The edit can change two files, so it goes into `followup`.

**Blocked by:** 01

**Status:** done

## Details

A one-use wrapper is a module-level function that has one caller. It only passes its arguments on to another call. The characterization tests target the single caller of the wrapper. The rewrite deletes the wrapper and changes the caller to make the inner call directly. The edit can change two files. For this reason, the edit goes into the list of results for the follow-up pull request (`followup`).

- [x] A fixture contains a one-use wrapper. On this fixture, `followup` holds edits that delete the wrapper and update its caller. The characterization tests of the caller pass on the result.
- [x] The gate does not remove a wrapper that has two or more callers.
- [x] The gate does not remove a wrapper whose caller is a method. Methods are out of scope for this kind.
- [x] The rule check confirms that the wrapper is gone. It also confirms that the rewrite adds no other function or class.
- [x] The wrapper and its caller can be in different files. In this case, both file edits appear in `followup`.

## Comments

- 2026-10-03: Built. Wrapper detection is static and uses no LLM. A wrapper is a module-level function whose body is only `return <call>`. The call passes every parameter once, unchanged. Detection runs before the duplicate search. Super would likely call a wrapper a duplicate of its inner function. The rewrite is mechanical. It uses no LLM and no Ultra retry. The characterization tests of the caller and the tests of the repo must pass on the rewrite.
- The gate silently leaves alone these cases:
  - The wrapper has two or more uses.
  - The caller is a method or a nested def.
  - Code uses an aliased import or an attribute access of the wrapper.
  - The wrapper is decorated or async.
  - The wrapper uses `*args` or `**kwargs` (marked `ponytail:`).
  - The call site reorders keyword arguments and an argument contains a call. Inlining would change the order of evaluation.
  - The call site omits an argument whose default is not a constant. Inlining would evaluate the default for each call.
- The rule check fails only on a broken rewrite. The rule check requires that the wrapper is gone and that exactly one def or class is removed. Mutation proves the rule check. When a mutation skips the deletion, the result is `rule: wrapper not deleted`. When a mutation adds a def, the result is `rule: adds a function or class`.
- There are 11 wrapper tests. In total, 45 offline tests pass. 6 live tests passed. 12 mutations each fail at least one test. The delegate adds 10 of these mutations. The review adds the other two, which are the two evaluation guards.
- Found while reviewing: vulture (the tool that finds unused code) reports unused function arguments as type `variable`. For this reason, the `dead` kind of ticket 03 fires on any function that ignores an argument. The rewrite then cannot remove the function because of the signature rule. The fix is in its own commit.
