import difflib
import json
import os
import re
import subprocess
import sys
from datetime import datetime

from bench.paths import RESULTS, write
from bench.score import cost

ROOT = RESULTS.parent.parent
DEMO = ROOT / "docs" / "demo"
RECORDINGS = DEMO / "recordings"
README = "https://github.com/agno-nymous/slopgate#try-slopgate-on-your-machine"
PHOENIX_CLI = "@arizeai/phoenix-cli@1.18.9"

STEPS = [{"name": name} for name in ("Candidates", "Kinds", "Tests", "Rewrite", "Proof")]

SPEC = {
    "pylint-7993": {
        "project": "pylint",
        "source": {"label": "pylint, SWE-bench pylint-dev__pylint-7993", "url": "https://github.com/pylint-dev/pylint"},
        "why": "A long if/elif chain in a linter. The rewrite is a dict lookup, and the complexity falls from 12 to 2.",
    },
    "pytest-7220": {
        "project": "pytest",
        "source": {"label": "pytest, SWE-bench pytest-dev__pytest-7220", "url": "https://github.com/pytest-dev/pytest"},
        "why": "Dead code in the capture code of pytest. The tests ran on the old and on the new code in the sandbox.",
    },
    "seaborn-3190": {
        "project": "seaborn",
        "source": {"label": "seaborn, SWE-bench mwaskom__seaborn-3190", "url": "https://github.com/mwaskom/seaborn"},
        "why": "A plotting library. One run proves a swallowed error and a deeply nested method.",
    },
    "flask-4992": {
        "project": "flask",
        "source": {"label": "flask, SWE-bench pallets__flask-4992", "url": "https://github.com/pallets/flask"},
        "why": "A web framework. The review proves fixes of more than one kind in the same run.",
    },
}

HOW = [
    {"text": "Install <a href=\"https://docs.astral.sh/uv/\">uv</a>, and get your keys at <a href=\"https://tokenfactory.nebius.com/project/api-keys\">Nebius Token Factory</a>."},
    {"text": "Set the keys in your shell. Slopgate sends them to Nebius only.", "cmd": "export NEBIUS_API_KEY=... NEBIUS_PROJECT_ID=..."},
    {"text": "Clone the repository you want to review, and check out the branch to review. Then run a dry run on its last commit. A dry run posts nothing to GitHub.", "cmd": "uvx --from git+https://github.com/agno-nymous/slopgate slopgate review --repo . --base HEAD~1 --head HEAD --dry-run"},
    {"text": f"The <a href=\"{README}\">README</a> has the full steps and the cost of one review."},
]

STEP_SPANS = ["gate.index", "sandbox.prepare", "gate.collect", "gate.baseline", "gate.characterize", "gate.rewrite", "gate.proof", "gate.repo_suite"]
SUGGESTION = re.compile(r"```suggestion\n(.*?)```", re.S)
PASSED = re.compile(r"(\d+) characterization tests passed")
OF = re.compile(r"rewrite of `([^`]+)`")
SPANS = 5000


def px(*args) -> list:
    env = {"PHOENIX_ENDPOINT": "http://127.0.0.1:6006", "PHOENIX_PROJECT": "slopgate-gate", **os.environ}
    out = subprocess.run(["npx", "-y", PHOENIX_CLI, "span", "list", *args, "--format", "raw", "--no-progress"], capture_output=True, text=True, check=True, env=env)
    return json.loads(out.stdout)


def seconds(span: dict) -> float:
    return (datetime.fromisoformat(span["end_time"]) - datetime.fromisoformat(span["start_time"])).total_seconds()


def diff_rows(before: str, after: str, context: int) -> list:
    rows = []
    for line in list(difflib.unified_diff(before.splitlines(), after.splitlines(), lineterm="", n=context))[2:]:
        rows.append(["@", ""] if line.startswith("@@") else [line[0], line[1:]])
    return [row for index, row in enumerate(rows) if row[0] != "@" or index]


def trace_of(result: dict) -> list:
    roots = [root for root in px("--name", "gate.review", "--parent-id", "null", "--limit", "200") if "output.value" in root["attributes"] and json.loads(root["attributes"]["output.value"]) == result]
    if len(roots) != 1:
        raise RuntimeError(f"{len(roots)} Phoenix traces match this recording; expected 1")
    spans = px("--trace-id", roots[0]["context"]["trace_id"], "--limit", str(SPANS))
    if len(spans) >= SPANS:
        raise RuntimeError("the trace has more spans than the limit")
    return spans


def proof_tests(spans: list) -> dict:
    parent = {s["context"]["span_id"]: s["parent_id"] for s in spans}
    function = {s["context"]["span_id"]: s["attributes"].get("metadata.qualname") for s in spans if s["name"] == "gate.function"}
    tests = {}
    for span in sorted((s for s in spans if s["name"] == "sandbox.run"), key=lambda s: s["start_time"]):
        node = span["context"]["span_id"]
        while node and node not in function:
            node = parent.get(node)
        files = json.loads(span["attributes"]["input.value"]).get("files", {})
        for path, text in files.items():
            if node and re.fullmatch(r"tests/test_slopgate_\d+\.py", path):
                tests[function[node]] = text
    return tests


