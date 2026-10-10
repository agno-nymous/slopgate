import argparse
import ast
import json
import os
import random
import re
import statistics
import sys
import textwrap
import time
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from functools import partial
from pathlib import Path
from uuid import UUID

from bench.detect import SAMPLE, checkout, parses, write
from bench.score import WORKERS, cost
from slopgate import llm, review
from slopgate.config import BASE_URL, MAX_OUTPUT_TOKENS, SUPER
from slopgate.diff import git
from slopgate.functions import parse
from slopgate.sandbox import Contree, InstallError, commands, tail

RESULTS = Path(__file__).parent / "results" / "characterize"
RUNS = RESULTS / "runs.json"
TABLE = RESULTS / "table.md"
TEST_PATH = "tests/test_slopgate_0.py"
CMD = f"python -m coverage run --branch -m pytest -q {TEST_PATH}"
ATTEMPTS = 4
STEPS, SECONDS, TOKENS = 15, 120, 150_000
MUTANTS = 8
# a mutant can loop forever, and a ConTree run has no time limit of its own
MUTANT_CMD = f"PYTHONHASHSEED=1 timeout 60 python -m pytest -q {TEST_PATH}"
SWAPS = {
    ast.Lt: ast.GtE,
    ast.GtE: ast.Lt,
    ast.Gt: ast.LtE,
    ast.LtE: ast.Gt,
    ast.Eq: ast.NotEq,
    ast.NotEq: ast.Eq,
    ast.Is: ast.IsNot,
    ast.IsNot: ast.Is,
    ast.In: ast.NotIn,
    ast.NotIn: ast.In,
}

SLOPGATE = [
    ("b2a2ad0", "slopgate/index.py", "build"),
    ("b2a2ad0", "slopgate/live.py", "seed"),
    ("b2a2ad0", "slopgate/live.py", "matches"),
    ("b2a2ad0", "slopgate/review.py", "find_duplicate"),
    ("b2a2ad0", "slopgate/review.py", "characterize"),
    ("70c27da340aeaadec60bfb22a711c84acdb0cabd", "slopgate/review.py", "characterize"),
]
# installs measured in ConTree on python:3.9-slim; werkzeug>=3 breaks the import of this flask commit
INSTALLS = {
    "django/django": "pip install -e .",
    "pytest-dev/pytest": "SETUPTOOLS_SCM_PRETEND_VERSION=5.4.0 pip install -e .",
    "psf/requests": "pip install -e .",
    "sympy/sympy": "pip install -e . mpmath",
    "pallets/flask": "pip install -e . 'werkzeug<2.3'",
}
PER_REPO = 6

REASONS = {
    "nondeterministic": "nondeterministic",
    "model cannot test": "cannot test",
    "tests reply is not python": "no reply",
    "could not record calls": "fail on original",
    "characterization tests miss branches": "missed branches",
    "characterization tests fail on original": "fail on original",
}
VERDICTS = {"fails": "fail on original", "missed": "missed branches", "nondeterministic": "nondeterministic", "no coverage": "error"}

MISSED_LIST_RETRY = """

Your tests pass, but they miss these branches of the function:

{branches}

Earlier test file:

```python
{tests}
```

Reply with the full test file in one ```python block. Keep every earlier test, and add tests that take each missed branch. Import the target with exactly this line: from {module} import {name}."""

RULES = """You write characterization tests in a sandbox. The repository is in /repo, and its dependencies are installed.

Rules:
- Write files only with the execute tool and a heredoc, for example: mkdir -p /repo/tests && cat > /repo/{test_path} <<'EOF' ... EOF. The write_file, edit_file, and task tools are off.
- Do not change any file except /repo/{test_path}.
- The tests get no network and no API keys. Do not call real network services or models: patch them.
- You can read files and run commands (grep, cat, python) in /repo.
- Stop when the tests pass twice and cover every branch of the target."""

TASK = """Write characterization tests for the Python function `{qualname}` in /repo/{path}. The tests must record what the code does now, bugs included.

```python
{source}
```

Write the tests to /repo/{test_path}. Import the target with exactly this line: from {module} import {name}

Goal: the test file passes twice on the original code, once with PYTHONHASHSEED=1 and once with PYTHONHASHSEED=2, and it covers every branch of `{qualname}` (lines {start} to {end} of {path}).

Run the tests with coverage:

cd /repo && PYTHONHASHSEED=1 {cmd}

Then show the missed branches of {path} as [from line, to line] pairs (a negative target means the function exits there):

cd /repo && python -m coverage json -q -o - | python -c "{missed}" {path}"""

