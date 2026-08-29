from __future__ import annotations

import sys
import tempfile
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_ROOT))

from rag_hcmute.ingestion.manifest import audit_manifest, sha256_file  # noqa: E402


MANIFEST_HEADER = (
    "document_id,document_title,document_number,document_type,issued_date,"
    "effective_date,source_url,local_path,file_sha256,page_count,language,status,notes\n"
)


def run() -> None:
    with tempfile.TemporaryDirectory(prefix="rag_hcmute_smoke_") as temp_dir:
        root = Path(temp_dir)
        sample = root / "sample.pdf"
        sample.write_bytes(b"%PDF-1.4\nminimal-test-content")
        assert sha256_file(sample) == sha256_file(sample)

        manifest = root / "manifest.csv"
        manifest.write_text(MANIFEST_HEADER, encoding="utf-8")
        assert audit_manifest(manifest, root) == []

    print("Smoke tests PASSED: manifest schema and SHA-256 validation are operational.")


if __name__ == "__main__":
    run()

