import ast
import json
import math
import re
import shlex
import subprocess
import textwrap
import time
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from typing import NamedTuple

from pydantic import BaseModel, Field

from slopgate import diff, index, llm, trace
from slopgate.config import AGENT_SECONDS, AGENT_STEPS, AGENT_TOKENS, DUPLICATE_SCORE, SUPER, ULTRA, WORKERS
from slopgate.functions import Function, complexity, dedent, is_test_file, nesting, parse, pytest_patterns, structure_hash
from slopgate.kinds import KINDS, classify, comments, leftover, problems
from slopgate.sandbox import InstallError, commands, tail

NONDETERMINISTIC = {"random", "secrets", "uuid", "time", "datetime"}
DEFS = (ast.FunctionDef, ast.AsyncFunctionDef)
BOOL_CALLS = {"bool", "isinstance", "issubclass", "callable", "hasattr", "all", "any"}
COVERAGE = "--slopgate-coverage--"
MISSED = "import json, sys; print(json.dumps(json.load(sys.stdin)['files'][sys.argv[1]]['missing_branches'], separators=(',', ':')))"

AGENT_RULES = """You write characterization tests in a sandbox. Commands run in the root of the repository, and its dependencies are installed.

Rules:
- Write files only with the execute tool and a heredoc, for example: mkdir -p tests && cat > {test_path} <<'EOF' ... EOF
- Do not change any file except {test_path}.
- The tests get no network and no API keys. Do not call real network services or models: patch them.
- You can read files and run commands (grep, cat, python) in the repository.
- Stop when the tests pass twice and cover every branch of the target."""

AGENT_TASK = """Write characterization tests for the Python function `{qualname}` in {path}. The tests must record what the code does now, bugs included.

```python
{source}
```

Write the tests to {test_path}. Import the target with exactly this line: from {module} import {name}

Goal: the test file passes twice on the original code, once with PYTHONHASHSEED=1 and once with PYTHONHASHSEED=2, and it covers every branch of `{qualname}` (lines {start} to {end} of {path}).

Run the tests with coverage:

PYTHONHASHSEED=1 {cmd}

Then show the missed branches of {path} as [from line, to line] pairs (a negative target means the function exits there):

python -m coverage json -q -o - | python -c "{missed}" {path}"""

EXECUTE = {
    "type": "function",
    "function": {
        "name": "execute",
        "description": "Run a shell command in the sandbox and return its output and exit code.",
        "parameters": {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]},
    },
}

REWRITE_PROMPT = """Rewrite the Python function below. Fix these problems:

{problems}

Rules:
- Keep the exact signature, the decorators, and the behavior, bugs included.
- Add no new functions, no lambdas, and no new classes.
- If every return gives True or False, keep it that way: `a and b` returns `a` itself when `a` is falsy, so wrap such a chain in bool().
- Reply with one ```python block that holds the full rewritten function, decorators included. Put no text outside the block.

```python
{source}
```"""

RETRY_PROMPT = (
    REWRITE_PROMPT
    + """

This earlier rewrite failed:

```python
{rewrite}
```

Failure:

{failure}"""
)


SAME_JOB_PROMPT = """Decide whether the new Python function does the same job as the existing helper, so that callers of the new function could call the helper instead.

Reply by calling the tool `SameJob`.

New function, in {path}:

```python
{source}
```

Existing helper, in {helper_path}:

```python
{helper_source}
```"""


class SameJob(BaseModel):
    """Report whether the new function does the same job as the existing helper."""

    difference: str = Field(description="The behavior difference between the two functions, or an empty string when they behave the same.")
    same_job: bool = Field(description="True if callers of the new function could call the existing helper instead and get the same behavior.")


def module_of(path: str) -> str:
    return path.removesuffix(".py").replace("/", ".")


def strip_fence(text: str) -> str | None:
    lines = text.splitlines(keepends=True)
    start = next((i for i, line in enumerate(lines) if line.startswith("```python")), None)
    if start is None:
        return None
    end = next((i for i in range(start + 1, len(lines)) if lines[i].strip() == "```"), None)
    return None if end is None else "".join(lines[start + 1 : end])