EXECUTE = {
    "type": "function",
    "function": {
        "name": "execute",
        "description": "Run a shell command in the sandbox and return its output and exit code.",
        "parameters": {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]},
    },
}

HEREDOC = re.compile(r"<<-?\s*(['\"]?)(\w+)\1")
TARGET = re.compile(r">\s*([^\s<>;&|]+)")


@dataclass(frozen=True)
class Target:
    id: str
    repo: str
    commit: str
    path: str
    qualname: str
    image: str
    setup: str | None


@dataclass
class Outcome:
    design: str
    run: int
    id: str
    proved: bool
    reason: str
    detail: str
    seconds: float = 0.0
    model_calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cost: float = 0.0
    sandbox_seconds: float = 0.0
    steps: int | None = None
    writes: int | None = None
    broken_writes: int | None = None
    tests: str | None = None
    mutants: int | None = None
    killed: int | None = None
    asserts: int | None = None


def dataset() -> list[Target]:
    main = str(Path(git(Path(__file__).parent, "rev-parse", "--path-format=absolute", "--git-common-dir").strip()).parent)
    found = []
    for commit, path, qualname in SLOPGATE:
        if not any(f.qualname == qualname for f in parse(path, git(main, "show", f"{commit}:{path}"))):
            print(f"skipped: {qualname} is not in {path} at {commit}", file=sys.stderr)
            continue
        found.append(Target(f"slopgate@{commit[:7]}:{path}:{qualname}", main, commit, path, qualname, "python:3.12-slim", commands(main, commit)[0]))
    sample = json.loads(SAMPLE.read_text())
    rng = random.Random(41)
    for repo, setup in INSTALLS.items():
        commit = sample["commits"][repo]
        root = str(checkout(repo, commit))
        # the import line comes from the file path; a path such as scripts/prepare-release-pr.py gives no module name
        rows = [row for row in sample["clean"] if row["repo"] == repo and all(p.isidentifier() for p in review.module_of(row["path"]).split("."))]
        for row in rng.sample(rows, PER_REPO):
            found.append(Target(row["id"], root, commit, row["path"], row["qualname"], "python:3.9-slim", setup))
    return found


def function_of(target: Target):
    return next(f for f in parse(target.path, git(target.repo, "show", f"{target.commit}:{target.path}")) if f.qualname == target.qualname)


def constants(repo, commit, functions) -> str:
    paths = set(git(repo, "ls-tree", "-r", "--name-only", commit).splitlines())
    trees = {}

    def tree(path):
        if path not in trees:
            text = git(repo, "show", f"{commit}:{path}")
            trees[path] = text, ast.parse(text)
        return trees[path][1]

    def assignment(path, name):
        found = None
        for stmt in tree(path).body:
            targets = stmt.targets if isinstance(stmt, ast.Assign) else [stmt.target] if isinstance(stmt, ast.AnnAssign) and stmt.value else []
            if any(isinstance(t, ast.Name) and t.id == name for t in targets):
                found = stmt
        return found

    found = {}
    for f in functions:
        imported = {
            alias.asname or alias.name: (node.module, alias.name)
            for node in tree(f.path).body
            if isinstance(node, ast.ImportFrom) and node.level == 0
            for alias in node.names
        }
        nodes = list(ast.walk(ast.parse(textwrap.dedent(f.source))))
        local = {n.id for n in nodes if isinstance(n, ast.Name) and not isinstance(n.ctx, ast.Load)} | {n.arg for n in nodes if isinstance(n, ast.arg)}
        for name in {n.id for n in nodes if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)} - local:
            path, real = f.path, name
            if name in imported:
                module, real = imported[name]
                base = module.replace(".", "/")
                path = next((p for p in (f"{base}.py", f"{base}/__init__.py") if p in paths), None)
            stmt = path and assignment(path, real)
            if stmt:
                found[path, stmt.lineno] = real, stmt
    blocks = {}
    for (path, _), (name, stmt) in sorted(found.items()):
        lines = stmt.end_lineno - stmt.lineno + 1
        text = ast.get_source_segment(trees[path][0], stmt) if lines <= 20 else f"{name} = ...  # {lines} lines, not shown"
        blocks.setdefault(path, []).append(text)
    return "\n\n".join(f"# {path}\n" + "\n".join(texts) for path, texts in blocks.items())


