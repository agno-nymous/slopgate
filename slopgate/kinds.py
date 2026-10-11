import ast
import functools
import io
import json
import subprocess
import sys
import tokenize

import vulture

from slopgate.config import NESTING
from slopgate.functions import BLOCKS, Function, dedent

KINDS = {
    "nesting": "It nests blocks deeply. Flatten it with guard clauses or a single boolean expression.",
    "redundant_check": "It repeats a check that an earlier check already guarantees. Remove the repeated check.",
    "swallowed_error": (
        "It catches broad exceptions or wraps code that cannot raise in a try block. "
        "Narrow each except to the exceptions that the code in its try block raises, "
        "and remove try blocks around code that cannot raise. Every input must still give the same result."
    ),
    "lookup_table": "It maps values to results with a long if/elif chain. Replace the chain with a dict lookup.",
    "dead": "It has unreachable code or unused variables. Remove them.",
}
RUFF = {
    "SIM116": "lookup_table",
    "BLE001": "swallowed_error",
    "E722": "swallowed_error",
    "S110": "swallowed_error",
    "S112": "swallowed_error",
    "F841": "dead",
    "RUF059": "dead",
}
DEAD = {"unreachable_code", "variable"}
EXITS = (ast.Return, ast.Raise, ast.Continue, ast.Break)
LOOPS = (ast.For, ast.AsyncFor, ast.While)
SCOPES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)
PURE = {"isinstance", "hasattr", "callable", "len", "type", "any", "all"}
FLIP = {
    ast.Is: ast.IsNot,
    ast.IsNot: ast.Is,
    ast.Eq: ast.NotEq,
    ast.NotEq: ast.Eq,
    ast.In: ast.NotIn,
    ast.NotIn: ast.In,
    ast.Lt: ast.GtE,
    ast.GtE: ast.Lt,
    ast.Gt: ast.LtE,
    ast.LtE: ast.Gt,
}


def comments(code: str) -> list[str]:
    return [t.string for t in tokenize.generate_tokens(io.StringIO(code).readline) if t.type == tokenize.COMMENT]


def has_dead_code(function, text: str) -> bool:
    scan = vulture.Vulture()
    scan.scan(text, filename=function.path)
    tree = ast.parse(dedent(function.source))
    # vulture reports unused parameters as typ "variable"; removing one would change a signature callers use
    params = {
        a.arg
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda))
        for a in (*node.args.posonlyargs, *node.args.args, node.args.vararg, *node.args.kwonlyargs, node.args.kwarg)
        if a
    }
    return any(
        item.typ in DEAD and function.start <= item.first_lineno <= function.end and item.name not in params
        for item in scan.get_unused_code()
    )


@functools.cache
def ruff(path: str, text: str) -> tuple[tuple[int, str], ...]:
    args = ["check", "--isolated", "--select", ",".join(RUFF), "--output-format", "json", "--stdin-filename", path, "-"]
    run = subprocess.run([sys.executable, "-m", "ruff", *args], input=text, capture_output=True, text=True)
    if run.returncode not in (0, 1):
        raise RuntimeError(f"ruff failed on {path}: {run.stderr.strip()}")
    found = json.loads(run.stdout)
    handlers = [n for n in ast.walk(ast.parse(text)) if isinstance(n, ast.ExceptHandler)]
    # option A (ticket 36): a broad except whose body uses the caught error handles it on purpose
    handled = {
        row
        for h in handlers
        if h.name and any(isinstance(n, ast.Name) and n.id == h.name for stmt in h.body for n in ast.walk(stmt))
        for row in range(h.lineno, h.type.end_lineno + 1)
    }
    return tuple(
        (item["location"]["row"], RUFF[item["code"]])
        for item in found
        if not (item["code"] == "BLE001" and item["location"]["row"] in handled)
    )


def key(test: ast.expr) -> str:
    return ast.dump(test, annotate_fields=False)


def negation(test: ast.expr) -> str:
    if isinstance(test, ast.UnaryOp) and isinstance(test.op, ast.Not):
        return key(test.operand)
    if isinstance(test, ast.Compare) and len(test.ops) == 1 and type(test.ops[0]) in FLIP:
        return key(ast.Compare(test.left, [FLIP[type(test.ops[0])]()], test.comparators))
    return key(ast.UnaryOp(ast.Not(), test))


def outer(node: ast.AST):
    for child in ast.iter_child_nodes(node):
        if not isinstance(child, SCOPES):
            yield child
            yield from outer(child)


def effects(nodes) -> tuple[set[str], bool]:
    found = [d for node in nodes for d in ([node] if isinstance(node, SCOPES) else [node, *outer(node)])]
    # a comprehension target lives in the comprehension's own scope
    local = {id(n) for c in found if isinstance(c, ast.comprehension) for n in ast.walk(c.target)}
    names = set()
    for n in found:
        match n:
            case ast.Name(ctx=ast.Store() | ast.Del()) if id(n) not in local:
                names.add(n.id)
            case ast.Attribute(ctx=ast.Store() | ast.Del()) | ast.Subscript(ctx=ast.Store() | ast.Del()):
                names |= {m.id for m in ast.walk(n) if isinstance(m, ast.Name)}
            case ast.FunctionDef() | ast.AsyncFunctionDef() | ast.ClassDef() | ast.ExceptHandler(name=str()) | ast.MatchAs(name=str()) | ast.MatchStar(name=str()):
                names.add(n.name)
            case ast.MatchMapping(rest=str()):
                names.add(n.rest)
            case ast.alias():
                names.add((n.asname or n.name).split(".")[0])
            case ast.Global() | ast.Nonlocal():
                names.update(n.names)
    called = any(isinstance(n, ast.Call) and not (isinstance(n.func, ast.Name) and n.func.id in PURE) for n in found)
    return names, called