def same_code(a: str, b: str) -> bool:
    a, b = dedent(a), dedent(b)
    return ast.dump(ast.parse(a)) == ast.dump(ast.parse(b)) and comments(a) == comments(b)


def nondeterministic(source: str) -> str | None:
    names = {node.id for node in ast.walk(ast.parse(source)) if isinstance(node, ast.Name)}
    return min(names & NONDETERMINISTIC, default=None)


def signature(node) -> tuple:
    return type(node), node.name, ast.dump(node.args), node.returns and ast.dump(node.returns)


def boolish(node) -> bool:
    match node:
        case ast.Constant(value=bool()) | ast.Compare() | ast.UnaryOp(op=ast.Not()):
            return True
        case ast.Call(func=ast.Name(id=name)):
            return name in BOOL_CALLS
        case ast.BoolOp(values=values):
            return all(boolish(value) for value in values)
        case ast.IfExp(body=body, orelse=orelse):
            return boolish(body) and boolish(orelse)
    return False


def returns(fn) -> list:
    return [node.value for node in scope(fn) if isinstance(node, ast.Return)]


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
    old_returns = returns(old.body[0])
    if old_returns and all(map(boolish, old_returns)) and not all(map(boolish, returns(new.body[0]))):
        return "returns a non-bool value where the original returns only bools"
    return None


def find_duplicate(function, pool) -> dict | None:
    code_hash = structure_hash(function.source)
    for record in pool:
        if record["hash"] == code_hash:
            return {"helper": record, "exact": True, "difference": "", "note": "exact structural copy"}
    for score, record in index.search(pool, function.source, DUPLICATE_SCORE, 5):
        prompt = SAME_JOB_PROMPT.format(
            path=function.path, source=function.source, helper_path=record["path"], helper_source=record["source"]
        )
        with trace.span("gate.same_job", helper=f"{record['path']}::{record['qualname']}", score=round(score, 2), prompt="SAME_JOB_PROMPT"):
            verdict = llm.decide(SUPER, prompt, SameJob)
        if verdict and verdict.same_job:
            return {"helper": record, "exact": False, "difference": verdict.difference, "note": f"score {score:.2f}"}
    return None


def apply(text: str, edits) -> str:
    lines = text.encode().splitlines(keepends=True) + [b""]
    for start_line, start_col, end_line, end_col, new in sorted(edits, reverse=True):
        lines[start_line - 1 : end_line] = [lines[start_line - 1][:start_col] + new.encode() + lines[end_line - 1][end_col:]]
    return b"".join(lines).decode()


def removal_edit(text: str, function) -> tuple:
    lines = text.splitlines()
    last = function.end
    while last < len(lines) and not lines[last].strip():
        last += 1
    start = function.start
    while last == len(lines) and start > 1 and not lines[start - 2].strip():
        start -= 1
    return start, 0, last + 1, 0, ""


def forwarded(node) -> ast.Call | None:
    args = node.args
    # ponytail: *args/**kwargs wrappers are skipped; map star arguments through when real wrappers need it
    if not isinstance(node, ast.FunctionDef) or node.decorator_list or args.vararg or args.kwarg:
        return None
    body = node.body[1:] if ast.get_docstring(node) is not None else node.body
    if len(body) != 1 or not isinstance(body[0], ast.Return) or not isinstance(body[0].value, ast.Call):
        return None
    call = body[0].value
    root = call.func
    while isinstance(root, ast.Attribute):
        root = root.value
    params = [a.arg for a in (*args.posonlyargs, *args.args, *args.kwonlyargs)]
    if not isinstance(root, ast.Name) or root.id in params or root.id == node.name:
        return None
    names = [a.id if isinstance(a, ast.Name) else None for a in call.args]
    names += [k.arg if isinstance(k.value, ast.Name) and k.value.id == k.arg else None for k in call.keywords]
    return call if names == params else None


