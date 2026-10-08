import ast
import io
import json
import re
import textwrap
import tokenize

import vulture

from slopgate import diff, embed, index, llm
from slopgate.config import COMPLEXITY, DUPLICATE_SCORE, LIGHTNING, NESTING, SUPER, ULTRA
from slopgate.functions import complexity, nesting, parse, structure_hash
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
BOOL_CALLS = {"bool", "isinstance", "issubclass", "callable", "hasattr", "all", "any"}
COVERAGE = "--slopgate-coverage--"
RECORDED = "--slopgate-recorded--"
RECORDER_PATH = "slopgate_record.py"

CLASSIFY_PROMPT = """Name the slop kind that fits the Python function below best.

Kinds:
{kinds}
- none: no kind above fits.

Reply with JSON only, in the form {{"kind": "<kind>"}}.

{source}"""

TESTS_PROMPT = """Write characterization tests for the Python function below. They must record what the code does now, bugs included.

{inputs_form}
Rules:
- Reply with one pytest file and nothing else.
- Import the target with exactly this one import line, and no other import of the module under test: from {module} import {name}
- Call the function as `{qualname}`.
- Cover every branch of the function.

File: {path}

{source}"""

INPUTS_FORM = """
If calls with plain-value arguments (literals and builtins only) cover every branch, reply instead with JSON only, in the form {{"inputs": ["<arguments>", ...]}}. Each item is the text between the parentheses of one call to `{name}`, for example "[10], 50" or "price=10, percent=50". Do not predict results: each call runs on the code, and its return value or exception and the state of its arguments afterward are recorded.
"""

CAPTURE = """

def capture(*args, **kwargs):
    return list(args), kwargs
"""

RECORDER = """import json

from {module} import {name}
""" + CAPTURE + """

results = []
for inputs in {inputs!r}:
    args, kwargs = eval("capture(" + inputs + ")")
    try:
        outcome = ["returns", repr({name}(*args, **kwargs))]
    except Exception as error:
        outcome = ["raises", type(error).__name__ + ": " + str(error)]
    results.append([*outcome, repr((args, kwargs))])
print({marker!r} + json.dumps(results))
"""

RETURNS_TEST = """

def test_call_{n}():
    args, kwargs = capture({inputs})
    assert repr({name}(*args, **kwargs)) == {value!r}
    assert repr((args, kwargs)) == {state!r}
"""

RAISES_TEST = """

def test_call_{n}():
    args, kwargs = capture({inputs})
    with pytest.raises(Exception) as error:
        {name}(*args, **kwargs)
    assert type(error.value).__name__ + ": " + str(error.value) == {value!r}
    assert repr((args, kwargs)) == {state!r}
"""

TESTS_RETRY = """

Your earlier test file failed on the unchanged code above, so some expected values are wrong. Reply with the corrected file: keep the inputs where you can, and change each expected value to what the code actually returns or raises.

Earlier test file:

{tests}
Failure:

{failure}"""

INPUTS_RETRY = """

Your earlier inputs could not be recorded on the unchanged code above. Each input must evaluate as Python with only literals and builtins: quote every string, and use no bare names. Reply again.

Earlier reply:

{reply}
Failure:

{failure}"""

CALLEES = """

Code it calls (context only; test the function above, through its behavior):

{code}"""

REWRITE_PROMPT = """Rewrite the Python function below. {instruction}

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

Reply with JSON only, in the form {{"same_job": true or false, "difference": "<the behavior difference, or an empty string>"}}.

New function, in {path}:

{source}

Existing helper, in {helper_path}:

{helper_source}"""


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
    def comments(code):
        return [t.string for t in tokenize.generate_tokens(io.StringIO(code).readline) if t.type == tokenize.COMMENT]

    a, b = textwrap.dedent(a), textwrap.dedent(b)
    return ast.dump(ast.parse(a)) == ast.dump(ast.parse(b)) and comments(a) == comments(b)


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


