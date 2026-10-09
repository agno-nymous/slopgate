import json
import sqlite3
from array import array
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import NamedTuple

from slopgate import embed, llm, trace
from slopgate.config import FLAG, HOOK_FLOOR, HOOK_K, LIGHTNING
from slopgate.functions import Function, is_test_file, jaccard, parse, pytest_patterns, structure_hash, tokens

STORE = Path(".slopgate") / "live.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS functions (
    path TEXT NOT NULL,
    qualname TEXT NOT NULL,
    start INTEGER NOT NULL,
    hash TEXT NOT NULL,
    tokens TEXT NOT NULL,
    vector BLOB NOT NULL,
    PRIMARY KEY (path, qualname)
);
CREATE INDEX IF NOT EXISTS functions_hash ON functions (hash);
"""

REUSE_PROMPT = (
    "A coding agent just wrote function B. Function A already exists in the same repository. "
    "Answer yes if B does the same job as A, so the agent should call A instead of keeping B, "
    "even when names, structure, or error messages differ. Answer no if they do different jobs. "
    "Reply with exactly one word: yes or no."
)


class Row(NamedTuple):
    path: str
    qualname: str
    start: int
    hash: str
    tokens: frozenset[str]
    vector: bytes


class Candidate(NamedTuple):
    new: Function
    existing: Row
    exact: bool


class Flag(NamedTuple):
    new: Function
    existing: Row
    confidence: float


def hook(payload: str) -> str:
    data = json.loads(payload)
    path = Path(data["tool_input"]["file_path"])
    if path.suffix != ".py":
        return ""
    root = next((parent for parent in path.parents if (parent / STORE).exists()), None)
    if root is None:
        return ""
    rel = path.relative_to(root).as_posix()
    stamp = path.stat().st_mtime_ns
    patterns = patterns_in(root)
    functions = [f for f in parse(rel, path.read_text()) if pooled(f.path, f.qualname, patterns)]
    db = store(root)
    vectors = {row.qualname: row.vector for row in rows(db, rel)}
    new = [f for f in functions if f.qualname not in vectors]
    candidates = []
    if new:
        embed.preload()
        names = {f.qualname for f in functions}
        pool = [row for row in rows(db) if row.path != rel or row.qualname in names]
        candidates = matches(new, embed.encode([f.source for f in new], query=True), pool)
        vectors |= {f.qualname: array("f", v).tobytes() for f, v in zip(new, embed.encode([f.source for f in new]))}
    with db:
        db.execute("BEGIN IMMEDIATE")
        # A later hook run for the same file owns its rows once the file has changed again.
        if path.stat().st_mtime_ns == stamp:
            put(db, {rel}, [(rel, f.qualname, f.start, structure_hash(f.source), f.source, vectors[f.qualname]) for f in functions])
    if not candidates:
        return ""
    with trace.span("hook.run", session=data.get("session_id"), path=rel):
        out = note(classify(root, candidates))
        trace.output(out)
    return out


def seed(repo: str, records: list[dict]) -> None:
    patterns = patterns_in(Path(repo))
    pool = [r for r in records if pooled(r["path"], r["qualname"], patterns)]
    vectors = embed.encode([r["source"] for r in pool]) if pool else []
    db = store(Path(repo))
    with db:
        db.execute("BEGIN IMMEDIATE")
        put(
            db,
            {r["path"] for r in records},
            [(r["path"], r["qualname"], r["start"], r["hash"], r["source"], array("f", v).tobytes()) for r, v in zip(pool, vectors)],
        )


def patterns_in(root: Path) -> list[str]:
    return pytest_patterns(lambda name: (root / name).read_text() if (root / name).exists() else None)


def pooled(path: str, qualname: str, patterns: list[str]) -> bool:
    return "." not in qualname and not qualname.startswith("test_") and not is_test_file(path, patterns)


def store(root: Path) -> sqlite3.Connection:
    db = sqlite3.connect(root / STORE, timeout=5, isolation_level=None)
    db.execute("PRAGMA journal_mode=WAL")
    db.executescript(SCHEMA)
    return db


def put(db: sqlite3.Connection, paths: set[str], entries: list[tuple]) -> None:
    db.executemany("DELETE FROM functions WHERE path = ?", [(path,) for path in paths])
    db.executemany(
        "INSERT OR REPLACE INTO functions VALUES (?, ?, ?, ?, ?, ?)",
        [(path, qualname, start, code_hash, " ".join(sorted(tokens(source))), vector) for path, qualname, start, code_hash, source, vector in entries],
    )


def rows(db: sqlite3.Connection, path: str | None = None) -> list[Row]:
    found = db.execute("SELECT * FROM functions WHERE path = ?", (path,)) if path else db.execute("SELECT * FROM functions")
    return [Row(p, qualname, start, code_hash, frozenset(text.split()), vector) for p, qualname, start, code_hash, text, vector in found]


def matches(new: list[Function], queries: list[list[float]], pool: list[Row]) -> list[Candidate]:
    import numpy

    if not pool:
        return []
    # ponytail: full scan of the store per new-function write (~60-120 ms at 4.5k rows); FTS5 prefilter or a cached matrix past ~20k functions
    vectors = numpy.frombuffer(b"".join(row.vector for row in pool), numpy.float32).reshape(len(pool), -1)
    found = []
    for function, query in zip(new, queries):
        code_hash = structure_hash(function.source)
        exact = next((row for row in pool if row.hash == code_hash), None)
        if exact:
            found.append(Candidate(function, exact, True))
            continue
        words = tokens(function.source)
        overlap = numpy.array([jaccard(words, row.tokens) for row in pool])
        fused = 0.5 * (vectors @ numpy.array(query, numpy.float32)) + 0.5 * overlap
        found += [Candidate(function, pool[i], False) for i in numpy.argsort(-fused)[:HOOK_K] if fused[i] >= HOOK_FLOOR]
    return found


def classify(root: Path, candidates: list[Candidate]) -> list[Flag]:
    asked = [c for c in candidates if not c.exact]
    with ThreadPoolExecutor() as threads:
        confidences = list(threads.map(trace.bind(lambda c: llm.yes_probability(LIGHTNING, question(source(root, c.existing), c.new.source))), asked))
    flags = [Flag(c.new, c.existing, 1.0) for c in candidates if c.exact]
    flags += [Flag(c.new, c.existing, confidence) for c, confidence in zip(asked, confidences) if confidence >= FLAG]
    best = {}
    for flag in flags:
        if flag.new not in best or flag.confidence > best[flag.new].confidence:
            best[flag.new] = flag
    return list(best.values())


def source(root: Path, row: Row) -> str:
    return next(f.source for f in parse(row.path, (root / row.path).read_text()) if f.qualname == row.qualname)


def question(existing: str, new: str) -> str:
    return f"{REUSE_PROMPT}\n\nFunction A:\n{existing}\nFunction B:\n{new}"


def note(flags: list[Flag]) -> str:
    if not flags:
        return ""
    lines = [
        f"slopgate: `{f.new.qualname}` ({f.new.path}:{f.new.start}) duplicates existing `{f.existing.qualname}` "
        f"({f.existing.path}:{f.existing.start}), confidence {f.confidence:.2f}. "
        f"Call `{f.existing.qualname}` instead of keeping `{f.new.qualname}`, unless the behavior must differ."
        for f in flags
    ]
    return json.dumps({"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": "\n".join(lines)}})
