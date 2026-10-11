import json
from dataclasses import asdict
from functools import cache
from pathlib import Path

from slopgate.diff import git, python_sources
from slopgate.functions import jaccard, parse, structure_hash, tokens

pool_tokens = cache(tokens)


def location(repo, ref) -> Path:
    return Path(repo) / ".slopgate" / f"{git(repo, 'rev-parse', f'{ref}^{{commit}}').strip()}.json"


def build(repo, ref) -> list[dict]:
    path = location(repo, ref)
    if path.exists():
        return json.loads(path.read_text())
    functions = []
    for name, text in python_sources(repo, path.stem):
        try:
            functions += parse(name, text)
        except SyntaxError:
            continue
    records = [{**asdict(f), "hash": structure_hash(f.source)} for f in functions]
    path.parent.mkdir(exist_ok=True)
    (path.parent / ".gitignore").write_text("*\n")
    path.write_text(json.dumps(records))
    return records


def search(index, source, floor, top) -> list[tuple[float, dict]]:
    words = tokens(source)
    # ponytail: linear scan of the pool per query (11 ms at 3,060 functions); an inverted index past ~100k functions
    scored = sorted(((jaccard(words, pool_tokens(r["source"])), r) for r in index), key=lambda pair: -pair[0])
    return [(score, r) for score, r in scored[:top] if score >= floor]
