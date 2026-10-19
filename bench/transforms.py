import ast
import re
import textwrap
import zlib

from slopgate.config import NESTING
from slopgate.functions import dedent, nesting, parse
from slopgate.review import DEFS, apply, forwarded, scope

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
    "dead": dead,
}


def indent_of(source: str) -> str:
    return re.match(r"[ \t]*", source)[0]


def transform(kind: str, source: str, text: str) -> str | None:
    source = source if source.endswith("\n") else source + "\n"
    new = TRANSFORMS[kind](textwrap.dedent(source), text)
    return new and textwrap.indent(new, indent_of(source))


def sites(text: str, function, covered: set[int], top: bool = False) -> list[ast.Name]:
    tree = ast.parse(text)
    outside = [node for node in ast.walk(tree) if isinstance(node, DEFS) and not function.start <= node.lineno <= function.end]
    # the gate inlines a wrapper only into a call that sits directly in a top-level function
    nodes = [n for fn in outside if fn in tree.body for n in scope(fn)] if top else [n for fn in outside for n in ast.walk(fn)]
    found = {
        id(n.func): n.func
        for n in nodes
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == function.qualname and n.lineno in covered
    }
    return sorted(found.values(), key=lambda name: (name.lineno, name.col_offset))


def unbound(text: str, name: str) -> bool:
    tree = ast.parse(text)
    bound = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
    bound |= {node.name for node in ast.walk(tree) if isinstance(node, (*DEFS, ast.ClassDef))}
    bound |= {(a.asname or a.name).split(".")[0] for node in ast.walk(tree) if isinstance(node, (ast.Import, ast.ImportFrom)) for a in node.names}
    return name not in bound


def insert_after(text: str, function, code: str) -> str:
    lines = text.splitlines(keepends=True)
    head = "".join(lines[: function.end])
    return head + ("" if head.endswith("\n") else "\n") + "\n\n" + code + "".join(lines[function.end :])


def rename(text: str, names: list[ast.Name], new: str) -> str:
    return apply(text, [(n.lineno, n.col_offset, n.end_lineno, n.end_col_offset, new) for n in names])


def wrapper(text: str, function, covered: set[int]) -> tuple[str, str] | None:
    node = next((n for n in ast.parse(text).body if isinstance(n, ast.FunctionDef) and n.lineno == function.start), None)
    if node is None or node.decorator_list or node.args.vararg or node.args.kwarg:
        return None
    new, found = f"_{function.qualname.lstrip('_')}_impl", sites(text, function, covered, top=True)
    if not found or not unbound(text, new):
        return None
    args = node.args
    forward = [*(a.arg for a in (*args.posonlyargs, *args.args)), *(f"{a.arg}={a.arg}" for a in args.kwonlyargs)]
    code = f"def {new}({ast.unparse(args)}):\n    return {function.qualname}({', '.join(forward)})\n"
    if forwarded(ast.parse(code).body[0]) is None:
        return None
    return insert_after(rename(text, found[:1], new), function, code), new


def duplicate(text: str, function, code: str, name: str, covered: set[int]) -> str | None:
    found = sites(text, function, covered)
    if not found or not unbound(text, name):
        return None
    return insert_after(rename(text, found, name), function, code)


def body_line(function) -> int | None:
    code = dedent(function.source)
    try:
        first = ast.parse(code).body[0].body[0]
    except SyntaxError:
        return None
    return function.start + first.lineno - 1 if not code.splitlines()[first.lineno - 1][: first.col_offset].strip() else None


def control(text: str, qualname: str) -> str:
    function = next(f for f in parse("", text) if f.qualname == qualname)
    line = body_line(function)
    if line is None:
        raise ValueError(f"{qualname} has no body line of its own")
    lines = text.splitlines(keepends=True)
    lines.insert(line - 1, indent_of(lines[line - 1]) + "raise RuntimeError('control')\n")
    return "".join(lines)