def import_line(tree, module: str, name: str) -> str | None:
    for stmt in tree.body:
        if isinstance(stmt, (ast.Import, ast.ImportFrom)):
            for alias in stmt.names:
                if (alias.asname or alias.name).split(".")[0] == name:
                    return ast.unparse(ast.Import([alias]) if isinstance(stmt, ast.Import) else ast.ImportFrom(stmt.module, [alias], stmt.level))
        elif (isinstance(stmt, (*DEFS, ast.ClassDef)) and stmt.name == name) or (
            isinstance(stmt, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name for t in stmt.targets)
        ):
            return f"from {module} import {name}"
    return None


def scope(fn):
    stack = list(fn.body)
    while stack:
        node = stack.pop()
        yield node
        if not isinstance(node, (*DEFS, ast.ClassDef, ast.Lambda)):
            stack.extend(ast.iter_child_nodes(node))


def wrapper_rule(trees, files, function) -> str | None:
    try:
        new = {path: ast.parse(text) for path, text in files.items()}
    except SyntaxError:
        return "does not parse"

    def count(group):
        return sum(isinstance(node, (*DEFS, ast.ClassDef)) for tree in group for node in ast.walk(tree))

    if any(isinstance(node, DEFS) and node.name == function.qualname for node in new[function.path].body):
        return "wrapper not deleted"
    if count(new.values()) != count(trees[path] for path in files) - 1:
        return "adds a function or class"
    return None


def removal(repo, head, function, text, node, inner) -> dict | None:
    module, name = module_of(function.path), function.qualname
    sources, trees, uses = {}, {}, []
    for path, source in diff.python_sources(repo, head):
        try:
            tree = ast.parse(source)
        except SyntaxError:
            continue
        aliases = [
            a for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.level == 0 and n.module == module for a in n.names if a.name == name
        ]
        if any(a.asname for a in aliases) or any(isinstance(n, ast.Attribute) and n.attr == name for n in ast.walk(tree)):
            return None
        if path != function.path and not aliases:
            continue
        sources[path], trees[path] = source, tree
        uses += [
            (path, n)
            for n in ast.walk(tree)
            if isinstance(n, ast.Name)
            and n.id == name
            and isinstance(n.ctx, ast.Load)
            and not (path == function.path and node.lineno <= n.lineno <= node.end_lineno)
        ]
    if len(uses) != 1:
        return None
    [(path, use)] = uses
    found = [(fn, n) for fn in trees[path].body if isinstance(fn, DEFS) for n in scope(fn) if isinstance(n, ast.Call) and n.func is use]
    if not found:
        return None
    [(fn, site)] = found
    args = node.args
    positional = [a.arg for a in (*args.posonlyargs, *args.args)]
    defaults = dict(zip(reversed(positional), reversed(args.defaults)))
    defaults |= {a.arg: d for a, d in zip(args.kwonlyargs, args.kw_defaults) if d}
    if len(site.args) > len(positional) or any(isinstance(a, ast.Starred) for a in site.args):
        return None
    given = dict(zip(positional, site.args))
    for keyword in site.keywords:
        if keyword.arg not in {a.arg for a in (*args.args, *args.kwonlyargs)} or keyword.arg in given:
            return None
        given[keyword.arg] = keyword.value
    order = [*positional, *(a.arg for a in args.kwonlyargs)]
    # inlining evaluates the arguments in parameter order, and a substituted default once per call
    reordered = list(given) != sorted(given, key=order.index)
    if reordered and any(isinstance(n, ast.Call) for v in given.values() for n in ast.walk(v)):
        return None
    if any(not isinstance(defaults[p], ast.Constant) for p in order if p not in given and p in defaults):
        return None
    exprs = {}
    for param in [*positional, *(a.arg for a in args.kwonlyargs)]:
        if param in given:
            exprs[param] = ast.get_source_segment(sources[path], given[param])
        elif param in defaults:
            exprs[param] = ast.get_source_segment(text, defaults[param])
        else:
            return None
    call_args = [exprs[a.id] for a in inner.args] + [f"{k.arg}={exprs[k.arg]}" for k in inner.keywords]
    callee = ast.get_source_segment(text, inner.func)
    edits = {function.path: [removal_edit(text, function)]}
    edits.setdefault(path, []).append((site.lineno, site.col_offset, site.end_lineno, site.end_col_offset, f"{callee}({', '.join(call_args)})"))
    if path != function.path:
        for n in trees[path].body:
            if isinstance(n, ast.ImportFrom) and n.level == 0 and n.module == module and any(a.name == name for a in n.names):
                keep = [a for a in n.names if a.name != name]
                if keep:
                    edits[path].append((n.lineno, n.col_offset, n.end_lineno, n.end_col_offset, ast.unparse(ast.ImportFrom(module, keep, 0))))
                else:
                    edits[path].append((n.lineno, 0, n.end_lineno + 1, 0, ""))
        root = callee.split(".")[0]
        line = import_line(trees[function.path], module, root)
        if line and not import_line(trees[path], module_of(path), root):
            after = max((n.end_lineno for n in trees[path].body if isinstance(n, (ast.Import, ast.ImportFrom))), default=0)
            edits[path].append((after + 1, 0, after + 1, 0, line + "\n"))
    files = {p: apply(sources[p], e) for p, e in edits.items()}
    caller = next(f for f in parse(path, sources[path]) if f.qualname == fn.name and f.start <= fn.lineno <= f.end)
    return {"caller": caller, "inner": callee, "files": files, "rule": wrapper_rule(trees, files, function)}


