import re
import sys
import textwrap

from slopgate import diff, llm, sandbox
from slopgate.config import COMPLEXITY, NESTING, SUPER
from slopgate.functions import complexity, nesting

TESTS_PROMPT = """Write characterization tests for the Python function below. They must record what the code does now, bugs included.

Rules:
- Reply with one pytest file and nothing else.
- Import the target with exactly this one import line, and no other import of the module under test: from {module} import {name}
- Call the function as `{qualname}`.
- Cover every branch of the function.

File: {path}

{source}"""

REWRITE_PROMPT = """Rewrite the Python function below to remove deep nesting and redundant branches. Use guard clauses or a single boolean expression where they fit.

Rules:
- Keep the exact signature, the decorators, and the behavior, bugs included.
- Add no new functions and no new classes.
- Reply with the full rewritten function, decorators included, and nothing else.

{source}"""


def strip_fence(text: str) -> str:
    m = re.search(r"```[\w-]*\n(.*?)```", text, re.S)
    return m[1] if m else text


def tail(output: str) -> str:
    return "\n".join(output.strip().splitlines()[-20:])


def review(repo, base, head) -> dict:
    result = {"suggestions": [], "followup": [], "rejected": []}
    flagged = [
        (function, added)
        for function, added in diff.changed_functions(repo, base, head)
        if complexity(function.source) >= COMPLEXITY or nesting(function.source) > NESTING
    ]
    if not flagged:
        return result
    checkpoint = sandbox.checkpoint(repo, head)
    for n, (function, added) in enumerate(flagged):
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
        cmd = [sys.executable, "-m", "coverage", "run", "--branch", "-m", "pytest", "-q", test_path]
        rejected = {"function": function.qualname, "path": function.path}

        code, output = sandbox.run(checkpoint, {test_path: tests}, cmd)
        if code:
            result["rejected"].append({**rejected, "reason": f"characterization tests fail on original: {tail(output)}"})
            continue

        dedented = textwrap.dedent(function.source)
        indent = function.source[: len(function.source) - len(function.source.lstrip())]
        rewrite = strip_fence(llm.complete(SUPER, REWRITE_PROMPT.format(source=dedented)))
        rewrite = textwrap.indent(rewrite.strip("\n") + "\n", indent)

        lines = (checkpoint / function.path).read_text().splitlines(keepends=True)
        spliced = "".join(lines[: function.start - 1]) + rewrite + "".join(lines[function.end :])
        code, output = sandbox.run(checkpoint, {test_path: tests, function.path: spliced}, cmd)
        if code:
            result["rejected"].append({**rejected, "reason": f"rewrite fails characterization tests: {tail(output)}"})
            continue

        start, end = function.start, function.end
        if set(range(start, end + 1)) <= added:
            passed = re.search(r"(\d+) passed", output)[1]
            body = (
                f"Slopgate rewrite of `{function.qualname}`: "
                f"nesting {nesting(function.source)} -> {nesting(rewrite)}, "
                f"complexity {complexity(function.source)} -> {complexity(rewrite)}. "
                f"{passed} characterization tests passed in sandbox.\n\n"
                f"```suggestion\n{rewrite}```"
            )
            suggestion = {"path": function.path, "line": end, "side": "RIGHT", "body": body}
            if start != end:
                suggestion |= {"start_line": start, "start_side": "RIGHT"}
            result["suggestions"].append(suggestion)
        else:
            result["followup"].append({"path": function.path, "start_line": start, "end_line": end, "code": rewrite})
    return result
