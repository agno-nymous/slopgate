import ast
import builtins
import json
from concurrent.futures import ProcessPoolExecutor

from bench.detect import accept, file_text, load_items
from bench.paths import GROUNDTRUTH, LABELS, RESULTS
from bench.score import WORKERS
from slopgate import kinds
from slopgate.functions import dedent

REPORT = RESULTS / "injection-check.md"
SCOPES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)


def bound(node: ast.AST) -> set[str]:
    match node:
        case (
            ast.Name(id=name, ctx=ast.Store() | ast.Del())
            | ast.arg(arg=name)
            | ast.ExceptHandler(name=str() as name)
            | ast.MatchAs(name=str() as name)
            | ast.MatchStar(name=str() as name)
            | ast.MatchMapping(rest=str() as name)
            | ast.FunctionDef(name=name)
            | ast.AsyncFunctionDef(name=name)
            | ast.ClassDef(name=name)
        ):
            return {name}
        case ast.Import(names=aliases) | ast.ImportFrom(names=aliases):
            return {alias.asname or alias.name.split(".")[0] for alias in aliases}
        case ast.Global(names=names) | ast.Nonlocal(names=names):
            return set(names)
    return set()


def unbound(source: str) -> set[str]:
    tree = ast.parse(dedent(source))
    loaded = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)}
    return loaded - set().union(*map(bound, ast.walk(tree)))


def module_names(text: str) -> set[str]:
    names, stack = set(), list(ast.parse(text).body)
    while stack:
        node = stack.pop()
        names |= bound(node)
        if not isinstance(node, SCOPES):
            stack.extend(ast.iter_child_nodes(node))
    return names


def new_names(source: str, new: str, module_text: str) -> set[str]:
    top = module_names(module_text)
    if "*" in top:
        return set()
    return unbound(new) - unbound(source) - top - set(dir(builtins))


def facts(args) -> tuple[str, str]:
    source, item, text = args
    scored = [kind for kind in item.injected if kind in kinds.KINDS]
    kept = "not scored" if not scored else "keeps" if accept(source, text, item.source, scored, item.origin) else "rejects"
    try:
        ast.parse(dedent(item.source))
    except SyntaxError as error:
        return kept, f"syntax error: {error.msg}"
    try:
        ast.parse(dedent(source.source))
    except SyntaxError:
        return kept, "syntax error in source"
    names = new_names(source.source, item.source, text)
    return kept, f"undefined name: {', '.join(sorted(names))}" if names else "ok"


def defective(row: tuple) -> bool:
    return row[2] == "rejects" or row[3] != "ok" or row[4] not in ("valid", "transform")


def cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


def main() -> None:
    items = load_items(json.loads(GROUNDTRUTH.read_text())["items"])
    by_id = {item.id: item for item in items}
    injections = json.loads(LABELS.read_text())["injections"]
    injected = [item for item in items if item.origin in ("transform", "nemotron")]
    sources = [by_id[item.source_id] for item in injected]
    texts = [file_text(source) for source in sources]
    with ProcessPoolExecutor(WORKERS) as pool:
        results = list(pool.map(facts, zip(sources, injected, texts)))
    rows = []
    for item, (kept, names) in zip(injected, results):
        verdict = injections.get(item.id, {})
        kind = "transform" if item.origin == "transform" else "valid" if verdict.get("valid") else "invalid" if verdict else "unlabelled"
        rows.append((item.id, "+".join(item.injected), kept, names, kind, verdict.get("reason", "")[:120]))
    rows.sort(key=lambda row: not defective(row))
    counts = (
        f"items {len(rows)}, not scored {sum(r[2] == 'not scored' for r in rows)}, gate misses {sum(r[2] == 'rejects' for r in rows)}, "
        f"new names not ok {sum(r[3] != 'ok' for r in rows)}, invalid {sum(r[4] == 'invalid' for r in rows)}"
    )
    table = ["| item | kinds | accept | new names | kind | reason |", "|---|---|---|---|---|---|"]
    table += ["| " + " | ".join(cell(c) for c in row) + " |" for row in rows]
    header = [
        "# Injection check",
        "",
        "A gate miss is not a defect: a valid item that the gate does not find stays in the recall.",
        "A `from x import *` in the module turns the name check off for that module.",
        "",
        counts,
        "",
        "The `new names` column finds only reads of names that nothing binds. It does not find other changes of behavior.",
        "",
    ]
    REPORT.write_text("\n".join([*header, *table]) + "\n")
    print(counts)
    for row in filter(defective, rows):
        print(" | ".join(row))


if __name__ == "__main__":
    main()