def inline(sandbox, checkpoint, function, plan, tests, test, test_path, cmd) -> tuple[dict | None, str | None]:
    code, output = sandbox.run(checkpoint, {**plan["files"], test_path: tests}, cmd)
    if code:
        return None, f"rewrite fails characterization tests: {tail(output)}"
    repo_code, repo_output = sandbox.run(checkpoint, plan["files"], test)
    if repo_code not in (0, 5):
        return None, f"rewrite fails repo tests: {tail(repo_output)}"
    caller = plan["caller"]
    passed = re.search(r"(\d+) passed", output)[1]
    reason = (
        f"`{function.qualname}` only forwards to `{plan['inner']}`; inlined into its single caller `{caller.qualname}` in {caller.path}. "
        f"{passed} characterization tests of the caller passed."
    )
    return {"function": function.qualname, "kinds": ["wrapper"], "reason": reason, "files": plan["files"]}, None


def replace_calls(repo, head, function, helper) -> dict[str, str]:
    old, new = function.qualname, helper["qualname"]
    module, helper_module = module_of(function.path), module_of(helper["path"])
    files = {}
    for path, text in diff.python_sources(repo, head):
        try:
            tree = ast.parse(text)
        except SyntaxError:
            continue
        edits = []
        deleted = range(0)
        if path == function.path:
            edit = removal_edit(text, function)
            deleted = range(edit[0], edit[2])
            edits.append(edit)
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


def check(sandbox, checkpoint, function, test_path, cmd, tests) -> str | None:
    code, output = sandbox.run(
        checkpoint, {test_path: tests}, f"PYTHONHASHSEED=1 {cmd} && echo {COVERAGE} && python -m coverage json -q -o - | python -c \"{MISSED}\" {shlex.quote(function.path)}"
    )
    if code == 124:
        return f"characterization tests time out: {tail(output)}"
    second, _ = sandbox.run(checkpoint, {test_path: tests}, f"PYTHONHASHSEED=2 {cmd}")
    passed = COVERAGE in output
    if passed != (not second):
        return "nondeterministic: characterization tests differ across two runs"
    if not passed:
        return f"characterization tests fail on original: {tail(output)}"
    try:
        branches = json.loads(output.split(COVERAGE)[1].strip().splitlines()[0])
    except (ValueError, IndexError):
        return f"coverage has no data for {function.path}"
    missed = [branch for branch in branches if function.start <= branch[0] <= function.end]
    return f"characterization tests miss branches: {len(missed)}" if missed else None


