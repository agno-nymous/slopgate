import random
import statistics
from collections import Counter
from dataclasses import replace

from slopgate import kinds
from slopgate.config import PRICES

WORKERS = 8
DRAWS = 1000
METRICS = ("precision", "recall", "fp_rate")


def split(items) -> dict[str, str]:
    keys = sorted({item.source_id or item.id for item in items})
    random.Random(39).shuffle(keys)
    tuning = set(keys[: round(0.6 * len(keys))])
    return {item.id: "tuning" if (item.source_id or item.id) in tuning else "held_out" for item in items}


def prepare(items: list, review: dict) -> tuple[list, dict]:
    injections = review["injections"]
    if missing := [item.id for item in items if item.origin == "nemotron" and item.id not in injections]:
        raise SystemExit(f"bench/labels.json has no `injections` entry for these Nemotron items: {', '.join(missing)}")
    # an invalid Nemotron item does not contain the kind it names, so it has no ground truth
    items = [item for item in items if item.origin != "nemotron" or injections[item.id]["valid"]]
    # the stored data still holds kinds that the gate no longer checks (filler_comment, ticket 39)
    items = [replace(item, injected=[k for k in item.injected if k in kinds.KINDS]) for item in items]
    items = [item for item in items if item.source_id is None or item.injected]
    labels = {i: {kind: label for kind, label in entry.items() if kind in kinds.KINDS} for i, entry in review["labels"].items()}
    return items, labels


def known(runs: dict) -> dict:
    def strip(run):
        return run | {"kinds": {k: v for k, v in run["kinds"].items() if k in kinds.KINDS}} if "kinds" in run else run

    return {i: [strip(run) for run in item_runs] for i, item_runs in runs.items()}


def truth(item, labels: dict, runs: dict) -> dict[str, bool]:
    own = {kind: label["decision"] == "slop" for kind, label in labels.get(item.id, {}).items()}
    if item.source_id is None:
        return own
    # a kind labelled or found on the source is scored once there; accept() rejects any other new kind, so the rest are exact
    on_source = labels.get(item.source_id, {}).keys() | {kind for run in runs.get(item.source_id, []) for kind in run.get("kinds", {})}
    scored = dict.fromkeys(kinds.KINDS, False) | own
    return {kind: value for kind, value in scored.items() if kind not in on_source} | dict.fromkeys(item.injected, True)


def outcomes(item, run: dict, labels: dict, runs: dict) -> list[tuple[str, str]]:
    expected = truth(item, labels, runs)
    found = set(run["kinds"])
    result = []
    for kind in found:
        if kind in expected:
            result.append((kind, "tp" if expected[kind] else "fp"))
        elif item.source_id is None:
            result.append((kind, "unlabelled"))
    return result + [(kind, "fn") for kind, value in expected.items() if value and kind not in found]


def ratio(a: int, b: int) -> float | None:
    return round(a / b, 3) if b else None


def scores(counts: Counter, items: set) -> dict:
    tp, fp, fn = counts["tp"], counts["fp"], counts["fn"]
    return {"items": len(items), "tp": tp, "fp": fp, "fn": fn, "precision": ratio(tp, tp + fp), "recall": ratio(tp, tp + fn)}


