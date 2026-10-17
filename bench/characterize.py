import argparse
import ast
import json
import random
import re
import statistics
import sys
import textwrap
import time
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from pathlib import Path
from uuid import UUID

from bench.detect import SAMPLE, checkout
from bench.paths import write
from bench.score import WORKERS, cost
from slopgate import llm, review
from slopgate.config import SUPER
from slopgate.diff import git
from slopgate.functions import parse
from slopgate.sandbox import Contree, InstallError, commands

RESULTS = Path(__file__).parent / "results" / "characterize"
# runs.json and table.md hold the stage 1 comparison of designs A to D; commit a834fac runs those designs
RUNS = RESULTS / "gate-runs.json"
TABLE = RESULTS / "gate-table.md"
DESIGN = "gate"
TEST_PATH = "tests/test_slopgate_0.py"
CMD = f"python -m coverage run --branch -m pytest -q {TEST_PATH}"
MUTANTS = 8
# a mutant can loop forever, and the default ConTree operation timeout is 1000 s
MUTANT_CMD = f"PYTHONHASHSEED=1 timeout 60 python -m pytest -q {TEST_PATH}"
SWAPS = {
    ast.Lt: ast.GtE,
    ast.GtE: ast.Lt,
    ast.Gt: ast.LtE,
    ast.LtE: ast.Gt,
    ast.Eq: ast.NotEq,
    ast.NotEq: ast.Eq,
    ast.Is: ast.IsNot,
    ast.IsNot: ast.Is,
    ast.In: ast.NotIn,
    ast.NotIn: ast.In,
}

SLOPGATE = [
    ("b2a2ad0", "slopgate/index.py", "build"),
    ("b2a2ad0", "slopgate/live.py", "seed"),
    ("b2a2ad0", "slopgate/live.py", "matches"),
    ("b2a2ad0", "slopgate/review.py", "find_duplicate"),
    ("b2a2ad0", "slopgate/review.py", "characterize"),
    ("70c27da340aeaadec60bfb22a711c84acdb0cabd", "slopgate/review.py", "characterize"),
]
# installs measured in ConTree on python:3.9-slim; werkzeug>=3 breaks the import of this flask commit
INSTALLS = {
    "django/django": "pip install -e .",
    "pytest-dev/pytest": "SETUPTOOLS_SCM_PRETEND_VERSION=5.4.0 pip install -e .",
    "psf/requests": "pip install -e .",
    "sympy/sympy": "pip install -e . mpmath",
    "pallets/flask": "pip install -e . 'werkzeug<2.3'",
}
PER_REPO = 6


@dataclass(frozen=True)
class Target:
    id: str
    repo: str
    commit: str
    path: str
    qualname: str
    image: str
    setup: str | None


@dataclass
class Outcome:
    design: str
    run: int
    id: str
    proved: bool
    reason: str
    detail: str
    seconds: float = 0.0
    model_calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cost: float = 0.0
    sandbox_seconds: float = 0.0
    tests: str | None = None
    mutants: int | None = None
    killed: int | None = None
    asserts: int | None = None


def dataset() -> list[Target]:
    main = str(Path(git(Path(__file__).parent, "rev-parse", "--path-format=absolute", "--git-common-dir").strip()).parent)
    found = []
    for commit, path, qualname in SLOPGATE:
        if not any(f.qualname == qualname for f in parse(path, git(main, "show", f"{commit}:{path}"))):
            print(f"skipped: {qualname} is not in {path} at {commit}", file=sys.stderr)
            continue
        found.append(Target(f"slopgate@{commit[:7]}:{path}:{qualname}", main, commit, path, qualname, "python:3.12-slim", commands(main, commit)[0]))
    sample = json.loads(SAMPLE.read_text())
    rng = random.Random(41)
    for repo, setup in INSTALLS.items():
        commit = sample["commits"][repo]
        root = str(checkout(repo, commit))
        # the import line comes from the file path; a path such as scripts/prepare-release-pr.py gives no module name
        rows = [row for row in sample["clean"] if row["repo"] == repo and all(p.isidentifier() for p in review.module_of(row["path"]).split("."))]
        for row in rng.sample(rows, PER_REPO):
            found.append(Target(row["id"], root, commit, row["path"], row["qualname"], "python:3.9-slim", setup))
    return found


def function_of(target: Target):
    return next(f for f in parse(target.path, git(target.repo, "show", f"{target.commit}:{target.path}")) if f.qualname == target.qualname)


def sites(node) -> list[int]:
    if isinstance(node, ast.Compare):
        return [j for j, op in enumerate(node.ops) if type(op) in SWAPS]
    number = isinstance(node, ast.Constant) and type(node.value) in (int, float)
    value = isinstance(node, ast.Return) and node.value is not None and not (isinstance(node.value, ast.Constant) and node.value.value is None)
    return [0] if number or value or isinstance(node, (ast.BoolOp, ast.If)) else []


