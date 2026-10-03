import json
from dataclasses import asdict
from pathlib import Path

from slopgate import embed
from slopgate.diff import git
from slopgate.functions import parse, structure_hash


def location(repo, ref) -> Path:
    return Path(repo) / ".slopgate" / f"{git(repo, 'rev-parse', f'{ref}^{{commit}}').strip()}.json"


def build(repo, ref) -> list[dict]:
    path = location(repo, ref)
    if path.exists():
        return json.loads(path.read_text())
    functions = []
    for name in git(repo, "ls-tree", "-r", "--name-only", path.stem).splitlines():
        if name.endswith(".py"):
            try:
                functions += parse(name, git(repo, "show", f"{path.stem}:{name}"))
            except SyntaxError:
                continue
    vectors = embed.encode([f.source for f in functions]) if functions else []
    records = [{**asdict(f), "hash": structure_hash(f.source), "vector": v} for f, v in zip(functions, vectors)]
    path.parent.mkdir(exist_ok=True)
    (path.parent / ".gitignore").write_text("*\n")
    path.write_text(json.dumps(records))
    return records


def search(index, vector, floor, top) -> list[tuple[float, dict]]:
    # ponytail: linear scan, numpy matrix when repos get large
    scored = sorted(((sum(a * b for a, b in zip(r["vector"], vector)), r) for r in index), key=lambda pair: -pair[0])
    return [(score, r) for score, r in scored[:top] if score >= floor]
