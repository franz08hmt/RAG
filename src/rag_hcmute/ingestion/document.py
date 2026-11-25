"""Versioned document metadata and backwards-compatible chunk provenance views."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from rag_hcmute.ingestion.chunk import Chunk
from rag_hcmute.ingestion.extract import PageText


@dataclass(frozen=True)
class Document:
    document_id: str
    title: str
    number: str
    source_url: str
    sha256: str
    page_count: int
    extraction_method: str
    pages: tuple[PageText, ...]

    @classmethod
    def from_manifest(cls, row: dict, pages: list[PageText]) -> Document:
        ordered = tuple(sorted(pages, key=lambda page: page.pdf_page))
        if any(page.document_id != row['document_id'] for page in ordered):
            raise ValueError('Page belongs to a different document')
        if len(ordered) != int(row['page_count']) or len({p.pdf_page for p in ordered}) != len(ordered):
            raise ValueError('Page count or page numbers do not match the manifest')
        methods = sorted({page.extraction_method for page in ordered})
        return cls(row['document_id'], row['document_title'], row.get('document_number', ''),
                   row['source_url'], row['file_sha256'], len(ordered), ', '.join(methods), ordered)


@dataclass(frozen=True)
class ChunkProvenance:
    chunk_id: str
    document_id: str
    char_start: int
    char_end: int
    pdf_page_start: int
    pdf_page_end: int
    printed_page_start: int | None
    printed_page_end: int | None
    section_path: str | None
    previous_chunk_id: str | None
    next_chunk_id: str | None
    token_counts: dict[str, int]
    coordinate_system: str = 'document_text_whitespace_normalized'


def chunk_provenance(document: Document, chunks: list[Chunk],
                     tokenizers: dict[str, Callable[[str], int]] | None = None) -> list[ChunkProvenance]:
    """Build a separate view; offsets refer to cleaned pages joined by single spaces."""
    words = [word for page in document.pages for word in page.text.split()]
    starts, ends, pos = [], [], 0
    for word in words:
        starts.append(pos)
        pos += len(word)
        ends.append(pos)
        pos += 1
    result = []
    for i, chunk in enumerate(chunks):
        if chunk.document_id != document.document_id:
            raise ValueError('Chunk belongs to a different document')
        start, end = chunk.token_start, chunk.token_end
        if start is None or end is None or not 0 <= start < end <= len(words):
            raise ValueError('Chunk requires valid document token offsets')
        if ' '.join(words[start:end]) != chunk.text:
            raise ValueError('Chunk text does not match its offsets')
        counts = {'whitespace_split_v1': len(words[start:end])}
        counts.update({name: fn(chunk.text) for name, fn in (tokenizers or {}).items()})
        result.append(ChunkProvenance(chunk.chunk_id, chunk.document_id, starts[start], ends[end-1],
            chunk.pdf_page_start, chunk.pdf_page_end, chunk.printed_page_start, chunk.printed_page_end,
            chunk.section_path, chunks[i-1].chunk_id if i else None,
            chunks[i+1].chunk_id if i+1 < len(chunks) else None, counts))
    return result