def branch_lines(function, missed) -> str:
    lines = function.source.splitlines()
    return "\n".join(
        f"- line {a}: {lines[a - function.start].strip()} " + (f"never goes to line {b}" if b > 0 else "never leaves the function here")
        for a, b in missed
    )


def sites(node) -> list[int]:
    if isinstance(node, ast.Compare):
        return [j for j, op in enumerate(node.ops) if type(op) in SWAPS]
    number = isinstance(node, ast.Constant) and type(node.value) in (int, float)
    value = isinstance(node, ast.Return) and node.value is not None and not (isinstance(node.value, ast.Constant) and node.value.value is None)
    return [0] if number or value or isinstance(node, (ast.BoolOp, ast.If)) else []


def mutate(node, j) -> None:
    if isinstance(node, ast.Compare):
        node.ops[j] = SWAPS[type(node.ops[j])]()
    elif isinstance(node, ast.BoolOp):
        node.op = ast.Or() if isinstance(node.op, ast.And) else ast.And()
    elif isinstance(node, ast.Constant):
        node.value += 1
    elif isinstance(node, ast.Return):
        node.value = ast.Constant(None)
    else:
        node.test = ast.UnaryOp(ast.Not(), node.test)


def mutants(function, text) -> tuple[str, list[str]]:
    def tree():
        node = ast.parse(textwrap.dedent(function.source)).body[0]
        node.decorator_list = []
        return node

    original, lines = tree(), text.splitlines(keepends=True)
    # function.start is the first decorator line; the decorator lines stay as they are
    start = function.start + original.lineno - 1
    indent = re.match(r"[ \t]*", lines[start - 1])[0]

    def splice(node):
        return "".join(lines[: start - 1]) + textwrap.indent(ast.unparse(node), indent) + "\n" + "".join(lines[function.end :])

    found = [(i, j) for i, node in enumerate(ast.walk(original)) for j in sites(node)]
    texts = []
    for i, j in sorted(random.Random(41).sample(found, min(MUTANTS, len(found)))):
        node = tree()
        mutate(list(ast.walk(node))[i], j)
        if ast.unparse(node) != ast.unparse(original):
            texts.append(splice(node))
    return splice(original), texts


def asserts(tests: str) -> int:
    return sum(
        isinstance(n, ast.Assert)
        or isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "raises" and isinstance(n.func.value, ast.Name) and n.func.value.id == "pytest"
        for n in ast.walk(ast.parse(tests))
    )


def strength(box, checkpoint, target, function, tests) -> dict:
    control, texts = mutants(function, git(target.repo, "show", f"{target.commit}:{target.path}"))
    # ast.unparse can change a docstring or emit syntax the target's Python cannot read; then every kill would be false
    if box.run(checkpoint, {TEST_PATH: tests, function.path: control}, MUTANT_CMD)[0]:
        return {"mutants": None, "killed": None, "asserts": asserts(tests)}
    killed = sum(box.run(checkpoint, {TEST_PATH: tests, function.path: text}, MUTANT_CMD)[0] != 0 for text in texts)
    return {"mutants": len(texts), "killed": killed, "asserts": asserts(tests)}


def heredocs(command: str) -> list[tuple[str, str]]:
    lines, found, i = command.split("\n"), [], 0
    while i < len(lines):
        start = HEREDOC.search(lines[i])
        target = start and TARGET.search(lines[i].replace(start[0], ""))
        if target:
            end = next((j for j in range(i + 1, len(lines)) if lines[j].strip() == start[2]), len(lines))
            found.append((target[1].strip("'\""), "\n".join(lines[i + 1 : end])))
            i = end
        i += 1
    return found


def writes(commands: list[str], invalid: int) -> tuple[int, int]:
    docs = [doc for command in commands for doc in heredocs(command)]
    return len(docs), sum(path.endswith(".py") and not parses(body) for path, body in docs) + invalid


