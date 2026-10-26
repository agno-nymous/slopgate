import ast
import json
import random
import re
import shutil
import statistics
import subprocess
import sys
import threading
import time
import traceback
import urllib.request
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import NamedTuple
from uuid import UUID

from contree_sdk import ContreeSync

from bench.detect import CACHE, ROWS, SKIPPED, changed, checkout, git, parses
from bench.paths import RESULTS, meta_path, stored_meta, write
from bench.score import WORKERS, cost, metadata, ratio, row, run_metadata
from bench.transforms import TRANSFORMS, body_line, control, duplicate, sites, transform, wrapper
from slopgate import diff, kinds, llm, review, trace
from slopgate.config import SUPER, ULTRA
from slopgate.functions import Function, complexity, dedent, is_test_file, nesting, parse, structure_hash
from slopgate.review import strip_fence
from slopgate.sandbox import Contree, InstallError, collect_error, commands, commit_date, tail

SWEBENCH = RESULTS / "swebench"
GROUNDTRUTH = SWEBENCH / "groundtruth.json"
RUNS = SWEBENCH / "runs.json"
REPORT = SWEBENCH / "swebench"
INSTALL = SWEBENCH / "install"
HEADS = SWEBENCH / "heads"
LITE = CACHE / "swebench-lite.json"
REPLIES = CACHE / "swebench-super.json"
CLONES = CACHE / "swebench"

INSTANCES = [
    "pytest-dev__pytest-5227",
    "pytest-dev__pytest-7220",
    "pytest-dev__pytest-8365",
    "pytest-dev__pytest-5692",
    "pytest-dev__pytest-7432",
    "sphinx-doc__sphinx-8627",
    "sphinx-doc__sphinx-8506",
    "sphinx-doc__sphinx-7975",
    "pylint-dev__pylint-7993",
    "pylint-dev__pylint-5859",
    "psf__requests-3362",
    "pallets__flask-4992",
    "pallets__flask-5063",
    "pydata__xarray-4248",
    "mwaskom__seaborn-3190",
]
EXTRA = [
    "psf__requests-1963",
    "pydata__xarray-3364",
    "sympy__sympy-11400",
    "scikit-learn__scikit-learn-10297",
    "matplotlib__matplotlib-18869",
    "astropy__astropy-6938",
    "scikit-learn__scikit-learn-10508",
    "scikit-learn__scikit-learn-11040",
    "matplotlib__matplotlib-22711",
    "matplotlib__matplotlib-23299",
    "astropy__astropy-12907",
    "astropy__astropy-14182",
    "sympy__sympy-12171",
]
TESTS = {
    "pytest-dev/pytest": "testing",
    "sphinx-doc/sphinx": "tests",
    "pylint-dev/pylint": "tests",
    "psf/requests": "tests",
    "pallets/flask": "tests",
    "pydata/xarray": "xarray/tests",
    "mwaskom/seaborn": "tests",
    "sympy/sympy": "sympy",
    "scikit-learn/scikit-learn": "sklearn",
    "matplotlib/matplotlib": "lib/matplotlib/tests",
    "astropy/astropy": "astropy",
}
FIELDS = ("repo", "instance_id", "base_commit", "patch", "test_patch", "PASS_TO_PASS")
IMAGE = "docker.io/swebench/sweb.eval.x86_64.{}:latest"
# the default PATH of the image puts the base conda env first, and its python is not the one with the repo installed
TESTBED_PATH = "/opt/miniconda3/envs/testbed/bin:/opt/miniconda3/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
PYTEST = "-rA -p no:cacheprovider --continue-on-collection-errors"
# the gate sandbox pins pytest 2.9 for this commit, and pytest before 3.0 has no --continue-on-collection-errors.
# Add an instance here when its install report shows "unrecognized arguments: --continue-on-collection-errors".
OLD_PYTEST = {"psf__requests-3362"}
MARK = "--bench-coverage--"
HIDDEN_SECONDS = 900
PER_INSTANCE = 3
TRIES = 6
SEED = 10
ORDER = [*TRANSFORMS, "wrapper", "duplicate"]
PATTERNS = ["test_*.py", "*_test.py"]
OUTCOME = {"suggestions": "suggestion", "followup": "followup", "rejected": "rejected", "notes": "note"}
INFRASTRUCTURE = ("error", "no_environment")
BENCH_TEST = "python -m pytest -q -rfE {}"

DUPLICATE_PROMPT = """Another coding agent works on the file {path}. That agent does not know that the function `{original}` exists.
Write the function that this agent writes for the same job. Name it `{name}`. Use the same parameters. Write no comment that says it is a copy.

Reply with the function in one ```python block.

File: {path}

```python
{source}
```"""
LOCK = threading.Lock()


class Injection(NamedTuple):
    text: str
    qualname: str
    source: str
    exact: bool = False


@dataclass
class Item:
    id: str
    instance: str
    repo: str
    kind: str
    path: str
    qualname: str
    source: str
    injected: str
    changed_lines: list[str]
    complexity: dict[str, int]
    nesting: dict[str, int]
    exact: bool


