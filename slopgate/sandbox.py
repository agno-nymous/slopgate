import fnmatch
import os
import shlex
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import tomllib
from datetime import datetime
from pathlib import Path

from contree_sdk import ContreeSync
from contree_sdk.sdk.exceptions import NotFoundError

from slopgate import trace
from slopgate.config import OLD_COMMIT_BEFORE, OLD_COMMIT_IMAGE, SANDBOX_TIMEOUT
from slopgate.diff import git


class InstallError(Exception):
    pass


def tail(output: str) -> str:
    return "\n".join(output.strip().splitlines()[-20:])


def archive(repo, ref) -> bytes:
    return subprocess.run(["git", "archive", ref], cwd=repo, capture_output=True, check=True).stdout


def commit_date(repo, ref) -> str:
    return git(repo, "show", "-s", "--format=%cI", ref).strip()


def is_old(date: str) -> bool:
    return datetime.fromisoformat(date) < datetime.fromisoformat(OLD_COMMIT_BEFORE)


# uv needs a path, not a name, to install into a Python that is not in a virtual environment.
PYTHON = '"$(command -v python)"'


def pinned_install(names, since) -> tuple[str, str | None]:
    # Each variant falls back to the plain install: a failed pinned install must not become "could not build test environment".
    plain = "pip install -e ."
    if "uv.lock" in names and "pyproject.toml" in names:
        pinned = f"R=$(mktemp) && uv export --frozen --all-groups --no-hashes --no-emit-project -o $R && uv pip install --python {PYTHON} -q -r $R -e ."
        image = None
    elif is_old(since):
        # The sandbox installs the newest pytest first: reinstall it with the date limit. A setuptools from before 2022 cannot build an
        # editable install, so setuptools is limited to the date only after the build: the newest one warns in `pkg_resources`.
        install = f"uv pip install --python {PYTHON} -q --exclude-newer {since}"
        pinned = f"{install} --exclude-newer-package setuptools=2100-01-01 -e . pytest --reinstall-package pytest && {install} setuptools --reinstall-package setuptools"
        image = OLD_COMMIT_IMAGE
    else:
        return plain, None
    return f"pip install -q uv && {pinned} || {plain}", image


def commands(repo, ref, since=None) -> tuple[str | None, str, str | None]:
    # `since` is the commit date of the merge-base. Without it the install is not pinned: the Local sandbox installs into this venv.
    names = git(repo, "ls-tree", "--name-only", ref).splitlines()
    override = tomllib.loads(git(repo, "show", f"{ref}:.slopgate.toml")) if ".slopgate.toml" in names else {}
    override = override.get("sandbox", {})
    requirements = sorted(fnmatch.filter(names, "requirements*.txt"))
    image = None
    if {"pyproject.toml", "setup.py"} & set(names):
        setup, image = pinned_install(names, since) if since else ("pip install -e .", None)
    elif requirements:
        setup = "pip install " + " ".join(f"-r {name}" for name in requirements)
    else:
        setup = None
    if "setup" in override:
        setup, image = override["setup"], None
    return setup, override.get("test", "python -m pytest -q -rfE"), image


def bounded(cmd: str, seconds: int) -> str:
    return f"timeout -k 5 {seconds} sh -c {shlex.quote(cmd)}"


def shell(cmd: str, cwd, timeout: float | None = None) -> tuple[int, str]:
    # The code under test must not see the API key or the tracing endpoint: it can print them into a span or a prompt.
    env = {k: v for k, v in os.environ.items() if not k.startswith(("NEBIUS_", "PHOENIX_", "OTEL_", "GH_TOKEN", "GITHUB_TOKEN"))}
    env["PATH"] = os.path.dirname(sys.executable) + os.pathsep + os.environ["PATH"]
    # Its own process group lets a timeout kill pytest too: a child that keeps the pipe open would block the read.
    proc = subprocess.Popen(
        cmd, shell=True, cwd=cwd, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, start_new_session=True
    )
    try:
        output, _ = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid, signal.SIGKILL)
        try:
            output, _ = proc.communicate(timeout=5)
        except subprocess.TimeoutExpired as expired:
            # A child that left the process group still holds the pipe open.
            proc.kill()
            proc.stdout.close()
            output = (expired.output or b"").decode(errors="replace")
        return 124, f"{output}\ntimed out after {timeout} s"
    return proc.returncode, output