def limit(steps: int, began: float, tokens: int) -> str | None:
    return "step limit" if steps >= STEPS else "time limit" if time.perf_counter() - began > SECONDS else "token limit" if tokens > TOKENS else None


spent = [0.0]


def timed(run):
    def wrapper(*args, **kwargs):
        began = time.perf_counter()
        try:
            return run(*args, **kwargs)
        finally:
            spent[0] += time.perf_counter() - began

    return wrapper


def design_a(box, checkpoint, target, function) -> dict:
    tests, failure = review.characterize(box, checkpoint, function, TEST_PATH, CMD, review.called_code(target.repo, target.commit, function))
    if tests is not None:
        return {"proved": True, "reason": "proved", "detail": "", "tests": tests}
    return {"proved": False, "reason": next((r for p, r in REASONS.items() if failure.startswith(p)), "error"), "detail": failure}


def design_b(box, checkpoint, target, function) -> dict:
    fields = {"module": review.module_of(function.path), "name": function.qualname.split(".")[0], "qualname": function.qualname}
    calls_allowed = "." not in function.qualname
    forms = review.TESTS_FORMS if calls_allowed else review.TESTS_FORMS[1:]
    prompt = review.TESTS_PROMPT.format(
        forms="\n".join(f"{n}. {form.format(**fields)}" for n, form in enumerate(forms, 1)), path=function.path, source=function.source
    )
    called = review.callees(target.repo, target.commit, function)
    code = "\n\n".join(f"# {f.path}\n{textwrap.dedent(f.source)}" for f in called)
    context = "\n\n".join(filter(None, [code, constants(target.repo, target.commit, [function, *called])]))
    request = prompt + (review.CALLEES.format(code=context) if context else "")
    retry, reason, detail = "", "no reply", ""
    for _ in range(ATTEMPTS):
        try:
            reply = review.parse_tests_reply(llm.complete(SUPER, request + retry), function, calls_allowed)
        except ValueError as error:
            retry, reason, detail = review.NOT_PYTHON_RETRY.format(error=error), "no reply", str(error)
            continue
        if isinstance(reply, review.CannotTest):
            return {"proved": False, "reason": "cannot test", "detail": reply.reason}
        if isinstance(reply, review.Calls):
            tests, failure = review.record(box, checkpoint, function, reply.calls)
            if failure:
                calls = "\n".join(f"{function.qualname}({call})" for call in reply.calls)
                retry, reason, detail = review.INPUTS_RETRY.format(calls=calls, failure=failure), "fail on original", failure
                continue
        else:
            tests = reply.code
        result = review.check(box, checkpoint, function, TEST_PATH, CMD, tests)
        if result.verdict == "proved":
            return {"proved": True, "reason": "proved", "detail": "", "tests": tests}
        reason, detail = VERDICTS[result.verdict], tail(result.output)
        if result.verdict == "fails":
            retry = review.TESTS_RETRY.format(tests=tests, failure="\n".join(result.output.strip().splitlines()[-60:]))
        elif result.verdict == "missed":
            retry = MISSED_LIST_RETRY.format(branches=branch_lines(function, result.missed), tests=tests, **fields)
        else:
            break
    return {"proved": False, "reason": reason, "detail": detail}


def loop_c(backend, task: str) -> tuple[int, int, int, str | None]:
    from deepagents import create_deep_agent
    from deepagents.middleware._tool_exclusion import _ToolExclusionMiddleware
    from langchain_core.messages import AIMessage
    from langchain_openai import ChatOpenAI

    model = ChatOpenAI(
        model=SUPER,
        base_url=BASE_URL,
        api_key=os.environ["NEBIUS_API_KEY"],
        temperature=0,
        max_tokens=MAX_OUTPUT_TOKENS,
        extra_body={"chat_template_kwargs": {"enable_thinking": False}},
    )
    agent = create_deep_agent(
        model=model,
        backend=backend,
        system_prompt=RULES.format(test_path=TEST_PATH),
        # permissions= raises NotImplementedError with a sandbox backend; a subagent (task) would hide its steps and tokens from the limits
        middleware=[_ToolExclusionMiddleware(excluded=frozenset({"write_file", "edit_file", "task"}))],
    )
    steps = written = broken = tokens = 0
    stop, began = None, time.perf_counter()
    for update in agent.stream({"messages": [{"role": "user", "content": task}]}, config={"recursion_limit": 100}, stream_mode="updates"):
        for node in update.values():
            for message in node.get("messages", []) if isinstance(node, dict) else []:
                if not isinstance(message, AIMessage):
                    continue
                steps += 1
                usage = message.usage_metadata or {}
                llm.usage.append((SUPER, usage.get("input_tokens", 0), usage.get("output_tokens", 0)))
                tokens += usage.get("input_tokens", 0)
                commands = [call["args"].get("command", "") for call in message.tool_calls if call["name"] == "execute"]
                w, b = writes(commands, len(message.invalid_tool_calls))
                written, broken = written + w, broken + b
        if stop := limit(steps, began, tokens):
            break
    return steps, written, broken, stop