def shown(code: int, output: str) -> str:
    # Stage 1 of ticket 41 measured the agent with the output form of Deep Agents: past 80,000 characters, only 5 head and 5 tail lines.
    if len(output) > 80_000:
        lines = output.splitlines()
        output = "\n".join([*lines[:5], f"... [{len(lines) - 10} lines truncated] ...", *lines[-5:]])
    return output + f"\n[Command {'succeeded' if code == 0 else 'failed'} with exit code {code}]"


def limit(steps: int, began: float, tokens: int) -> str | None:
    if steps >= AGENT_STEPS:
        return "step limit"
    if time.perf_counter() - began > AGENT_SECONDS:
        return "time limit"
    return "token limit" if tokens > AGENT_TOKENS else None


def characterize(sandbox, checkpoint, function, test_path, cmd) -> tuple[str | None, str | None]:
    source = dedent(function.source)
    name = nondeterministic(source)
    if name:
        return None, f"nondeterministic: uses {name}"
    session = sandbox.session(checkpoint)
    task = AGENT_TASK.format(
        qualname=function.qualname,
        path=function.path,
        source=source,
        test_path=test_path,
        module=module_of(function.path),
        name=function.qualname.split(".")[0],
        start=function.start,
        end=function.end,
        cmd=cmd,
        missed=MISSED,
    )
    messages = [{"role": "system", "content": AGENT_RULES.format(test_path=test_path)}, {"role": "user", "content": task}]
    steps = tokens = 0
    began = time.perf_counter()
    # A failed reply or command ends the agent, but the file it already wrote still goes to the check.
    try:
        while not (stop := limit(steps, began, tokens)):
            steps += 1
            with trace.span("gate.agent", step=steps):
                message, sent = llm.step(SUPER, messages, [EXECUTE])
            tokens += sent
            calls = message.tool_calls or []
            if not calls:
                break
            messages.append(
                {
                    "role": "assistant",
                    "content": message.content,
                    "tool_calls": [{"id": c.id, "type": "function", "function": {"name": c.function.name, "arguments": c.function.arguments}} for c in calls],
                }
            )
            for call in calls:
                remaining = AGENT_SECONDS - (time.perf_counter() - began)
                if remaining <= 0:
                    stop = "time limit"
                    break
                try:
                    command = str(json.loads(call.function.arguments)["command"])
                except (ValueError, KeyError, TypeError) as error:
                    content = f"Error: invalid arguments for execute: {error!r}"
                else:
                    content = shown(*session.execute(command, max(1, math.ceil(remaining))))
                messages.append({"role": "tool", "tool_call_id": call.id, "content": content})
            if stop:
                break
    except llm.CutOff:
        stop = "reply cut off"
    except Exception as error:
        stop = f"agent error: {error!r}"
    try:
        tests = session.read(test_path)
    except Exception as error:
        return None, f"no test file: agent stopped ({stop or 'no tool call'}), read failed: {error!r}"
    if tests is None:
        return None, f"no test file: agent stopped ({stop or 'no tool call'})"
    failure = check(sandbox, checkpoint, function, test_path, cmd, tests)
    if failure is None:
        return tests, None
    return None, f"{stop}: {failure}" if stop else failure


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
    return {"function": function.qualname, "kinds": ["duplicate"], "reason": reason, "files": files}, None


TEST_FILE = "Slopgate does not change test files."
REJECTED = "Slopgate could not prove a rewrite of this function, so it changed nothing."
NO_ENVIRONMENT = "Slopgate could not build the test environment, so it could not prove a rewrite and changed nothing."


