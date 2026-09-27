from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass

from rag_hcmute.ingestion.extract import PageText
from rag_hcmute.ingestion.sectioning import find_section_markers, is_document_structured

DEFAULT_CHUNK_TOKENS = 500
DEFAULT_OVERLAP_TOKENS = 80
MIN_TRAILING_CHUNK_TOKENS = 60


def tokenize(text: str) -> list[str]:
    return text.split()


@dataclass
class Chunk:
    chunk_id: str
    document_id: str
    document_title: str
    pdf_page_start: int
    pdf_page_end: int
    printed_page_start: int | None
    printed_page_end: int | None
    section_path: str | None
    text: str
    token_count: int
    text_sha256: str
    chunk_method: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class _TokenStream:
    tokens: list[str]
    token_pdf_page: list[int]
    token_printed_page: list[int | None]


def _build_token_stream(pages: list[PageText]) -> _TokenStream:
    tokens: list[str] = []
    token_pdf_page: list[int] = []
    token_printed_page: list[int | None] = []
    for page in pages:
        page_tokens = tokenize(page.text)
        tokens.extend(page_tokens)
        token_pdf_page.extend([page.pdf_page] * len(page_tokens))
        token_printed_page.extend([page.printed_page] * len(page_tokens))
    return _TokenStream(tokens=tokens, token_pdf_page=token_pdf_page, token_printed_page=token_printed_page)


def _make_chunk_id(document_id: str, index: int) -> str:
    return f"{document_id}__c{index:04d}"


def _slice_chunk(
    document_id: str,
    document_title: str,
    stream: _TokenStream,
    start: int,
    end: int,
    index: int,
    section_path: str | None,
    chunk_method: str,
) -> Chunk:
    token_slice = stream.tokens[start:end]
    text = " ".join(token_slice)
    pages_in_range = stream.token_pdf_page[start:end]
    printed_in_range = [p for p in stream.token_printed_page[start:end] if p is not None]

    return Chunk(
        chunk_id=_make_chunk_id(document_id, index),
        document_id=document_id,
        document_title=document_title,
        pdf_page_start=min(pages_in_range),
        pdf_page_end=max(pages_in_range),
        printed_page_start=min(printed_in_range) if printed_in_range else None,
        printed_page_end=max(printed_in_range) if printed_in_range else None,
        section_path=section_path,
        text=text,
        token_count=len(token_slice),
        text_sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(),
        chunk_method=chunk_method,
    )


def _sliding_windows(total_tokens: int, chunk_tokens: int, overlap_tokens: int) -> list[tuple[int, int]]:
    if total_tokens <= chunk_tokens:
        return [(0, total_tokens)]

    stride = chunk_tokens - overlap_tokens
    windows: list[list[int]] = []
    start = 0
    while True:
        end = min(start + chunk_tokens, total_tokens)
        windows.append([start, end])
        if end >= total_tokens:
            break
        start += stride

    if len(windows) >= 2 and (windows[-1][1] - windows[-1][0]) < MIN_TRAILING_CHUNK_TOKENS:
        windows[-2][1] = windows[-1][1]
        windows.pop()

    return [(w[0], w[1]) for w in windows]


def chunk_document(
    pages: list[PageText],
    document_id: str,
    document_title: str,
    chunk_tokens: int = DEFAULT_CHUNK_TOKENS,
    overlap_tokens: int = DEFAULT_OVERLAP_TOKENS,
) -> list[Chunk]:
    stream = _build_token_stream(pages)
    if not stream.tokens:
        return []

    markers = find_section_markers(pages, tokenize)
    structured = is_document_structured(markers)

    chunks: list[Chunk] = []
    index = 0

    if not structured:
        windows = _sliding_windows(len(stream.tokens), chunk_tokens, overlap_tokens)
        for start, end in windows:
            chunks.append(
                _slice_chunk(
                    document_id, document_title, stream, start, end, index,
                    section_path=None, chunk_method="sliding_window_fallback",
                )
            )
            index += 1
        return chunks

    dieu_markers = [m for m in markers if m.dieu_label is not None]
    boundaries = [m.token_offset for m in dieu_markers] + [len(stream.tokens)]

    if boundaries[0] > 0:
        # Preamble before the first Điều (e.g. "Căn cứ...", phần mở đầu quyết định).
        for start, end in _sliding_windows(boundaries[0], chunk_tokens, overlap_tokens):
            chunks.append(
                _slice_chunk(
                    document_id, document_title, stream, start, end, index,
                    section_path=None, chunk_method="preamble_sliding_window",
                )
            )
            index += 1

    for marker, next_offset in zip(dieu_markers, boundaries[1:]):
        block_start = marker.token_offset
        block_end = next_offset
        if block_end <= block_start:
            continue
        block_len = block_end - block_start
        section_path = marker.section_path

        if block_len <= chunk_tokens + MIN_TRAILING_CHUNK_TOKENS:
            chunks.append(
                _slice_chunk(
                    document_id, document_title, stream, block_start, block_end, index,
                    section_path=section_path, chunk_method="dieu_bounded_single",
                )
            )
            index += 1
        else:
            for start, end in _sliding_windows(block_len, chunk_tokens, overlap_tokens):
                chunks.append(
                    _slice_chunk(
                        document_id, document_title, stream,
                        block_start + start, block_start + end, index,
                        section_path=section_path, chunk_method="dieu_bounded_sliding",
                    )
                )
                index += 1

    return chunks