def shown(response) -> str:
    output = response.output
    # deepagents moves output past 4 chars x 20,000 tokens to a file and shows the model only 5 head and 5 tail lines
    if len(output) > 80_000:
        lines = output.splitlines()
        output = "\n".join([*lines[:5], f"... [{len(lines) - 10} lines truncated] ...", *lines[-5:]])
    if response.exit_code is not None:
        output += f"\n[Command {'succeeded' if response.exit_code == 0 else 'failed'} with exit code {response.exit_code}]"
    return output + ("\n[Output was truncated due to size limits]" if response.truncated else "")


def loop_d(backend, task: str) -> tuple[int, int, int, str | None]:
    client = llm.client()
    messages = [
        {"role": "system", "content": RULES.format(test_path=TEST_PATH).replace(" The write_file, edit_file, and task tools are off.", "")},
        {"role": "user", "content": task},
    ]
    steps = written = broken = tokens = 0
    stop, began = None, time.perf_counter()
    while True:
        reply = client.chat.completions.create(
            model=SUPER,
            messages=messages,
            tools=[EXECUTE],
            tool_choice="auto",
            temperature=0,
            max_tokens=MAX_OUTPUT_TOKENS,
            extra_body={"chat_template_kwargs": {"enable_thinking": False}},
        )
        steps += 1
        llm.usage.append((SUPER, reply.usage.prompt_tokens, reply.usage.completion_tokens))
        tokens += reply.usage.prompt_tokens
        message = reply.choices[0].message
        calls = message.tool_calls or []
        commands = []
        for call in calls:
            try:
                commands.append(str(json.loads(call.function.arguments)["command"]))
            except (ValueError, KeyError, TypeError) as error:
                commands.append(error)
        w, b = writes([c for c in commands if isinstance(c, str)], sum(isinstance(c, Exception) for c in commands))
        written, broken = written + w, broken + b
        if (stop := limit(steps, began, tokens)) or not calls:
            break
        messages.append(
            {
                "role": "assistant",
                "content": message.content,
                "tool_calls": [{"id": c.id, "type": "function", "function": {"name": c.function.name, "arguments": c.function.arguments}} for c in calls],
            }
        )
        for call, command in zip(calls, commands):
            content = f"Error: invalid arguments for execute: {command!r}" if isinstance(command, Exception) else shown(backend.execute(command))
            messages.append({"role": "tool", "tool_call_id": call.id, "content": content})
        if stop := limit(steps, began, tokens):
            break
    return steps, written, broken, stop


def agent(loop, box, checkpoint, target, function) -> dict:
    from contree_sdk.langchain.sandbox import ContreeSandbox

    backend = ContreeSandbox(checkpoint.session())
    execute = timed(backend.execute)
    # a test that waits for input would block the stream past the time limit
    backend.execute = lambda command, *, timeout=None: execute(command, timeout=timeout or SECONDS)
    task = TASK.format(
        qualname=function.qualname,
        path=function.path,
        source=textwrap.dedent(function.source),
        test_path=TEST_PATH,
        module=review.module_of(function.path),
        name=function.qualname.split(".")[0],
        start=function.start,
        end=function.end,
        cmd=CMD,
        missed=review.MISSED,
    )
    steps, written, broken, stop = loop(backend, task)
    extra = {"steps": steps, "writes": written, "broken_writes": broken}
    [file] = backend.download_files([f"/repo/{TEST_PATH}"])
    if file.error:
        return extra | {"proved": False, "reason": stop or "no reply", "detail": f"no test file: {file.error}"}
    tests = file.content.decode()
    result = review.check(box, checkpoint, function, TEST_PATH, CMD, tests)
    if result.verdict == "proved":
        return extra | {"proved": True, "reason": "proved", "detail": "", "tests": tests}
    return extra | {"proved": False, "reason": stop or VERDICTS[result.verdict], "detail": tail(result.output)}


