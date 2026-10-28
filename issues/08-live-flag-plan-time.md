# 08 — Live duplicate flag at plan time

## Summary

- **Goal:** When a coding agent submits a plan, tell it which plan step an existing function already does. Example: the step "write a slug helper" gets a note that names `slugify`. The agent can then change the plan.
- **Checkable finish condition:** `slopgate hook` reads a recorded `PreToolUse` payload for `ExitPlanMode`. It prints a note when a step matches an existing function, and prints nothing when no step matches. It exits 0.
- **Evidence:** Not built yet. Before: no check runs at plan time. After: tests with recorded plan payloads show the note and the empty output, and one test shows that all steps go to the classifier in one call.
- **Constraints:** The hook never blocks the plan. Nemotron Lightning writes each function summary once, and `slopgate index` stores it. Make one batched classifier call for all steps. A step with a classifier confidence below 0.8 gives no note.

**Blocked by:** 07

**Status:** wontfix

## Details

The index gains a one-line summary for each function. Nemotron Lightning writes each summary once. The hook works as follows:
1. Split the plan into steps.
2. Search the summaries for each step.
3. Make one batched classifier call for all steps.

- [ ] The command that builds the index (`slopgate index`) writes a one-line summary for each function. Functions that the hook adds at write time also get a summary.
- [ ] The command that runs the hook (`slopgate hook`) reads a recorded `PreToolUse` payload for `ExitPlanMode`. It prints a note when a step matches an existing function.
- [ ] A plan has numbered or bulleted steps. The hook splits this plan into one query for each step.
- [ ] A plan has no matching step. In this case, the hook prints nothing.
- [ ] All steps of one plan go to the classifier in one call.
- [ ] A step is vague, for example "handle errors properly". When the classifier confidence is below 0.8, this step produces no note.
- [ ] The hook never blocks the plan. The hook exits 0.

## Comments

### 2026-10-27 — wontfix (decided with the user)

The user cut this ticket. The plan-time hook runs, but real plans rarely get a note. The write-time hook of ticket 07 already covers the live-flag scene of the video.

**Plan-time measurements** (a separate session built the code in an uncommitted worktree, `ticket-08-plan-time-flag`; nothing was pushed or merged):

- 5 real plans that Claude wrote: 1 got a note (`overlap` against `jaccard`, confidence 0.82 to 0.85). 3 got no note. 1 run failed because the session had no `NEBIUS_API_KEY`.
- Of the 3 plans without a note, 2 were `duration` plans (Lightning answered no, yes-probability 0.25 to 0.44). 1 was an `overlap` plan (the step scored 0.249, below the 0.25 floor).
- Cause: real plans write code-level steps (signatures, format rules). The function summaries are plain words. The recall of 8 of 10 on short test steps did not carry over to real plans.
- Each fix moved the miss to another function. A cosine path raised `jaccard` and cut `strip_fence` from 8 of 8 to 3 of 8.
- It is not proven that a note reaches the agent. After "No, keep planning", the agent quoted no hook context. In plan mode, the agent often reads the code and finds the helper itself.

**Write-time hook measurements** (2026-10-27, scratch clone of this repo at `3c7a927`, 754 functions indexed, headless `claude -p` sessions with the hook logged). One natural prompt for each of 6 functions of this repo. Each prompt describes the job and does not name the function:

| Existing function | Note | Lightning yes-probability (flag at 0.8) |
|---|---|---|
| `plural` | yes, 0.89 | |
| `jaccard` | yes, 0.89 | |
| `is_test_file` | yes, 0.83 | |
| `tail` | no | 0.75 |
| `comments` | no | 0.32 (the new code strips the `#`, so the behavior differs) |
| `strip_fence` | no | 0.22 (a regex in a module constant, and different edge cases) |

- The keyword and embedding search found the right function as the top match in 6 of 6 cases. The misses come from the Lightning threshold.
- A first run of the `plural` prompt scored 0.705 and gave no note. A second run scored 0.89. The Lightning score is noisy near the threshold.
- The hook sees only the function body. When the logic is in a module-level constant (`WORD = re.compile(...)`), Lightning cannot judge the function. One test with `identifier_words` against `tokens` gave 0.13 for this reason.
- When the agent got a note, it read both functions and told the user. In 2 of 3 cases it kept the copy, because the prompt said "write only that file". In 1 case it replaced the copy with a call to `plural`.
- The sample is one run for each prompt. The rate of 3 of 6 is rough.

**Known limits.** The plan-time hook needs a better match between plan steps and function summaries. A fix is a new ticket after the submission.
