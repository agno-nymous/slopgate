import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from pydantic import BaseModel, Field

from bench.paths import GROUNDTRUTH, LABELS, RESULTS, all_runs, write
from bench.score import agreement, cost, metadata
from slopgate import kinds, llm, trace
from slopgate.config import ULTRA
from slopgate.functions import dedent

VARIANTS = ("rule", "definition")
DEFINITIONS = {
    "nesting": "A block (if, for, while, with, or try) sits more than 2 levels deep in the function; an elif does not add a level. And an if on that deep path can be made flatter in one of these ways: one branch of an if/else ends with return, raise, continue, or break, so the other branch can move out of the if; an if at the end of the function or of a loop body wraps more blocks, so it can become a guard clause; or an if holds only another if, so the two conditions can join with `and`. Depth alone is not this kind: if no such change makes the code flatter, the answer is False.",
    "redundant_check": "An if tests a condition, or its negation, that an earlier if on the same path already decided, and no statement between them can change a value that the condition reads (an assignment to it or any function call can change it). Inside the body of `if c:` the test c is known true; inside its else, c is known false; after an `if c:` whose body ends with return, raise, continue, or break, c is known false. An if that tests a new fact is not this kind, even if its body does nothing.",
    "swallowed_error": "A bare `except:` clause, which is always this kind. Or an except clause that catches Exception or BaseException and does not raise again. Or an except handler whose body is only `pass` or `continue`, so the error disappears.",
    "lookup_table": "An if/elif chain that compares one value with a different constant in each branch, and each branch only returns a value. A dict lookup can replace the chain.",
    "dead": "A local variable that gets a value and is never read, including one name of a tuple unpacking. Or a statement that can never run, such as a statement after return, raise, continue, or break in the same block.",
}
NO_EVIDENCE = "The detector gave no evidence lines."
LABEL_NAMES = {"label": ("slop", "false positive"), "injection": ("valid", "invalid")}
DISAGREEMENTS = RESULTS / "label-disagreements.md"

LABEL_PROMPT = """Decide whether the Python function below has this kind of slop: {kind}.

The rule for this kind: {rule}{definition}

Evidence lines from a static check:
{evidence}

Decide by the rule, for this function only. The evidence lines can be wrong.

File: {path}

```python
{source}
```"""


class Label(BaseModel):
    """Report whether the function has this kind of slop by the rule."""

    reason: str = Field(description="One or two sentences. Quote the line of the function that decides the answer.")
    slop: bool = Field(description="True only if the function has this kind of slop by the rule. False if the rule does not apply to the function.")


def row(item: dict, kind: str, origin: str, first: bool, first_reason: str, evidence: list[str]) -> dict:
    return {
        "key": f"{item['id']}|{kind}",
        "id": item["id"],
        "kind": kind,
        "origin": origin,
        "first": first,
        "first_reason": first_reason,
        "path": item["path"],
        "source": dedent(item["source"]).rstrip("\n"),
        "evidence": evidence or [NO_EVIDENCE],
    }


def rows(groundtruth_items: list[dict], review: dict, runs_list: list[dict]) -> list[dict]:
    by_id = {item["id"]: item for item in groundtruth_items}
    found = []
    for item_id, entry in review["labels"].items():
        for kind, label in entry.items():
            if kind in kinds.KINDS:
                lines = next((run["kinds"][kind] for runs in runs_list for run in runs.get(item_id, []) if kind in run.get("kinds", {})), [])
                found.append(row(by_id[item_id], kind, "label", label["decision"] == "slop", label["reason"], lines))
    for item_id, entry in review["injections"].items():
        kind = item_id.rsplit(":", 1)[1]
        if kind in kinds.KINDS:
            found.append(row(by_id[item_id], kind, "injection", entry["valid"], entry["reason"], by_id[item_id]["changed_lines"]))
    return found


def cache(variant: str) -> Path:
    return RESULTS / ("labels-ultra.json" if variant == "rule" else f"labels-ultra-{variant}.json")


def prompt(r: dict, variant: str = "definition") -> str:
    definition = f"\n\nThe full definition of this kind: {DEFINITIONS[r['kind']]}" if variant == "definition" else ""
    evidence = "\n".join(f"- {line}" for line in r["evidence"])
    return LABEL_PROMPT.format(kind=r["kind"], rule=kinds.KINDS[r["kind"]], definition=definition, evidence=evidence, path=r["path"], source=r["source"])