def classify(source: str) -> str | None:
    kinds = "\n".join(f"- {kind}: {instruction}" for kind, instruction in KINDS.items())
    try:
        kind = json.loads(llm.complete(LIGHTNING, CLASSIFY_PROMPT.format(kinds=kinds, source=source), json=True))["kind"]
        return kind if kind in KINDS else None
    except (TypeError, ValueError, KeyError, llm.CutOff):
        return None


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
    [vector] = embed.encode([function.source], query=True)
    for score, record in index.search(pool, vector, DUPLICATE_SCORE, 5):
        prompt = SAME_JOB_PROMPT.format(
            path=function.path, source=function.source, helper_path=record["path"], helper_source=record["source"]
        )
        try:
            verdict = json.loads(llm.complete(SUPER, prompt, json=True))
            if verdict["same_job"] is True:
                return {"helper": record, "exact": False, "difference": str(verdict.get("difference") or ""), "note": f"score {score:.2f}"}
        except (TypeError, ValueError, KeyError, llm.CutOff):
            continue
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
    for path in diff.git(repo, "ls-tree", "-r", "--name-only", head).splitlines():
        if not path.endswith(".py"):
            continue
        source = text if path == function.path else diff.git(repo, "show", f"{head}:{path}")
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
    caller = next(f for f in parse(path, sources[path]) if f.qualname == fn.name and f.end == fn.end_lineno)
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
    return {"function": function.qualname, "kind": "wrapper", "reason": reason, "files": plan["files"]}, None


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


def called_code(repo, head, function, depth=2) -> str:
    paths = set(diff.git(repo, "ls-tree", "-r", "--name-only", head).splitlines())
    texts = {}

    def module_functions(path):
        if path not in texts:
            texts[path] = diff.git(repo, "show", f"{head}:{path}")
        return {f.qualname: f for f in parse(path, texts[path]) if "." not in f.qualname}

    seen, found, frontier = {(function.path, function.qualname)}, [], [function]
    # ponytail: follows plain-name calls only; `module.func()` and `self.method()` callees are not resolved
    for _ in range(depth):
        following = []
        for caller in frontier:
            local = module_functions(caller.path)
            imported = {
                alias.asname or alias.name: (node.module, alias.name)
                for node in ast.parse(texts[caller.path]).body
                if isinstance(node, ast.ImportFrom) and node.level == 0
                for alias in node.names
            }
            for call in ast.walk(ast.parse(textwrap.dedent(caller.source))):
                if not (isinstance(call, ast.Call) and isinstance(call.func, ast.Name)):
                    continue
                target = local.get(call.func.id)
                if target is None and call.func.id in imported:
                    module, name = imported[call.func.id]
                    path = next((p for p in (f"{module.replace('.', '/')}.py", f"{module.replace('.', '/')}/__init__.py") if p in paths), None)
                    target = path and module_functions(path).get(name)
                if target and (target.path, target.qualname) not in seen:
                    seen.add((target.path, target.qualname))
                    found.append(target)
                    following.append(target)
        frontier = following
    return "\n\n".join(f"# {f.path}\n{textwrap.dedent(f.source)}" for f in found)


def record(sandbox, checkpoint, function, inputs) -> tuple[str | None, str | None]:
    module, name = module_of(function.path), function.qualname
    script = RECORDER.format(module=module, name=name, inputs=inputs, marker=RECORDED)
    _, output = sandbox.run(checkpoint, {RECORDER_PATH: script}, f"PYTHONHASHSEED=1 python {RECORDER_PATH}")
    if RECORDED not in output:
        return None, f"could not record calls: {tail(output)}"
    outcomes = json.loads(output.split(RECORDED)[-1])
    tests = f"import pytest\n\nfrom {module} import {name}\n" + CAPTURE
    for n, (text, (outcome, value, state)) in enumerate(zip(inputs, outcomes)):
        template = RETURNS_TEST if outcome == "returns" else RAISES_TEST
        tests += template.format(n=n, name=name, inputs=text, value=value, state=state)
    return tests, None


def proposed_inputs(reply: str) -> list[str] | None:
    try:
        inputs = json.loads(reply)["inputs"]
    except (ValueError, TypeError, KeyError):
        return None
    return [str(text) for text in inputs] if isinstance(inputs, list) else None