def build(image, script: str, files: dict):
    done = image.run(shell=script, env={"PATH": TESTBED_PATH}, preserve_env=True, files=files, disposable=False).wait()
    if done.exit_code:
        raise InstallError(tail(done.stdout + done.stderr))
    return done


def hidden(box: Contree, checkpoint, files: dict[str, str], command: str) -> tuple[str, frozenset[str], str]:
    with trace.span("bench.hidden", input={"cmd": command, "files": list(files)}):
        code, output = box.run(checkpoint, files, command, HIDDEN_SECONDS)
    if code == 124:
        return "timeout", frozenset(), output
    passes = passed(output)
    return ("ok" if passes is not None else "no_summary"), passes or frozenset(), output


def dataset() -> dict[str, dict]:
    if not LITE.exists():
        rows = [r["row"] for offset in range(0, 300, 100) for r in json.load(urllib.request.urlopen(ROWS.format(offset)))["rows"]]
        write(LITE, [{field: r[field] for field in FIELDS} for r in rows])
    return {r["instance_id"]: r for r in json.loads(LITE.read_text())}


PASSED = re.compile(r"^PASSED (\S.*?)(?: - .*)?$", re.M)


def passed(output: str) -> frozenset[str] | None:
    summary = output.partition(MARK)[0]
    if "short test summary info" not in summary:
        return None
    return frozenset(PASSED.findall(summary.rpartition("short test summary info")[2]))


def executed(output: str) -> dict[str, set[int]]:
    files = json.JSONDecoder().raw_decode(output.partition(MARK)[2].lstrip())[0]["files"]
    return {path.removeprefix("/repo/"): set(data["executed_lines"]) for path, data in files.items()}


def hidden_command(tests: list[str], coverage: bool = False) -> str:
    if not coverage:
        return f"python -m pytest {PYTEST} {' '.join(tests)}"
    return f"python -m coverage run --source=/repo -m pytest {PYTEST} {' '.join(tests)}; echo {MARK}; {review.COMBINE}; python -m coverage json -q -o -"


def gate_test_command(instance_id: str, repo: str) -> str:
    flag = "" if instance_id in OLD_PYTEST else " --continue-on-collection-errors"
    return f"python -m pytest -q -rfE -p no:cacheprovider{flag} {TESTS[repo]}"


def patch_files(test_patch: str) -> tuple[list[str], list[str]]:
    files = [path for path in re.findall(r"^\+\+\+ b/(\S+)", test_patch, re.M) if path.endswith(".py")]
    return files, [path for path in files if is_test_file(path, PATTERNS) or {"tests", "testing"} & set(path.split("/")[:-1])]


def gold_spans(patch: str) -> dict[str, list[range]]:
    spans, path = {}, None
    for line in patch.splitlines():
        if line.startswith("--- "):
            path = line[len("--- a/") :] if line.startswith("--- a/") else None
        elif path and (hunk := re.match(r"@@ -(\d+)(?:,(\d+))? ", line)):
            spans.setdefault(path, []).append(range(int(hunk[1]), int(hunk[1]) + max(int(hunk[2] or 1), 1)))
    return spans


def eligible(root: Path, covered: dict[str, set[int]], spans: dict[str, list[range]]) -> list[Function]:
    found = []
    for path in sorted(covered):
        if not path.endswith(".py") or SKIPPED & set(path.split("/")[:-1]) or is_test_file(path, PATTERNS) or not (root / path).is_file():
            continue
        try:
            functions = parse(path, (root / path).read_text())
        except (SyntaxError, ValueError, UnicodeDecodeError):
            continue
        names = Counter(f.qualname for f in functions)
        for f in functions:
            size = f.end - f.start + 1
            hit = any(span.start <= f.end and f.start < span.stop for span in spans.get(path, []))
            # parses() uses textwrap.dedent like transform(): a method with a docstring line left of the def fails both
            if not (names[f.qualname] == 1 and 3 <= size <= 60 and not hit and parses(f.source)):
                continue
            # the def line and the decorators run at import, so only the body shows that the function runs
            if (body := body_line(f)) and covered[path] & set(range(body, f.end + 1)):
                found.append(f)
    return found


def duplicate_name(function: Function) -> str:
    return f"{function.qualname}_alt"


def duplicate_code(reply: str | None, name: str) -> str | None:
    code = reply and strip_fence(reply)
    if not code:
        return None
    try:
        body = ast.parse(dedent(code)).body
    except SyntaxError:
        return None
    if len(body) != 1 or not isinstance(body[0], ast.FunctionDef) or body[0].name != name:
        return None
    return dedent(code).strip("\n") + "\n"


def function_source(text: str, qualname: str) -> str:
    return next(f.source for f in parse("", text) if f.qualname == qualname)


