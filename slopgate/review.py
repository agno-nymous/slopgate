import ast
import json
import re
import textwrap

import vulture

from slopgate import diff, embed, index, llm
from slopgate.config import COMPLEXITY, DUPLICATE_SCORE, LIGHTNING, NESTING, SUPER, ULTRA
from slopgate.functions import complexity, nesting, structure_hash
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


SAME_JOB_PROMPT = """Decide whether the new Python function does the same job as the existing helper, so that callers of the new function could call the helper instead.

Reply with JSON only, in the form {{"same_job": true or false, "difference": "<the behavior difference, or an empty string>"}}.

New function, in {path}:

{source}

Existing helper, in {helper_path}:

{helper_source}"""


def module_of(path: str) -> str:
    return path.removesuffix(".py").replace("/", ".")


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


def find_duplicate(function, pool) -> dict | None:
    code_hash = structure_hash(function.source)
    for record in pool:
        if record["hash"] == code_hash:
            return {"helper": record, "exact": True, "difference": "", "note": "exact structural copy"}
    [vector] = embed.encode([function.source], query=True)
    for score, record in index.search(pool, vector, DUPLICATE_SCORE, 5):
        prompt = SAME_JOB_PROMPT.format(
            path=function.path, source=function.source, helper_path=record["path"], helper_source=record["source"]
        )
        try:
            verdict = json.loads(llm.complete(SUPER, prompt, json=True))
            if verdict["same_job"] is True:
                return {"helper": record, "exact": False, "difference": str(verdict.get("difference") or ""), "note": f"score {score:.2f}"}
        except (TypeError, ValueError, KeyError):
            continue
    return None


def apply(text: str, edits) -> str:
    lines = text.encode().splitlines(keepends=True) + [b""]
    for start_line, start_col, end_line, end_col, new in sorted(edits, reverse=True):
        lines[start_line - 1 : end_line] = [lines[start_line - 1][:start_col] + new.encode() + lines[end_line - 1][end_col:]]
    return b"".join(lines).decode()


def replace_calls(repo, head, function, helper) -> dict[str, str]:
    old, new = function.qualname, helper["qualname"]
    module, helper_module = module_of(function.path), module_of(helper["path"])
    files = {}
    for path in diff.git(repo, "ls-tree", "-r", "--name-only", head).splitlines():
        if not path.endswith(".py"):
            continue
        text = diff.git(repo, "show", f"{head}:{path}")
        try:
            tree = ast.parse(text)
        except SyntaxError:
            continue
        edits = []
        deleted = range(0)
        if path == function.path:
            lines = text.splitlines()
            last = function.end
            while last < len(lines) and not lines[last].strip():
                last += 1
            deleted = range(function.start, last + 1)
            edits.append((function.start, 0, last + 1, 0, ""))
        sees = path == function.path
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.level == 0 and node.module == module:
                [alias] = [a for a in node.names if a.name == old] or [None]
                if alias:
                    sees = sees or alias.asname is None
                    keep = [a for a in node.names if a is not alias]
                    imports = [ast.ImportFrom(module, keep, 0)] if keep else []
                    imports.append(ast.ImportFrom(helper_module, [ast.alias(new, alias.asname)], 0))
                    replacement = "; ".join(ast.unparse(i) for i in imports)
                    edits.append((node.lineno, node.col_offset, node.end_lineno, node.end_col_offset, replacement))
        calls = [
            node
            for node in ast.walk(tree)
            if sees and isinstance(node, ast.Name) and node.id == old and isinstance(node.ctx, ast.Load) and node.lineno not in deleted
        ]
        edits += [(n.lineno, n.col_offset, n.end_lineno, n.end_col_offset, new) for n in calls]
        bound = {n.name for n in tree.body if isinstance(n, (*DEFS, ast.ClassDef))} | {
            (a.asname or a.name).split(".")[0] for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom)) for a in n.names
        }
        if path == function.path and calls and new not in bound:
            after = max((n.end_lineno for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom))), default=0)
            edits.append((after + 1, 0, after + 1, 0, f"from {helper_module} import {new}\n"))
        if edits:
            files[path] = apply(text, edits)
    return files


