import json
from pathlib import Path

ROOT = Path(__file__).parent
RESULTS = ROOT / "results"
GROUNDTRUTH = RESULTS / "groundtruth.json"
RUNS = RESULTS / "runs.json"
LABELS = ROOT / "labels.json"


def write(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(data, indent=1) + "\n")
    temporary.replace(path)


def meta_path(path: Path) -> Path:
    return path.with_suffix(".meta.json")


def stored_meta(path: Path) -> dict | None:
    return json.loads(meta_path(path).read_text()) if meta_path(path).exists() else None


def all_runs() -> list[dict]:
    return [json.loads(path.read_text()) for path in (RUNS, RESULTS / "runs-t39.json") if path.exists()]
