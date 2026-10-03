# 02 — Real Nebius sandbox with checkpoint

**What to build:** The gate proves rewrites in a real Nebius Token Factory Sandbox (ConTree), not only in the local fake. The repo at the head ref is uploaded once per pull request and installed on `python:3.12-slim`. The installed state is kept as a checkpoint. Every trial (original tests, rewrite tests) starts from that checkpoint and never changes it. At most 8 trials run at the same time.

The install and test commands come from `.slopgate.toml` if it exists, then `pyproject.toml`, then `requirements*.txt`. When the install fails, the gate reports it and stops without proving anything.

Start with a short spike: confirm which ConTree SDK call starts a new run from a saved session state, and record the answer in the ticket's Comments.

**Blocked by:** 01

**Status:** ready-for-agent

- [ ] The spike result is written under `## Comments` in this ticket.
- [ ] The nested-function fixture from ticket 01 passes under the `live` marker with the real sandbox, with the same JSON result as the fake.
- [ ] The repo installs once per review, no matter how many trials run (checked by counting install runs).
- [ ] A trial with a broken edit reports failure and does not affect the next trial.
- [ ] `.slopgate.toml` with `[sandbox]` keys `setup` and `test` overrides the detected commands.
- [ ] A repo whose install fails produces one `rejected`-style notice that starts with "could not build test environment" and holds the last 20 output lines, and the process exits 0.
- [ ] Without `.slopgate.toml`, both `pyproject.toml` and `requirements.txt` repos are detected correctly.