def characterize(sandbox, checkpoint, function, test_path, cmd, context="") -> tuple[str | None, str | None]:
    name = nondeterministic(textwrap.dedent(function.source))
    if name:
        return None, f"nondeterministic: uses {name}"
    prompt = TESTS_PROMPT.format(
        module=module_of(function.path),
        name=function.qualname.split(".")[0],
        qualname=function.qualname,
        path=function.path,
        source=function.source,
        # the recorder sees only the arguments, so a method's effect on its object would go unchecked
        inputs_form="" if "." in function.qualname else INPUTS_FORM.format(name=function.qualname),
    )
    request = prompt + (CALLEES.format(code=context) if context else "")
    retry = ""
    for last in (False, True):
        reply = llm.complete(SUPER, request + retry)
        fenced = strip_fence(reply)
        reply = reply if fenced is None else fenced
        inputs = proposed_inputs(reply)
        tests, failure = (reply, None) if inputs is None else record(sandbox, checkpoint, function, inputs)
        if failure:
            retry = INPUTS_RETRY.format(reply=reply, failure=failure)
        else:
            code, output = sandbox.run(
                checkpoint, {test_path: tests}, f"PYTHONHASHSEED=1 {cmd} && echo {COVERAGE} && python -m coverage json -q -o -"
            )
            second, _ = sandbox.run(checkpoint, {test_path: tests}, f"PYTHONHASHSEED=2 {cmd}")
            if bool(code) != bool(second):
                return None, "nondeterministic: characterization tests differ across two runs"
            if not code:
                break
            failure = f"characterization tests fail on original: {tail(output)}"
            retry = TESTS_RETRY.format(tests=tests, failure="\n".join(output.strip().splitlines()[-60:]))
        if last:
            return None, failure
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
    wrapped, plans = set(), {}
    for function, _ in changed:
        if "." not in function.qualname:
            text = diff.git(repo, "show", f"{head}:{function.path}")
            node = next((n for n in ast.parse(text).body if isinstance(n, DEFS) and n.lineno == function.start), None)
            inner = node and forwarded(node)
            if inner:
                wrapped.add(function)
                plan = removal(repo, head, function, text, node, inner)
                if plan and plan["rule"]:
                    result["rejected"].append({"function": function.qualname, "path": function.path, "reason": f"rule: {plan['rule']}"})
                elif plan:
                    plans[function] = plan
    matches = {}
    if any("." not in function.qualname for function, _ in changed):
        base_index = index.build(repo, base)
        known = {(r["path"], r["qualname"]) for r in base_index}
        skip = {(function.path, function.qualname) for function, _ in changed}
        pool = [r for r in base_index if "." not in r["qualname"] and (r["path"], r["qualname"]) not in skip]
        for function, _ in changed:
            if "." not in function.qualname and function not in wrapped and (function.path, function.qualname) not in known:
                matches[function] = find_duplicate(function, pool)
    candidates = []
    for function, added in changed:
        text = diff.git(repo, "show", f"{head}:{function.path}")
        if function in plans:
            kind = "wrapper"
        elif function in wrapped:
            continue
        elif matches.get(function):
            kind = "duplicate"
        elif has_dead_code(function, text):
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
        try:
            test_path = f"tests/test_slopgate_{n}.py"
            cmd = f"python -m coverage run --branch -m pytest -q {test_path}"
            match = matches.get(function)
            plan = plans.get(function)
            tests = None
            if not (match and match["exact"]):
                target = plan["caller"] if plan else function
                tests, failure = characterize(sandbox, checkpoint, target, test_path, cmd, called_code(repo, head, target))
                if failure:
                    result["rejected"].append({**rejected, "reason": failure})
                    continue
            if match or plan:
                if plan:
                    followup, failure = inline(sandbox, checkpoint, function, plan, tests, test, test_path, cmd)
                else:
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
                fenced = strip_fence(reply)
                if fenced is None:
                    failure = "rewrite reply is not a python block"
                    break
                rewrite = textwrap.dedent(fenced).strip("\n") + "\n"
                failure = broken_rule(dedented, rewrite)
                if failure:
                    failure = f"rule: {failure}"
                    break
                if same_code(dedented, rewrite):
                    failure = "rewrite makes no change"
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
        except llm.CutOff:
            result["rejected"].append({**rejected, "reason": "reply cut off"})
    return result
