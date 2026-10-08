import sysconfig
from functools import cache
from pathlib import Path

import pytest
from test_duplicates import RESTRUCTURED, SLUGIFY, TYPE_ERROR_COPY
from test_hook import SLUG_COPY

from slopgate.config import DUPLICATE_SCORE
from slopgate.functions import parse, structure_hash
from slopgate.index import search

ROOT = Path(__file__).parent.parent
SKIPPED = {"test", "idlelib", "lib2to3", "tkinter", "turtledemo", "site-packages"}

CHUNKS = '''\
def chunks(items, size):
    return [items[i : i + size] for i in range(0, len(items), size)]
'''

CHUNKS_COPY = '''\
def batched(sequence, n):
    start = 0
    while start < len(sequence):
        yield sequence[start : start + n]
        start += n
'''

DURATION_COPY = '''\
def format_elapsed(total_seconds: float) -> str:
    whole = round(total_seconds)
    minutes = whole // 60
    seconds = whole % 60
    if minutes:
        return f"{minutes} min {seconds} s"
    return f"{seconds} s"
'''

PLURAL_COPY = '''\
def count_label(count: int, noun: str) -> str:
    if count == 1:
        return f"{count} {noun}"
    return f"{count} {noun}s"
'''

TAIL_COPY = '''\
def last_lines(text: str) -> str:
    lines = text.strip().splitlines()
    recent = lines[-20:]
    return "\\n".join(recent)
'''

MODULE_OF_COPY = '''\
def dotted_name(file_path: str) -> str:
    if file_path.endswith(".py"):
        file_path = file_path[:-3]
    return ".".join(file_path.split("/"))
'''

STRIP_FENCE_COPY = '''\
def extract_code_block(reply: str) -> str | None:
    inside = False
    body = []
    for line in reply.splitlines(keepends=True):
        if not inside:
            if line.startswith("```python"):
                inside = True
        elif line.strip() == "```":
            return "".join(body)
        else:
            body.append(line)
    return None
'''

APPLY_COPY = '''\
def apply_edits(source: str, changes) -> str:
    rows = source.encode("utf-8").splitlines(keepends=True) + [b""]
    for first, first_col, last, last_col, text in sorted(changes, reverse=True):
        rows[first - 1 : last] = [rows[first - 1][:first_col] + text.encode("utf-8") + rows[last - 1][last_col:]]
    return b"".join(rows).decode("utf-8")
'''

POOLED_COPY = '''\
def is_candidate(file_path: str, name: str, globs: list[str]) -> bool:
    if "." in name or name.startswith("test_"):
        return False
    return not is_test_file(file_path, globs)
'''

TOKENS_COPY = '''\
def word_set(code: str) -> frozenset[str]:
    found = re.findall(r"[A-Za-z_][A-Za-z0-9_]*|\\d+|[^\\sA-Za-z0-9_]", code)
    parts = (piece.lower() for w in found for piece in re.split(r"_|(?<=[a-z])(?=[A-Z])", w))
    return frozenset(p for p in parts if p)
'''

SHELL_COPY = '''\
def run_command(command: str, workdir) -> tuple[int, str]:
    env = dict(os.environ)
    env["PATH"] = os.pathsep.join([os.path.dirname(sys.executable), env["PATH"]])
    try:
        out = subprocess.check_output(command, shell=True, cwd=workdir, env=env, stderr=subprocess.STDOUT, text=True)
        return 0, out
    except subprocess.CalledProcessError as error:
        return error.returncode, error.output
'''

GIT_COPY = '''\
def run_git(path, *argv) -> str:
    return subprocess.check_output(["git", *argv], cwd=path, text=True, stderr=subprocess.PIPE)
'''

COMPLEXITY_COPY = '''\
def cyclomatic(code: str) -> int:
    blocks = cc_visit(textwrap.dedent(code))
    return blocks[0].complexity
'''

FIXTURES = {"slugify": SLUGIFY, "chunks": CHUNKS}

# (path, qualname) of the original, tier, copy. Tiers: R renamed, S restructured, A another approach.
COPIES = {
    "slugify-slug-copy": ("fixture", "slugify", "S", SLUG_COPY),
    "slugify-type-error": ("fixture", "slugify", "S", TYPE_ERROR_COPY),
    "slugify-restructured": ("fixture", "slugify", "S", RESTRUCTURED),
    "chunks": ("fixture", "chunks", "A", CHUNKS_COPY),
    "duration": ("slopgate/github.py", "duration", "S", DURATION_COPY),
    "plural": ("slopgate/github.py", "plural", "S", PLURAL_COPY),
    "tail": ("slopgate/sandbox.py", "tail", "S", TAIL_COPY),
    "module_of": ("slopgate/review.py", "module_of", "S", MODULE_OF_COPY),
    "strip_fence": ("slopgate/review.py", "strip_fence", "S", STRIP_FENCE_COPY),
    "pooled": ("slopgate/live.py", "pooled", "S", POOLED_COPY),
    "tokens": ("slopgate/functions.py", "tokens", "R", TOKENS_COPY),
    "apply": ("slopgate/review.py", "apply", "R", APPLY_COPY),
    "shell": ("slopgate/sandbox.py", "shell", "A", SHELL_COPY),
    "git": ("slopgate/diff.py", "git", "A", GIT_COPY),
    "complexity": ("slopgate/functions.py", "complexity", "R", COMPLEXITY_COPY),
}


def module_functions(root: Path, prefix: str) -> list[dict]:
    found = []
    for path in sorted(root.rglob("*.py")):
        rel = path.relative_to(root)
        if SKIPPED & set(rel.parts):
            continue
        try:
            found += parse(f"{prefix}{rel.as_posix()}", path.read_text())
        except (SyntaxError, ValueError):
            continue
    return [{"path": f.path, "qualname": f.qualname, "source": f.source} for f in found if "." not in f.qualname]


@cache
def pool(stdlib: bool) -> list[dict]:
    if stdlib:
        return pool(False) + module_functions(Path(sysconfig.get_paths()["stdlib"]), "stdlib/")
    repo = module_functions(ROOT / "slopgate", "slopgate/") + module_functions(ROOT / "tests", "tests/")
    fixtures = [{"path": "fixture", "qualname": name, "source": source} for name, source in FIXTURES.items()]
    return [r for r in repo if r["qualname"] not in FIXTURES] + fixtures


@pytest.mark.parametrize("stdlib", [False, True], ids=["pool-a", "pool-b"])
@pytest.mark.parametrize(("path", "qualname", "tier", "copy"), COPIES.values(), ids=COPIES.keys())
def test_keyword_search_finds_the_original_of_each_copy(stdlib, path, qualname, tier, copy):
    records = pool(stdlib)
    [original] = [r for r in records if (r["path"], r["qualname"]) == (path, qualname)]

    assert structure_hash(copy) != structure_hash(original["source"])
    assert original in [r for _, r in search(records, copy, DUPLICATE_SCORE, 5)]
