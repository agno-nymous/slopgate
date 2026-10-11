import ast
import configparser
import fnmatch
import hashlib
import re
import tomllib
from dataclasses import dataclass

from radon.complexity import cc_visit

BLOCKS = (ast.If, ast.For, ast.AsyncFor, ast.While, ast.Try, ast.TryStar, ast.With, ast.AsyncWith, ast.Match)


@dataclass(frozen=True)
class Function:
    qualname: str
    path: str
    start: int
    end: int
    source: str


def parse(path: str, text: str) -> list[Function]:
    lines = text.splitlines(keepends=True)
    found = []

    def walk(body, prefix):
        for node in body:
            if isinstance(node, ast.ClassDef):
                walk(node.body, f"{prefix}{node.name}.")
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                start = node.decorator_list[0].lineno if node.decorator_list else node.lineno
                end = node.end_lineno
                if lines[end - 1].encode()[node.end_col_offset :].strip() == b"\\":
                    end += 1
                source = "".join(lines[start - 1 : end])
                found.append(Function(prefix + node.name, path, start, end, source))

    walk(ast.parse(text).body, "")
    return found


def dedent(source: str) -> str:
    first = next((line for line in source.splitlines() if line.strip()), "")
    prefix = first[: len(first) - len(first.lstrip())]
    # unlike textwrap.dedent, a less indented line (a column-0 comment, a multi-line string line) stays as it is
    return "".join(line.removeprefix(prefix) for line in source.splitlines(keepends=True))


def structure_hash(source: str) -> str:
    node = ast.parse(dedent(source)).body[0]
    if ast.get_docstring(node) is not None:
        node.body = node.body[1:] or [ast.Pass()]
    names = {}

    def placeholder(name):
        return names.setdefault(name, f"_{len(names)}")

    node.name = placeholder(node.name)
    args = node.args
    for arg in [*args.posonlyargs, *args.args, args.vararg, *args.kwonlyargs, args.kwarg]:
        if arg:
            arg.arg = placeholder(arg.arg)
    stored = {n.id for n in ast.walk(node) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store)}
    for n in ast.walk(node):
        if isinstance(n, ast.Name) and (n.id in names or n.id in stored):
            n.id = placeholder(n.id)
    return hashlib.sha256(ast.dump(node).encode()).hexdigest()


def complexity(source: str) -> int:
    return cc_visit(dedent(source))[0].complexity


def nesting(source: str) -> int:
    def depth(node, is_elif=False):
        inner = [
            depth(child, isinstance(node, ast.If) and isinstance(child, ast.If) and node.orelse == [child])
            for child in ast.iter_child_nodes(node)
        ]
        return (isinstance(node, BLOCKS) and not is_elif) + max(inner, default=0)

    return depth(ast.parse(dedent(source)))


def tokens(source: str) -> frozenset[str]:
    words = re.findall(r"[A-Za-z_][A-Za-z0-9_]*|\d+|[^\sA-Za-z0-9_]", source)
    return frozenset(part.lower() for word in words for part in re.split(r"_|(?<=[a-z])(?=[A-Z])", word) if part)


def jaccard(a: frozenset[str], b: frozenset[str]) -> float:
    return len(a & b) / len(a | b)


def pytest_patterns(read) -> list[str]:
    if (ini := read("pytest.ini")) is not None:
        config = configparser.ConfigParser(interpolation=None)
        config.read_string(ini)
        value = config.get("pytest", "python_files", fallback=None)
    else:
        value = tomllib.loads(read("pyproject.toml") or "").get("tool", {}).get("pytest", {}).get("ini_options", {}).get("python_files")
    if not value:
        return ["test_*.py", "*_test.py"]
    return value.split() if isinstance(value, str) else value


def is_test_file(path: str, patterns: list[str]) -> bool:
    name = path.rsplit("/", 1)[-1]
    return name == "conftest.py" or any(fnmatch.fnmatchcase(name, pattern) for pattern in patterns)
