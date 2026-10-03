# Issue tracker: Local Markdown

The spec and tickets for this repo live as markdown files at the repo root.

## Conventions

- The spec is `spec.md` at the repo root.
- Tickets are one file per ticket at `issues/<NN>-<slug>.md`, numbered from `01` in dependency order. Never put all tickets in one file.
- Each ticket records triage state on a `Status:` line near the top (see `triage-labels.md` for the strings).
- Each ticket lists its blockers on a `Blocked by:` line. A ticket is unblocked when every ticket it lists has `Status: done`.
- Comments and progress notes go at the bottom of the ticket file under a `## Comments` heading.

## When a skill says "publish to the issue tracker"

Create a new file under `issues/`, with the next free number.

## When a skill says "fetch the relevant ticket"

Read the file at the referenced path. The user normally passes the path or the ticket number.

## Frontier

The frontier is every ticket that is not done and whose blockers are all done. Take the lowest number first.