def make(kind: str, function: Function, text: str, covered: set[int], ask) -> Injection | None:
    if kind in TRANSFORMS:
        new = function.end - function.start >= 4 and transform(kind, function.source, text)
        if not new or new == function.source:
            return None
        spliced = review.splice(text, function, new)
        if not parses(spliced) or kind in kinds.classify(function, text):
            return None
        return Injection(spliced, function.qualname, new)
    if "." in function.qualname:
        return None
    if kind == "wrapper":
        made = wrapper(text, function, covered)
        return made and Injection(made[0], made[1], function_source(made[0], made[1]))
    name = duplicate_name(function)
    if not sites(text, function, covered):
        return None
    code = duplicate_code(ask(function), name)
    spliced = code and duplicate(text, function, code, name, covered)
    # the control needs a body line of its own, and Super may write a one-line copy
    if not spliced or body_line(next(f for f in parse(function.path, spliced) if f.qualname == name)) is None:
        return None
    return Injection(spliced, name, code, structure_hash(code) == structure_hash(function.source))


def item_of(instance_id: str, repo: str, kind: str, function: Function, made: Injection) -> Item:
    before = function.source if kind in TRANSFORMS else ""
    return Item(
        f"{instance_id}:{function.path}:{made.qualname}:{kind}",
        instance_id,
        repo,
        kind,
        function.path,
        made.qualname,
        function.source,
        made.source,
        changed(before, made.source),
        {"original": complexity(function.source), "injected": complexity(made.source)},
        {"original": nesting(function.source), "injected": nesting(made.source)},
        made.exact,
    )


def inject(instance_id, repo, order, functions, root, covered, ask, behaves) -> tuple[list[tuple[Item, str]], Counter, Counter]:
    made, rejected, blind, used, asked = [], Counter(), Counter(), set(), []

    def counted(function: Function) -> str | None:
        asked.append(function)
        return ask(function)

    for kind in order:
        tried = 0
        for function in random.Random(f"{SEED}:{instance_id}:{kind}").sample(functions, len(functions)):
            if len(made) == PER_INSTANCE or tried == TRIES:
                break
            if function.path in used:
                continue
            before = len(asked)
            injection = make(kind, function, (root / function.path).read_text(), covered[function.path], counted)
            # a Super reply that is not usable still costs a call, so it counts as a try
            tried += injection is not None or len(asked) > before
            if injection is None:
                continue
            verdict = behaves(function.path, injection.text, injection.qualname)
            if verdict != "ok":
                (rejected if verdict == "breaks" else blind)[kind] += 1
                continue
            made.append((item_of(instance_id, repo, kind, function, injection), injection.text))
            used.add(function.path)
            break
    return made, rejected, blind


def asker(instance_id: str, usage: Counter):
    def ask(function: Function) -> str | None:
        key = f"{instance_id}:{function.path}:{function.qualname}"
        prompt = DUPLICATE_PROMPT.format(path=function.path, original=function.qualname, name=duplicate_name(function), source=dedent(function.source).rstrip("\n"))
        with LOCK:
            cache = json.loads(REPLIES.read_text()) if REPLIES.exists() else {}
            if key not in cache:
                used = len(llm.usage)
                try:
                    reply = llm.complete(SUPER, prompt)
                except Exception as error:
                    print(f"{key}: {error!r}", file=sys.stderr)
                    return None
                calls = llm.usage[used:]
                cache[key] = {"reply": reply, "input_tokens": sum(c[1] for c in calls), "output_tokens": sum(c[2] for c in calls)}
                write(REPLIES, cache)
        usage.update({"calls": 1, "input_tokens": cache[key]["input_tokens"], "output_tokens": cache[key]["output_tokens"]})
        return cache[key]["reply"]

    return ask


def commit(clone: Path, texts: dict[str, str], hidden_files: list[str], test: str) -> str:
    for path in hidden_files:
        (clone / path).unlink(missing_ok=True)
    for path, text in texts.items():
        (clone / path).write_text(text)
    (clone / ".slopgate.toml").write_text(f'[sandbox]\ntest = "{test}"\n')
    git("-C", str(clone), "add", "-A")
    git("-C", str(clone), "-c", "user.name=bench", "-c", "user.email=bench@example.invalid", "commit", "-q", "-m", "bench: inject slop")
    return git("-C", str(clone), "rev-parse", "HEAD")


def clone_at(instance_id: str, repo: str, base: str) -> Path:
    clone = CLONES / instance_id
    shutil.rmtree(clone, ignore_errors=True)
    git("clone", "-q", "--shared", str(checkout(repo, base)), str(clone))
    git("-C", str(clone), "checkout", "-q", "--detach", base)
    return clone


def select_one(source: dict) -> tuple[dict, list[Item]] | None:
    instance_id, repo, base = source["instance_id"], source["repo"], source["base_commit"]
    usage, began = Counter(), time.perf_counter()
    instance = {"instance_id": instance_id, "repo": repo, "base": base, "skipped": None, "rejected": {}, "blind": {}}
    try:
        items = select_items(source, instance, usage)
    except InstallError as error:
        instance["skipped"] = repr(error)
        items = []
    except Exception:
        print(instance_id, file=sys.stderr)
        traceback.print_exc()
        return None
    instance["seconds"] = round(time.perf_counter() - began, 1)
    instance["super_usage"] = dict(usage)
    return instance, items


