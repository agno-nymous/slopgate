import shutil
import subprocess
import tempfile
from pathlib import Path


def checkpoint(repo, ref) -> Path:
    path = Path(tempfile.mkdtemp(prefix="slopgate-"))
    archive = subprocess.run(["git", "archive", ref], cwd=repo, capture_output=True, check=True).stdout
    subprocess.run(["tar", "-x", "-C", path], input=archive, check=True)
    return path


def run(checkpoint: Path, files: dict[str, str], cmd: list[str]) -> tuple[int, str]:
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp) / "repo"
        shutil.copytree(checkpoint, work)
        for rel, content in files.items():
            (work / rel).parent.mkdir(parents=True, exist_ok=True)
            (work / rel).write_text(content)
        proc = subprocess.run(cmd, cwd=work, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        return proc.returncode, proc.stdout
