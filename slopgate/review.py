import ast
import json
import re
import textwrap

import vulture

from slopgate import diff, llm
from slopgate.config import COMPLEXITY, LIGHTNING, NESTING, SUPER, ULTRA
from slopgate.functions import complexity, nesting
from slopgate.sandbox import InstallError, commands, tail

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
DEAD = {"unreachable_code", "variable"}
NONDETERMINISTIC = {"random", "secrets", "uuid", "time", "datetime"}
DEFS = (ast.FunctionDef, ast.AsyncFunctionDef)
COVERAGE = "--slopgate-coverage--"

CLASSIFY_PROMPT = """Name the slop kind that fits the Python function below best.

Kinds:
{kinds}
- none: no kind above fits.

Reply with JSON only, in the form {{"kind": "<kind>"}}.

{source}"""

TESTS_PROMPT = """Write characterization tests for the Python function below. They must record what the code does now, bugs included.

Rules:
- Reply with one pytest file and nothing else.
- Import the target with exactly this one import line, and no other import of the module under test: from {module} import {name}
- Call the function as `{qualname}`.
- Cover every branch of the function.

File: {path}

{source}"""

REWRITE_PROMPT = """Rewrite the Python function below. {instruction}

Rules:
- Keep the exact signature, the decorators, and the behavior, bugs included.
- Add no new functions, no lambdas, and no new classes.
- Reply with the full rewritten function, decorators included, and nothing else.

{source}"""

RETRY_PROMPT = (
    REWRITE_PROMPT
    + """

This earlier rewrite failed:

{rewrite}
Failure:

{failure}"""
)


def strip_fence(text: str) -> str:
    m = re.search(r"```[\w-]*\n(.*?)```", text, re.S)
    return m[1] if m else text


def dead_lines(path: str, text: str) -> set[int]:
    scan = vulture.Vulture()
    scan.scan(text, filename=path)
    return {
        line
        for item in scan.get_unused_code()
        if item.typ in DEAD
        for line in range(item.first_lineno, item.last_lineno + 1)
    }


def classify(source: str) -> str | None:
    kinds = "\n".join(f"- {kind}: {instruction}" for kind, instruction in KINDS.items())
    reply = llm.complete(LIGHTNING, CLASSIFY_PROMPT.format(kinds=kinds, source=source), json=True)
    try:
        kind = json.loads(reply)["kind"]
        return kind if kind in KINDS else None
    except (TypeError, ValueError, KeyError):
        return None


def nondeterministic(source: str) -> str | None:
    names = {node.id for node in ast.walk(ast.parse(source)) if isinstance(node, ast.Name)}
    return min(names & NONDETERMINISTIC, default=None)


def signature(node) -> tuple:
    return type(node), node.name, ast.dump(node.args), node.returns and ast.dump(node.returns)


def broken_rule(original: str, rewrite: str) -> str | None:
    try:
        new = ast.parse(rewrite)
    except SyntaxError:
        return "does not parse"
    old = ast.parse(original)

    def count(tree, types):
        return sum(isinstance(node, types) for node in ast.walk(tree))

    if count(new, ast.ClassDef) > count(old, ast.ClassDef):
        return "adds a class"
    if count(new, (*DEFS, ast.Lambda)) > count(old, (*DEFS, ast.Lambda)):
        return "adds a function"
    if len(new.body) != 1 or not isinstance(new.body[0], DEFS) or signature(new.body[0]) != signature(old.body[0]):
        return "signature changed"
    return None


