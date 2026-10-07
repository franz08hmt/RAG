from __future__ import annotations

import argparse
import csv
import hashlib
import json
import statistics
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path


print(f"Python executable: {sys.executable}")

PROJECT_ROOT = Path(__file__).resolve().parents[1]

import pymupdf  # noqa: E402


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def _read_jsonl(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as stream:
        return [json.loads(line) for line in stream if line.strip()]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _git_revision() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=PROJECT_ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unavailable"


def _distribution(values: list[int]) -> dict[str, int | None]:
    ordered = sorted(values)
    return {
        "min": ordered[0] if ordered else None,
        "median": int(statistics.median(ordered)) if ordered else None,
        "max": ordered[-1] if ordered else None,
    }


def build_profile() -> dict:
    manifest_path = PROJECT_ROOT / "data/manifests/corpus_manifest.csv"
    snapshot_path = PROJECT_ROOT / "data/processed/g0_reproduction/snapshot.json"
    pages_dir = PROJECT_ROOT / "data/processed/g0_reproduction/pages"
    chunks_path = PROJECT_ROOT / "data/processed/g0_reproduction/chunks/chunks.jsonl"
    manifest_rows = _read_csv(manifest_path)
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    snapshot_docs = {row["document_id"]: row for row in snapshot["documents"]}

    chunks_by_doc: dict[str, list[dict]] = defaultdict(list)
    all_chunk_keys: Counter[str] = Counter()
    for chunk in _read_jsonl(chunks_path):
        chunks_by_doc[chunk["document_id"]].append(chunk)
        all_chunk_keys.update(chunk.keys())

    documents = []
    for manifest_row in manifest_rows:
        document_id = manifest_row["document_id"]
        pdf_path = PROJECT_ROOT / manifest_row["local_path"]
        actual_hash = _sha256(pdf_path)
        expected_hash = manifest_row["file_sha256"].strip().lower()
        if actual_hash != expected_hash:
            raise SystemExit(f"SHA-256 mismatch for {document_id}; stopping the audit.")

        page_rows = _read_jsonl(pages_dir / f"{document_id}.jsonl")
        chunk_rows = chunks_by_doc[document_id]
        page_char_counts = [int(row.get("char_count", 0)) for row in page_rows]
        page_field_counts: Counter[str] = Counter()
        for row in page_rows:
            page_field_counts.update(row.keys())
        chunk_method_counts = Counter(row.get("chunk_method", "unknown") for row in chunk_rows)
        chunk_token_counts = [int(row.get("token_count", 0)) for row in chunk_rows]

        raster_pages = 0
        raster_references = 0
        with pymupdf.open(pdf_path) as pdf:
            pdf_page_count = len(pdf)
            if pdf_page_count != int(manifest_row["page_count"]):
                raise SystemExit(f"Page count differs from manifest for {document_id}.")
            for page in pdf:
                image_refs = page.get_images(full=True)
                raster_references += len(image_refs)
                raster_pages += bool(image_refs)

        snapshot_doc = snapshot_docs[document_id]
        if len(page_rows) != pdf_page_count or len(chunk_rows) != int(snapshot_doc["chunk_count"]):
            raise SystemExit(f"Processed page/chunk counts differ for {document_id}.")

        documents.append(
            {
                "document_id": document_id,
                "document_type": manifest_row["document_type"],
                "title": manifest_row["document_title"],
                "source_hash_matches_manifest": True,
                "page_count": len(page_rows),
                "chunk_count": len(chunk_rows),
                "probable_scan_page_numbers_from_snapshot": snapshot_doc.get(
                    "probable_scan_pages", []
                ),
                "probable_scan_page_count": len(snapshot_doc.get("probable_scan_pages", [])),
                "page_character_count": _distribution(page_char_counts),
                "pages_with_embedded_raster_references": raster_pages,
                "embedded_raster_references": raster_references,
                "dieu_structured": snapshot_doc.get("dieu_structured"),
                "dieu_markers_found": snapshot_doc.get("dieu_markers_found"),
                "chunk_methods": dict(chunk_method_counts),
                "chunk_token_count": _distribution(chunk_token_counts),
                "chunks_with_section_path": sum(bool(row.get("section_path")) for row in chunk_rows),
                "page_records_with_extraction_method": sum(
                    "extraction_method" in row for row in page_rows
                ),
                "chunks_with_extraction_methods": sum(
                    bool(row.get("extraction_methods")) for row in chunk_rows
                ),
                "chunks_with_ocr_confidence": sum(
                    row.get("ocr_confidence_mean") is not None for row in chunk_rows
                ),
                "chunks_with_token_offsets": sum(
                    row.get("token_start") is not None and row.get("token_end") is not None
                    for row in chunk_rows
                ),
                "page_record_fields": sorted(page_field_counts),
            }
        )

    return {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "metadata_only_local_corpus_audit",
        "snapshot_id": snapshot["snapshot_id"],
        "git_revision": _git_revision(),
        "pymupdf_version": pymupdf.__version__,
        "manifest_sha256": _sha256(manifest_path),
        "snapshot_sha256": _sha256(snapshot_path),
        "snapshot_config": snapshot.get("config", {}),
        "snapshot_totals": snapshot.get("totals", {}),
        "chunk_record_fields": sorted(all_chunk_keys),
        "privacy_note": "Aggregates and metadata only; extracted document text is not written to the report.",
        "documents": documents,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Audit corpus document classes, page/chunk metadata, suspected scans, and raster references. "
            "No extracted document text is emitted."
        )
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROJECT_ROOT / "artifacts/results/input_document_profile",
    )
    args = parser.parse_args()
    report = build_profile()

    output_dir = args.output_dir.resolve()
    ignored_root = (PROJECT_ROOT / "artifacts/results").resolve()
    if not output_dir.is_relative_to(ignored_root):
        raise SystemExit("--output-dir must remain under Git-ignored artifacts/results.")
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_path = output_dir / f"input_profile_{timestamp}.json"
    with output_path.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write("\n")

    print(f"Status: {report['status']} | snapshot: {report['snapshot_id']}")
    for document in report["documents"]:
        print(
            f"{document['document_type']} {document['document_id']}: "
            f"{document['page_count']} pages, {document['chunk_count']} chunks, "
            f"probable-scan={document['probable_scan_page_count']}, "
            f"raster-pages={document['pages_with_embedded_raster_references']}, "
            f"chunk-methods={document['chunk_methods']}"
        )
    print(f"Raw output (Git-ignored): {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
