from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from rag_hcmute.ingestion.chunk import Chunk

TEXT_PREVIEW_CHARS = 220


@dataclass
class RetrievalHit:
    rank: int
    chunk_id: str
    document_id: str
    document_title: str
    pdf_page_start: int
    pdf_page_end: int
    section_path: str | None
    score: float
    text_preview: str

    def to_dict(self) -> dict:
        return asdict(self)


def load_chunks(chunks_path: Path) -> list[Chunk]:
    chunks: list[Chunk] = []
    with chunks_path.open("r", encoding="utf-8") as stream:
        for line in stream:
            line = line.strip()
            if not line:
                continue
            chunks.append(Chunk(**json.loads(line)))
    return chunks


def make_preview(text: str, limit: int = TEXT_PREVIEW_CHARS) -> str:
    # Retrieval logs are committed to a public repo; a truncated preview is enough
    # to sanity-check a hit without redistributing the full source document text.
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[:limit].rsplit(" ", 1)[0] + "…"


def hit_from_chunk(rank: int, chunk: Chunk, score: float) -> RetrievalHit:
    return RetrievalHit(
        rank=rank,
        chunk_id=chunk.chunk_id,
        document_id=chunk.document_id,
        document_title=chunk.document_title,
        pdf_page_start=chunk.pdf_page_start,
        pdf_page_end=chunk.pdf_page_end,
        section_path=chunk.section_path,
        score=score,
        text_preview=make_preview(chunk.text),
    )
