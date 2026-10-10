import json
from types import SimpleNamespace

from bench.characterize import branch_lines, constants, loop_d, mutants, writes
from slopgate import llm
from slopgate.config import SUPER
from slopgate.functions import parse

CONFIG = "SCORE = 0.3\nUNUSED = 1\n"

CORE = (
    "import os\n"
    "from os import sep\n"
    "from app.config import SCORE\n"
    "\n"
    "LIMIT: int = 3\n"
    "MODE = 'a'\n"
    "TABLE = {\n" + "".join(f"    {n}: {n},\n" for n in range(20)) + "}\n"
    "\n"
    "\n"
    "def helper(value):\n"
    "    return TABLE.get(value, sep)\n"
    "\n"
    "\n"
    "def check(items):\n"
    "    MODE = 'b'\n"
    "    count = len(items)\n"
    "    if count > LIMIT and helper(count) > SCORE:\n"
    "        return MODE\n"
    "    return os.sep\n"
)


def test_constants_lists_each_module_constant_the_function_and_its_callees_read(make_repo):
    repo = make_repo({"app/__init__.py": ""}, {"app/config.py": CONFIG, "app/core.py": CORE})
    found = {f.qualname: f for f in parse("app/core.py", CORE)}
    text = constants(repo, "HEAD", [found["check"], found["helper"]])
    assert text == "# app/config.py\nSCORE = 0.3\n\n# app/core.py\nLIMIT: int = 3\nTABLE = ...  # 22 lines, not shown"


def test_branch_lines_name_each_missed_branch_by_line():
    [f] = parse("app/m.py", "\n\ndef pick(pool):\n    if not pool:\n        return None\n    return pool[0]\n")
    assert branch_lines(f, [[4, 5], [4, -3]]) == "- line 4: if not pool: never goes to line 5\n- line 4: if not pool: never leaves the function here"


def test_writes_count_heredocs_and_broken_python_files():
    command = (
        "mkdir -p /repo/tests && cat > /repo/tests/test_a.py <<'EOF'\n"
        "def test_a():\n"
        "    assert 1 << 2 > 0\n"
        "EOF\n"
        "cd /repo && python -m pytest -q"
    )
    commands = [command, "cat > /repo/tests/test_b.py << EOF\ndef test_b(:\nEOF", "cat <<'EOF' > /repo/notes.txt\nnot python (\nEOF"]
    assert writes(commands, 1) == (3, 2)


def call(arguments):
    return SimpleNamespace(id="call_0", function=SimpleNamespace(name="execute", arguments=arguments))


def fake_client(monkeypatch, replies):
    requests = []

    def create(**kwargs):
        requests.append(list(kwargs["messages"]))
        message = SimpleNamespace(content="", tool_calls=replies.pop(0))
        return SimpleNamespace(choices=[SimpleNamespace(message=message)], usage=SimpleNamespace(prompt_tokens=1000, completion_tokens=100))

    monkeypatch.setattr(llm, "client", lambda: SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create))))
    monkeypatch.setattr(llm, "usage", [])
    return requests


class Backend:
    def __init__(self):
        self.commands = []

    def execute(self, command):
        self.commands.append(command)
        return SimpleNamespace(output="1 passed", exit_code=0, truncated=False)


def test_loop_d_runs_each_execute_call_and_stops_on_a_reply_without_tool_calls(monkeypatch):
    command = "cat > /repo/tests/test_slopgate_0.py <<'EOF'\ndef test_a():\n    assert True\nEOF"
    requests = fake_client(monkeypatch, [[call(json.dumps({"command": command}))], None])
    backend = Backend()
    assert loop_d(backend, "task") == (2, 1, 0, None)
    assert backend.commands == [command]
    assert requests[1][-1]["content"] == "1 passed\n[Command succeeded with exit code 0]"
    assert llm.usage == [(SUPER, 1000, 100)] * 2


def test_loop_d_counts_tool_call_arguments_that_are_not_json_as_a_broken_write(monkeypatch):
    requests = fake_client(monkeypatch, [[call('{"command": "cat > /repo/t.py <<EOF')], []])
    backend = Backend()
    assert loop_d(backend, "task") == (2, 0, 1, None)
    assert backend.commands == []
    assert requests[1][-1]["content"].startswith("Error: invalid arguments for execute")


def test_mutants_change_one_site_each_and_keep_the_rest_of_the_file():
    text = "import os\n\n\ndef f(a, b):\n    return a < 3 and b\n\n\nX = 1\n"
    [f] = parse("app/m.py", text)
    head, tail = "import os\n\n\n", "\n\nX = 1\n"
    control, texts = mutants(f, text)
    assert texts == [
        head + "def f(a, b):\n    return None\n" + tail,
        head + "def f(a, b):\n    return a < 3 or b\n" + tail,
        head + "def f(a, b):\n    return a >= 3 and b\n" + tail,
        head + "def f(a, b):\n    return a < 4 and b\n" + tail,
    ]
    assert control == text


def test_mutants_of_a_decorated_method_keep_the_decorator_and_the_indentation():
    text = "class C:\n    @property\n    def g(self):\n        if self.x:\n            return 1\n"
    [f] = parse("app/m.py", text)
    head = "class C:\n    @property\n    def g(self):\n"
    control, texts = mutants(f, text)
    assert texts == [
        head + "        if not self.x:\n            return 1\n",
        head + "        if self.x:\n            return None\n",
        head + "        if self.x:\n            return 2\n",
    ]
    assert control == text