def kept(facts: dict, nodes) -> dict:
    changed, called = effects(nodes)
    # a call can change any state a fact reads: a global, a nonlocal, an attribute, or the object a name holds
    return {} if called else {fact: read for fact, read in facts.items() if not read & changed}


def repeated_checks(source: str) -> list[str]:
    source = dedent(source)
    lines = source.splitlines()
    found = []

    def walk(stmts, facts):
        for stmt in stmts:
            if isinstance(stmt, ast.If):
                test, opposite = key(stmt.test), negation(stmt.test)
                facts = kept(facts, [stmt.test])
                if test in facts or opposite in facts:
                    found.append(lines[stmt.lineno - 1].strip())
                names = {n.id for n in ast.walk(stmt.test) if isinstance(n, ast.Name)}
                walk(stmt.body, facts | {test: names})
                walk(stmt.orelse, facts | {opposite: names})
                if not stmt.orelse and isinstance(stmt.body[-1], EXITS):
                    facts[opposite] = names
                else:
                    facts = kept(facts, stmt.body + stmt.orelse)
                continue
            if isinstance(stmt, (ast.Try, ast.TryStar)):
                walk(stmt.body, facts)
                walk(stmt.orelse, kept(facts, stmt.body))
                walk(stmt.finalbody, kept(facts, stmt.body + stmt.handlers + stmt.orelse))
            elif isinstance(stmt, (ast.With, ast.AsyncWith)):
                walk(stmt.body, kept(facts, stmt.items))
            else:
                walk(getattr(stmt, "body", []), {})
                walk(getattr(stmt, "orelse", []), {})
            # a handler runs after its try body stopped part way, and a case pattern can bind names, so both start with no facts
            for part in [*getattr(stmt, "handlers", []), *getattr(stmt, "cases", [])]:
                walk(part.body, {})
            facts = kept(facts, [stmt])

    walk(ast.parse(source).body[0].body, {})
    return list(dict.fromkeys(found))


def flattenable(source: str) -> bool:
    function = ast.parse(dedent(source)).body[0]

    def rest(node):
        return [] if len(node.orelse) == 1 and isinstance(node.orelse[0], ast.Pass) else node.orelse

    def exits(stmts):
        return bool(stmts) and isinstance(stmts[-1], EXITS)

    def has_block(stmts):
        return any(isinstance(n, BLOCKS) for stmt in stmts for n in ast.walk(stmt))

    bodies = [function.body, *(n.body for n in ast.walk(function) if isinstance(n, LOOPS))]
    last = {id(body[-1]) for body in bodies}

    def shape(node):
        other = rest(node)
        chain = len(other) == 1 and isinstance(other[0], ast.If)
        return (
            (node.orelse and not other)
            or (other and not chain and (exits(node.body) and has_block(other) or exits(other) and has_block(node.body)))
            or (not node.orelse and id(node) in last and has_block(node.body))
            or (not other and len(node.body) == 1 and isinstance(node.body[0], ast.If) and not rest(node.body[0]))
        )

    # only an if on a chain of blocks deeper than NESTING: an ancestor of a deep block, or inside one
    deep = set()

    def visit(node, depth, path, is_elif=False):
        depth += isinstance(node, BLOCKS) and not is_elif
        if isinstance(node, BLOCKS) and depth > NESTING:
            deep.update(map(id, path), map(id, ast.walk(node)))
        for child in ast.iter_child_nodes(node):
            visit(child, depth, [*path, node], isinstance(node, ast.If) and isinstance(child, ast.If) and node.orelse == [child])

    visit(function, 0, [])
    return any(shape(n) for n in ast.walk(function) if isinstance(n, ast.If) and id(n) in deep)


def measured(function, text: str) -> dict[str, list[str]]:
    found = {kind: [] for row, kind in ruff(function.path, text) if function.start <= row <= function.end}
    if flattenable(function.source):
        found["nesting"] = []
    if lines := repeated_checks(function.source):
        found["redundant_check"] = lines
    if has_dead_code(function, text):
        found["dead"] = []
    return found


def classify(function, text: str) -> dict[str, list[str]]:
    found = measured(function, text)
    return {kind: found[kind] for kind in KINDS if kind in found}


def leftover(kinds, function, suggested: str, spliced: str) -> str | None:
    new = Function(function.qualname, function.path, function.start, function.start + suggested.count("\n") - 1, suggested)
    found = measured(new, spliced)
    return next((f"rewrite leaves the slop: {kind}" for kind in kinds if kind in found), None)


def problems(kinds) -> str:
    return "\n".join(
        f"{n}. {KINDS[kind]}" + (" These lines:" + "".join(f"\n   {line}" for line in lines) if lines else "")
        for n, (kind, lines) in enumerate(kinds.items(), 1)
    )