def select_items(source: dict, instance: dict, usage: Counter) -> list[Item]:
    instance_id, repo, base = instance["instance_id"], instance["repo"], instance["base"]
    p2p = set(json.loads(source["PASS_TO_PASS"]))
    hidden_files, tests = patch_files(source["test_patch"])
    if not tests:
        raise InstallError("the test patch has no Python test file")
    clone = clone_at(instance_id, repo, base)

    ref = IMAGE.format(instance_id.replace("__", "_1776_"))
    image = ContreeSync().images.oci(ref, timeout=3600)
    # the image adds a "SWE-bench" commit on top of the base; on 6 images it changed only file modes (and tox.ini of sphinx)
    script = (
        f'cd /testbed || exit 1; [ "$(git rev-parse HEAD~1)" = {base} ] || [ "$(git rev-parse HEAD)" = {base} ] '
        f'|| {{ echo "/testbed is not at {base}"; exit 1; }}; '
        "git apply /tmp/test.patch && mv /testbed /repo && ln -s /repo /testbed && pip install -q pytest coverage"
    )
    checkpoint = build(image, script, {"/tmp/test.patch": source["test_patch"].encode()})
    box = Contree()
    status, passes, output = hidden(box, checkpoint, {}, hidden_command(tests, coverage=True))
    if status != "ok":
        raise InstallError("hidden tests gave no summary on the base commit" if status == "no_summary" else "hidden tests timed out on the base commit")
    base_pass, covered = passes & p2p, executed(output)
    if not base_pass:
        raise InstallError("no hidden test of PASS_TO_PASS passes on the base commit")

    plain = hidden_command(tests)
    functions = eligible(clone, covered, gold_spans(source["patch"]))
    index = INSTANCES.index(instance_id) % len(ORDER)

    # a run that is not ok has no passing tests, and base_pass is not empty
    def behaves(path: str, text: str, qualname: str) -> str:
        if not base_pass <= hidden(box, checkpoint, {path: text}, plain)[1]:
            return "breaks"
        status, passes, _ = hidden(box, checkpoint, {path: control(text, qualname)}, plain)
        return "ok" if status != "ok" or not base_pass <= passes else "blind"

    made, rejected, blind = inject(instance_id, repo, ORDER[index:] + ORDER[:index], functions, clone, covered, asker(instance_id, usage), behaves)
    instance |= {"rejected": rejected, "blind": blind}
    if not made:
        raise InstallError("no injection kept the hidden tests passing and showed a break to them")

    def together() -> frozenset[str]:
        return hidden(box, checkpoint, {item.path: text for item, text in made}, plain)[1]

    slop_pass = together()
    while made and not base_pass <= slop_pass:
        rejected[made.pop()[0].kind] += 1
        slop_pass = together() if made else frozenset()
    if not made:
        raise InstallError("the injections together break the hidden tests")
    test = gate_test_command(instance_id, repo)
    head = commit(clone, {item.path: text for item, text in made}, [p for p in hidden_files if (clone / p).exists()], test)
    HEADS.mkdir(exist_ok=True)
    git("-C", str(clone), "bundle", "create", "-q", str(HEADS / f"{instance_id}.bundle"), f"{base}..HEAD")
    instance |= {
        "head": head,
        "image": ref,
        "hidden_uuid": str(checkpoint.uuid),
        "hidden_files": hidden_files,
        "hidden_tests": tests,
        "base_pass": sorted(base_pass),
        "slop_pass": sorted(slop_pass & p2p),
    }
    return [item for item, _ in made]


def select() -> None:
    trace.start("slopgate-bench")
    stored = json.loads(GROUNDTRUTH.read_text()) if GROUNDTRUTH.exists() else {"super_usage": {}, "instances": {}, "items": []}
    rows = dataset()
    todo = [rows[i] for i in INSTANCES if i not in stored["instances"]]
    # each base commit is checked out once and in turn: the per-instance clones share these objects
    for source in todo:
        checkout(source["repo"], source["base_commit"])
    # the first span must open outside the thread pool (ticket 61)
    with trace.span("bench.swebench_select"), ThreadPoolExecutor(WORKERS) as threads:
        for done, future in enumerate(as_completed([threads.submit(trace.bind(select_one), source) for source in todo]), 1):
            if not (selected := future.result()):
                continue
            instance, items = selected
            stored["instances"][instance["instance_id"]] = instance
            stored["items"] += [asdict(item) for item in items]
            stored["super_usage"] = dict(sum((Counter(i["super_usage"]) for i in stored["instances"].values()), Counter()))
            write(GROUNDTRUTH, stored)
            print(f"{done}/{len(todo)} {instance['instance_id']}: {len(items)} items{' skipped: ' + instance['skipped'] if instance['skipped'] else ''}", file=sys.stderr)
    counts = Counter(item["kind"] for item in stored["items"])
    write(meta_path(GROUNDTRUTH), metadata({"injection": SUPER}, {"DUPLICATE_PROMPT": DUPLICATE_PROMPT}, {"select": SEED}, counts=dict(counts)))


