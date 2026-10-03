# Triage Labels

The skills speak in terms of five canonical triage roles. This file maps those roles to the actual label strings used in this repo's issue tracker.

| Label in mattpocock/skills | Label in our tracker | Meaning                                  |
| -------------------------- | -------------------- | ---------------------------------------- |
| `needs-triage`             | `needs-triage`       | Maintainer needs to evaluate this issue  |
| `needs-info`               | `needs-info`         | Waiting on reporter for more information |
| `ready-for-agent`          | `ready-for-agent`    | Fully specified, ready for an AFK agent  |
| `ready-for-human`          | `ready-for-human`    | Requires human implementation            |
| `wontfix`                  | `wontfix`            | Will not be actioned                     |

When a skill mentions a role (e.g. "apply the AFK-ready triage label"), use the corresponding label string from this table.

Edit the right-hand column to match whatever vocabulary you actually use.

## Progress states

Besides the triage labels, a ticket's `Status:` line can hold these progress states:

| Status             | Meaning                                                                                                   |
| ------------------ | --------------------------------------------------------------------------------------------------------- |
| `in-progress`      | An agent is working on it                                                                                 |
| `needs-live-check` | Offline work is done and verified with fakes; only boxes that need an external service (blocked on access) stay open. It does NOT count as done for the frontier |
| `done`             | Every acceptance box is checked                                                                           |
