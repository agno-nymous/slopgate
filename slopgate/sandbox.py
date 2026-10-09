import fnmatch
import os
import shutil
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path

from contree_sdk import ContreeSync

from slopgate import trace
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
    # The code under test must not see the API key or the tracing endpoint: it can print them into a span or a prompt.
    env = {k: v for k, v in os.environ.items() if not k.startswith(("NEBIUS_", "PHOENIX_", "OTEL_", "GH_TOKEN", "GITHUB_TOKEN"))}
    env["PATH"] = os.path.dirname(sys.executable) + os.pathsep + os.environ["PATH"]
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
        with trace.span("sandbox.run", input={"cmd": cmd, "files": files}), tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp) / "repo"
            shutil.copytree(checkpoint, work)
            for rel, content in files.items():
                (work / rel).parent.mkdir(parents=True, exist_ok=True)
                (work / rel).write_text(content)
            code, output = shell(cmd, work)
            trace.output({"exit_code": code, "output": output})
            return code, output


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
        with trace.span("sandbox.run", input={"cmd": cmd, "files": files}):
            files = {f"/repo/{rel}": content.encode() for rel, content in files.items()}
            result = checkpoint.run(shell=cmd, cwd="/repo", files=files).wait()
            output = result.stdout + result.stderr
            trace.output({"exit_code": result.exit_code, "output": output})
            return result.exit_code, output
