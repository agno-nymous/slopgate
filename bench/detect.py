import ast
import functools
import hashlib
import itertools
import json
import random
import subprocess
import sys
import textwrap
import time
import urllib.request
import warnings
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field, replace
from difflib import SequenceMatcher
from pathlib import Path

from bench import label
from bench.paths import GROUNDTRUTH, LABELS, RESULTS, RUNS, all_runs, meta_path, stored_meta, write
from bench.score import BOOTSTRAP_SEED, SPLIT_SEED, WORKERS, compare, cost, markdown, metadata, mismatch, score, split
from bench.transforms import TRANSFORMS, indent_of, transform
from slopgate import kinds, llm
from slopgate.config import SUPER
from slopgate.functions import Function, is_test_file, parse
from slopgate.review import strip_fence

DETECTION = RESULTS / "detection"
CACHE = Path.home() / ".cache" / "slopgate" / "bench"
SAMPLE = CACHE / "sample.json"
REPLIES = CACHE / "super.json"
# the repos have old regex strings with invalid escapes; each ast.parse would print a warning
warnings.filterwarnings("ignore", category=SyntaxWarning)

ROWS = "https://datasets-server.huggingface.co/rows?dataset=princeton-nlp/SWE-bench_Lite&config=default&split=test&offset={}&length=100"
REPOS = [
    "django/django",
    "sympy/sympy",
    "psf/requests",
    "pallets/flask",
    "astropy/astropy",
    "scikit-learn/scikit-learn",
    "sphinx-doc/sphinx",
    "pytest-dev/pytest",
]
# injection sources only: the 8 repos give fewer than 12 functions that the lookup_table transform applies to
EXTRA = ["matplotlib/matplotlib", "pydata/xarray", "pylint-dev/pylint", "mwaskom/seaborn"]
SKIPPED = {"tests", "test", "testing", "doc", "docs", "examples", "benchmarks"}
CLEAN_PER_REPO = 25
TRANSFORM_ITEMS = 12
NEMOTRON_ITEMS = 10
RUNS_PER_ITEM = 3
SEED = 37

INJECT = {
    "nesting": (
        "Replace early returns with nested if/else blocks, so that some code sits three or more blocks deep. "
        "Use the conditions that the function already has. Do not add constant conditions such as `if True`."
    ),
    "redundant_check": "Add an if condition that tests a fact that an earlier check in the function already guarantees.",
    "swallowed_error": "Wrap code in a try block whose `except Exception` hides the error and returns a default value.",
    "lookup_table": (
        "Turn the dict lookup into an if/elif chain that compares the key with each constant of the dict "
        "and returns the matching value in each branch."
    ),
    "dead": "Add a local variable that is never used, or a statement after a return that can never run.",
}

INJECT_PROMPT = """Add one kind of slop to the Python function below: {kind}. {description}

Write the slop as a coding agent would write it. Keep the behavior of the function the same. Do not change other code.
Do not write a comment that names or explains the slop.

Reply with the whole function in one ```python block.

File: {path}

```python
{source}
```"""


@dataclass
class Item:
    id: str
    repo: str
    commit: str
    path: str
    qualname: str
    start: int
    end: int
    source: str
    origin: str
    source_id: str | None = None
    injected: list[str] = field(default_factory=list)
    changed_lines: list[str] = field(default_factory=list)


def git(*args) -> str:
    return subprocess.run(["git", *args], check=True, capture_output=True, text=True).stdout.strip()


@functools.cache
def checkout(repo: str, commit: str) -> Path:
    path = CACHE / repo.replace("/", "__")
    if not path.exists():
        git("clone", "-q", "--filter=blob:none", "--no-checkout", f"https://github.com/{repo}.git", str(path))
    if git("-C", str(path), "rev-parse", "HEAD") != commit:
        git("-C", str(path), "checkout", "-q", "--detach", commit)
    return path


def file_text(item: Item) -> str:
    return (checkout(item.repo, item.commit) / item.path).read_text()


def splice(item: Item, source: str, text: str) -> str:
    lines = text.splitlines(keepends=True)
    return "".join(lines[: item.start - 1] + [source] + lines[item.end :])


def function(item: Item, source: str) -> Function:
    return Function(item.qualname, item.path, item.start, item.start + len(source.splitlines()) - 1, source)


def load_items(rows) -> list[Item]:
    return [Item(**row) for row in rows]


