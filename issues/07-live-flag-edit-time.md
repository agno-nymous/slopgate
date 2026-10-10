# 07 — Live duplicate flag at edit time

## Summary

- **Goal:** Warn the coding agent when it writes a copy of a function that already exists. Example: the agent writes `price_text` in `shop/report.py`, and the hook adds a note that it duplicates `format_total` in `shop/checkout.py`.
- **Checkable finish condition:** `slopgate hook` reads a recorded `PostToolUse` payload and prints the note with the helper, its file, and the confidence. It prints nothing below confidence 0.8, and it always exits 0.
- **Evidence:** Built on 2026-10-04. 13 offline tests and 3 live tests passed, and the full suite had 106 passed tests. 13 of 15 planted bugs failed a test. A live run on the demo repo gave the `price_text` note at confidence 0.95 in 2.08 s.
- **Constraints:** The hook never blocks the write. It uses Nemotron Lightning with a one-token yes/no answer, and the flag threshold is 0.8. A write with no candidate makes no network call.

**Blocked by:** 04

**Status:** done

## Details

A coding agent works in Claude Code. A hook checks every file that the agent writes or edits. The note names the existing function and its file. The note also gives a confidence score.

The hook does these steps in order:
1. It parses the new functions.
2. It checks the structure hash.
3. It runs a local keyword and vector search.

The hook calls the classifier only when a candidate passes the score floor. The log-probability of the token is the confidence.

The hook puts each new function into the index when the agent writes it. For this reason, the hook also checks the earlier functions of the agent. The ticket also documents how to install the hook in the Claude Code settings of a project.

- [x] The command that runs the hook (`slopgate hook`) reads a recorded `PostToolUse` payload for `Write` or `Edit` from stdin. It prints a note in the format that Claude Code accepts as added context.
- [x] A write duplicates an existing helper. In this case, the hook produces a note. The note names that helper, its file, and the confidence.
- [x] A write has no candidate above the floor. In this case, the hook prints nothing and makes no network call. A test asserts this behavior.
- [x] On the path with no candidate, record the median runtime on the test machine in the Comments of the ticket. The embedding model stays loaded or is cached. Measure a cold load of the model separately.
- [x] The hook finds a function that the agent wrote earlier in the same session. This happens when the agent later writes a copy of the function.
- [x] A classifier confidence below 0.8 produces no note.
- [x] The hook exits 0 in every case. This includes a parse error in the written file.

## Comments

- 2026-10-04: Built. The command that runs the hook (`slopgate hook`) reads the PostToolUse payload, reads the saved file from disk, and keeps a mirror of the working tree in a SQLite file (`.slopgate/live.db`). The mirror holds one row for each module-level function that is not a test. Each write replaces the rows of its own file. For this reason, a function that the agent wrote earlier in the session is in the search pool. The code is in `slopgate/live.py`.
- Design: three designs were compared, with measurements. Design A kept the embedding model loaded in a background process for each repo. Design B used keyword search only, with no model. Design C compiles the model once to an int8 ONNX file and loads it in each hook process. Design C won. It is the only design with hybrid search measured on 4,583 functions, and it has no background process. Design A is the upgrade path if the hook is too slow.
- Search: an equal structure hash flags the function at once, with no classifier call. Otherwise the score is 0.5 x embedding cosine + 0.5 x token Jaccard. The top 2 rows with a score of 0.30 or more go to the classifier. On 6 renamed and restructured copies in 139 functions, this hybrid score ranked each copy first. Its smallest lead was 0.17, against 0.05 for Jaccard only and 0.07 for cosine only.
- Floor: the floor is 0.30, not 0.35, because one true copy (a generator rewrite of `chunks`) scored 0.34. The floor removes few candidates in a real repo: 40 of the 49 module-level functions of this repo reach the classifier at 0.35. The classifier makes most of the decisions.
- Classifier: Nemotron Lightning is a thinking model. A one-token answer needs `chat_template_kwargs: {"enable_thinking": False}`. Without it, the first token is always "Here". The question asks if the agent should call A instead of keeping B. With this question, the 10 true copies scored 0.89 to 0.99, and the 20 closest wrong matches scored 0.004 to 0.029. The flag threshold stays at 0.8. The first question ("same behavior?") flagged only 3 of 6 copies at 0.8.
- Median runtime on the path with no candidate (box 4), measured on an M1 Mac with 20 subprocess runs of `slopgate hook` on this repo:
  1. A write to a file that is not Python: 58 ms.
  2. An edit of known functions only (no new function): 85 ms.
  3. A write that adds a function with no candidate: 430 ms. The model load is most of this time.
  4. A write with a candidate (one Lightning call): 1,652 ms median over 5 runs.
  5. The first `slopgate index` on a machine compiles the model: 35.6 s, once.
  6. A cold model load after a reboot was not measured. The design measurement was 0.93 s.
- The command-line start (`slopgate --help`) dropped from 0.64 s to 0.03 s. The review modules and openai now load only in the commands that use them.
- Tests: 13 seam tests (19 cases with parameters) in `tests/test_hook.py` drive `main(["hook"])` with a recorded payload. They cover all 7 boxes, an exact structural copy, test functions out of the pool, a renamed function, an edit that loads no model, and a classifier failure. 3 live tests pass with the real model and real Lightning. The int8 vectors match the torch vectors at cosine 0.933 to 0.966. The full suite has 106 passed tests.
- Mutations: 13 of 15 mutations fail at least one test. The 2 survivors use only the vector half or only the keyword half of the score. The test embedding fake is a bag of tokens, so both halves agree on every fixture. Only the real model separates them.
- Live run on a copy of the demo repo: a new file `shop/report.py` with `price_text`, a rewrite of the money formatter, produced the note "`price_text` (shop/report.py:1) duplicates existing `format_total` (shop/checkout.py:20), confidence 0.95" in 2.08 s. A new unique function printed nothing in 0.60 s. An edit of its body printed nothing in 0.07 s. A syntax error printed one line on stderr and exited 0.
- Known limits: two copies of the same new helper in one parallel batch of writes are not flagged until a later write. A file changed outside the hook stays old in the mirror until the next write of that file or the next `slopgate index`. A torch upgrade can break the ONNX export; the live parity test catches this.
