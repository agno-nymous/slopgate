import statistics
from collections import Counter

from slopgate import kinds
from slopgate.config import PRICES

MEASURED = set(kinds.KINDS) - set(kinds.RULES)
WORKERS = 8


def truth(item, labels: dict) -> dict[str, bool]:
    own = {kind: label["decision"] == "slop" for kind, label in labels.get(item.id, {}).items()}
    if item.source_id is None:
        return own
    # a kind on the source is scored once there; accept() rejects any new measured kind, so the other measured kinds are exact
    scored = dict.fromkeys(MEASURED, False) | own
    return {kind: value for kind, value in scored.items() if kind not in labels.get(item.source_id, {})} | dict.fromkeys(item.injected, True)


def outcomes(item, run: dict, labels: dict) -> list[tuple[str, str]]:
    expected = truth(item, labels)
    on_source = labels.get(item.source_id, {})
    found = set(run["kinds"])
    result = []
    for kind in found:
        if kind in expected:
            result.append((kind, "tp" if expected[kind] else "fp"))
        elif kind not in on_source:
            result.append((kind, "unlabelled"))
    return result + [(kind, "fn") for kind, value in expected.items() if value and kind not in found]


def ratio(a: int, b: int) -> float | None:
    return round(a / b, 3) if b else None


def scores(counts: Counter, items: set) -> dict:
    tp, fp, fn = counts["tp"], counts["fp"], counts["fn"]
    return {"items": len(items), "tp": tp, "fp": fp, "fn": fn, "precision": ratio(tp, tp + fp), "recall": ratio(tp, tp + fn)}


def score(items: list, runs: dict, review: dict) -> dict:
    injections = review["injections"]
    if missing := [item.id for item in items if item.origin == "nemotron" and item.id not in injections]:
        raise SystemExit(f"bench/labels.json has no `injections` entry for these Nemotron items: {', '.join(missing)}")
    # an invalid Nemotron item does not contain the kind it names, so it has no ground truth
    items = [item for item in items if item.origin != "nemotron" or injections[item.id]["valid"]]
    labels = review["labels"]
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
                for kind, outcome in outcomes(item, run, labels) if "kinds" in run else []:
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
        for kind, outcome in outcomes(item, run, labels)
        if outcome != "tp"
    )
    for outcome, key in (("fp", "false_positives"), ("fn", "false_negatives"), ("unlabelled", "unlabelled")):
        report[key] = [{"id": i, "kind": k, "runs": n} for (o, i, k), n in sorted(listed.items()) if o == outcome]

    clean_runs = [(item, run) for item in items if item.origin == "clean" for run in runs.get(item.id, []) if "kinds" in run]
    fps = [{kind for kind, outcome in outcomes(item, run, labels) if outcome == "fp"} for item, run in clean_runs]
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


def cost(model: str, usage: dict) -> float:
    price_in, price_out = PRICES[model]
    return round((usage["input_tokens"] * price_in + usage["output_tokens"] * price_out) / 1e6, 4)


def markdown(report: dict) -> str:
    def row(*cells):
        return "| " + " | ".join("" if c is None else str(c) for c in cells) + " |"

    out = ["# Detection benchmark", "", "`items` is the number of distinct items with at least one TP, FP, or FN.", ""]
    for name, group in report["groups"].items():
        out += [f"## Precision and recall: {name}", "", row("kind", "items", "TP", "FP", "FN", "precision", "recall"), row(*["---"] * 7)]
        out += [row(kind, s["items"], s["tp"], s["fp"], s["fn"], s["precision"], s["recall"]) for kind, s in group.items()] + [""]
    clean = report["clean"]
    out += ["## False positives on clean functions", "", f"Clean item-runs: {clean['item_runs']}. Share with any kind: {clean['any_kind_rate']}.", ""]
    out += [row("kind", "false-positive rate"), row("---", "---")] + [row(kind, rate) for kind, rate in clean["fp_rate"].items()] + [""]
    seconds = report["seconds"]
    out += ["## Time for each function (seconds)", "", row("mean", "median", "p95", "max"), row(*["---"] * 4), row(*(seconds.get(k) for k in ("mean", "median", "p95", "max"))), ""]
    out += [f"{WORKERS} worker processes; times include queueing.", ""]
    out += ["## Tokens and cost", "", "The Lightning tokens count all runs, including the runs of the excluded Nemotron items.", ""]
    out += [row("model", "use", "input tokens", "output tokens", "USD"), row(*["---"] * 5)]
    out += [row(m["model"], m["use"], m["input_tokens"], m["output_tokens"], m["usd"]) for m in report["tokens"]] + [""]
    out += ["## Stability (same kinds in all runs)", "", row("items", "share"), row("---", "---")] + [row(k, v) for k, v in report["stability"].items()] + [""]
    out += ["## Counts", "", row("origin", "items"), row("---", "---")] + [row(k, v) for k, v in report["counts"]["origin"].items()] + [""]
    out += [row("repo", "items"), row("---", "---")] + [row(k, v) for k, v in report["counts"]["repo"].items()] + [""]
    for key, title in (("false_positives", "False positives"), ("false_negatives", "False negatives"), ("unlabelled", "Unlabelled kinds")):
        out += [f"## {title}", "", row("item", "kind", "runs"), row(*["---"] * 3)] + [row(e["id"], e["kind"], e["runs"]) for e in report[key]] + [""]
    out += ["## Errors", "", row("item", "error"), row("---", "---")] + [row(e["id"], e["error"]) for e in report["errors"]] + [""]
    return "\n".join(out)
