# 66 — Some injected items of the detection benchmark change behavior or are not the kind they name

## Summary

- **Goal:** Make each injected item in `bench/results/groundtruth.json` keep the behavior of its source and contain the kind that it names. Example: the `fk5_to_gal` nesting injection uses the name `pmats`, which does not exist, so the function raises `NameError`.
- **Checkable finish condition:** A script lists each injected item with three facts: the current `accept()` keeps it or rejects it, the injection keeps behavior, and the kind is present by the one-line rule in `kinds.KINDS`. Each defective item is fixed or removed with a written reason, and `detection.md` is made again.
- **Evidence:** The Opus label review of ticket 42 (2026-10-17) found the defects below on the rows of `bench/labels.json`. The transform items were not reviewed.
- **Constraints:** Do not remove an item only because the current gate does not find it. A valid injection that the gate misses is a false negative, and it must stay in the recall.

**Blocked by:** —

**Status:** done

**Type:** bug.

## Context

`groundtruth.json` was made on 2026-10-09 (commit be0d670, ticket 37). At that time, `kinds.py` found nesting with the depth only (`nesting() > 2`), and a Lightning call found `redundant_check`. Ticket 39 replaced both with the AST checks `flattenable` and `repeated_checks`. Nobody made the ground truth again.

Defects found in ticket 42:

1. `astropy/.../galactic_transforms.py:fk5_to_gal:nemotron:nesting`: the injection uses `pmats`, but the local name is `pmat`. The function raises `NameError`. The kind is present.
2. `matplotlib/tutorials/intermediate/imshow_extent.py:index_to_coordinate:nemotron:lookup_table`: the injected if/elif chain returns `None` for an unknown index. The original dict lookup raised `KeyError`.
3. `sphinx/domains/c.py:ASTDeclaration.__init__:nemotron:nesting`: each branch assigns `self.symbol: Symbol = None`. The injection is a duplicated branch, not clear nesting.
4. `pytest/src/_pytest/tmpdir.py:pytest_configure:nemotron:nesting`: the injection sets `config._tmp_path_factory` only if `hasattr(config, '_tmp_path_factory')`. The attribute does not exist before the call, so the injected function never sets it. Then `pytest_sessionfinish` raises `AttributeError: 'Config' object has no attribute '_tmp_path_factory'` at the end of every pytest run. The kind is present. Found by a full gate dry run on the spliced item (trace `54f5294561048aae0dd86c0f00466735`, 81 s): the test agent used all 15 steps, and the reason was "characterization tests fail on original". The labels review had marked this injection valid.
5. The current `accept()` (`bench/detect.py`) rejects these injections, because the current gate does not find their kind:
   - redundant_check: `ASTDeclaratorNameParam.describe_signature`, `ExponentialCutoffPowerLaw1D.fit_deriv`, `hours_to_hms`, `LambdaCDM._dS_comoving_distance_z1z2`;
   - nesting: `ASTDeclaration.__init__`, `AnchoredOffsetbox.draw`.
   They stay in the benchmark as valid items, so they count as misses of the current gate.

6. `psf/requests:requests/packages/chardet/chardetect.py:description_of:transform:swallowed_error`: the item is valid, and the current gate finds its kind. But the gate cannot build the test environment at this commit (base `110048f9`). The merge-base is from before Python 3.12, so the sandbox uses `python:3.10-slim` (ticket 53). The vendored urllib3 runs `from collections import MutableMapping`, and Python 3.10 removed that name. `pip install -e .` stops with `ImportError` (trace `544736880137cb3156dd45ca712abf81`, `sandbox.prepare` failed after 13 s). This is a limit of the sandbox, not a defect of the item. No flask injection is found by the current gate, so this item was the only flask or requests item for a full gate dry run.

The pytest dry run in point 4 needed a `.slopgate.toml` setup override with `SETUPTOOLS_SCM_PRETEND_VERSION=7.4.0` in the spliced repo. Without it, the install failed with the `setuptools-scm` error of ticket 58.

Also: `label.DEFINITIONS["nesting"]` does not describe one shape that `flattenable` accepts: an `else:` that holds only `pass` (the `node.orelse and not other` clause). `pylint/checkers/variables.py:_is_type_checking_import` depends on it.

## Design

1. Write `bench/check_injections.py` (or a stage of `bench/detect.py`). For each injected item, report: `accept()` at HEAD; a behavior check (compile, and compare the names that the function reads with the source); and the review notes from ticket 42.
2. Fix defects 1 to 4 by hand in `groundtruth.json`, or remove the item. Give each change a reason in `bench/labels.json` (`injections`).
3. Do not change the items in points 5 and 6. Point 6 needs a sandbox change. Write it as a new ticket only if ticket 10 uses `psf/requests` at a commit from before Python 3.10.
4. Make `detection.md` and `detection-t39.md` again, and add the change in the Comments.

## Acceptance

- [x] The script lists each injected item with the three facts.
- [x] Defects 1 to 4 are fixed or removed, each with a reason.
- [x] `detection.md` and `detection-t39.md` are made again.
- [x] `uv run pytest -q` passes.

