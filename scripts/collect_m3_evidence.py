"""Package approved numerical results only. Preserve hashes of the original runs."""
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNS = {
    "chunking": "chunking_20261104T135721Z",
    "embeddings": "embeddings_20261105T010154Z",
    "ranking": "ranking_20261105T010609Z",
    "generation": "generation_20261104T140158Z",
    "ocr": "ocr_20261105T010203Z",
    "review": "review_audit_20261105",
}
FORBIDDEN = {"question", "query", "answer", "text", "quote", "evidence_text", "private_directory"}


def check_safe(value):
    if isinstance(value, dict):
        if FORBIDDEN.intersection(value):
            raise ValueError("Private field in numerical export")
        for child in value.values():
            check_safe(child)
    elif isinstance(value, list):
        for child in value:
            check_safe(child)
    elif isinstance(value, str) and (":\\" in value or ":/" in value[:3]):
        raise ValueError("Absolute workstation path in numerical export")


def save(path, value):
    data = (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()
    if path.exists() and path.read_bytes() != data:
        raise ValueError(f"Evidence changed: {path.name}")
    path.write_bytes(data)
    return hashlib.sha256(data).hexdigest()


def main():
    print(sys.executable)
    out = ROOT / "docs/evidence/m3/runs"
    out.mkdir(parents=True, exist_ok=True)
    manifest = {}
    for name, run in RUNS.items():
        raw = (ROOT / "artifacts/results/m3" / (run + ".json")).read_bytes()
        record = json.loads(raw)
        if name in ("chunking", "embeddings", "ranking", "generation"):
            if not record["completed"] or record["holdout_used"]:
                raise ValueError(f"Unexpected run status: {name}")
        if name == "generation":
            record.pop("private_directory")
        check_safe(record)
        manifest[name] = {
            "source_file": run + ".json",
            "source_sha256": hashlib.sha256(raw).hexdigest(),
            "export_sha256": save(out / (name + ".json"), record),
        }
    save(out.parent / "manifest.json", manifest)


if __name__ == "__main__":
    main()
