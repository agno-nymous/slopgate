import re
import subprocess

from slopgate.functions import Function, parse


def git(repo, *args) -> str:
    return subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, check=True).stdout


def python_sources(repo, ref):
    for path in git(repo, "ls-tree", "-r", "--name-only", ref).splitlines():
        if path.endswith(".py"):
            try:
                text = git(repo, "show", f"{ref}:{path}")
            except UnicodeDecodeError:
                continue
            yield path, text


def changed_functions(repo, base, head) -> list[tuple[Function, set[int]]]:
    added: dict[str, set[int]] = {}
    for line in git(repo, "diff", "--unified=0", "--diff-filter=AM", base, head, "--", "*.py").splitlines():
        if line.startswith("+++ b/"):
            path = line[len("+++ b/") :]
            added[path] = set()
        elif line.startswith("@@"):
            m = re.search(r"\+(\d+)(?:,(\d+))?", line)
            start = int(m[1])
            added[path].update(range(start, start + int(m[2] or 1)))
    changed = []
    for path, lines in added.items():
        for function in parse(path, git(repo, "show", f"{head}:{path}")):
            touched = lines & set(range(function.start, function.end + 1))
            if touched:
                changed.append((function, touched))
    return changed


def old_function(repo, base, function) -> tuple[Function, str] | None:
    try:
        text = git(repo, "show", f"{base}:{function.path}")
        found = parse(function.path, text)
    except (subprocess.CalledProcessError, UnicodeDecodeError, SyntaxError, ValueError):
        return None
    return next(((old, text) for old in found if old.qualname == function.qualname), None)
