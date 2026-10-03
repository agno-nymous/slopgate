import ast
import textwrap
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
                source = "".join(lines[start - 1 : node.end_lineno])
                found.append(Function(prefix + node.name, path, start, node.end_lineno, source))

    walk(ast.parse(text).body, "")
    return found


def complexity(source: str) -> int:
    return cc_visit(textwrap.dedent(source))[0].complexity


def nesting(source: str) -> int:
    def depth(node, is_elif=False):
        inner = [
            depth(child, isinstance(node, ast.If) and isinstance(child, ast.If) and node.orelse == [child])
            for child in ast.iter_child_nodes(node)
        ]
        return (isinstance(node, BLOCKS) and not is_elif) + max(inner, default=0)

    return depth(ast.parse(textwrap.dedent(source)))