def mutate(node, j) -> None:
    if isinstance(node, ast.Compare):
        node.ops[j] = SWAPS[type(node.ops[j])]()
    elif isinstance(node, ast.BoolOp):
        node.op = ast.Or() if isinstance(node.op, ast.And) else ast.And()
    elif isinstance(node, ast.Constant):
        node.value += 1
    elif isinstance(node, ast.Return):
        node.value = ast.Constant(None)
    else:
        node.test = ast.UnaryOp(ast.Not(), node.test)


def mutants(function, text) -> tuple[str, list[str]]:
    def tree():
        node = ast.parse(textwrap.dedent(function.source)).body[0]
        node.decorator_list = []
        return node

    original, lines = tree(), text.splitlines(keepends=True)
    # function.start is the first decorator line; the decorator lines stay as they are
    start = function.start + original.lineno - 1
    indent = re.match(r"[ \t]*", lines[start - 1])[0]

    def splice(node):
        return "".join(lines[: start - 1]) + textwrap.indent(ast.unparse(node), indent) + "\n" + "".join(lines[function.end :])

    found = [(i, j) for i, node in enumerate(ast.walk(original)) for j in sites(node)]
    texts = []
    for i, j in sorted(random.Random(41).sample(found, min(MUTANTS, len(found)))):
        node = tree()
        mutate(list(ast.walk(node))[i], j)
        if ast.unparse(node) != ast.unparse(original):
            texts.append(splice(node))
    return splice(original), texts


def asserts(tests: str) -> int:
    return sum(
        isinstance(n, ast.Assert)
        or isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "raises" and isinstance(n.func.value, ast.Name) and n.func.value.id == "pytest"
        for n in ast.walk(ast.parse(tests))
    )


def strength(box, checkpoint, target, function, tests) -> dict:
    control, texts = mutants(function, git(target.repo, "show", f"{target.commit}:{target.path}"))
    # ast.unparse can change a docstring or emit syntax the target's Python cannot read; then every kill would be false
    if box.run(checkpoint, {TEST_PATH: tests, function.path: control}, MUTANT_CMD)[0]:
        return {"mutants": None, "killed": None, "asserts": asserts(tests)}
    killed = sum(box.run(checkpoint, {TEST_PATH: tests, function.path: text}, MUTANT_CMD)[0] != 0 for text in texts)
    return {"mutants": len(texts), "killed": killed, "asserts": asserts(tests)}


spent = [0.0]


def timed(run):
    def wrapper(*args, **kwargs):
        began = time.perf_counter()
        try:
            return run(*args, **kwargs)
        finally:
            spent[0] += time.perf_counter() - began

    return wrapper


def gate(box, checkpoint, function) -> dict:
    tests, failure = review.characterize(box, checkpoint, function, TEST_PATH, CMD)
    if tests is not None:
        return {"proved": True, "reason": "proved", "detail": "", "tests": tests}
    return {"proved": False, "reason": failure.partition(":")[0], "detail": failure}


def job(run: int, target: Target, uuid: str) -> dict:
    from contree_sdk import ContreeSync

    box = Contree(target.image)
    box.run = timed(box.run)

    def session(checkpoint):
        opened = Contree.session(box, checkpoint)
        opened.execute = timed(opened.execute)
        return opened

    box.session = session
    used, spent[0], began = len(llm.usage), 0.0, time.perf_counter()
    try:
        function = function_of(target)
        checkpoint = ContreeSync().images.use(UUID(uuid))
        result = gate(box, checkpoint, function)
    except llm.CutOff:
        result = {"proved": False, "reason": "token limit", "detail": "reply cut off"}
    except Exception as error:
        result = {"proved": False, "reason": "error", "detail": repr(error)}
    seconds = round(time.perf_counter() - began, 1)
    if result["proved"]:
        try:
            result |= strength(box, checkpoint, target, function, result["tests"])
        except Exception as error:
            result["detail"] = f"mutation check: {error!r}"
    calls = llm.usage[used:]
    usage = {"input_tokens": sum(c[1] for c in calls), "output_tokens": sum(c[2] for c in calls)}
    result["detail"] = result["detail"][-300:]
    return asdict(
        Outcome(
            design=DESIGN,
            run=run,
            id=target.id,
            seconds=seconds,
            model_calls=len(calls),
            cost=cost(SUPER, usage),
            sandbox_seconds=round(spent[0], 1),
            **usage,
            **result,
        )
    )


def prepare(key) -> tuple[str | None, str | None]:
    repo, commit, image, setup = key
    try:
        return str(Contree(image).prepare(repo, commit, setup).uuid), None
    except InstallError as error:
        return None, str(error)