def characterize(sandbox, checkpoint, function, test_path, cmd) -> tuple[str | None, str | None]:
    name = nondeterministic(textwrap.dedent(function.source))
    if name:
        return None, f"nondeterministic: uses {name}"
    tests = strip_fence(
        llm.complete(
            SUPER,
            TESTS_PROMPT.format(
                module=module_of(function.path),
                name=function.qualname.split(".")[0],
                qualname=function.qualname,
                path=function.path,
                source=function.source,
            ),
        )
    )
    code, output = sandbox.run(
        checkpoint, {test_path: tests}, f"PYTHONHASHSEED=1 {cmd} && echo {COVERAGE} && python -m coverage json -q -o -"
    )
    second, _ = sandbox.run(checkpoint, {test_path: tests}, f"PYTHONHASHSEED=2 {cmd}")
    if bool(code) != bool(second):
        return None, "nondeterministic: characterization tests differ across two runs"
    if code:
        return None, f"characterization tests fail on original: {tail(output)}"
    report = json.loads(output.split(COVERAGE)[1])["files"][function.path]
    missed = sum(function.start <= line <= function.end for line, _ in report["missing_branches"])
    if missed:
        return None, f"characterization tests miss branches: {missed}"
    return tests, None


def deduplicate(repo, head, sandbox, checkpoint, function, match, tests, test, test_path, cmd) -> tuple[dict | None, str | None]:
    helper = match["helper"]
    reason = f"`{function.qualname}` does the same job as `{helper['qualname']}` in {helper['path']} ({match['note']})."
    if tests is not None:
        target = f"from {module_of(function.path)} import {function.qualname}"
        swapped = re.sub(
            rf"^{re.escape(target)}$",
            f"from {module_of(helper['path'])} import {helper['qualname']} as {function.qualname}",
            tests,
            count=1,
            flags=re.M,
        )
        if swapped == tests:
            return None, f"characterization tests lack the import line: {target}"
        code, output = sandbox.run(checkpoint, {test_path: swapped}, cmd)
        if code and not match["difference"]:
            return None, f"differential tests fail on helper: {tail(output)}"
        if code:
            failed = ", ".join(re.findall(r"^FAILED \S+::(\w+)", output, re.M))
            reason += f" Difference: {match['difference'].rstrip('.')}. Differential tests that fail on the helper: {failed}."
    files = replace_calls(repo, head, function, helper)
    code, output = sandbox.run(checkpoint, files, test)
    if code not in (0, 5):
        return None, f"rewrite fails repo tests: {tail(output)}"
    return {"function": function.qualname, "kind": "duplicate", "reason": reason, "files": files}, None


def review(repo, base, head, sandbox) -> dict:
    result = {"suggestions": [], "followup": [], "rejected": []}
    changed = diff.changed_functions(repo, base, head)
    matches = {}
    if any("." not in function.qualname for function, _ in changed):
        base_index = index.build(repo, base)
        known = {(r["path"], r["qualname"]) for r in base_index}
        skip = {(function.path, function.qualname) for function, _ in changed}
        pool = [r for r in base_index if "." not in r["qualname"] and (r["path"], r["qualname"]) not in skip]
        for function, _ in changed:
            if "." not in function.qualname and (function.path, function.qualname) not in known:
                matches[function] = find_duplicate(function, pool)
    candidates = []
    for function, added in changed:
        text = diff.git(repo, "show", f"{head}:{function.path}")
        if matches.get(function):
            kind = "duplicate"
        elif dead_lines(function.path, text) & set(range(function.start, function.end + 1)):
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
        test_path = f"tests/test_slopgate_{n}.py"
        cmd = f"python -m coverage run --branch -m pytest -q {test_path}"
        match = matches.get(function)
        tests = None
        if not (match and match["exact"]):
            tests, failure = characterize(sandbox, checkpoint, function, test_path, cmd)
            if failure:
                result["rejected"].append({**rejected, "reason": failure})
                continue
        if match:
            followup, failure = deduplicate(repo, head, sandbox, checkpoint, function, match, tests, test, test_path, cmd)
            if failure:
                result["rejected"].append({**rejected, "reason": failure})
            else:
                result["followup"].append(followup)
            continue

        dedented = textwrap.dedent(function.source)
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
        passed = re.search(r"(\d+) passed", output)[1]
        summary = (
            f"Slopgate (`{kind}`) rewrite of `{function.qualname}`: "
            f"nesting {nesting(function.source)} -> {nesting(rewrite)}, "
            f"complexity {complexity(function.source)} -> {complexity(rewrite)}. "
            f"{passed} characterization tests passed in sandbox."
        )
        if set(range(start, end + 1)) <= added:
            suggestion = {"path": function.path, "line": end, "side": "RIGHT", "body": f"{summary}\n\n```suggestion\n{suggested}```"}
            if start != end:
                suggestion |= {"start_line": start, "start_side": "RIGHT"}
            result["suggestions"].append(suggestion)
        else:
            result["followup"].append({"function": function.qualname, "kind": kind, "reason": summary, "files": {function.path: spliced}})
    return result
