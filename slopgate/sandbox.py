import fnmatch
import os
import shutil
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path

from contree_sdk import ContreeSync

from slopgate.diff import git


class InstallError(Exception):
    pass


def tail(output: str) -> str:
    return "\n".join(output.strip().splitlines()[-20:])


def archive(repo, ref) -> bytes:
    return subprocess.run(["git", "archive", ref], cwd=repo, capture_output=True, check=True).stdout


def commands(repo, ref) -> tuple[str | None, str]:
    names = git(repo, "ls-tree", "--name-only", ref).splitlines()
    override = tomllib.loads(git(repo, "show", f"{ref}:.slopgate.toml")) if ".slopgate.toml" in names else {}
    override = override.get("sandbox", {})
    requirements = sorted(fnmatch.filter(names, "requirements*.txt"))
    if "pyproject.toml" in names:
        setup = "pip install -e ."
    elif requirements:
        setup = "pip install " + " ".join(f"-r {name}" for name in requirements)
    else:
        setup = None
    return override.get("setup", setup), override.get("test", "python -m pytest -q")


def shell(cmd: str, cwd) -> tuple[int, str]:
    env = {**os.environ, "PATH": os.path.dirname(sys.executable) + os.pathsep + os.environ["PATH"]}
    proc = subprocess.run(cmd, shell=True, cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    return proc.returncode, proc.stdout


class Local:
    def prepare(self, repo, ref, setup: str | None) -> Path:
        path = Path(tempfile.mkdtemp(prefix="slopgate-"))
        subprocess.run(["tar", "-x", "-C", path], input=archive(repo, ref), check=True)
        if setup:
            code, output = shell(setup, path)
            if code:
                raise InstallError(tail(output))
        return path

    def run(self, checkpoint: Path, files: dict[str, str], cmd: str) -> tuple[int, str]:
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp) / "repo"
            shutil.copytree(checkpoint, work)
            for rel, content in files.items():
                (work / rel).parent.mkdir(parents=True, exist_ok=True)
                (work / rel).write_text(content)
            return shell(cmd, work)


class Contree:
    def __init__(self):
        self.client = ContreeSync()

    def prepare(self, repo, ref, setup: str | None):
        script = "mkdir -p /repo && tar -x -f /tmp/repo.tar -C /repo && cd /repo && pip install -q pytest coverage || exit\n"
        result = (
            self.client.images.use("python:3.12-slim")
            .run(shell=script + (setup or ""), files={"/tmp/repo.tar": archive(repo, ref)}, disposable=False)
            .wait()
        )
        if result.exit_code:
            raise InstallError(tail(result.stdout + result.stderr))
        return result

    def run(self, checkpoint, files: dict[str, str], cmd: str) -> tuple[int, str]:
        files = {f"/repo/{rel}": content.encode() for rel, content in files.items()}
        result = checkpoint.run(shell=cmd, cwd="/repo", files=files).wait()
        return result.exit_code, result.stdout + result.stderr