def entries(result: dict) -> list[dict]:
    return [entry | {"outcome": outcome} for outcome in OUTCOME for entry in result[outcome]]


def span_of(text: str, qualname: str) -> tuple[int, int] | None:
    return next(((f.start, f.end) for f in parse("", text) if f.qualname == qualname), None)


def hits(entry: dict, item: dict, span: tuple[int, int] | None) -> bool:
    if entry["outcome"] == "suggestions":
        # the gate posts exactly the lines of the function
        return bool(span) and entry["path"] == item["path"] and entry.get("start_line", entry["line"]) == span[0] and entry["line"] == span[1]
    if entry["outcome"] == "followup":
        return entry["function"] == item["qualname"] and item["path"] in entry["files"]
    return entry.get("function") == item["qualname"] and entry.get("path") == item["path"]


SUGGESTED = re.compile(r"Slopgate \((.*?)\) rewrite of")


def entry_kinds(entry: dict) -> list[str]:
    if entry["outcome"] != "suggestions":
        return entry["kinds"]
    return re.findall(r"`(\w+)`", found[1]) if (found := SUGGESTED.match(entry["body"])) else []


def splice_suggestion(text: str, entry: dict) -> str:
    code = entry["body"].split("```suggestion\n", 1)[1].rsplit("```", 1)[0]
    lines = text.splitlines(keepends=True)
    return "".join(lines[: entry.get("start_line", entry["line"]) - 1]) + code + "".join(lines[entry["line"] :])


def rewritten(entry: dict, texts: dict[str, str]) -> dict[str, str]:
    if entry["outcome"] == "suggestions":
        return {entry["path"]: splice_suggestion(texts[entry["path"]], entry)}
    return entry["files"]


def after_of(item: dict, files: dict[str, str]) -> dict | None:
    source = next((f.source for f in parse(item["path"], files[item["path"]]) if f.qualname == item["qualname"]), None)
    return source and {"complexity": complexity(source), "nesting": nesting(source)}


def grade(item: dict, found: list[dict], texts: dict[str, str]) -> tuple[dict, dict[str, str]]:
    span = span_of(texts[item["path"]], item["qualname"])
    matched = [entry for entry in found if hits(entry, item, span)]
    relevant = sorted((e for e in matched if item["kind"] in entry_kinds(e)), key=lambda e: list(OUTCOME).index(e["outcome"]))
    best = relevant[0] if relevant else None
    outcome = OUTCOME[best["outcome"]] if best else "missed"
    if best and review.NO_ENVIRONMENT in best.get("body", ""):
        outcome = "no_environment"
    result = {
        "id": item["id"],
        "kind": item["kind"],
        "detected": best is not None,
        "gate_kinds": sorted({kind for e in matched for kind in entry_kinds(e)}),
        "outcome": outcome,
        "reason": (best.get("reason") or best.get("body", "")) if best else "",
        "accepted": outcome in ("suggestion", "followup"),
        "complexity": item["complexity"],
        "nesting": item["nesting"],
        "after": None,
        "removed": False,
        "exact": item["exact"],
        "hidden": None,
        "broken": [],
        "flaky": [],
    }
    files = rewritten(best, texts) if result["accepted"] else {}
    if files:
        after = after_of(item, texts | files)
        result |= {"after": after, "removed": after is None}
    return result, files


def usage_of(calls: list[tuple[str, int, int]]) -> dict[str, dict[str, int]]:
    tokens = {}
    for model, tokens_in, tokens_out in calls:
        total = tokens.setdefault(model, {"input_tokens": 0, "output_tokens": 0})
        total["input_tokens"] += tokens_in
        total["output_tokens"] += tokens_out
    return tokens


def check(box: Contree, instance: dict, texts: dict[str, str], files: dict[str, str]) -> dict:
    checkpoint = ContreeSync().images.use(UUID(instance["hidden_uuid"]))
    command = hidden_command(instance["hidden_tests"])
    status, after, _ = hidden(box, checkpoint, texts | files, command)
    if status == "timeout":
        # a rewrite that loops is a real break
        return {"hidden": status, "broken": ["<timeout>"], "flaky": []}
    if status == "no_summary":
        # the slop commit gave a summary at selection, so a rewrite that gives none breaks the suite
        again, _, _ = hidden(box, checkpoint, texts, command)
        return {"hidden": status, "broken": ["<no summary>"] if again == "ok" else [], "flaky": []}
    broken = sorted(set(instance["slop_pass"]) - after)
    flaky = []
    if broken:
        again, before, _ = hidden(box, checkpoint, texts, command)
        if again == "ok":
            flaky = [test for test in broken if test not in before]
            broken = [test for test in broken if test in before]
    return {"hidden": status, "broken": broken, "flaky": flaky}