def parses(source: str) -> bool:
    try:
        ast.parse(textwrap.dedent(source))
    except SyntaxError:
        return False
    return True


def base_commits() -> dict[str, str]:
    rows = [row["row"] for offset in range(0, 300, 100) for row in json.load(urllib.request.urlopen(ROWS.format(offset)))["rows"]]
    first = {}
    for row in sorted(rows, key=lambda row: row["instance_id"]):
        first.setdefault(row["repo"], row["base_commit"])
    return first


def repo_functions(repo: str, commit: str) -> list[Item]:
    root = checkout(repo, commit)
    found, unparsed = [], 0
    for path in filter(None, git("-C", str(root), "ls-files", "-z", "*.py").split("\0")):
        if is_test_file(path, ["test_*.py", "*_test.py"]) or SKIPPED & set(path.split("/")[:-1]):
            continue
        try:
            functions = parse(path, (root / path).read_text())
        except (SyntaxError, ValueError, UnicodeDecodeError):
            continue
        names = Counter(f.qualname for f in functions)
        for f in functions:
            if names[f.qualname] > 1 or not 5 <= f.end - f.start + 1 <= 60:
                continue
            if not parses(f.source):
                unparsed += 1
                continue
            found.append(Item(f"{repo}:{path}:{f.qualname}", repo, commit, path, f.qualname, f.start, f.end, f.source, "source"))
    print(f"{repo}: {len(found)} functions, {unparsed} skipped because the dedented source does not parse", file=sys.stderr)
    return found


def sample() -> None:
    if SAMPLE.exists():
        return
    rng = random.Random(SEED)
    commits = base_commits()
    clean, rest = [], []
    for repo in REPOS:
        found = repo_functions(repo, commits[repo])
        picked = rng.sample(found, CLEAN_PER_REPO)
        clean += [replace(item, origin="clean") for item in picked]
        rest += [item for item in found if item not in picked]
    rest += [item for repo in EXTRA for item in repo_functions(repo, commits[repo])]
    write(SAMPLE, {"commits": {repo: commits[repo] for repo in REPOS + EXTRA}, "clean": [asdict(i) for i in clean], "pool": [asdict(i) for i in rest]})


@functools.cache
def measured(path: str, start: int, source: str, text: str) -> frozenset[str]:
    return frozenset(kinds.measured(Function("", path, start, start + len(source.splitlines()) - 1, source), text))


def changed(old: str, new: str) -> list[str]:
    a = [line.strip() for line in old.splitlines()]
    b = [line.strip() for line in new.splitlines()]
    return [b[j] for tag, _, _, j1, j2 in SequenceMatcher(None, a, b, autojunk=False).get_opcodes() if tag in ("replace", "insert") for j in range(j1, j2) if b[j]]


def accept(source: Item, text: str, new: str | None, injected: list[str], origin: str) -> Item | None:
    if not new or new == source.source:
        return None
    spliced = splice(source, new, text)
    try:
        ast.parse(textwrap.dedent(new))
        ast.parse(spliced)
    except SyntaxError:
        return None
    before = measured(source.path, source.start, source.source, text)
    after = measured(source.path, source.start, new, spliced)
    # the ground truth must stay exact: no measured kind may appear that was not injected
    if after - before - set(injected) or any(kind in before or kind not in after for kind in injected):
        return None
    lines = changed(source.source, new)
    if not lines:
        return None
    return replace(source, id=f"{source.id}:{origin}:{'+'.join(injected)}", source=new, origin=origin, source_id=source.id, injected=injected, changed_lines=lines)


def shuffled(items: list[Item], name: str) -> list[Item]:
    return random.Random(f"{SEED}:{name}").sample(items, len(items))


def transformed(injected: list[str], pool: list[Item], count: int) -> list[Item]:
    found = []
    for source in shuffled(pool, "+".join(injected)):
        text = file_text(source)
        new = source.source
        for kind in injected:
            new = new and transform(kind, new, text)
        if item := accept(source, text, new, injected, "transform"):
            found.append(item)
            if len(found) == count:
                break
    return found


