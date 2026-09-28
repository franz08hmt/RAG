import csv
import shutil
from pathlib import Path

import pytest

from rag_hcmute.ingestion.manifest import sha256_file
from scripts.prepare_table_variants import _find_source_document

FIXTURE = Path(__file__).parent / "fixtures" / "sample_quy_dinh.pdf"


def _write_manifest(path: Path, local_path: str, expected_hash: str) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=["document_id", "document_title", "local_path", "file_sha256"],
        )
        writer.writeheader()
        writer.writerow(
            {
                "document_id": "TEST_DOC",
                "document_title": "Tài liệu kiểm thử",
                "local_path": local_path,
                "file_sha256": expected_hash,
            }
        )


def test_source_document_requires_manifest_hash_match(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    raw_dir = project_root / "data" / "raw"
    raw_dir.mkdir(parents=True)
    source = raw_dir / "sample.pdf"
    shutil.copyfile(FIXTURE, source)
    manifest = project_root / "manifest.csv"
    _write_manifest(manifest, "data/raw/sample.pdf", sha256_file(source))

    row = _find_source_document(manifest, project_root, "TEST_DOC")

    assert row["_resolved_pdf_path"] == str(source.resolve())
    assert row["_verified_sha256"] == sha256_file(source)

    _write_manifest(manifest, "data/raw/sample.pdf", "0" * 64)
    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        _find_source_document(manifest, project_root, "TEST_DOC")


def test_source_document_refuses_paths_outside_project_root(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    outside_source = tmp_path / "outside.pdf"
    shutil.copyfile(FIXTURE, outside_source)
    manifest = project_root / "manifest.csv"
    _write_manifest(manifest, "../outside.pdf", sha256_file(outside_source))

    with pytest.raises(ValueError, match="outside project-root"):
        _find_source_document(manifest, project_root, "TEST_DOC")
