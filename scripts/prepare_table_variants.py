from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_ROOT))

import pymupdf  # noqa: E402

from rag_hcmute.ingestion.manifest import read_manifest, sha256_file  # noqa: E402
from rag_hcmute.ingestion.tables import (  # noqa: E402
    TableProvenance,
    table_as_markdown_chunk,
    table_as_row_chunks,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Tạo sidecar T1/T2 cho một bảng PDF được chọn thủ công; "
            "không thay đổi corpus hoặc pipeline mặc định."
        )
    )
    parser.add_argument("--document-id", required=True)
    parser.add_argument("--pdf-page", required=True, type=int, help="Số trang PDF, bắt đầu từ 1.")
    parser.add_argument(
        "--table-index",
        required=True,
        type=int,
        help="Thứ tự bảng do PyMuPDF tìm thấy trên trang, bắt đầu từ 1.",
    )
    parser.add_argument(
        "--header-row-index",
        required=True,
        type=int,
        help="Hàng tiêu đề đã kiểm tra trực quan; hiện chỉ hỗ trợ hàng đầu tiên (1).",
    )
    parser.add_argument("--title", required=True, help="Tiêu đề bảng đã đối chiếu với PDF.")
    parser.add_argument(
        "--manifest",
        type=Path,
        default=PROJECT_ROOT / "data/manifests/corpus_manifest.csv",
    )
    parser.add_argument("--project-root", type=Path, default=PROJECT_ROOT)
    parser.add_argument(
        "--output-root",
        type=Path,
        default=PROJECT_ROOT / "artifacts/results/table_variants",
        help="Đầu ra bắt buộc nằm trong artifacts/results (Git-ignored).",
    )
    return parser


def _project_path(path: Path, project_root: Path) -> Path:
    return (path if path.is_absolute() else project_root / path).resolve()


def _find_source_document(manifest_path: Path, project_root: Path, document_id: str) -> dict[str, str]:
    _, rows = read_manifest(manifest_path)
    matching = [row for row in rows if row.get("document_id") == document_id]
    if len(matching) != 1:
        raise ValueError(f"Expected one manifest row for document_id={document_id}; found {len(matching)}.")

    row = matching[0]
    relative_source = Path(row["local_path"])
    source_path = _project_path(relative_source, project_root)
    if not source_path.is_relative_to(project_root):
        raise ValueError("The manifest PDF path resolves outside project-root; refusing to read it.")
    if not source_path.is_file():
        raise FileNotFoundError(f"Source PDF is missing: {source_path}")

    expected_hash = (row.get("file_sha256") or "").strip().lower()
    actual_hash = sha256_file(source_path)
    if not expected_hash or actual_hash != expected_hash:
        raise ValueError(
            f"Source SHA-256 mismatch for {document_id}: expected={expected_hash or '(empty)'}, "
            f"actual={actual_hash}. No output was written."
        )
    row["_resolved_pdf_path"] = str(source_path)
    row["_verified_sha256"] = actual_hash
    return row


def _write_jsonl(path: Path, objects: list[dict]) -> None:
    with path.open("x", encoding="utf-8") as stream:
        for item in objects:
            stream.write(json.dumps(item, ensure_ascii=False) + "\n")


def main(argv: list[str] | None = None) -> int:
    print(f"Python executable: {sys.executable}")
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.pdf_page < 1:
        parser.error("--pdf-page must be a positive 1-based page number.")
    if args.table_index < 1:
        parser.error("--table-index must be a positive 1-based index.")
    if not re.fullmatch(r"[A-Za-z0-9_-]+", args.document_id):
        parser.error("--document-id may contain only letters, digits, '_' and '-'.")
    if args.header_row_index != 1:
        parser.error(
            "Only the first extracted row is supported as the header. "
            "Flatten and visually verify multi-row headers before using this prototype."
        )
    if not args.title.strip():
        parser.error("--title must be a non-empty title checked against the PDF.")

    project_root = args.project_root.resolve()
    manifest_path = _project_path(args.manifest, project_root)
    output_root = _project_path(args.output_root, project_root)
    ignored_root = (project_root / "artifacts" / "results").resolve()
    if not output_root.is_relative_to(ignored_root):
        parser.error("--output-root must remain inside artifacts/results to keep extracted text out of Git.")

    try:
        manifest_row = _find_source_document(manifest_path, project_root, args.document_id)
        source_path = Path(manifest_row["_resolved_pdf_path"])
        with pymupdf.open(source_path) as document:
            if args.pdf_page > document.page_count:
                raise ValueError(
                    f"PDF page {args.pdf_page} is out of range; document has {document.page_count} pages."
                )
            page = document.load_page(args.pdf_page - 1)
            found_tables = page.find_tables().tables
            if args.table_index > len(found_tables):
                raise ValueError(
                    f"Table index {args.table_index} is out of range; PyMuPDF found {len(found_tables)} "
                    f"table(s) on PDF page {args.pdf_page}."
                )
            extracted_rows = found_tables[args.table_index - 1].extract()

        if len(extracted_rows) < 2:
            raise ValueError("Selected table must contain a header row and at least one data row.")

        table_id = f"pdf{args.pdf_page:03d}_table{args.table_index:02d}"
        provenance = TableProvenance(
            document_id=args.document_id,
            pdf_page=args.pdf_page,
            table_id=table_id,
            title=args.title.strip(),
        )
        headers, data_rows = extracted_rows[0], extracted_rows[1:]
        document_title = manifest_row["document_title"]
        markdown_chunk = table_as_markdown_chunk(
            provenance, document_title, headers, data_rows
        )
        row_chunks = table_as_row_chunks(provenance, document_title, headers, data_rows)

        output_root.mkdir(parents=True, exist_ok=True)
        run_dir = output_root / f"{args.document_id}_p{args.pdf_page:03d}_t{args.table_index:02d}"
        run_dir.mkdir(exist_ok=False)
        _write_jsonl(run_dir / "t1_markdown.jsonl", [markdown_chunk.to_dict()])
        _write_jsonl(run_dir / "t2_row_context.jsonl", [chunk.to_dict() for chunk in row_chunks])
        selection = {
            "document_id": args.document_id,
            "document_title": document_title,
            "source_sha256": manifest_row["_verified_sha256"],
            "pdf_page": args.pdf_page,
            "table_index_1_based": args.table_index,
            "header_row_index_1_based": args.header_row_index,
            "table_id": table_id,
            "table_title": args.title.strip(),
            "extracted_rows": len(extracted_rows),
            "columns": len(headers),
            "pymupdf_version": pymupdf.pymupdf_version,
            "representations": {
                "T1_markdown_chunk_ids": [markdown_chunk.chunk_id],
                "T2_row_chunk_ids": [chunk.chunk_id for chunk in row_chunks],
            },
        }
        with (run_dir / "selection.json").open("x", encoding="utf-8") as stream:
            json.dump(selection, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
    except (FileNotFoundError, OSError, ValueError, KeyError) as error:
        print(f"Table variant preparation failed: {error}", file=sys.stderr)
        return 1

    print(
        f"Source verified | PDF page={args.pdf_page} | table={args.table_index} | "
        f"shape={len(extracted_rows)}x{len(headers)}"
    )
    print(f"Created: T1=1 chunk, T2={len(row_chunks)} row chunks")
    print(f"Local Git-ignored output: {run_dir.relative_to(project_root)}")
    print("Note: merged cells were not forward-filled; inspect output and source before retrieval evaluation.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
