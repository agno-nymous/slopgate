# 05 — Wrapper removal

**What to build:** The gate removes a one-use wrapper function: a module-level function with a single caller that only passes its arguments on to another call. The characterization tests target the wrapper's single caller, because the caller's behavior is what must not change. The rewrite deletes the wrapper and changes the caller to make the inner call directly. The edit can span two files, so it goes into `followup`.

**Blocked by:** 01

**Status:** ready-for-agent

- [ ] On a fixture with a one-use wrapper, `followup` holds edits that delete the wrapper and update its caller, and the caller's characterization tests pass on the result.
- [ ] A wrapper with two or more callers is not removed.
- [ ] A wrapper whose caller is a method is not removed (methods are out of scope for this kind).
- [ ] The rule check confirms that the wrapper is gone and that no other function or class was added.
- [ ] When the wrapper and its caller are in different files, both file edits appear in `followup`.