def score(items: list, runs: dict, review: dict) -> dict:
    items, labels = prepare(items, review)
    runs = known(runs)
    injections = review["injections"]
    groups = {
        "all": items,
        "transform": [i for i in items if i.origin == "transform"],
        "nemotron": [i for i in items if i.origin == "nemotron"],
        "two_kinds": [i for i in items if len(i.injected) == 2],
    }
    report = {"groups": {}, "invalid_injections": {i: entry["reason"] for i, entry in injections.items() if not entry["valid"]}}
    for name, members in groups.items():
        counts = {kind: Counter() for kind in kinds.KINDS}
        scored = {kind: set() for kind in kinds.KINDS}
        for item in members:
            for run in runs.get(item.id, []):
                for kind, outcome in outcomes(item, run, labels, runs) if "kinds" in run else []:
                    counts[kind][outcome] += 1
                    if outcome != "unlabelled":
                        scored[kind].add(item.id)
        report["groups"][name] = {kind: scores(counts[kind], scored[kind]) for kind in kinds.KINDS} | {
            "total": scores(sum(counts.values(), Counter()), set().union(*scored.values()))
        }

    listed = Counter(
        (outcome, item.id, kind)
        for item in items
        for run in runs.get(item.id, [])
        if "kinds" in run
        for kind, outcome in outcomes(item, run, labels, runs)
        if outcome != "tp"
    )
    for outcome, key in (("fp", "false_positives"), ("fn", "false_negatives"), ("unlabelled", "unlabelled")):
        report[key] = [{"id": i, "kind": k, "runs": n} for (o, i, k), n in sorted(listed.items()) if o == outcome]

    clean_runs = [(item, run) for item in items if item.origin == "clean" for run in runs.get(item.id, []) if "kinds" in run]
    fps = [{kind for kind, outcome in outcomes(item, run, labels, runs) if outcome == "fp"} for item, run in clean_runs]
    report["clean"] = {
        "item_runs": len(clean_runs),
        "fp_rate": {kind: ratio(sum(kind in f for f in fps), len(fps)) for kind in kinds.KINDS} | {"total": ratio(sum(bool(f) for f in fps), len(fps))},
        "any_kind_rate": ratio(sum(bool(run["kinds"]) for _, run in clean_runs), len(clean_runs)),
    }

    seconds = sorted(run["seconds"] for item in items for run in runs.get(item.id, []) if "kinds" in run)
    report["seconds"] = (
        {
            "mean": round(statistics.mean(seconds), 3),
            "median": round(statistics.median(seconds), 3),
            "p95": round(seconds[int(0.95 * (len(seconds) - 1))], 3),
            "max": seconds[-1],
        }
        if seconds
        else {}
    )
    report["errors"] = [{"id": item.id, "error": run["error"]} for item in items for run in runs.get(item.id, []) if "error" in run]

    def stable(members):
        sets = [{frozenset(run.get("kinds", {"error": 1})) for run in runs[item.id]} for item in members if runs.get(item.id)]
        return ratio(sum(len(s) == 1 for s in sets), len(sets))

    report["stability"] = {"all": stable(items)} | {origin: stable([i for i in items if i.origin == origin]) for origin in ("clean", "source", "transform", "nemotron")}
    report["counts"] = {"origin": dict(Counter(i.origin for i in items)), "repo": dict(Counter(i.repo for i in items))}
    return report


def tally(item, item_runs: list, labels: dict, runs: dict) -> Counter:
    counts = Counter()
    for run in item_runs:
        if "kinds" not in run:
            continue
        found = [(kind, outcome) for kind, outcome in outcomes(item, run, labels, runs) if outcome != "unlabelled"]
        counts.update(found + [("total", outcome) for _, outcome in found])
        if item.origin == "clean":
            fps = {kind for kind, outcome in found if outcome == "fp"}
            counts.update([("clean", "runs")] + [(kind, "clean_fp") for kind in fps] + [("total", "clean_fp")] * bool(fps))
    return counts


def metric(counts: Counter, kind: str, name: str) -> float | None:
    tp, fp, fn = counts[kind, "tp"], counts[kind, "fp"], counts[kind, "fn"]
    a, b = {"precision": (tp, tp + fp), "recall": (tp, tp + fn), "fp_rate": (counts[kind, "clean_fp"], counts["clean", "runs"])}[name]
    return a / b if b else None


def measures(before: Counter, after: Counter, kind: str, name: str) -> dict[str, float | None]:
    b, a = metric(before, kind, name), metric(after, kind, name)
    return {"base": b, "new": a, "difference": None if a is None or b is None else a - b}


def interval(point: float | None, values: list[float]) -> dict:
    values = sorted(values)
    low, high = (values[int(q * (len(values) - 1))] for q in (0.025, 0.975)) if values else (None, None)
    result = {key: None if v is None else round(v, 3) for key, v in (("value", point), ("low", low), ("high", high))}
    return result | ({"resamples": len(values)} if len(values) != DRAWS else {})