def items_of(result: dict, repo: str, head: str, tests: dict) -> list:
    def show(path):
        return subprocess.run(["git", "-C", repo, "show", f"{head}:{path}"], capture_output=True, text=True, check=True).stdout

    items = []
    for entry in result["suggestions"]:
        body = entry["body"]
        name, passed = OF.search(body)[1], PASSED.search(body)
        start = entry.get("start_line", entry["line"])
        before = "".join(show(entry["path"]).splitlines(keepends=True)[start - 1 : entry["line"]])
        kinds = re.findall(r"`(\w+)`", body.split(")")[0])
        items.append({"where": "inline suggestion", "function": name, "path": entry["path"], "kinds": kinds, "summary": body.split("\n\n")[0].split("\n", 1)[1], "diff": diff_rows(before, SUGGESTION.search(body)[1], 1), "tests": tests.get(name), "tests_passed": passed and int(passed[1])})
    for entry in result["followup"]:
        rows = []
        for path, after in entry["files"].items():
            rows += [["@", path]] + diff_rows(show(path), after, 2)
        passed = PASSED.search(entry["reason"])
        # A duplicate follow-up has no tests of its own: its last sandbox run swaps the import, so tests.get would label that file wrongly.
        own = None if entry["kinds"] == ["duplicate"] else tests.get(entry["function"])
        items.append({"where": "follow-up pull request", "function": entry["function"], "path": next(iter(entry["files"])), "kinds": entry["kinds"], "summary": entry["reason"].split("\n", 1)[-1] if passed else entry["reason"], "diff": rows, "tests": own, "tests_passed": passed and int(passed[1])})
    return items


def meta(name: str, repo: str, head: str) -> None:
    result = json.loads((RECORDINGS / f"{name}.json").read_text())
    spans = trace_of(result)
    used = {}
    for span in spans:
        if span["name"] == "ChatCompletion" and "llm.model_name" in span["attributes"]:
            usage = used.setdefault(span["attributes"]["llm.model_name"], {"input_tokens": 0, "output_tokens": 0})
            usage["input_tokens"] += span["attributes"].get("llm.token_count.prompt", 0)
            usage["output_tokens"] += span["attributes"].get("llm.token_count.completion", 0)
    steps = []
    for step in STEP_SPANS:
        found = [s for s in spans if s["name"] == step]
        if found:
            steps.append({"name": step, "count": len(found), "seconds": round(sum(seconds(s) for s in found), 1)})
    root = next(s for s in spans if s["name"] == "gate.review")
    write(
        RECORDINGS / f"{name}.meta.json",
        {
            "seconds": round(seconds(root)),
            "usd": round(sum(cost(model, usage) for model, usage in used.items()), 4),
            "tokens": ", ".join(f"{usage['input_tokens'] + usage['output_tokens']:,} tokens ({model.split('/')[-1]})" for model, usage in used.items()),
            "trace": root["context"]["trace_id"],
            "steps": steps,
            "rejected": sum(1 for entry in result["rejected"] if "function" in entry),
            "items": items_of(result, repo, head, proof_tests(spans)),
        },
    )


def headline() -> dict:
    report = json.loads((RESULTS / "swebench" / "swebench.json").read_text())
    kinds = [{"kind": name, **row} for name, row in report["kinds"].items() if not name.endswith(")")]
    total = report["total"]
    runs = json.loads((RESULTS / "swebench" / "runs.json").read_text())
    cells = {}
    for run in runs.values():
        for item in run["items"]:
            cells.setdefault(item["kind"], []).append("proven" if item["accepted"] else "note" if item["detected"] else "missed")
    return {
        "items": total["items"],
        "detected": total["detected"],
        "accepted": total["accepted"],
        "silent_breaks": total["silent_breaks"],
        "usd": report["usd"],
        "instances": report["metadata"]["runs"]["counts"]["instances"],
        "repositories": len({instance.rsplit("-", 1)[0] for instance in runs}),
        "kinds": [{"kind": k["kind"], "cells": sorted(cells[k["kind"]], key=["proven", "note", "missed"].index)} for k in kinds],
    }


def reviews() -> list:
    out = []
    for name, spec in SPEC.items():
        view = json.loads((RECORDINGS / f"{name}.meta.json").read_text())
        names = ", ".join(item["function"] for item in view["items"])
        out.append(spec | view | {"slug": name, "title": f"{spec['project']}: {len(view['items'])} proven {'fix' if len(view['items']) == 1 else 'fixes'}, {names}"})
    return out


def data() -> dict:
    return {"headline": headline(), "steps": STEPS, "reviews": reviews(), "how": HOW}


if __name__ == "__main__":
    match sys.argv[1:]:
        case ["meta", name, repo, head]:
            meta(name, repo, head)
        case _:
            sys.exit("usage: python -m bench.showcase meta <name> <repo> <head>   (python -m bench.pages writes the pages)")