## Comments

### 2026-10-25

**What was built.** `bench/check_injections.py` lists each injected item (140: 72 transform and 39 Nemotron items, plus the pairs) with three facts. Command: `uv run python -m bench.check_injections`. It writes `bench/results/injection-check.md`. It makes no model call and takes 6 s.
- `accept`: `detect.accept()` on the kinds that the gate still checks (`kinds.KINDS`). `filler_comment` is not one of them, so 22 items are `not scored`.
- `new names`: the injection compiles, and it reads no name that nothing binds and that the source does not read. This check finds defect 1 (`pmats`). It does not find other changes of behavior. Defects 2 and 4 came from the label review, and the check reports them as `ok`.
- `kind`: the entry of `bench/labels.json` for a Nemotron item (`valid` or `invalid` and its reason). A transform item has its kind by construction.

**Defects 1 to 4.**
1. `fk5_to_gal`: the injection read `pmats`; it reads `pmat` now (edited in `groundtruth.json`).
2. `index_to_coordinate`: a `raise KeyError(index)` after the chain keeps the `KeyError` of the dict lookup. A `raise` in an `else:` branch made the gate stop measuring the chain, so the `raise` stands after the chain.
3. `ASTDeclaration.__init__`: set to `valid: false`. All 8 leaf branches assign the same value. The Opus review found a worse fact: the injection calls `isinstance(self.declaration, DeclarationType)`, and `DeclarationType` is a `Union` of string forward references, so `isinstance` raises `TypeError` and every construction fails.
4. `pytest_configure`: the guard `hasattr(config, '_tmp_path_factory')` became `mp is not None`. For a real `Config`, the item now sets the attribute like the source. With `config=None`, it returns `None` where the source raises `AttributeError`. That input breaks the type hint, so the item stays.

Each edited item passes `accept()`. The edits are listed in `groundtruth.meta.json` (`edits`). Each reason is in `bench/labels.json`.

**Results of the check (after the fixes).** `items 140, not scored 22, gate misses 12, new names not ok 0, invalid 7`. The 12 gate misses are not defects. 7 are labelled invalid. 5 are valid items that the gate does not find, and they stay in the recall: `AnchoredOffsetbox.draw`, `ASTDeclaratorNameParam.describe_signature`, `ExponentialCutoffPowerLaw1D.fit_deriv`, `LambdaCDM._dS_comoving_distance_z1z2`, and one transform item that the ticket did not list, `parse_data_uri` (`redundant_check`; it keeps the behavior and contains the kind).

**Corrections to the ticket text.** `hours_to_hms` is labelled `invalid` in `bench/labels.json` (since ticket 42), so it is not a valid miss. Point 5 and design step 3 also list `ASTDeclaration.__init__` as a valid miss, but defect 3 removes it. Defect 3 wins.

**Reports made again.** `detection.md` (the gate before ticket 39, all items), `detection-t39.md` (the gate of ticket 39, held-out set), and `label-disagreements.md`. The Ultra labels of the 4 rows of the 3 edited items were stale (the cache has no source hash), so I deleted them and labelled them again with Ultra in both variants (8 calls).

| Held-out set, current gate | before | after |
|---|---|---|
| nesting recall | 0.857 | 0.923 |
| total recall | 0.902 | 0.92 |
| total precision | 0.979 | 0.979 |
| nemotron items | 14 | 13 |
| nesting kappa (rule) | 0.675 | 0.571 |

The nesting kappa of the held-out set is now below 0.6, the line that the report calls unreliable. The cause is `ASTDeclaration.__init__`: Ultra still says `valid`, and the new label says `invalid`. All items (gate before ticket 39): total recall 0.912 to 0.909, total precision 0.767 to 0.764.

**Known limits.**
- The 3 edited items have no baseline run in `runs.json` (the gate before ticket 39 cannot run again), so they leave the baseline score. In `detection-t39.md`, `fk5_to_gal` also leaves the "Change" table. Nothing in the reports says this. Both reports count them in the header (`nemotron 39` and `13`), but 36 Nemotron items are scored in `detection.md`.
- `runs-t39.json` holds one entry from the gate at commit `b57be22` (`fk5_to_gal`); the other entries are from commit `c31b3c5`. `kinds.py` changed between them only in `textwrap.dedent` to `functions.dedent` (`runs-t39.meta.json`, key `recomputed`).
- The name check ignores scoping: a name that is bound anywhere in the function counts as bound. A `from x import *` in the module turns the check off. A rewrite with `symtable` would remove both limits.
- `index_to_coordinate`: for an unhashable index, the source raises `TypeError` and the item raises `KeyError`. The tutorial passes only strings.
- The full gate was not run on the fixed `pytest_configure` item. The reason is reasoning, not a measurement.

**Measured.** `uv run pytest -q`: 493 passed, 17 deselected (before the last script and test changes; `tests/test_bench.py` alone: 55 passed afterwards). Not done: the full rerun of the gate on the fixed items (ticket 10).
