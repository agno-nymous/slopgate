# 24 — Save the embedding model cache on the default branch

**What to build:** A push to the default branch fills the GitHub cache with the CodeRankEmbed model. Each new pull request then restores the model from the cache and does not download it.

**Blocked by:** None — can start immediately.

**Status:** ready-for-agent

## Context

The action (`action.yml`) caches `~/.cache/huggingface` with the key `slopgate-coderankembed-v1`. The cache holds the CodeRankEmbed model, about 506 MB.

GitHub scopes each cache to the branch that saved it. A pull request run saves its cache under the pull request ref. Another pull request cannot read that cache. A pull request can read a cache from the default branch.

The Slopgate workflow (`.github/workflows/slopgate.yml`, and the workflow in `README.md`) runs only on `pull_request`. So no run ever saves the cache on `main`, and each new pull request downloads the model again.

## Design

1. Add `push: branches: [main]` to the trigger of `.github/workflows/slopgate.yml` and of the example workflow in `README.md`.
2. In `action.yml`, keep the setup, cache, and install steps for both events. On `push`, run one step that loads the model and exits: `python -c "from slopgate import embed; embed.preload()"` (or the smallest call that downloads the model). Skip the review step on `push`. The review step needs `pull_request` data.
3. The `actions/cache` post step then saves the cache under the `main` scope.
4. Do not change the cache key. If the key must change later, change `v1` to `v2`.

## Acceptance

- [ ] A push to `main` runs the workflow. The run downloads the model and saves the cache. The run posts nothing.
- [ ] The next new pull request restores the cache ("Cache restored from key: slopgate-coderankembed-v1" in the log) and does not download the model.
- [ ] The README workflow example has the `push` trigger, with one sentence that says why.

## How to verify

1. Merge the change. Check the Actions run on `main`.
2. Open a new pull request. Check the cache step in its log.

## Comments