def note(function, kinds, added, found, patterns, why) -> dict:
    kinds = list(kinds)
    if kinds == ["duplicate"]:
        helper = found["helper"]
        fix = "Consider one parametrized test." if is_test_file(helper["path"], patterns) else "Call it instead."
        finding = f"`{function.qualname}` does the same job as `{helper['qualname']}` in {helper['path']}. {fix}"
    elif kinds == ["wrapper"]:
        finding = f"`{function.qualname}` only forwards to `{found['inner']}`. Inline it into its single caller."
    else:
        finding = f"`{function.qualname}`: " + " ".join(KINDS[kind] for kind in kinds)
    body = f"{', '.join(f'**{kind}**' for kind in kinds)} (not rewritten): {finding} {why}"
    return {"path": function.path, "function": function.qualname, "kinds": kinds, "line": max(added), "body": body}


def unproven(candidates, patterns, why) -> list:
    return [note(function, kinds, added, found, patterns, why) for function, added, kinds, _, found in candidates]


def rejection(function, kinds, reason: str) -> dict:
    return {"function": function.qualname, "path": function.path, "kinds": list(kinds), "reason": reason}


class Rewrite(NamedTuple):
    function: Function
    text: str
    suggested: str


def prove(repo, head, sandbox, checkpoint, test, n, candidate) -> tuple[str, dict, str | None]:
    function, _, kinds, _, _ = candidate
    with trace.span("gate.function", path=function.path, qualname=function.qualname, slop_kinds=list(kinds)):
        try:
            outcome = trial(repo, head, sandbox, checkpoint, test, n, candidate)
        except llm.CutOff:
            outcome = "rejected", rejection(function, kinds, "reply cut off"), None
        # One broken candidate must not lose the results of the others (the review of PR #15 was lost this way).
        except Exception as error:
            outcome = "rejected", rejection(function, kinds, f"internal error: {error!r}"), None
        into, entry, suggested = outcome
        trace.output({into: entry, "repo_suite": "pending" if suggested else "not needed"})
    return outcome


def trial(repo, head, sandbox, checkpoint, test, n, candidate) -> tuple[str, dict, str | None]:
    function, added, kinds, text, found = candidate
    test_path = f"tests/test_slopgate_{n}.py"
    cmd = f"python -m coverage run --branch -m pytest -q {test_path}"
    wrapper = "wrapper" in kinds
    tests = None
    indent = function.source[: len(function.source) - len(function.source.lstrip())]
    # dedent leaves such a line (in a multi-line string) as it is, so indenting the rewrite back would change it
    if not found and any(line.strip() and not line.startswith(indent) and not line.lstrip().startswith("#") for line in function.source.splitlines()):
        return "rejected", rejection(function, kinds, "a line is left of the def, so the gate cannot re-indent a rewrite"), None
    if wrapper or not (found and found["exact"]):
        target = found["caller"] if wrapper else function
        with trace.span("gate.characterize"):
            tests, failure = characterize(sandbox, checkpoint, target, test_path, cmd)
            trace.output(failure or "passed")
        if failure:
            return "rejected", rejection(function, kinds, failure), None
    if found:
        with trace.span("gate.proof", attempt=1):
            if wrapper:
                followup, failure = inline(sandbox, checkpoint, function, found, tests, test, test_path, cmd)
            else:
                followup, failure = deduplicate(repo, head, sandbox, checkpoint, function, found, tests, test, test_path, cmd)
            trace.output(failure or "passed")
        if failure:
            return "rejected", rejection(function, kinds, failure), None
        return "followup", followup, None

    dedented = dedent(function.source)
    with trace.span("gate.rewrite", prompt="REWRITE_PROMPT"):
        reply = llm.complete(SUPER, REWRITE_PROMPT.format(problems=problems(kinds), source=dedented))
    for retry in (False, True):
        with trace.span("gate.proof", attempt=retry + 1):
            fenced = strip_fence(reply)
            if fenced is None:
                failure = "rewrite reply is not a python block"
                break
            rewrite = dedent(fenced).strip("\n") + "\n"
            failure = broken_rule(dedented, rewrite)
            if failure:
                failure = f"rule: {failure}"
                break
            if same_code(dedented, rewrite):
                failure = "rewrite makes no change"
                break
            suggested = textwrap.indent(rewrite, indent)
            spliced = splice(text, function, suggested)
            failure = leftover(kinds, function, suggested, spliced)
            if not failure:
                code, output = sandbox.run(checkpoint, {test_path: tests, function.path: spliced}, cmd)
                failure = f"rewrite fails characterization tests: {tail(output)}" if code else None
            trace.output(failure or "passed")
        if not failure or retry:
            break
        with trace.span("gate.retry", prompt="RETRY_PROMPT"):
            reply = llm.complete(
                ULTRA, RETRY_PROMPT.format(problems=problems(kinds), source=dedented, rewrite=rewrite, failure=failure)
            )
    if failure:
        return "rejected", rejection(function, kinds, failure), None

    start, end = function.start, function.end
    passed = re.search(r"(\d+) passed", output)[1]
    summary = (
        f"Slopgate ({', '.join(f'`{kind}`' for kind in kinds)}) rewrite of `{function.qualname}`.\n"
        f"nesting {nesting(function.source)} -> {nesting(rewrite)}, "
        f"complexity {complexity(function.source)} -> {complexity(rewrite)}. "
        f"{passed} characterization tests passed in sandbox."
    )
    if set(range(start, end + 1)) <= added:
        suggestion = {"path": function.path, "line": end, "side": "RIGHT", "body": f"{summary}\n\n```suggestion\n{suggested}```"}
        if start != end:
            suggestion |= {"start_line": start, "start_side": "RIGHT"}
        return "suggestions", suggestion, suggested
    return "followup", {"function": function.qualname, "kinds": list(kinds), "reason": summary, "files": {function.path: spliced}}, suggested