DESIGNS = {"A": design_a, "B": design_b, "C": partial(agent, loop_c), "D": partial(agent, loop_d)}
AGENTS = ("C", "D")


def job(design: str, run: int, target: Target, uuid: str) -> dict:
    from contree_sdk import ContreeSync

    box = Contree(target.image)
    box.run = timed(box.run)
    used, spent[0], began = len(llm.usage), 0.0, time.perf_counter()
    try:
        function = function_of(target)
        checkpoint = ContreeSync().images.use(UUID(uuid))
        if name := review.nondeterministic(textwrap.dedent(function.source)):
            result = {"proved": False, "reason": "nondeterministic", "detail": f"uses {name}"}
        else:
            result = DESIGNS[design](box, checkpoint, target, function)
    except llm.CutOff:
        result = {"proved": False, "reason": "token limit", "detail": "reply cut off"}
    except Exception as error:
        result = {"proved": False, "reason": "error", "detail": repr(error)}
    seconds = round(time.perf_counter() - began, 1)
    if result["proved"]:
        try:
            result |= strength(box, checkpoint, target, function, result["tests"])
        except Exception as error:
            result["detail"] = f"mutation check: {error!r}"
    calls = llm.usage[used:]
    usage = {"input_tokens": sum(c[1] for c in calls), "output_tokens": sum(c[2] for c in calls)}
    result["detail"] = result["detail"][-300:]
    return asdict(
        Outcome(
            design=design,
            run=run,
            id=target.id,
            seconds=seconds,
            model_calls=len(calls),
            cost=cost(SUPER, usage),
            sandbox_seconds=round(spent[0], 1),
            **usage,
            **result,
        )
    )


def prepare(key) -> tuple[str | None, str | None]:
    repo, commit, image, setup = key
    try:
        return str(Contree(image).prepare(repo, commit, setup).uuid), None
    except InstallError as error:
        return None, str(error)


def p90(values):
    return statistics.quantiles(values, n=10, method="inclusive")[-1] if len(values) > 1 else values[0]


def kill_rate(rows: list[dict]) -> str:
    mutants, killed = sum(r.get("mutants") or 0 for r in rows), sum(r.get("killed") or 0 for r in rows)
    return f"{killed / mutants:.0%} ({killed}/{mutants})" if mutants else "-"