def job(instance: dict, items: list[dict]) -> dict:
    trace.start("slopgate-bench")
    clone, head = str(CLONES / instance["instance_id"]), instance["head"]
    texts = {path: diff.git(clone, "show", f"{head}:{path}") for path in dict.fromkeys(item["path"] for item in items)}
    used, began = len(llm.usage), time.perf_counter()
    failure, errors, found = None, [], []
    box = Contree()
    with trace.span("bench.swebench", instance=instance["instance_id"]):
        try:
            result = review.review(clone, instance["base"], head, box)
            found = entries(result)
            errors = [e["reason"] for e in result["rejected"] if "function" not in e]
        except Exception as error:
            failure = repr(error)
        gate_seconds = round(time.perf_counter() - began, 1)
        rows = []
        for item in items:
            graded, files = grade(item, found, texts)
            if failure:
                graded |= {"outcome": "error", "reason": failure}
            if graded["accepted"]:
                try:
                    graded |= check(box, instance, texts, files)
                except Exception as error:
                    graded["hidden"] = f"error: {error!r}"
            rows.append(graded)
    tokens = usage_of(llm.usage[used:])
    return {
        "instance_id": instance["instance_id"],
        "seconds": round(time.perf_counter() - began, 1),
        "gate_seconds": gate_seconds,
        "error": failure,
        "gate_errors": errors,
        "tokens": tokens,
        "usd": round(sum(cost(model, total) for model, total in tokens.items()), 4),
        "items": rows,
    }


def restore(instance: dict) -> None:
    clone, head = CLONES / instance["instance_id"], instance["head"]
    if has_commit(clone, head):
        return
    clone_at(instance["instance_id"], instance["repo"], instance["base"])
    git("-C", str(clone), "fetch", "-q", str(HEADS / f"{instance['instance_id']}.bundle"), "HEAD")
    git("-C", str(clone), "checkout", "-q", "--detach", head)


def run() -> None:
    truth = json.loads(GROUNDTRUTH.read_text())
    runs = json.loads(RUNS.read_text()) if RUNS.exists() else {}
    todo = [(instance, [i for i in truth["items"] if i["instance"] == instance_id]) for instance_id, instance in truth["instances"].items() if not instance["skipped"]]
    todo = [(instance, items) for instance, items in todo if instance["instance_id"] not in runs]
    # serial: checkout() moves HEAD of the shared source repo
    for instance, _ in todo:
        restore(instance)
    with ProcessPoolExecutor(WORKERS) as workers:
        for done, future in enumerate(as_completed([workers.submit(job, instance, items) for instance, items in todo]), 1):
            result = future.result()
            runs[result["instance_id"]] = result
            write(RUNS, runs)
            print(f"{done}/{len(todo)} {result['instance_id']}: {result['seconds']} s, ${result['usd']}", file=sys.stderr)
    prompts = {name: getattr(review, name) for name in ("AGENT_RULES", "AGENT_TASK", "HINT_TASK", "REWRITE_PROMPT", "RETRY_PROMPT", "SAME_JOB_PROMPT")}
    usd = round(sum(r["usd"] for r in runs.values()), 4)
    write(meta_path(RUNS), metadata({"tests and rewrites": SUPER, "retry and summary": ULTRA}, prompts, {}, counts={"instances": len(runs)}, usd=usd))


def mean(values: list[int]) -> float | None:
    return round(statistics.mean(values), 2) if values else None


def tally(rows: list[dict], rejected: int | None) -> dict:
    infrastructure = sum(r["outcome"] in INFRASTRUCTURE for r in rows)
    rows = [r for r in rows if r["outcome"] not in INFRASTRUCTURE]
    detected = [r for r in rows if r["detected"]]
    accepted = [r for r in rows if r["accepted"]]
    measured = [r for r in accepted if r["hidden"] == "ok" or r["broken"]]
    silent = [r for r in measured if r["broken"]]
    # wrapper and duplicate rewrites remove a function; only a rewrite in place has a complexity to compare
    kept = [r for r in accepted if r["kind"] in TRANSFORMS and r["after"]]
    return {
        "items": len(rows),
        "detected": len(detected),
        "accepted": len(accepted),
        "silent_breaks": len(silent),
        "unmeasured": len(accepted) - len(measured),
        "infrastructure_errors": infrastructure,
        "rejected_for_behavior": rejected,
        "recall": ratio(len(detected), len(rows)),
        "acceptance": ratio(len(accepted), len(detected)),
        "acceptance_of_items": ratio(len(accepted), len(rows)),
        "silent_break_rate": ratio(len(silent), len(measured)),
        "complexity_vs_injected": mean([r["after"]["complexity"] - r["complexity"]["injected"] for r in kept]),
        "complexity_vs_original": mean([r["after"]["complexity"] - r["complexity"]["original"] for r in kept]),
        "nesting_vs_injected": mean([r["after"]["nesting"] - r["nesting"]["injected"] for r in kept]),
        "nesting_vs_original": mean([r["after"]["nesting"] - r["nesting"]["original"] for r in kept]),
        "removed": sum(r["removed"] for r in accepted),
    }


