from pathlib import Path

from rag_hcmute.ingestion.manifest import audit_manifest, format_report, read_manifest, sha256_file

MANIFEST_HEADER = (
    "document_id,document_title,document_number,document_type,issued_date,"
    "effective_date,source_url,local_path,file_sha256,page_count,language,status,notes\n"
)


def test_sha256_file_is_stable(tmp_path: Path) -> None:
    sample = tmp_path / "sample.pdf"
    sample.write_bytes(b"%PDF-1.4\nminimal-test-content")

    assert sha256_file(sample) == sha256_file(sample)


def test_empty_manifest_is_valid_schema(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.csv"
    manifest.write_text(MANIFEST_HEADER, encoding="utf-8")

    assert audit_manifest(manifest, tmp_path) == []


def test_empty_manifest_is_reported_as_not_ready_not_complete(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.csv"
    manifest.write_text(MANIFEST_HEADER, encoding="utf-8")

    _, rows = read_manifest(manifest)
    issues = audit_manifest(manifest, tmp_path)
    report = format_report(rows, issues)

    assert "PASSED" in report
    assert "CHUA SAN SANG" in report


def test_manifest_with_valid_document_is_reported_as_ready(tmp_path: Path) -> None:
    pdf_path = tmp_path / "doc.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\nminimal-test-content")
    file_hash = sha256_file(pdf_path)

    manifest = tmp_path / "manifest.csv"
    manifest.write_text(
        MANIFEST_HEADER
        + f"DOC1,Sample title,01/QD,quyet_dinh,2024-01-01,2024-02-01,https://example.com/doc.pdf,"
        f"doc.pdf,{file_hash},1,vi,hieu_luc,\n",
        encoding="utf-8",
    )

    _, rows = read_manifest(manifest)
    issues = audit_manifest(manifest, tmp_path)
    report = format_report(rows, issues)

    assert issues == []
    assert "CORPUS SAN SANG" in report


def test_hash_mismatch_is_a_reported_issue_not_silently_ready(tmp_path: Path) -> None:
    pdf_path = tmp_path / "doc.pdf"
    pdf_path.write_bytes(b"%PDF-1.4\nminimal-test-content")

    manifest = tmp_path / "manifest.csv"
    manifest.write_text(
        MANIFEST_HEADER
        + "DOC1,Sample title,01/QD,quyet_dinh,2024-01-01,2024-02-01,https://example.com/doc.pdf,"
        "doc.pdf,0000000000000000000000000000000000000000000000000000000000000000,1,vi,hieu_luc,\n",
        encoding="utf-8",
    )

    issues = audit_manifest(manifest, tmp_path)
    assert any(issue.field == "file_sha256" for issue in issues)