def review(repo, base, head, sandbox) -> dict:
    result = {"suggestions": [], "followup": [], "rejected": []}
    candidates = []
    for function, added in diff.changed_functions(repo, base, head):
        text = diff.git(repo, "show", f"{head}:{function.path}")
        if dead_lines(function.path, text) & set(range(function.start, function.end + 1)):
            kind = "dead"
        elif complexity(function.source) >= COMPLEXITY or nesting(function.source) > NESTING:
            kind = classify(function.source)
        else:
            continue
        if kind:
            candidates.append((function, added, kind, text))
    if not candidates:
        return result
    setup, test = commands(repo, head)
    try:
        checkpoint = sandbox.prepare(repo, head, setup)
    except InstallError as error:
        result["rejected"].append({"reason": f"could not build test environment\n{error}"})
        return result
    # ponytail: one trial at a time (well under the cap of 8); a thread pool of 8 when review time matters
    for n, (function, added, kind, text) in enumerate(candidates):
        rejected = {"function": function.qualname, "path": function.path}
        dedented = textwrap.dedent(function.source)
        name = nondeterministic(dedented)
        if name:
            result["rejected"].append({**rejected, "reason": f"nondeterministic: uses {name}"})
            continue

        module = function.path.removesuffix(".py").replace("/", ".")
        tests = strip_fence(
            llm.complete(
                SUPER,
                TESTS_PROMPT.format(
                    module=module,
                    name=function.qualname.split(".")[0],
                    qualname=function.qualname,
                    path=function.path,
                    source=function.source,
                ),
            )
        )
        test_path = f"tests/test_slopgate_{n}.py"
        cmd = f"python -m coverage run --branch -m pytest -q {test_path}"

        code, output = sandbox.run(
            checkpoint, {test_path: tests}, f"PYTHONHASHSEED=1 {cmd} && echo {COVERAGE} && python -m coverage json -q -o -"
        )
        second, _ = sandbox.run(checkpoint, {test_path: tests}, f"PYTHONHASHSEED=2 {cmd}")
        if bool(code) != bool(second):
            result["rejected"].append({**rejected, "reason": "nondeterministic: characterization tests differ across two runs"})
            continue
        if code:
            result["rejected"].append({**rejected, "reason": f"characterization tests fail on original: {tail(output)}"})
            continue
        report = json.loads(output.split(COVERAGE)[1])["files"][function.path]
        missed = sum(function.start <= line <= function.end for line, _ in report["missing_branches"])
        if missed:
            result["rejected"].append({**rejected, "reason": f"characterization tests miss branches: {missed}"})
            continue

        indent = function.source[: len(function.source) - len(function.source.lstrip())]
        lines = text.splitlines(keepends=True)
        reply = llm.complete(SUPER, REWRITE_PROMPT.format(instruction=KINDS[kind], source=dedented))
        for retry in (False, True):
            rewrite = textwrap.dedent(strip_fence(reply)).strip("\n") + "\n"
            failure = broken_rule(dedented, rewrite)
            if failure:
                failure = f"rule: {failure}"
                break
            suggested = textwrap.indent(rewrite, indent)
            spliced = "".join(lines[: function.start - 1]) + suggested + "".join(lines[function.end :])
            code, output = sandbox.run(checkpoint, {test_path: tests, function.path: spliced}, cmd)
            if code:
                failure = f"rewrite fails characterization tests: {tail(output)}"
            else:
                repo_code, repo_output = sandbox.run(checkpoint, {function.path: spliced}, test)
                failure = f"rewrite fails repo tests: {tail(repo_output)}" if repo_code not in (0, 5) else None
            if not failure or retry:
                break
            reply = llm.complete(
                ULTRA, RETRY_PROMPT.format(instruction=KINDS[kind], source=dedented, rewrite=rewrite, failure=failure)
            )
        if failure:
            result["rejected"].append({**rejected, "reason": failure})
            continue

        start, end = function.start, function.end
        if set(range(start, end + 1)) <= added:
            passed = re.search(r"(\d+) passed", output)[1]
            body = (
                f"Slopgate (`{kind}`) rewrite of `{function.qualname}`: "
                f"nesting {nesting(function.source)} -> {nesting(rewrite)}, "
                f"complexity {complexity(function.source)} -> {complexity(rewrite)}. "
                f"{passed} characterization tests passed in sandbox.\n\n"
                f"```suggestion\n{suggested}```"
            )
            suggestion = {"path": function.path, "line": end, "side": "RIGHT", "body": body}
            if start != end:
                suggestion |= {"start_line": start, "start_side": "RIGHT"}
            result["suggestions"].append(suggestion)
        else:
            result["followup"].append({"path": function.path, "start_line": start, "end_line": end, "code": suggested})
    return result
