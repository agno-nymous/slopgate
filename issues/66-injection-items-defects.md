# 66 — Some injected items of the detection benchmark change behavior or are not the kind they name

## Summary

- **Goal:** Make each injected item in `bench/results/groundtruth.json` keep the behavior of its source and contain the kind that it names. Example: the `fk5_to_gal` nesting injection uses the name `pmats`, which does not exist, so the function raises `NameError`.
- **Checkable finish condition:** A script lists each injected item with three facts: the current `accept()` keeps it or rejects it, the injection keeps behavior, and the kind is present by the one-line rule in `kinds.KINDS`. Each defective item is fixed or removed with a written reason, and `detection.md` is made again.
- **Evidence:** The Opus label review of ticket 42 (2026-10-17) found the defects below on the rows of `bench/labels.json`. The transform items were not reviewed.
- **Constraints:** Do not remove an item only because the current gate does not find it. A valid injection that the gate misses is a false negative, and it must stay in the recall.

**Blocked by:** —

**Status:** ready-for-agent

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

- [ ] The script lists each injected item with the three facts.
- [ ] Defects 1 to 4 are fixed or removed, each with a reason.
- [ ] `detection.md` and `detection-t39.md` are made again.
- [ ] `uv run pytest -q` passes.

## Comments
