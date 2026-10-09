import ast
import re
import textwrap
import zlib

from slopgate import kinds
from slopgate.config import NESTING
from slopgate.functions import nesting

INVERSE = {ast.Is: ast.IsNot, ast.IsNot: ast.Is, ast.Eq: ast.NotEq, ast.NotEq: ast.Eq, ast.In: ast.NotIn, ast.NotIn: ast.In}
SYMBOL = {ast.Is: "is", ast.IsNot: "is not", ast.Eq: "==", ast.NotEq: "!=", ast.In: "in", ast.NotIn: "not in"}


def statements(node) -> list[ast.stmt]:
    return node.body[1:] if ast.get_docstring(node, clean=False) is not None else node.body


def start(node) -> int:
    return min([node.lineno] + [d.lineno for d in getattr(node, "decorator_list", [])])


def shift(code: str, first: int, last: int) -> list[str]:
    # lines inside a multi-line string are part of its value, so they must not move
    inside = {
        n
        for node in ast.walk(ast.parse(code))
        if isinstance(node, ast.JoinedStr) or (isinstance(node, ast.Constant) and isinstance(node.value, (str, bytes)))
        for n in range(node.lineno + 1, node.end_lineno + 1)
    }
    lines = code.splitlines(keepends=True)
    return ["    " + line if line.strip() and n not in inside else line for n, line in enumerate(lines[first - 1 : last], first)]


def guards(code: str) -> list[tuple[ast.If, list[ast.stmt]]]:
    found = []
    for node in ast.walk(ast.parse(code).body[0]):
        for name in ("body", "orelse", "finalbody"):
            block = getattr(node, name, None)
            if not isinstance(block, list):
                continue
            for i, stmt in enumerate(block[:-1]):
                if (
                    isinstance(stmt, ast.If)
                    and not stmt.orelse
                    and isinstance(stmt.body[-1], (ast.Return, ast.Raise, ast.Continue))
                    and stmt.test.end_lineno == stmt.lineno
                    and stmt.body[0].lineno > stmt.lineno
                ):
                    found.append((stmt, block[i + 1 :]))
    return sorted(found, key=lambda pair: pair[0].lineno)


def operand(node, code: str) -> str:
    text = ast.get_source_segment(code, node)
    # a source segment drops the parentheses that a low-precedence operand needs inside a comparison
    low = isinstance(node, (ast.NamedExpr, ast.Lambda, ast.IfExp, ast.BoolOp, ast.Compare)) or (isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not))
    return f"({text})" if low else text


def negate(test, code: str) -> str:
    if isinstance(test, ast.UnaryOp) and isinstance(test.op, ast.Not):
        return ast.get_source_segment(code, test.operand)
    if isinstance(test, ast.Compare) and len(test.ops) == 1 and type(test.ops[0]) in INVERSE:
        return f"{operand(test.left, code)} {SYMBOL[INVERSE[type(test.ops[0])]]} {operand(test.comparators[0], code)}"
    return f"not ({ast.get_source_segment(code, test)})"


def nested(code: str, text: str) -> str | None:
    while found := guards(code):
        guard, rest = found[0]
        lines = code.splitlines(keepends=True)
        pad = " " * guard.col_offset
        code = "".join(
            lines[: guard.lineno - 1]
            + [f"{pad}if {negate(guard.test, code)}:\n"]
            + shift(code, guard.end_lineno + 1, rest[-1].end_lineno)
            + [f"{pad}else:\n"]
            + lines[guard.lineno : guard.end_lineno]
            + lines[rest[-1].end_lineno :]
        )
    return code if nesting(code) > NESTING else None


def redundant(code: str, text: str) -> str | None:
    found = guards(code)
    if not found:
        return None
    guard, rest = found[0]
    after = rest[0]
    lines = code.splitlines(keepends=True)
    first = start(after)
    return "".join(lines[: first - 1] + [f"{' ' * after.col_offset}if {negate(guard.test, code)}:\n"] + shift(code, first, after.end_lineno) + lines[after.end_lineno :])


def swallowed(code: str, text: str) -> str | None:
    node = ast.parse(code).body[0]
    body = statements(node)
    if not body or body[0].lineno == node.lineno:
        return None
    pad = " " * body[0].col_offset
    lines = code.splitlines(keepends=True)
    first = start(body[0])
    return "".join(
        lines[: first - 1] + [f"{pad}try:\n"] + shift(code, first, node.end_lineno) + [f"{pad}except Exception:\n", f"{pad}    return None\n"] + lines[node.end_lineno :]
    )


def table(value, module: dict[str, ast.Dict]):
    match value:
        case ast.Subscript(value=ast.Dict() as mapping, slice=key):
            return mapping, key, None
        case ast.Subscript(value=ast.Name(id=name), slice=key) if name in module:
            return module[name], key, None
        case ast.Call(func=ast.Attribute(value=ast.Name(id=name), attr="get"), args=[key, *default], keywords=[]) if name in module and len(default) < 2:
            return module[name], key, default[0] if default else ast.Constant(None)
    return None