def summarize(rows: list[dict], rejected: dict[str, int]) -> dict:
    by_kind = {kind: tally([r for r in rows if r["kind"] == kind], rejected.get(kind, 0)) for kind in ORDER}
    copies = [r for r in rows if r["kind"] == "duplicate"]
    # the rejections are counted for each kind, not for each sort of copy
    by_kind["duplicate (exact)"] = tally([r for r in copies if r["exact"]], None)
    by_kind["duplicate (rewritten)"] = tally([r for r in copies if not r["exact"]], None)
    return {"kinds": by_kind, "total": tally(rows, sum(rejected.values()))}


def markdown(report: dict) -> str:
    columns = list(report["total"])
    out = ["# SWE-bench benchmark with injected slop", ""]
    out += run_metadata(report["metadata"])
    out += ["## Results", "", row("kind", *columns), row(*["---"] * (1 + len(columns)))]
    out += [row(kind, *values.values()) for kind, values in [*report["kinds"].items(), ("total", report["total"])]] + [""]
    out += ["## Tokens and cost", "", row("model", "use", "input tokens", "output tokens", "USD"), row(*["---"] * 5)]
    out += [row(t["model"], t["use"], t["input_tokens"], t["output_tokens"], t["usd"]) for t in report["tokens"]]
    out += ["", f"Total USD: {report['usd']}. Mean seconds for each instance: {report['seconds']}, of which the gate: {report['gate_seconds']}."]
    out += [f"Injections dropped because the hidden tests cannot see a break: {report['blind']}.", ""]
    out += ["## Skipped instances", "", row("instance", "reason"), row("---", "---")]
    out += [row(i, reason) for i, reason in report["skipped"].items()] + [""]
    out += ["## Gate errors", "", row("instance", "errors"), row("---", "---")]
    out += [row(i, " / ".join(errors)[-200:].replace("\n", " ").replace("|", "/")) for i, errors in report["gate_errors"].items()] + [""]
    out += ["## Items", "", row("item", "detected", "gate kinds", "outcome", "silent break", "reason"), row(*["---"] * 6)]
    out += [row(i["id"], i["detected"], ", ".join(i["gate_kinds"]), i["outcome"], ", ".join(i["broken"][:3]), i["reason"][-120:].replace("\n", " ").replace("|", "/")) for i in report["items"]]
    return "\n".join(out) + "\n"


def report() -> None:
    truth = json.loads(GROUNDTRUTH.read_text())
    runs = json.loads(RUNS.read_text())
    rows = [item for r in runs.values() for item in r["items"]]
    ran = [truth["instances"][i] for i in runs]
    rejected = sum((Counter(i["rejected"]) for i in ran), Counter())
    tokens = [{"model": SUPER, "use": "injection"} | {k: truth["super_usage"].get(k, 0) for k in ("input_tokens", "output_tokens")}]
    tokens[0]["usd"] = cost(SUPER, tokens[0])
    total = Counter()
    for r in runs.values():
        for model, usage in r["tokens"].items():
            total.update({(model, k): v for k, v in usage.items()})
    for model in dict.fromkeys(model for model, _ in total):
        usage = {"input_tokens": total[model, "input_tokens"], "output_tokens": total[model, "output_tokens"]}
        tokens.append({"model": model, "use": "gate"} | usage | {"usd": cost(model, usage)})
    result = summarize(rows, dict(rejected)) | {
        "tokens": tokens,
        "usd": round(sum(t["usd"] for t in tokens), 4),
        "blind": sum(sum(i.get("blind", {}).values()) for i in truth["instances"].values()),
        "seconds": mean([r["seconds"] for r in runs.values()]),
        "gate_seconds": mean([r["gate_seconds"] for r in runs.values()]),
        "skipped": {i["instance_id"]: i["skipped"] for i in truth["instances"].values() if i["skipped"]},
        "gate_errors": {i: ([r["error"]] if r["error"] else []) + r["gate_errors"] for i, r in runs.items() if r["error"] or r["gate_errors"]},
        "items": rows,
    }
    result["metadata"] = {"report": metadata({}, {}, {}, usd=result["usd"]), "groundtruth": stored_meta(GROUNDTRUTH), "runs": stored_meta(RUNS)}
    write(REPORT.with_suffix(".json"), result)
    REPORT.with_suffix(".md").write_text(markdown(result))


def has_commit(clone: Path, commit: str) -> bool:
    return subprocess.run(["git", "-C", str(clone), "rev-parse", "--verify", "-q", f"{commit}^{{commit}}"], capture_output=True).returncode == 0


def elapsed(began: float) -> float:
    return round(time.perf_counter() - began, 1)