def splice(text: str, function, suggested: str) -> str:
    lines = text.splitlines(keepends=True)
    return "".join(lines[: function.start - 1]) + suggested + "".join(lines[function.end :])


def repo_suite(sandbox, checkpoint, test, accepted: list[Rewrite], threads) -> dict:
    def run(rewrites):
        files = {}
        # Bottom up, so that the line numbers of the other rewrites in one file stay valid.
        for rewrite in sorted(rewrites, key=lambda rewrite: rewrite.function.start, reverse=True):
            path = rewrite.function.path
            files[path] = splice(files.get(path, rewrite.text), rewrite.function, rewrite.suggested)
        code, output = sandbox.run(checkpoint, files, test)
        return code in (0, 5), output

    failures = {}
    with trace.span("gate.repo_suite", rewrites=len(accepted)):
        together, output = run(accepted)
        if not together:
            alone = [(together, output)] if len(accepted) == 1 else threads.map(trace.bind(lambda rewrite: run([rewrite])), accepted)
            passed = []
            for rewrite, (ok, output) in zip(accepted, alone):
                if ok:
                    passed.append(rewrite)
                else:
                    failures[rewrite.function] = f"rewrite fails repo tests: {tail(output)}"
            # When every rewrite passed alone, the first run already tried them together.
            if len(passed) > 1 and passed != accepted:
                together, _ = run(passed)
            if len(passed) > 1 and not together:
                kept = passed[:1]
                for rewrite in passed[1:]:
                    ok, _ = run([*kept, rewrite])
                    if ok:
                        kept.append(rewrite)
                    else:
                        failures[rewrite.function] = "rewrite conflicts with another rewrite"
        trace.output({f"{function.path}::{function.qualname}": reason for function, reason in failures.items()} or "passed")
    return failures


