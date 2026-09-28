from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, dataclass
from typing import Sequence

from rag_hcmute.ingestion.chunk import Chunk, tokenize


@dataclass(frozen=True)
class TableProvenance:
    """Source coordinates for one manually reviewed table representation."""

    document_id: str
    pdf_page: int
    table_id: str
    title: str = ""

    def __post_init__(self) -> None:
        if not self.document_id.strip():
            raise ValueError("document_id must not be empty.")
        if self.pdf_page < 1:
            raise ValueError("pdf_page must be a positive 1-based page number.")
        if not re.fullmatch(r"[A-Za-z0-9_-]+", self.table_id):
            raise ValueError("table_id may contain only letters, digits, '_' and '-'.")


@dataclass(frozen=True)
class TableRowRecord:
    chunk_id: str
    document_id: str
    pdf_page: int
    table_id: str
    table_title: str
    row_index: int
    text: str

    def to_dict(self) -> dict[str, str | int]:
        return asdict(self)


def _clean_cell(value: object) -> str:
    if value is None:
        return ""
    return " ".join(str(value).replace("\r", "\n").split())


def _prepare_table(
    headers: Sequence[object], rows: Sequence[Sequence[object]]
) -> tuple[list[str], list[list[str]]]:
    normalized_headers = [_clean_cell(cell) for cell in headers]
    if not normalized_headers or any(not header for header in normalized_headers):
        raise ValueError("Provide a non-empty, explicit label for every table column.")

    normalized_rows: list[list[str]] = []
    for row_index, row in enumerate(rows, start=1):
        if len(row) > len(normalized_headers):
            raise ValueError(
                f"Data row {row_index} has {len(row)} cells but only "
                f"{len(normalized_headers)} headers were supplied."
            )
        cells = [_clean_cell(cell) for cell in row]
        normalized_rows.append(cells + [""] * (len(normalized_headers) - len(cells)))
    return normalized_headers, normalized_rows


def _markdown_cell(value: str) -> str:
    return value.replace("|", r"\|").replace("\n", "<br>")


def table_as_markdown(
    provenance: TableProvenance,
    headers: Sequence[object],
    rows: Sequence[Sequence[object]],
) -> str:
    """Serialize an explicitly reviewed table without inferring merged cells."""
    normalized_headers, normalized_rows = _prepare_table(headers, rows)
    lines = [
        f"Tài liệu: {provenance.document_id}",
        f"Trang PDF: {provenance.pdf_page}",
        f"Mã bảng: {provenance.table_id}",
    ]
    if provenance.title.strip():
        lines.append(f"Tiêu đề bảng: {_clean_cell(provenance.title)}")

    header_line = "| " + " | ".join(_markdown_cell(value) for value in normalized_headers) + " |"
    separator_line = "| " + " | ".join("---" for _ in normalized_headers) + " |"
    lines.extend((header_line, separator_line))
    lines.extend(
        "| " + " | ".join(_markdown_cell(value) for value in row) + " |"
        for row in normalized_rows
    )
    return "\n".join(lines)


def table_as_row_records(
    provenance: TableProvenance,
    headers: Sequence[object],
    rows: Sequence[Sequence[object]],
    *,
    verified_group_context_by_row: dict[int, str] | None = None,
) -> list[TableRowRecord]:
    """Create one traceable record per non-empty data row.

    ``verified_group_context_by_row`` uses 1-based data-row indexes and must only
    contain group labels checked against the original PDF. Blank cells are not
    forward-filled: merged-cell relationships require explicit reviewed context.
    """
    normalized_headers, normalized_rows = _prepare_table(headers, rows)
    group_context = verified_group_context_by_row or {}
    invalid_indexes = sorted(
        index for index in group_context if index < 1 or index > len(normalized_rows)
    )
    if invalid_indexes:
        raise ValueError(f"Group context refers to unknown data row(s): {invalid_indexes}.")

    records: list[TableRowRecord] = []
    for row_index, row in enumerate(normalized_rows, start=1):
        values = [f"{header}: {value}" for header, value in zip(normalized_headers, row) if value]
        if not values:
            continue

        parts = [
            f"Tài liệu: {provenance.document_id}",
            f"Trang PDF: {provenance.pdf_page}",
            f"Bảng: {provenance.title.strip()} ({provenance.table_id})"
            if provenance.title.strip()
            else f"Bảng: {provenance.table_id}",
            f"Hàng dữ liệu: {row_index}",
        ]
        verified_context = _clean_cell(group_context.get(row_index, ""))
        if verified_context:
            parts.append(f"Nhóm hàng đã đối chiếu với PDF: {verified_context}")
        parts.append("Các giá trị: " + "; ".join(values))

        records.append(
            TableRowRecord(
                chunk_id=f"{provenance.document_id}__{provenance.table_id}__row{row_index:03d}",
                document_id=provenance.document_id,
                pdf_page=provenance.pdf_page,
                table_id=provenance.table_id,
                table_title=provenance.title,
                row_index=row_index,
                text="\n".join(parts),
            )
        )
    return records


def _as_chunk(
    provenance: TableProvenance,
    document_title: str,
    chunk_id: str,
    text: str,
    chunk_method: str,
    section_path: str,
) -> Chunk:
    if not document_title.strip():
        raise ValueError("document_title must not be empty.")
    return Chunk(
        chunk_id=chunk_id,
        document_id=provenance.document_id,
        document_title=document_title,
        pdf_page_start=provenance.pdf_page,
        pdf_page_end=provenance.pdf_page,
        printed_page_start=None,
        printed_page_end=None,
        section_path=section_path,
        text=text,
        token_count=len(tokenize(text)),
        text_sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(),
        chunk_method=chunk_method,
    )


def table_as_markdown_chunk(
    provenance: TableProvenance,
    document_title: str,
    headers: Sequence[object],
    rows: Sequence[Sequence[object]],
) -> Chunk:
    """Create one standard RAG chunk containing a reviewed table in Markdown."""
    label = provenance.title.strip() or provenance.table_id
    return _as_chunk(
        provenance=provenance,
        document_title=document_title,
        chunk_id=f"{provenance.document_id}__{provenance.table_id}__markdown",
        text=table_as_markdown(provenance, headers, rows),
        chunk_method="table_markdown",
        section_path=f"Bảng: {label}",
    )


def table_as_row_chunks(
    provenance: TableProvenance,
    document_title: str,
    headers: Sequence[object],
    rows: Sequence[Sequence[object]],
    *,
    verified_group_context_by_row: dict[int, str] | None = None,
) -> list[Chunk]:
    """Convert reviewed row-context records to the existing RAG ``Chunk`` schema."""
    label = provenance.title.strip() or provenance.table_id
    records = table_as_row_records(
        provenance,
        headers,
        rows,
        verified_group_context_by_row=verified_group_context_by_row,
    )
    return [
        _as_chunk(
            provenance=provenance,
            document_title=document_title,
            chunk_id=record.chunk_id,
            text=record.text,
            chunk_method="table_row_context",
            section_path=f"Bảng: {label} > Hàng dữ liệu {record.row_index}",
        )
        for record in records
    ]