def from_reply(source: Item, reply: str | None, kind: str) -> str | None:
    code = reply and strip_fence(reply)
    if not code or not parses(code):
        return None
    # Super labels its slop ("# Slop: unused variable", `unused_slop_variable = 42`); a label gives the answer to the checker
    added = set(kinds.comments(code)) - set(kinds.comments(source.source))
    if ("slop" in code.lower() and "slop" not in source.source.lower()) or added:
        return None
    body = ast.parse(textwrap.dedent(code)).body
    if len(body) != 1 or not isinstance(body[0], (ast.FunctionDef, ast.AsyncFunctionDef)) or body[0].name != source.qualname.rsplit(".", 1)[-1]:
        return None
    return textwrap.indent(textwrap.dedent(code), indent_of(source.source))


def ask(source: Item, kind: str) -> str | None:
    prompt = INJECT_PROMPT.format(kind=kind, description=INJECT[kind], path=source.path, source=textwrap.dedent(source.source).rstrip("\n"))
    try:
        return llm.complete(SUPER, prompt)
    except Exception as error:
        print(f"{source.id} {kind}: {error!r}", file=sys.stderr)
        return None


def nemotron(pool: list[Item]) -> tuple[list[Item], dict]:
    cache = json.loads(REPLIES.read_text()) if REPLIES.exists() else {"usage": {"calls": 0, "input_tokens": 0, "output_tokens": 0}, "replies": {}}
    found = []
    for kind in INJECT:
        # without a dict lookup to turn into a chain, Super invents one that returns calls, which Ruff SIM116 does not flag
        candidates = (
            s
            for s in shuffled(pool, f"nemotron:{kind}")
            if "```" not in s.source and (kind != "lookup_table" or transform(kind, s.source, file_text(s)))
        )
        kept, tried = [], 0
        while len(kept) < NEMOTRON_ITEMS and tried < 5 * NEMOTRON_ITEMS:
            batch = list(itertools.islice(candidates, min(NEMOTRON_ITEMS - len(kept), 5 * NEMOTRON_ITEMS - tried)))
            if not batch:
                break
            tried += len(batch)
            missing = [s for s in batch if f"{s.id}:{kind}" not in cache["replies"]]
            used = len(llm.usage)
            with ThreadPoolExecutor(8) as threads:
                for s, reply in zip(missing, threads.map(lambda s: ask(s, kind), missing)):
                    if reply is not None:
                        cache["replies"][f"{s.id}:{kind}"] = reply
            calls = llm.usage[used:]
            usage = cache["usage"]
            usage["calls"] += len(calls)
            usage["input_tokens"] += sum(c[1] for c in calls)
            usage["output_tokens"] += sum(c[2] for c in calls)
            write(REPLIES, cache)
            for s in batch:
                text = file_text(s)
                if item := accept(s, text, from_reply(s, cache["replies"].get(f"{s.id}:{kind}"), kind), [kind], "nemotron"):
                    kept.append(item)
        print(f"nemotron {kind}: kept {len(kept)} of {tried}", file=sys.stderr)
        found += kept
    return found, cache["usage"]


def inject() -> None:
    if GROUNDTRUTH.exists():
        return
    data = json.loads(SAMPLE.read_text())
    clean, pool = load_items(data["clean"]), load_items(data["pool"])
    injected = [item for kind in TRANSFORMS for item in transformed([kind], pool, TRANSFORM_ITEMS)]
    pairs = []
    for pair in itertools.combinations(TRANSFORMS, 2):
        if len(pairs) < TRANSFORM_ITEMS:
            pairs += transformed(list(pair), pool, 1)
    by_nemotron, usage = nemotron(pool)
    injected += pairs + by_nemotron
    by_id = {item.id: item for item in pool}
    sources = [by_id[i] for i in dict.fromkeys(item.source_id for item in injected)]
    for name, count in Counter(f"{item.origin} {'+'.join(item.injected)}" for item in injected).items():
        print(f"{name}: {count}", file=sys.stderr)
    write(GROUNDTRUTH, {"super_usage": usage, "items": [asdict(item) for item in clean + sources + injected]})
    prompts = {"INJECT_PROMPT": INJECT_PROMPT, "INJECT": json.dumps(INJECT, sort_keys=True)}
    write(meta_path(GROUNDTRUTH), metadata({"injection": SUPER}, prompts, {"sample": SEED}))


def source_sha(item: Item) -> str:
    return hashlib.sha256(item.source.encode()).hexdigest()[:12]


def current(item: Item, runs: dict) -> list[dict]:
    return [run for run in runs.get(item.id, []) if run.get("source_sha") == source_sha(item)]