def review(repo, base, head, sandbox) -> dict:
    result = {"suggestions": [], "followup": [], "rejected": [], "notes": []}
    try:
        fork = diff.git(repo, "merge-base", base, head).strip()
    except subprocess.CalledProcessError as error:
        raise RuntimeError(f"{base} and {head} have no merge-base; fetch the full history (git fetch --unshallow)") from error
    changed = diff.changed_functions(repo, fork, head)
    names = diff.git(repo, "ls-tree", "--name-only", head).splitlines()
    patterns = pytest_patterns(lambda name: diff.git(repo, "show", f"{head}:{name}") if name in names else None)
    wrapped, plans = set(), {}
    for function, added in changed:
        if "." not in function.qualname and not is_test_file(function.path, patterns):
            text = diff.git(repo, "show", f"{head}:{function.path}")
            node = next((n for n in ast.parse(text).body if isinstance(n, DEFS) and n.lineno == function.start), None)
            inner = node and forwarded(node)
            if inner:
                wrapped.add(function)
                plan = removal(repo, head, function, text, node, inner)
                if plan and plan["rule"]:
                    result["rejected"].append(rejection(function, ["wrapper"], f"rule: {plan['rule']}"))
                    result["notes"].append(note(function, ["wrapper"], added, plan, patterns, REJECTED))
                elif plan:
                    plans[function] = plan
    matches = {}
    if any("." not in function.qualname for function, _ in changed):
        with trace.span("gate.index"):
            base_index = index.build(repo, fork)
            known = {(r["path"], r["qualname"]) for r in base_index}
            skip = {(function.path, function.qualname) for function, _ in changed}
            kept = {(r["path"], r["qualname"]) for r in index.build(repo, head)}
            pool = [r for r in base_index if "." not in r["qualname"] and (r["path"], r["qualname"]) not in skip and (r["path"], r["qualname"]) in kept]
        for function, _ in changed:
            if "." not in function.qualname and function not in wrapped and (function.path, function.qualname) not in known:
                with trace.span("gate.duplicate", path=function.path, qualname=function.qualname):
                    matches[function] = find_duplicate(function, pool)
                    trace.output(matches[function])
    candidates = []
    for function, added in changed:
        text = diff.git(repo, "show", f"{head}:{function.path}")
        if function in plans:
            kinds, found = {"wrapper": []}, plans[function]
        elif function in wrapped:
            continue
        elif matches.get(function):
            kinds, found = {"duplicate": []}, matches[function]
        else:
            found = None
            with trace.span("gate.classify", path=function.path, qualname=function.qualname):
                try:
                    kinds = classify(function, text)
                except Exception as error:
                    result["rejected"].append(rejection(function, [], f"internal error: {error!r}"))
                    continue
                trace.output(kinds)
        if not kinds:
            continue
        if is_test_file(function.path, patterns):
            result["notes"].append(note(function, kinds, added, found, patterns, TEST_FILE))
        else:
            candidates.append((function, added, kinds, text, found))
    if not candidates:
        return result
    setup, test = commands(repo, head)
    try:
        with trace.span("sandbox.prepare", input=setup):
            checkpoint = sandbox.prepare(repo, head, setup)
    except InstallError as error:
        result["rejected"].append({"reason": f"could not build test environment\n{error}"})
        result["notes"] += unproven(candidates, patterns, NO_ENVIRONMENT)
        return result
    worker = trace.bind(partial(prove, repo, head, sandbox, checkpoint, test))
    with ThreadPoolExecutor(WORKERS) as threads:
        outcomes = list(threads.map(worker, range(len(candidates)), candidates))
        accepted = [Rewrite(function, text, suggested) for (function, _, _, text, _), (_, _, suggested) in zip(candidates, outcomes) if suggested]
        try:
            failures = repo_suite(sandbox, checkpoint, test, accepted, threads) if accepted else {}
        except Exception as error:
            failures = {rewrite.function: f"internal error: {error!r}" for rewrite in accepted}
    for (function, _, kinds, _, _), (into, entry, _) in zip(candidates, outcomes):
        if function in failures:
            into, entry = "rejected", rejection(function, kinds, failures[function])
        result[into].append(entry)
    failed = {(r["path"], r["function"]) for r in result["rejected"] if "function" in r}
    result["notes"] += unproven([c for c in candidates if (c[0].path, c[0].qualname) in failed], patterns, REJECTED)
    return result
