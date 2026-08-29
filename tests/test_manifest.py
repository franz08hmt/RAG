from pathlib import Path

from rag_hcmute.ingestion.manifest import audit_manifest, sha256_file


def test_sha256_file_is_stable(tmp_path: Path) -> None:
    sample = tmp_path / "sample.pdf"
    sample.write_bytes(b"%PDF-1.4\nminimal-test-content")

    assert sha256_file(sample) == sha256_file(sample)


def test_empty_manifest_is_valid_schema(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.csv"
    manifest.write_text(
        "document_id,document_title,document_number,document_type,issued_date,"
        "effective_date,source_url,local_path,file_sha256,page_count,language,status,notes\n",
        encoding="utf-8",
    )

    assert audit_manifest(manifest, tmp_path) == []