def classify_item(item: Item) -> tuple[str, list[dict]]:
    text = splice(item, item.source, file_text(item))
    runs = []
    for _ in range(RUNS_PER_ITEM):
        kinds.ruff.cache_clear()
        began = time.perf_counter()
        try:
            run = {"kinds": kinds.classify(function(item, item.source), text)}
        except Exception as error:
            run = {"error": repr(error)}
        runs.append(run | {"seconds": round(time.perf_counter() - began, 3), "source_sha": source_sha(item)})
    return item.id, runs


def chosen(items: list[Item], subset: str) -> list[Item]:
    if subset not in ("tuning", "held_out", "all"):
        raise SystemExit(f"unknown set {subset!r}: use tuning, held_out, or all")
    sets = split(items)
    return [item for item in items if subset in ("all", sets[item.id])]


def runs_path(name: str | None) -> Path:
    return RUNS if name is None else RESULTS / f"runs-{name}.json"


def run(name: str | None = None, subset: str = "all") -> None:
    path = runs_path(name)
    items = chosen(load_items(json.loads(GROUNDTRUTH.read_text())["items"]), subset)
    runs = json.loads(path.read_text()) if path.exists() else {}
    todo = [item for item in items if len(current(item, runs)) < RUNS_PER_ITEM]
    with ProcessPoolExecutor(WORKERS) as workers:
        for done, future in enumerate(as_completed([workers.submit(classify_item, item) for item in todo]), 1):
            item_id, item_runs = future.result()
            runs[item_id] = item_runs
            write(path, runs)
            print(f"{done}/{len(todo)} {item_id}", file=sys.stderr)
    write(meta_path(path), metadata({}, {"KINDS": json.dumps(kinds.KINDS, sort_keys=True)}, {}, RUNS_PER_ITEM))


def report(name: str | None = None, subset: str = "all") -> None:
    groundtruth = json.loads(GROUNDTRUTH.read_text())
    items = chosen(load_items(groundtruth["items"]), subset)
    review = json.loads(LABELS.read_text())
    stored = json.loads(runs_path(name).read_text())
    runs = {item.id: current(item, stored) for item in items}
    result = {"runs": runs_path(name).name + (" (gate before ticket 39)" if name is None else ""), "set": subset} | score(items, runs, review)
    if name is not None:
        base = json.loads(RUNS.read_text())
        result["change"] = compare(items, review, {item.id: current(item, base) for item in items}, runs)
    injection = groundtruth["super_usage"]
    result["tokens"] = [{"model": SUPER, "use": "injection"} | {k: injection[k] for k in ("input_tokens", "output_tokens")} | {"usd": cost(SUPER, injection)}]
    agreement, disagreements, labelling = label.summary([asdict(item) for item in items], review, all_runs())
    result["tokens"] += labelling
    if agreement:
        result["agreement"] = agreement
    if disagreements and name is None and subset == "all":
        label.DISAGREEMENTS.write_text(disagreements)
    seeds = {"split": SPLIT_SEED, "bootstrap": BOOTSTRAP_SEED}
    usd = round(sum(t["usd"] for t in result["tokens"]), 4)
    result["metadata"] = {
        "report": metadata({}, {}, seeds, RUNS_PER_ITEM, result["counts"]["origin"], usd),
        "groundtruth": stored_meta(GROUNDTRUTH),
        "runs": stored_meta(runs_path(name)),
    }
    if name is not None:
        result["metadata"]["base_runs"] = stored_meta(RUNS)
        result["mismatch"] = mismatch(result["metadata"]["base_runs"] or {}, result["metadata"]["runs"] or {})
        for line in result["mismatch"]:
            print(f"setup differs from {RUNS.name}: {line}", file=sys.stderr)
    if labels := {v: json.loads(label.cache(v).read_text()).get("metadata") for v in label.VARIANTS if label.cache(v).exists()}:
        result["metadata"]["labels"] = labels
    detection = DETECTION if name is None else RESULTS / f"detection-{name}"
    write(detection.with_suffix(".json"), result)
    detection.with_suffix(".md").write_text(markdown(result))


STAGES = {"sample": sample, "inject": inject, "run": run, "report": report}

if __name__ == "__main__":
    if sys.argv[1:]:
        STAGES[sys.argv[1]](*sys.argv[2:])
    else:
        for stage in STAGES.values():
            stage()
