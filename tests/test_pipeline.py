import csv
import hashlib
import shutil
from pathlib import Path

from rag_hcmute.ingestion.pipeline import build_snapshot


MANIFEST_COLUMNS = [
    "document_id",
    "document_title",
    "document_number",
    "document_type",
    "issued_date",
    "effective_date",
    "source_url",
    "local_path",
    "file_sha256",
    "page_count",
    "language",
    "status",
    "notes",
]


def test_build_snapshot_resolves_relative_output_paths(tmp_path: Path) -> None:
    fixture = Path(__file__).parent / "fixtures" / "sample_quy_dinh.pdf"
    local_pdf = tmp_path / "sample.pdf"
    shutil.copyfile(fixture, local_pdf)
    digest = hashlib.sha256(local_pdf.read_bytes()).hexdigest()

    manifest_path = tmp_path / "manifest.csv"
    with manifest_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=MANIFEST_COLUMNS)
        writer.writeheader()
        writer.writerow(
            {
                "document_id": "TEST_DOC",
                "document_title": "Test document",
                "document_number": "TEST/01",
                "document_type": "test",
                "issued_date": "2026-01-01",
                "effective_date": "2026-01-01",
                "source_url": "https://example.invalid/test.pdf",
                "local_path": "sample.pdf",
                "file_sha256": digest,
                "page_count": "3",
                "language": "vi",
                "status": "test",
                "notes": "",
            }
        )

    snapshot = build_snapshot(
        manifest_path=manifest_path,
        project_root=tmp_path,
        pages_output_dir=Path("data/processed/pages"),
        chunks_output_dir=Path("data/processed/chunks"),
        snapshot_manifest_path=Path("data/processed/corpus_snapshot.json"),
        build_log_path=Path("artifacts/logs/build.log"),
    )

    assert snapshot["totals"]["document_count"] == 1
    assert snapshot["totals"]["page_count"] == 3
    assert snapshot["totals"]["ocr_page_count"] == 0
    assert snapshot["config"]["ocr"] == {"enabled": False}
    assert (tmp_path / "data/processed/corpus_snapshot.json").is_file()
    assert (tmp_path / "data/processed/chunks/chunks.jsonl").is_file()
