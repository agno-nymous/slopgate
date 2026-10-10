# 02 — Real Nebius sandbox with checkpoint

## Summary

- **Goal:** Let the gate prove rewrites in a real Nebius sandbox (ConTree), not only in the local fake. Example: the repo of a pull request installs once, and every test run then starts from that saved install.
- **Checkable finish condition:** `uv run --env-file .env pytest -m live -q` passes. The nested-function fixture from ticket 01 gives the same JSON in the real sandbox as in the local fake. A count of install runs shows one install for each review.
- **Evidence:** Done. The spike result is in Comments. On commit 20af887, 4 live tests passed in 45 s. The install took 6.6 s. Two parallel trials plus one more from the same saved install took 2.4 s. A file that one trial wrote was absent in the other trials. 10 offline tests pass, and 7 planted bugs each fail at least one test.
- **Constraints:** Install once for each review on `python:3.12-slim`, and save the result as a checkpoint. Every trial starts from the checkpoint and never changes it. At most 8 trials run at the same time. Take the install and test commands from `.slopgate.toml`, then `pyproject.toml`, then `requirements*.txt`. Keep the shape `checkpoint(repo, ref)` and `run(checkpoint, files, cmd)`. If the install fails, report "could not build test environment", prove nothing, and exit 0.

**Blocked by:** 01

**Status:** done

## Details

The gate uploads the repo at the head ref once for each pull request. It installs the repo and keeps the installed state as the checkpoint. A trial is one test run, either the original tests or the rewrite tests. When the install fails, the gate reports the failure and stops. Start with a short spike: find which ConTree SDK call starts a new run from a saved session state, and record the answer in the Comments of this ticket.

- [x] The spike result is written under `## Comments` in this ticket.
- [x] The nested-function fixture from ticket 01 passes under the `live` marker with the real sandbox. The JSON result is the same as the result from the fake.
- [x] The repo installs once for each review, for any number of trials. A count of install runs checks this.
- [x] A trial with a broken edit reports failure. The failure does not affect the next trial.
- [x] A `.slopgate.toml` file with the `[sandbox]` keys `setup` and `test` overrides the detected commands.
- [x] A repo whose install fails produces one notice in the style of `rejected`. The notice starts with "could not build test environment" and holds the last 20 lines of output. The process exits 0.
- [x] Without `.slopgate.toml`, the gate detects both `pyproject.toml` repos and `requirements.txt` repos correctly.

## Comments

- ConTree facts from the planning handoff (do not research them again): Install the SDK with `pip install contree-sdk` (Python 3.10 to 3.13). The async client is `Contree(ContreeAsyncClient(key, base_url="https://api.tokenfactory.nebius.com/sandboxes"))`. The sync client is `ContreeSync`. First call `await contree.images.use("python:3.12-slim")`. Then call `await image.run(shell=..., files=[UploadFileSpec(source=..., path=...)])`. The run returns `stdout`, `stderr`, and `exit_code`. The call `image.session()` creates a new image state after each command. Unconfirmed: how to start a new run from a saved session state (the spike). 7,000+ SWE-bench images are preloaded. At most 50 operations run at the same time. Slopgate uses 8. Runs are reported free in beta (unconfirmed).
- Ticket 01 left a local sandbox in `slopgate/sandbox.py`. It has `checkpoint(repo, ref) -> Path` and `run(checkpoint, files, cmd) -> (exit_code, output)`. The real sandbox must keep that shape.
- 2026-10-02 spike result (read from the contree-sdk 0.3.6 source; the live run was blocked, see the next note): The call `run()` takes `disposable=True` by default. This default discards the resulting image. The install run must pass `disposable=False`. The result of that run is an image. The call `checkpoint.run(shell=..., cwd="/repo", files={...}).wait()` starts a new run from that saved state. It never changes the saved state. A disposable result has no uuid. A call to `run` on a disposable result raises `DisposableImageRunError`. File contents in `files` must be `bytes`. The SDK reads a `str` value as a local path. For auth, `ContreeSync()` reads `NEBIUS_API_KEY` and `NEBIUS_PROJECT_ID`. The SDK sends `NEBIUS_PROJECT_ID` as the `Project` header.
- 2026-10-02 live blocker: The key and the project ID were set. `GET /sandboxes/v1/images` returned `403 {"error": "Insufficient permissions: list"}`. Without the `Project` header, it returned `400 Missing "Project" header`. The credentials parse. The account or the key lacks Sandboxes permission. The two live boxes stay open until this is fixed.
- Offline half built: The `Local` and `Contree` sandboxes are in `slopgate/sandbox.py`. Command detection works as follows. Keys in `.slopgate.toml` win one by one. Then `pyproject.toml` gives `pip install -e .`. Then the root `requirements*.txt` gives `pip install -r ...`. The default test command is `python -m pytest -q`. The install runs once for each review, before any LLM call. An install failure gives one rejected notice. A repo-test run happens on each rewrite (exit 0 or 5 passes). The option `--sandbox local|contree` selects the sandbox. The default is `contree`. 10 offline tests pass. 7 code mutations each fail at least one test.
- Trials run one at a time. This satisfies the cap of 8. A thread pool of 8 is the upgrade when review time matters. A `ponytail:` comment in `review` marks this.
- 2026-10-03: Sandboxes access is requested. Nebius has not approved it yet. Status is set to `needs-live-check`. The offline work is done. The two live boxes stay open. When access is approved, do these steps. 1. Create a fresh API key if needed. 2. Run `uv run --env-file .env pytest -m live -q`. 3. Tick the two boxes. 4. Set `Status: done`.
- 2026-10-03: Sandboxes access was approved. The live spike confirmed the reading of the SDK. The install with `disposable=False` took 6.6 s. Two parallel trials plus one more trial from the same checkpoint took 2.4 s in total. A file that one trial wrote was absent in the other trials. The exit code of a trial (3) came back unchanged. Pip has network access inside the sandbox. The command `uv run --env-file .env pytest -m live` on commit 20af887 gave 4 passed in 45 s. The four tests were: model IDs, nested fixture with identical JSON under contree and local, pyproject detection, and requirements detection. Status was set to `done`.
