from __future__ import annotations

import hashlib
import json
import platform
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import pymupdf

from rag_hcmute.ingestion.chunk import DEFAULT_CHUNK_TOKENS, DEFAULT_OVERLAP_TOKENS, Chunk, chunk_document
from rag_hcmute.ingestion.clean import clean_document_pages
from rag_hcmute.ingestion.extract import extract_pdf_pages, write_pages_jsonl
from rag_hcmute.ingestion.manifest import read_manifest, sha256_file
from rag_hcmute.ingestion.sectioning import find_section_markers, is_document_structured


@dataclass
class DocumentBuildStats:
    document_id: str
    document_title: str
    page_count: int
    probable_scan_pages: list[int]
    printed_page_unresolved_pages: list[int]
    chunk_count: int
    dieu_structured: bool
    dieu_markers_found: int
    boilerplate_lines_removed: int


def _snapshot_id(document_hashes: list[tuple[str, str]], config: dict) -> str:
    payload = json.dumps({"documents": sorted(document_hashes), "config": config}, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def build_snapshot(
    manifest_path: Path,
    project_root: Path,
    pages_output_dir: Path,
    chunks_output_dir: Path,
    snapshot_manifest_path: Path,
    build_log_path: Path,
    chunk_tokens: int = DEFAULT_CHUNK_TOKENS,
    overlap_tokens: int = DEFAULT_OVERLAP_TOKENS,
) -> dict:
    _, rows = read_manifest(manifest_path)

    usable_rows = []
    skipped_rows = []
    for row in rows:
        local_path = (project_root / row["local_path"]).resolve() if row.get("local_path") else None
        if local_path is None or not local_path.is_file():
            skipped_rows.append((row.get("document_id", "?"), "khong_tim_thay_file"))
            continue
        actual_hash = sha256_file(local_path)
        expected_hash = (row.get("file_sha256") or "").strip().lower()
        if expected_hash and actual_hash != expected_hash:
            skipped_rows.append((row.get("document_id", "?"), "sha256_khong_khop"))
            continue
        usable_rows.append((row, local_path, actual_hash))

    config = {
        "chunk_tokens": chunk_tokens,
        "overlap_tokens": overlap_tokens,
        "tokenizer": "whitespace_split_v1",
        "extraction_tool": f"pymupdf=={pymupdf.pymupdf_version}",
    }
    document_hashes = [(row["document_id"], h) for row, _, h in usable_rows]
    snapshot_id = _snapshot_id(document_hashes, config)

    all_chunks: list[Chunk] = []
    doc_stats: list[DocumentBuildStats] = []
    log_lines: list[str] = [
        f"Build snapshot {snapshot_id} at {datetime.now(timezone.utc).isoformat()}",
        f"Python: {sys.version.split()[0]} | Platform: {platform.platform()}",
        f"Config: {config}",
        "",
    ]

    for row, local_path, actual_hash in usable_rows:
        document_id = row["document_id"]
        document_title = row["document_title"]

        pages = extract_pdf_pages(local_path, document_id)
        write_pages_jsonl(pages, pages_output_dir / f"{document_id}.jsonl")

        cleaned_pages, clean_result = clean_document_pages(pages)
        markers = find_section_markers(cleaned_pages, tokenize=lambda t: t.split())
        dieu_markers = [m for m in markers if m.dieu_label is not None]
        structured = is_document_structured(markers)

        chunks = chunk_document(
            cleaned_pages, document_id, document_title,
            chunk_tokens=chunk_tokens, overlap_tokens=overlap_tokens,
        )
        all_chunks.extend(chunks)

        scan_pages = [p.pdf_page for p in pages if p.is_probable_scan]
        unresolved_printed = [p.pdf_page for p in pages if p.printed_page is None]

        stats = DocumentBuildStats(
            document_id=document_id,
            document_title=document_title,
            page_count=len(pages),
            probable_scan_pages=scan_pages,
            printed_page_unresolved_pages=unresolved_printed,
            chunk_count=len(chunks),
            dieu_structured=structured,
            dieu_markers_found=len(dieu_markers),
            boilerplate_lines_removed=len(clean_result.boilerplate_lines_removed),
        )
        doc_stats.append(stats)

        log_lines.append(f"[{document_id}] {document_title}")
        log_lines.append(f"  pages={len(pages)} chunks={len(chunks)} dieu_structured={structured} dieu_markers={len(dieu_markers)}")
        if scan_pages:
            log_lines.append(f"  CANH BAO trang nghi la PDF scan / trich xuat kem: {scan_pages}")
        if unresolved_printed:
            log_lines.append(f"  Khong xac dinh so trang in tren van ban cho cac trang PDF: {unresolved_printed}")
        if clean_result.boilerplate_lines_removed:
            log_lines.append(f"  Da loai {len(clean_result.boilerplate_lines_removed)} dong header/footer lap lai.")
        log_lines.append("")

    for doc_id, reason in skipped_rows:
        log_lines.append(f"[{doc_id}] BO QUA: {reason}")

    chunks_output_dir.mkdir(parents=True, exist_ok=True)
    chunks_file = chunks_output_dir / "chunks.jsonl"
    with chunks_file.open("w", encoding="utf-8") as stream:
        for chunk in all_chunks:
            stream.write(json.dumps(chunk.to_dict(), ensure_ascii=False))
            stream.write("\n")

    snapshot_manifest = {
        "snapshot_id": snapshot_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "config": config,
        "manifest_path": str(manifest_path.relative_to(project_root)),
        "totals": {
            "document_count": len(usable_rows),
            "skipped_document_count": len(skipped_rows),
            "page_count": sum(s.page_count for s in doc_stats),
            "chunk_count": len(all_chunks),
            "probable_scan_page_count": sum(len(s.probable_scan_pages) for s in doc_stats),
        },
        "documents": [
            {
                "document_id": s.document_id,
                "document_title": s.document_title,
                "page_count": s.page_count,
                "chunk_count": s.chunk_count,
                "dieu_structured": s.dieu_structured,
                "dieu_markers_found": s.dieu_markers_found,
                "probable_scan_pages": s.probable_scan_pages,
                "printed_page_unresolved_pages": s.printed_page_unresolved_pages,
                "boilerplate_lines_removed": s.boilerplate_lines_removed,
                "file_sha256": next(h for doc_id, h in document_hashes if doc_id == s.document_id),
            }
            for s in doc_stats
        ],
        "skipped_documents": [{"document_id": doc_id, "reason": reason} for doc_id, reason in skipped_rows],
        "chunks_file": str(chunks_output_dir.relative_to(project_root) / "chunks.jsonl"),
    }

    snapshot_manifest_path.parent.mkdir(parents=True, exist_ok=True)
    snapshot_manifest_path.write_text(
        json.dumps(snapshot_manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    build_log_path.parent.mkdir(parents=True, exist_ok=True)
    build_log_path.write_text("\n".join(log_lines), encoding="utf-8")

    return snapshot_manifest