def module_dicts(text: str) -> dict[str, ast.Dict]:
    return {
        target.id: node.value
        for node in ast.parse(text).body
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Dict)
        for target in node.targets
        if isinstance(target, ast.Name)
    }


def lookup(code: str, text: str) -> str | None:
    tree = ast.parse(code)
    returns = [node for node in ast.walk(tree) if isinstance(node, ast.Return) and isinstance(node.value, (ast.Subscript, ast.Call))]
    module = module_dicts(text) if returns else {}
    lines = code.splitlines(keepends=True)
    names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
    for node in returns:
        if not (found := table(node.value, module)):
            continue
        mapping, key, default = found
        if not 3 <= len(mapping.keys) <= 12 or not all(isinstance(k, ast.Constant) for k in mapping.keys):
            continue
        line = lines[node.lineno - 1]
        if isinstance(key, ast.Constant) or len(line) - len(line.lstrip()) != node.col_offset or (not isinstance(key, ast.Name) and "key" in names):
            continue
        pad = " " * node.col_offset
        subject = ast.get_source_segment(code, key) if isinstance(key, ast.Name) else "key"
        chain = [] if isinstance(key, ast.Name) else [f"{pad}key = {ast.unparse(key)}\n"]
        for n, (k, v) in enumerate(zip(mapping.keys, mapping.values)):
            chain += [f"{pad}{'if' if n == 0 else 'elif'} {subject} == {ast.unparse(k)}:\n", f"{pad}    return {ast.unparse(v)}\n"]
        chain.append(f"{pad}raise KeyError({subject})\n" if default is None else f"{pad}return {ast.unparse(default)}\n")
        return "".join(lines[: node.lineno - 1] + chain + lines[node.end_lineno :])
    return None


def restate(node) -> str | None:
    match node:
        case ast.Return(value=ast.Name(id=name)):
            return f"return the {name}"
        case ast.Return(value=value) if value is not None:
            return "return the result"
        case ast.For(iter=ast.Name(id=name)):
            return f"loop over {name}"
        case ast.For():
            return "loop over the items"
        case ast.Expr(value=ast.Call(func=ast.Name(id=name) | ast.Attribute(attr=name))):
            return f"call {name}"
        case ast.Assign(targets=[ast.Name(id=name)]):
            return f"set {name}"
        case ast.AugAssign(target=ast.Name(id=name)):
            return f"update {name}"
    return None


def filler(code: str, text: str) -> str | None:
    if kinds.comments(code):
        return None
    lines = code.splitlines(keepends=True)
    notes = {}
    for node in ast.walk(ast.parse(code).body[0]):
        line = lines[node.lineno - 1] if isinstance(node, ast.stmt) else ""
        if line and len(line) - len(line.lstrip()) == node.col_offset and (note := restate(node)):
            notes.setdefault(node.lineno, f"{' ' * node.col_offset}# {note}\n")
    picked = sorted(notes.items())[:3]
    if len(picked) < 2:
        return None
    for lineno, comment in reversed(picked):
        lines.insert(lineno - 1, comment)
    return "".join(lines)


def unused_local(code: str, text: str) -> str | None:
    node = ast.parse(code).body[0]
    params = [a.arg for a in (*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs) if a.arg not in ("self", "cls")]
    body = statements(node)
    if not params or not body or body[0].lineno == node.lineno:
        return None
    lines = code.splitlines(keepends=True)
    lines.insert(start(body[0]) - 1, f"{' ' * body[0].col_offset}original_{params[0]} = {params[0]}\n")
    return "".join(lines)


def after_return(code: str, text: str) -> str | None:
    node = ast.parse(code).body[0]
    last = node.body[-1]
    if not isinstance(last, ast.Return) or last.lineno == node.lineno:
        return None
    lines = code.splitlines(keepends=True)
    lines.insert(last.end_lineno, f"{' ' * last.col_offset}return None\n")
    return "".join(lines)


def dead(code: str, text: str) -> str | None:
    # alternate the two forms of dead code across functions, and fall back to the other form
    first, second = (unused_local, after_return) if zlib.crc32(code.encode()) % 2 else (after_return, unused_local)
    return first(code, text) or second(code, text)


TRANSFORMS = {
    "nesting": nested,
    "redundant_check": redundant,
    "swallowed_error": swallowed,
    "lookup_table": lookup,
    "filler_comment": filler,
    "dead": dead,
}


def indent_of(source: str) -> str:
    return re.match(r"[ \t]*", source)[0]


def transform(kind: str, source: str, text: str) -> str | None:
    source = source if source.endswith("\n") else source + "\n"
    new = TRANSFORMS[kind](textwrap.dedent(source), text)
    return new and textwrap.indent(new, indent_of(source))