def p90(values):
    return statistics.quantiles(values, n=10, method="inclusive")[-1] if len(values) > 1 else values[0]


def kill_rate(rows: list[dict]) -> str:
    mutants, killed = sum(r.get("mutants") or 0 for r in rows), sum(r.get("killed") or 0 for r in rows)
    return f"{killed / mutants:.0%} ({killed}/{mutants})" if mutants else "-"


def table(rows: list[dict], targets: list[Target]) -> str:
    ids = {t.id for t in targets}
    rows = [r for r in rows if r["id"] in ids]
    first = [r for r in rows if r["run"] == 0]
    if not first:
        return "no runs\n"
    proved = sum(r["proved"] for r in first)
    reasons = ", ".join(f"{reason} {n}" for reason, n in Counter(r["reason"] for r in first).most_common())
    seconds = [r["seconds"] for r in first]
    counted = [r["asserts"] for r in first if r["proved"] and r.get("asserts") is not None]
    out = [
        "| functions | proved | proof rate | reasons | median s | p90 s | mean calls | tokens in / out | cost $ | median sandbox s | kill rate | median asserts |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|",
        f"| {len(first)} | {proved} | {proved / len(first):.0%} | {reasons} | {statistics.median(seconds):.0f} | {p90(seconds):.0f} "
        f"| {statistics.mean(r['model_calls'] for r in first):.1f} | {sum(r['input_tokens'] for r in first):,} / {sum(r['output_tokens'] for r in first):,} "
        f"| {sum(r['cost'] for r in first):.3f} | {statistics.median(r['sandbox_seconds'] for r in first):.0f} "
        f"| {kill_rate([r for r in first if r['proved']])} | {statistics.median(counted) if counted else '-'} |",
    ]
    by_id = {}
    for r in rows:
        by_id.setdefault(r["id"], []).append(r)
    repeated = [runs for runs in by_id.values() if len({r["run"] for r in runs}) == 3]
    if repeated:
        counts = Counter(sum(r["proved"] for r in runs) for runs in repeated)
        out += ["", f"Variance over {len(repeated)} functions run 3 times: " + ", ".join(f"proved {n}/3: {counts[n]}" for n in (3, 2, 1, 0))]
    out += ["", "| function | result |", "|---|---|"]
    for target in targets:
        cells = " / ".join(r["reason"] for r in sorted(by_id.get(target.id, []), key=lambda r: r["run"])) or "-"
        out.append(f"| {target.id} | {cells} |")
    return "\n".join(out) + "\n"


def env_check(target: Target) -> None:
    from contree_sdk import ContreeSync

    uuid, error = prepare((target.repo, target.commit, target.image, target.setup))
    if error:
        raise SystemExit(error)
    _, output = Contree(target.image).session(ContreeSync().images.use(UUID(uuid))).execute("env", 60)
    names = sorted(line.split("=", 1)[0] for line in output.splitlines() if "=" in line)
    print(" ".join(names))
    print("API key in the sandbox" if any(n.startswith("NEBIUS") for n in names) else "no API key in the sandbox")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int)
    parser.add_argument("--only", default="")
    parser.add_argument("--repeat", type=int, default=0)
    parser.add_argument("--env-check", action="store_true")
    args = parser.parse_args()
    targets = [t for t in dataset() if args.only in t.id][: args.limit]
    if args.env_check:
        env_check(targets[0])
        return
    rows = json.loads(RUNS.read_text()) if RUNS.exists() else []
    done = {(r["run"], r["id"]) for r in rows}
    jobs = [(0, t) for t in targets] + [(run, t) for run in (1, 2) for t in targets[: args.repeat]]
    jobs = [(run, t) for run, t in jobs if (run, t.id) not in done]
    keys = list(dict.fromkeys((t.repo, t.commit, t.image, t.setup) for _, t in jobs))
    with ThreadPoolExecutor(WORKERS) as threads:
        prepared = dict(zip(keys, threads.map(prepare, keys)))
    pending = []
    for run, target in jobs:
        uuid, error = prepared[target.repo, target.commit, target.image, target.setup]
        if error:
            rows.append(asdict(Outcome(DESIGN, run, target.id, False, "install", error[-300:])))
        else:
            pending.append((run, target, uuid))
    write(RUNS, rows)
    with ProcessPoolExecutor(WORKERS) as workers:
        futures = [workers.submit(job, *args) for args in pending]
        for n, future in enumerate(as_completed(futures), 1):
            row = future.result()
            rows.append(row)
            write(RUNS, rows)
            print(f"{n}/{len(futures)} {row['run']} {row['id']}: {row['reason']} ({row['seconds']} s)", file=sys.stderr)
    text = table(rows, targets)
    TABLE.write_text(text)
    print(text)


if __name__ == "__main__":
    main()