def compare(items: list, review: dict, base: dict, new: dict) -> dict:
    items, labels = prepare(items, review)
    base, new = known(base), known(new)
    # both arms take "found on the source" from the runs of both, so they score each item against the same ground truth
    both = {i: base.get(i, []) + new.get(i, []) for i in base.keys() | new.keys()}
    # the unit of resampling is the function: a source and its injected items move together
    functions = {}
    for item in items:
        if base.get(item.id) and new.get(item.id):
            before, after = functions.setdefault(item.source_id or item.id, (Counter(), Counter()))
            before.update(tally(item, base[item.id], labels, both))
            after.update(tally(item, new[item.id], labels, both))
    keys = sorted(functions)
    rng = random.Random(39)
    draws = []
    for _ in range(DRAWS):
        before, after = Counter(), Counter()
        for key in rng.choices(keys, k=len(keys)):
            before.update(functions[key][0])
            after.update(functions[key][1])
        draws.append((before, after))
    full = tuple(sum((pair[n] for pair in functions.values()), Counter()) for n in (0, 1))
    result = {}
    for kind in [*kinds.KINDS, "total"]:
        result[kind] = {}
        for name in METRICS:
            point = measures(*full, kind, name)
            samples = [measures(*draw, kind, name) for draw in draws]
            result[kind][name] = {variant: interval(value, [s[variant] for s in samples if s[variant] is not None]) for variant, value in point.items()}
    return result


def cost(model: str, usage: dict) -> float:
    price_in, price_out = PRICES[model]
    return round((usage["input_tokens"] * price_in + usage["output_tokens"] * price_out) / 1e6, 4)


def markdown(report: dict) -> str:
    def row(*cells):
        return "| " + " | ".join("" if c is None else str(c) for c in cells) + " |"

    def cell(entry):
        return "" if entry["value"] is None else f"{entry['value']} [{entry['low']}, {entry['high']}]" + (f" ({entry['resamples']} resamples)" if "resamples" in entry else "")

    out = [f"# Detection benchmark: {report['runs']}, {report['set']}", ""]
    if change := report.get("change"):
        out += ["## Change against the gate before ticket 39", "", f"Each cell is the value and its 95% range from {DRAWS} bootstrap resamples of whole functions.", ""]
        header = [f"{variant} {name}" for name in ("precision", "recall", "FP rate") for variant in ("base", "new", "difference")]
        out += [row("kind", *header), row(*["---"] * 10)]
        out += [row(kind, *(cell(entry[name][variant]) for name in METRICS for variant in ("base", "new", "difference"))) for kind, entry in change.items()] + [""]
    out += ["`items` is the number of distinct items with at least one TP, FP, or FN.", ""]
    for name, group in report["groups"].items():
        out += [f"## Precision and recall: {name}", "", row("kind", "items", "TP", "FP", "FN", "precision", "recall"), row(*["---"] * 7)]
        out += [row(kind, s["items"], s["tp"], s["fp"], s["fn"], s["precision"], s["recall"]) for kind, s in group.items()] + [""]
    clean = report["clean"]
    out += ["## False positives on clean functions", "", f"Clean item-runs: {clean['item_runs']}. Share with any kind: {clean['any_kind_rate']}.", ""]
    out += [row("kind", "false-positive rate"), row("---", "---")] + [row(kind, rate) for kind, rate in clean["fp_rate"].items()] + [""]
    seconds = report["seconds"]
    out += ["## Time for each function (seconds)", "", row("mean", "median", "p95", "max"), row(*["---"] * 4), row(*(seconds.get(k) for k in ("mean", "median", "p95", "max"))), ""]
    out += [f"{WORKERS} worker processes; times include queueing.", ""]
    out += ["## Tokens and cost", ""]
    out += [row("model", "use", "input tokens", "output tokens", "USD"), row(*["---"] * 5)]
    out += [row(m["model"], m["use"], m["input_tokens"], m["output_tokens"], m["usd"]) for m in report["tokens"]] + [""]
    out += ["## Stability (same kinds in all runs)", "", row("items", "share"), row("---", "---")] + [row(k, v) for k, v in report["stability"].items()] + [""]
    out += ["## Counts", "", row("origin", "items"), row("---", "---")] + [row(k, v) for k, v in report["counts"]["origin"].items()] + [""]
    out += [row("repo", "items"), row("---", "---")] + [row(k, v) for k, v in report["counts"]["repo"].items()] + [""]
    for key, title in (("false_positives", "False positives"), ("false_negatives", "False negatives"), ("unlabelled", "Unlabelled kinds")):
        out += [f"## {title}", "", row("item", "kind", "runs"), row(*["---"] * 3)] + [row(e["id"], e["kind"], e["runs"]) for e in report[key]] + [""]
    out += ["## Errors", "", row("item", "error"), row("---", "---")] + [row(e["id"], e["error"]) for e in report["errors"]] + [""]
    return "\n".join(out)