def ask(r: dict, variant: str) -> Label | None:
    with trace.span("bench.label_row", key=r["key"], origin=r["origin"], prompt="LABEL_PROMPT", variant=variant):
        try:
            reply = llm.decide(ULTRA, prompt(r, variant), Label)
        except Exception as error:
            print(f"{r['key']}: {error!r}", file=sys.stderr)
            reply = None
        trace.output(reply and reply.model_dump())
        return reply


def setup(variant: str) -> dict:
    prompts = {"LABEL_PROMPT": LABEL_PROMPT, "KINDS": json.dumps(kinds.KINDS, sort_keys=True), "Label": json.dumps(Label.model_json_schema(), sort_keys=True)}
    if variant == "definition":
        prompts["DEFINITIONS"] = json.dumps(DEFINITIONS, sort_keys=True)
    return metadata({"second_labeller": ULTRA}, prompts, {}, 1)


def disagreements(rows: list[dict], second: dict, variant: str) -> str:
    def cell(origin, value, reason):
        return f"{LABEL_NAMES[origin][not value]}: {reason}".replace("|", "\\|").replace("\n", " ")

    out = [
        f"## Prompt: {variant}",
        "",
        "| item | kind | origin | first label | second label |",
        "| --- | --- | --- | --- | --- |",
    ]
    for r in rows:
        other = second[r["key"]]
        if r["first"] != other["slop"]:
            out.append(f"| {r['id']} | {r['kind']} | {r['origin']} | {cell(r['origin'], r['first'], r['first_reason'])} | {cell(r['origin'], other['slop'], other['reason'])} |")
    return "\n".join(out) + "\n"


def summary(items: list[dict], review: dict, runs_list: list[dict]) -> tuple[dict, str | None, list[dict]]:
    sections = ["# Label disagreements", "", "Rows where the first labeller (`bench/labels.json`) and the second labeller (Ultra) disagree. The benchmark still scores with `bench/labels.json`.", ""]
    ids = {item["id"] for item in items}
    review = {part: {i: entry for i, entry in review[part].items() if i in ids} for part in ("labels", "injections")}
    by_variant, tokens = {}, []
    for variant in (v for v in VARIANTS if cache(v).exists()):
        second = json.loads(cache(variant).read_text())
        labelled = [r for r in rows(items, review, runs_list) if r["key"] in second["rows"]]
        by_variant[variant] = agreement([(r["kind"], r["first"], second["rows"][r["key"]]["slop"]) for r in labelled])
        sections.append(disagreements(labelled, second["rows"], variant))
        usage = second["usage"]
        tokens.append({"model": ULTRA, "use": f"second labeller ({variant})"} | {k: usage[k] for k in ("input_tokens", "output_tokens")} | {"usd": cost(ULTRA, usage)})
    return by_variant, "\n".join(sections) if by_variant else None, tokens


def main(variant: str = "definition") -> None:
    if variant not in VARIANTS:
        raise SystemExit(f"unknown variant {variant!r}, use one of {VARIANTS}")
    file = cache(variant)
    current = setup(variant)
    stored = json.loads(file.read_text()) if file.exists() else {"metadata": current, "usage": {"calls": 0, "input_tokens": 0, "output_tokens": 0}, "rows": {}}
    if stored.get("metadata", {}).get("prompts") != current["prompts"]:
        raise SystemExit(f"the {variant!r} labels in {file} come from other prompts than the current ones: move the file aside and run again")

    trace.start("slopgate-bench")
    items = json.loads(GROUNDTRUTH.read_text())["items"]
    review = json.loads(LABELS.read_text())
    todo = [r for r in rows(items, review, all_runs()) if r["key"] not in stored["rows"]]
    used = len(llm.usage)
    with trace.span("bench.label", rows=len(todo), variant=variant), ThreadPoolExecutor(8) as threads:
        for r, reply in zip(todo, threads.map(trace.bind(ask), todo, [variant] * len(todo))):
            if reply is None:
                print(f"{r['key']}: no label", file=sys.stderr)
            else:
                stored["rows"][r["key"]] = {"slop": reply.slop, "reason": reply.reason}
    calls = llm.usage[used:]
    usage = stored["usage"]
    usage["calls"] += len(calls)
    usage["input_tokens"] += sum(c[1] for c in calls)
    usage["output_tokens"] += sum(c[2] for c in calls)
    write(file, stored)
    print(f"labelled {len(todo)} rows, {len(stored['rows'])} in the cache", file=sys.stderr)


if __name__ == "__main__":
    main(*sys.argv[1:2])
