import ast
import functools
import io
import json
import subprocess
import sys
import textwrap
import tokenize
from concurrent.futures import ThreadPoolExecutor

import vulture
from pydantic import BaseModel, Field

from slopgate import llm, trace
from slopgate.config import LIGHTNING, NESTING
from slopgate.functions import Function, nesting

KINDS = {
    "nesting": "It nests blocks deeply. Flatten it with guard clauses or a single boolean expression.",
    "redundant_check": "It repeats a check that an earlier check already guarantees. Remove the repeated check.",
    "swallowed_error": (
        "It catches broad exceptions or wraps code that cannot raise in a try block. "
        "Narrow each except to the exceptions that the code in its try block raises, "
        "and remove try blocks around code that cannot raise. Every input must still give the same result."
    ),
    "lookup_table": "It maps values to results with a long if/elif chain. Replace the chain with a dict lookup.",
    "filler_comment": "It has comments that only restate the code. Remove them and keep comments that explain why.",
    "dead": "It has unreachable code or unused variables. Remove them.",
}
RULES = {
    "redundant_check": (
        "A condition tests a fact that an earlier condition in the same function already guarantees, "
        "so at that point the test is always true or always false. "
        "Example: `if price > 0:` in a branch that runs only after `if price <= 0: return 0`."
    ),
    "filler_comment": (
        "A comment only repeats in words what the code on the next line says, for example `# loop over the values` above `for value in values:`. "
        "A comment that explains why, states a limit, or gives a reference is not slop. A function with no `#` comment never has this kind."
    ),
}
GUARDS = {"if", "elif", "while", "and", "or", "assert"}
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

CHECK_PROMPT = """Check the Python function below for one kind of slop: {kind}.

Rule: {rule}

Report a line only when it matches the rule. Most functions have no such line.

Reply by calling the tool `Check`.

File: {path}

{fence}python
{source}
{fence}"""


class Check(BaseModel):
    """Report the lines of the function that match the rule."""

    reason: str = Field(description="What you checked, and why each reported line matches the rule, or why no line matches.")
    lines: list[str] = Field(description="Each line of the function that matches the rule, copied exactly. An empty list when no line matches.")


def comments(code: str) -> list[str]:
    return [t.string for t in tokenize.generate_tokens(io.StringIO(code).readline) if t.type == tokenize.COMMENT]


def has_dead_code(function, text: str) -> bool:
    scan = vulture.Vulture()
    scan.scan(text, filename=function.path)
    tree = ast.parse(textwrap.dedent(function.source))
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


def measured(function, text: str) -> set[str]:
    kinds = {kind for row, kind in ruff(function.path, text) if function.start <= row <= function.end}
    if nesting(function.source) > NESTING:
        kinds.add("nesting")
    if has_dead_code(function, text):
        kinds.add("dead")
    return kinds


def conditions(source: str) -> int:
    tree = ast.parse(source)
    return sum(isinstance(n, (ast.If, ast.IfExp, ast.While, ast.BoolOp)) for n in ast.walk(tree)) + sum(
        len(n.ifs) for n in ast.walk(tree) if isinstance(n, ast.comprehension)
    )


def in_source(evidence: str, source: str) -> bool:
    lines = {line.strip() for line in source.splitlines()}
    parts = [part.strip() for part in evidence.splitlines() if part.strip()]
    return bool(parts) and all(part in lines for part in parts)


def grounded_line(kind: str, evidence: str, source: str) -> bool:
    if not in_source(evidence, source):
        return False
    code = "\n".join(part.strip() for part in evidence.splitlines())
    try:
        if kind == "filler_comment":
            return bool(comments(code))
        names = {t.string for t in tokenize.generate_tokens(io.StringIO(code).readline) if t.type == tokenize.NAME}
    except (tokenize.TokenError, IndentationError):
        return False
    return bool(names & GUARDS)


def classify(function, text: str) -> dict[str, list[str]]:
    source = textwrap.dedent(function.source)
    asked = [kind for kind, ask in (("redundant_check", conditions(source) >= 2), ("filler_comment", bool(comments(source)))) if ask]
    fence = "````" if "```" in source else "```"

    def check(kind):
        prompt = CHECK_PROMPT.format(kind=kind, rule=RULES[kind], path=function.path, source=source, fence=fence)
        with trace.span("gate.check", slop_kind=kind, prompt="CHECK_PROMPT"):
            try:
                reply = llm.decide(LIGHTNING, prompt, Check)
            except Exception as error:
                trace.output(f"internal error: {error!r}")
                return kind, []
            lines = [line.strip() for line in reply.lines if grounded_line(kind, line, source)] if reply else []
            trace.output(lines)
        return kind, lines

    with ThreadPoolExecutor() as threads:
        found = {kind: lines for kind, lines in threads.map(trace.bind(check), asked) if lines}
    found |= dict.fromkeys(measured(function, text), [])
    return {kind: found[kind] for kind in KINDS if kind in found}


def leftover(kinds, function, suggested: str, spliced: str) -> str | None:
    new = Function(function.qualname, function.path, function.start, function.start + suggested.count("\n") - 1, suggested)
    found = measured(new, spliced)
    for kind, evidence in kinds.items():
        if kind in found or (evidence and all(in_source(line, suggested) for line in evidence)):
            return f"rewrite leaves the slop: {kind}"
    return None


def problems(kinds) -> str:
    return "\n".join(
        f"{n}. {KINDS[kind]}" + (" These lines:" + "".join(f"\n   {line}" for line in lines) if lines else "")
        for n, (kind, lines) in enumerate(kinds.items(), 1)
    )