def table(rows: list[dict], designs: list[str], targets: list[Target]) -> str:
    ids = {t.id for t in targets}
    rows = [r for r in rows if r["id"] in ids and r["design"] in designs]
    out = [
        "| design | functions | proved | proof rate | reasons | median s | p90 s | mean calls | tokens in / out | cost $ | median sandbox s "
        "| agent steps median | agent broken / writes | kill rate | median asserts |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for design in designs:
        first = [r for r in rows if r["design"] == design and r["run"] == 0]
        if not first:
            continue
        proved = sum(r["proved"] for r in first)
        reasons = ", ".join(f"{reason} {n}" for reason, n in Counter(r["reason"] for r in first).most_common())
        seconds = [r["seconds"] for r in first]
        steps, broken = "-", "-"
        if design in AGENTS:
            steps = statistics.median(r["steps"] or 0 for r in first)
            broken = f"{sum(r['broken_writes'] or 0 for r in first)} / {sum(r['writes'] or 0 for r in first)}"
        counted = [r["asserts"] for r in first if r["proved"] and r.get("asserts") is not None]
        out.append(
            f"| {design} | {len(first)} | {proved} | {proved / len(first):.0%} | {reasons} | {statistics.median(seconds):.0f} | {p90(seconds):.0f} "
            f"| {statistics.mean(r['model_calls'] for r in first):.1f} | {sum(r['input_tokens'] for r in first):,} / {sum(r['output_tokens'] for r in first):,} "
            f"| {sum(r['cost'] for r in first):.3f} | {statistics.median(r['sandbox_seconds'] for r in first):.0f} "
            f"| {steps} | {broken} | {kill_rate([r for r in first if r['proved']])} | {statistics.median(counted) if counted else '-'} |"
        )
    by_id = {}
    for r in rows:
        by_id.setdefault(r["id"], {}).setdefault(r["design"], []).append(r)
    run0 = {(r["design"], r["id"]): r for r in rows if r["run"] == 0}
    common = [i for i in by_id if all(run0.get((d, i), {}).get("proved") for d in designs)]
    out += [
        "",
        f"Kill rate on the {len(common)} functions that {', '.join(designs)} all proved in run 0: "
        + ", ".join(f"{d} {kill_rate([run0[d, i] for i in common])}" for d in designs),
    ]
    for design in [d for d in designs if d in AGENTS]:
        repeated = [runs[design] for runs in by_id.values() if len({r["run"] for r in runs.get(design, [])}) == 3]
        if repeated:
            counts = Counter(sum(r["proved"] for r in runs) for runs in repeated)
            out += ["", f"{design} variance over {len(repeated)} functions run 3 times: " + ", ".join(f"proved {n}/3: {counts[n]}" for n in (3, 2, 1, 0))]
    out += ["", "| function | " + " | ".join(designs) + " |", "|---|" + "---|" * len(designs)]
    for target in targets:
        runs = by_id.get(target.id, {})
        cells = [" / ".join(r["reason"] for r in sorted(runs.get(d, []), key=lambda r: r["run"])) or "-" for d in designs]
        out.append(f"| {target.id} | " + " | ".join(cells) + " |")
    return "\n".join(out) + "\n"


def env_check(target: Target) -> None:
    from contree_sdk import ContreeSync
    from contree_sdk.langchain.sandbox import ContreeSandbox

    uuid, error = prepare((target.repo, target.commit, target.image, target.setup))
    if error:
        raise SystemExit(error)
    output = ContreeSandbox(ContreeSync().images.use(UUID(uuid)).session()).execute("env").output
    names = sorted(line.split("=", 1)[0] for line in output.splitlines() if "=" in line)
    print(" ".join(names))
    print("API key in the sandbox" if any(n.startswith("NEBIUS") for n in names) else "no API key in the sandbox")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--designs", default="A,B,C")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--only", default="")
    parser.add_argument("--repeat", type=int, default=0)
    parser.add_argument("--env-check", action="store_true")
    args = parser.parse_args()
    targets = [t for t in dataset() if args.only in t.id][: args.limit]
    if args.env_check:
        env_check(targets[0])
        return
    designs = args.designs.split(",")
    rows = json.loads(RUNS.read_text()) if RUNS.exists() else []
    done = {(r["design"], r["run"], r["id"]) for r in rows}
    jobs = [(d, 0, t) for d in designs for t in targets]
    jobs += [(d, run, t) for d in designs if d in AGENTS for run in (1, 2) for t in targets[: args.repeat]]
    jobs = [(d, run, t) for d, run, t in jobs if (d, run, t.id) not in done]
    keys = list(dict.fromkeys((t.repo, t.commit, t.image, t.setup) for _, _, t in jobs))
    with ThreadPoolExecutor(WORKERS) as threads:
        prepared = dict(zip(keys, threads.map(prepare, keys)))
    pending = []
    for design, run, target in jobs:
        uuid, error = prepared[target.repo, target.commit, target.image, target.setup]
        if error:
            rows.append(asdict(Outcome(design, run, target.id, False, "install", error[-300:])))
        else:
            pending.append((design, run, target, uuid))
    write(RUNS, rows)
    with ProcessPoolExecutor(WORKERS) as workers:
        futures = [workers.submit(job, *args) for args in pending]
        for n, future in enumerate(as_completed(futures), 1):
            row = future.result()
            rows.append(row)
            write(RUNS, rows)
            print(f"{n}/{len(futures)} {row['design']}{row['run']} {row['id']}: {row['reason']} ({row['seconds']} s)", file=sys.stderr)
    text = table(rows, designs, targets)
    TABLE.write_text(text)
    print(text)


if __name__ == "__main__":
    main()
