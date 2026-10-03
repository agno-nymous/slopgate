# 02 — Real Nebius sandbox with checkpoint

**What to build:** The gate proves rewrites in a real Nebius Token Factory Sandbox (ConTree), not only in the local fake. The repo at the head ref is uploaded once per pull request and installed on `python:3.12-slim`. The installed state is kept as a checkpoint. Every trial (original tests, rewrite tests) starts from that checkpoint and never changes it. At most 8 trials run at the same time.

The install and test commands come from `.slopgate.toml` if it exists, then `pyproject.toml`, then `requirements*.txt`. When the install fails, the gate reports it and stops without proving anything.

Start with a short spike: confirm which ConTree SDK call starts a new run from a saved session state, and record the answer in the ticket's Comments.

**Blocked by:** 01

**Status:** done

- [x] The spike result is written under `## Comments` in this ticket.
- [x] The nested-function fixture from ticket 01 passes under the `live` marker with the real sandbox, with the same JSON result as the fake.
- [x] The repo installs once per review, no matter how many trials run (checked by counting install runs).
- [x] A trial with a broken edit reports failure and does not affect the next trial.
- [x] `.slopgate.toml` with `[sandbox]` keys `setup` and `test` overrides the detected commands.
- [x] A repo whose install fails produces one `rejected`-style notice that starts with "could not build test environment" and holds the last 20 output lines, and the process exits 0.
- [x] Without `.slopgate.toml`, both `pyproject.toml` and `requirements.txt` repos are detected correctly.

## Comments

- ConTree facts from the planning handoff (do not re-research): install with `pip install contree-sdk` (Python 3.10 to 3.13). Async client: `Contree(ContreeAsyncClient(key, base_url="https://api.tokenfactory.nebius.com/sandboxes"))`; sync: `ContreeSync`. Calls: `await contree.images.use("python:3.12-slim")`, then `await image.run(shell=..., files=[UploadFileSpec(source=..., path=...)])` returns `stdout`, `stderr`, `exit_code`. `image.session()` creates a new image state after each command. Unconfirmed: how to start a new run from a saved session state (the spike). 7,000+ SWE-bench images are preloaded. At most 50 operations run at the same time; Slopgate uses 8. Runs are reported free in beta (unconfirmed).
- Ticket 01 left a local sandbox in `slopgate/sandbox.py` with `checkpoint(repo, ref) -> Path` and `run(checkpoint, files, cmd) -> (exit_code, output)`. The real sandbox should keep that shape.
- 2026-10-02 spike result (read from the contree-sdk 0.3.6 source; live run blocked, see next note): `run()` takes `disposable=True` by default, which discards the resulting image. The install run must pass `disposable=False`. Its result is an image: `checkpoint.run(shell=..., cwd="/repo", files={...}).wait()` starts a new run from that saved state and never changes it. A disposable result has no uuid, so calling `run` on it raises `DisposableImageRunError`. File contents in `files` must be `bytes`; a `str` value is read as a local path. Auth: `ContreeSync()` reads `NEBIUS_API_KEY` and `NEBIUS_PROJECT_ID` (sent as the `Project` header).
- 2026-10-02 live blocker: with key and project ID set, `GET /sandboxes/v1/images` returns `403 {"error": "Insufficient permissions: list"}`; without the `Project` header it returns `400 Missing "Project" header`. So credentials parse, but the account or key lacks Sandboxes permission. The two live boxes stay open until that is fixed.
- Offline half built: `Local` and `Contree` sandboxes in `slopgate/sandbox.py`, command detection (`.slopgate.toml` keys win one by one, then `pyproject.toml` -> `pip install -e .`, then root `requirements*.txt` -> `pip install -r ...`, default test `python -m pytest -q`), install once per review before any LLM call, install failure as one rejected notice, and a repo-test run on each rewrite (exit 0 or 5 passes). `--sandbox local|contree`, default `contree`. 10 offline tests pass; 7 code mutations each fail at least one test.
- Trials run one at a time. That satisfies the cap of 8. A thread pool of 8 is the upgrade when review time matters (marked with a `ponytail:` comment in `review`).
- 2026-10-03: Sandboxes access is requested and waiting for Nebius approval. Status set to `needs-live-check`: the offline work is done; the two live boxes stay open. When access is approved, create a fresh API key if needed, run `uv run --env-file .env pytest -m live -q`, tick the two boxes, and set `Status: done`.
- 2026-10-03: Sandboxes access approved. Live spike confirmed the SDK reading: install with `disposable=False` took 6.6 s; two parallel trials plus one more from the same checkpoint took 2.4 s in total; a file written by one trial was absent in the others; a trial's exit code (3) comes back unchanged; pip has network inside the sandbox. `uv run --env-file .env pytest -m live` on commit 20af887: 4 passed in 45 s (model IDs, nested fixture gives identical JSON under contree and local, pyproject and requirements detection). Status set to `done`.
