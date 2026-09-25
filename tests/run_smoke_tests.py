from __future__ import annotations

import sys
import tempfile
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_ROOT))

from rag_hcmute.ingestion.chunk import chunk_document  # noqa: E402
from rag_hcmute.ingestion.clean import clean_document_pages  # noqa: E402
from rag_hcmute.ingestion.extract import extract_pdf_pages  # noqa: E402
from rag_hcmute.ingestion.manifest import audit_manifest, format_report, read_manifest, sha256_file  # noqa: E402
from rag_hcmute.retrieval.bm25_index import BM25Retriever  # noqa: E402


MANIFEST_HEADER = (
    "document_id,document_title,document_number,document_type,issued_date,"
    "effective_date,source_url,local_path,file_sha256,page_count,language,status,notes\n"
)

FIXTURE_PDF = PROJECT_ROOT / "tests" / "fixtures" / "sample_quy_dinh.pdf"


def run() -> None:
    with tempfile.TemporaryDirectory(prefix="rag_hcmute_smoke_") as temp_dir:
        root = Path(temp_dir)
        sample = root / "sample.pdf"
        sample.write_bytes(b"%PDF-1.4\nminimal-test-content")
        assert sha256_file(sample) == sha256_file(sample)

        manifest = root / "manifest.csv"
        manifest.write_text(MANIFEST_HEADER, encoding="utf-8")
        assert audit_manifest(manifest, root) == []

        _, rows = read_manifest(manifest)
        report = format_report(rows, audit_manifest(manifest, root))
        assert "CHUA SAN SANG" in report, "manifest rong phai duoc bao la CHUA SAN SANG"

    print("Smoke test 1/2 PASSED: manifest schema, SHA-256 va phan biet 'rong' vs 'san sang'.")

    assert FIXTURE_PDF.is_file(), f"Thieu fixture PDF: {FIXTURE_PDF}"
    pages = extract_pdf_pages(FIXTURE_PDF, "SMOKE_DOC")
    assert len(pages) == 3
    cleaned, _ = clean_document_pages(pages)
    chunks = chunk_document(cleaned, "SMOKE_DOC", "Smoke test fixture")
    assert len(chunks) > 0

    retriever = BM25Retriever(chunks)
    result = retriever.query("MA_KIEM_THU_DIEU_MOT", top_k=3)
    assert result.hits and "MA_KIEM_THU_DIEU_MOT" in next(
        c.text for c in chunks if c.chunk_id == result.hits[0].chunk_id
    )

    print("Smoke test 2/2 PASSED: extract -> clean -> chunk -> BM25 chay dung tren fixture.")


if __name__ == "__main__":
    run()