def install_job(source: dict) -> dict:
    trace.start("slopgate-bench")
    instance_id, repo, base = source["instance_id"], source["repo"], source["base_commit"]
    clone = CLONES / instance_id
    since = commit_date(clone, base)
    setup, test, image = commands(clone, base, since)
    box = Contree()
    image = image or box.image
    result = {
        "instance_id": instance_id,
        "repo": repo,
        "image": image,
        "python": image.rpartition(":")[2].split("-")[0],
        "setup": setup,
        "test": test,
        "built": False,
        "error": None,
        "collects": False,
        "reason": None,
        "calibration": None,
        "seconds": {},
    }
    stored = json.loads(GROUNDTRUTH.read_text())["instances"].get(instance_id, {}) if GROUNDTRUTH.exists() else {}
    with trace.span("bench.install", instance=instance_id):
        began = time.perf_counter()
        try:
            checkpoint = box.prepare(clone, base, setup, image)
        except InstallError as error:
            result["error"] = str(error)
        else:
            result["built"] = True
        result["seconds"]["build"] = elapsed(began)
        if result["built"]:
            began = time.perf_counter()
            reason = collect_error(box, checkpoint, test)
            result |= {"collects": reason is None, "reason": reason}
            result["seconds"]["collect"] = elapsed(began)
        if stored.get("hidden_uuid"):
            began = time.perf_counter()
            official = box.client.images.use(UUID(stored["hidden_uuid"]))
            result["calibration"] = {
                "production": collect_error(box, official, test),
                "bench": collect_error(box, official, BENCH_TEST.format(TESTS[repo])),
            }
            result["seconds"]["calibration"] = elapsed(began)
    return result


def install_summary(results: list[dict]) -> dict:
    calibrated = [r["calibration"] for r in results if r["calibration"]]
    return {
        "instances": len(results),
        "built": sum(r["built"] for r in results),
        "collects": sum(r["collects"] for r in results),
        "false_triggers": sum(r["built"] and not r["collects"] for r in results),
        "calibrated": len(calibrated),
        "calibration_production": sum(c["production"] is None for c in calibrated),
        "calibration_bench": sum(c["bench"] is None for c in calibrated),
        "seconds": mean([sum(r["seconds"].values()) for r in results]),
    }


def verdict(calibration: dict | None, key: str) -> str:
    return "" if calibration is None else "pass" if calibration[key] is None else "fail"


def install_markdown(results: list[dict], summary: dict, meta: dict) -> str:
    out = ["# Default install of the test environment", ""]
    out += run_metadata({"report": meta})
    out += [
        "## Results",
        "",
        f"- Instances: {summary['instances']}. Default built: {summary['built']}. Default succeeds (built, and the tests collect): {summary['collects']}.",
        f"- False triggers (built, and the tests do not collect): {summary['false_triggers']}.",
        f"- Calibration on the SWE-bench image, {summary['calibrated']} instances: the production command passes on {summary['calibration_production']}, the bench command on {summary['calibration_bench']}.",
        f"- Mean seconds for each instance: {summary['seconds']}.",
        "",
    ]
    out += ["## Instances", "", row("instance", "python", "built", "collects", "calibration production", "calibration bench", "seconds", "reason"), row(*["---"] * 8)]
    for r in results:
        reason = (r["reason"] or r["error"] or "")[-120:].replace("\n", " ").replace("|", "/")
        out += [row(r["instance_id"], r["python"], r["built"], r["collects"], verdict(r["calibration"], "production"), verdict(r["calibration"], "bench"), round(sum(r["seconds"].values()), 1), reason)]
    return "\n".join(out) + "\n"


def install() -> None:
    results = json.loads(INSTALL.with_suffix(".json").read_text()) if INSTALL.with_suffix(".json").exists() else {}
    rows = dataset()
    todo = [rows[i] for i in [*INSTANCES, *EXTRA] if i not in results]
    # each base commit is checked out once and in turn: the per-instance clones share these objects
    for source in todo:
        if not has_commit(CLONES / source["instance_id"], source["base_commit"]):
            clone_at(source["instance_id"], source["repo"], source["base_commit"])
    with ProcessPoolExecutor(WORKERS) as workers:
        futures = {workers.submit(install_job, source): source["instance_id"] for source in todo}
        for done, future in enumerate(as_completed(futures), 1):
            try:
                result = future.result()
            except Exception:
                print(futures[future], file=sys.stderr)
                traceback.print_exc()
                continue
            results[result["instance_id"]] = result
            write(INSTALL.with_suffix(".json"), results)
            print(f"{done}/{len(todo)} {result['instance_id']}: built {result['built']}, collects {result['collects']}, {sum(result['seconds'].values()):.0f} s", file=sys.stderr)
    ordered = [results[i] for i in [*INSTANCES, *EXTRA] if i in results]
    summary = install_summary(ordered)
    meta = metadata({}, {}, {}, counts={key: value for key, value in summary.items() if key != "seconds"})
    write(meta_path(INSTALL), meta)
    INSTALL.with_suffix(".md").write_text(install_markdown(ordered, summary, meta))


STAGES = {"select": select, "run": run, "report": report, "install": install}

if __name__ == "__main__":
    if sys.argv[1:]:
        STAGES[sys.argv[1]]()
    else:
        for stage in (select, run, report):
            stage()