class LocalSession:
    def __init__(self, checkpoint: Path):
        self.tmp = tempfile.TemporaryDirectory(prefix="slopgate-agent-")
        self.root = Path(self.tmp.name) / "repo"
        shutil.copytree(checkpoint, self.root)

    def execute(self, command: str, timeout: int) -> tuple[int, str]:
        with trace.span("sandbox.execute", input=command):
            code, output = shell(command, self.root, timeout)
            trace.output({"exit_code": code, "output": output})
            return code, output

    def read(self, path: str) -> str | None:
        file = self.root / path
        return file.read_text() if file.is_file() else None


class ContreeSession:
    def __init__(self, checkpoint):
        self.session = checkpoint.session()

    def execute(self, command: str, timeout: int) -> tuple[int, str]:
        with trace.span("sandbox.execute", input=command):
            # The SDK uses its timeout for the server and for the client wait. The client gives up first and the session
            # fails for good, so `timeout` in the sandbox ends the command and the SDK waits 60 s longer.
            done = self.session.run(
                shell=bounded(command, timeout),
                cwd="/repo",
                timeout=timeout + 60,
                disposable=False,
                # The default cut at 65,535 bytes would hide the end of a long pytest run; stage 1 of ticket 41 measured 10 MiB.
                truncate_output_at=10 * 1024 * 1024,
            ).wait()
            output = done.stdout + done.stderr
            if done.result.truncated:
                output += "\n[Output was truncated due to size limits]"
            trace.output({"exit_code": done.exit_code, "output": output})
            return done.exit_code, output

    def read(self, path: str) -> str | None:
        try:
            return self.session.read(f"/repo/{path}").decode()
        except NotFoundError:
            return None


class Local:
    pins = False

    def prepare(self, repo, ref, setup: str | None, image=None) -> Path:
        path = Path(tempfile.mkdtemp(prefix="slopgate-"))
        subprocess.run(["tar", "-x", "-C", path], input=archive(repo, ref), check=True)
        if setup:
            code, output = shell(setup, path)
            if code:
                raise InstallError(tail(output))
        return path

    def run(self, checkpoint: Path, files: dict[str, str], cmd: str, seconds: int | None = None) -> tuple[int, str]:
        if seconds is None:
            seconds = SANDBOX_TIMEOUT
        with trace.span("sandbox.run", input={"cmd": cmd, "files": files}), tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp) / "repo"
            shutil.copytree(checkpoint, work)
            for rel, content in files.items():
                (work / rel).parent.mkdir(parents=True, exist_ok=True)
                (work / rel).write_text(content)
            code, output = shell(cmd, work, seconds)
            trace.output({"exit_code": code, "output": output})
            return code, output

    def session(self, checkpoint: Path) -> LocalSession:
        return LocalSession(checkpoint)


class Contree:
    pins = True

    def __init__(self, image="python:3.12-slim"):
        self.client = ContreeSync()
        self.image = image

    def prepare(self, repo, ref, setup: str | None, image=None):
        script = "mkdir -p /repo && tar -x -f /tmp/repo.tar -C /repo && cd /repo && pip install -q pytest coverage || exit\n"
        result = (
            self.client.images.use(image or self.image)
            .run(shell=script + (setup or ""), files={"/tmp/repo.tar": archive(repo, ref)}, disposable=False)
            .wait()
        )
        if result.exit_code:
            raise InstallError(tail(result.stdout + result.stderr))
        return result

    def run(self, checkpoint, files: dict[str, str], cmd: str, seconds: int | None = None) -> tuple[int, str]:
        if seconds is None:
            seconds = SANDBOX_TIMEOUT
        with trace.span("sandbox.run", input={"cmd": cmd, "files": files}):
            files = {f"/repo/{rel}": content.encode() for rel, content in files.items()}
            began = time.monotonic()
            result = checkpoint.run(shell=bounded(cmd, seconds), cwd="/repo", files=files, timeout=seconds + 60).wait()
            code, output = result.exit_code, result.stdout + result.stderr
            # The exit code cannot tell a timeout: a command may exit 124 itself, and one that ignores SIGTERM ends with 137.
            if time.monotonic() - began >= seconds:
                code, output = 124, f"{output}\ntimed out after {seconds} s"
            trace.output({"exit_code": code, "output": output})
            return code, output

    def session(self, checkpoint) -> ContreeSession:
        return ContreeSession(checkpoint)
