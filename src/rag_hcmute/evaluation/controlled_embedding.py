"""Shared input construction for a length-controlled embedding experiment.

This is an experimental fixed-window policy, not the production section splitter.
Gold questions/answers are deliberately absent from this interface.
"""
from __future__ import annotations

import hashlib
from collections.abc import Callable

from rag_hcmute.ingestion.chunk import Chunk
from rag_hcmute.ingestion.extract import PageText


def shared_budget_chunks(
    pages: list[PageText],
    document_id: str,
    document_title: str,
    token_counters: list[Callable[[str], int]],
    *,
    max_model_tokens: int = 512,
    max_whitespace_tokens: int = 250,
    overlap_whitespace_tokens: int = 40,
) -> list[Chunk]:
    """Use identical complete strings fitting every model, retaining source offsets.

    ``token_counters`` must include each model's passage prefix and special tokens.
    A decreasing search avoids assuming subword token counts are monotonic. If a
    single whitespace unit cannot fit, fail explicitly rather than truncate it.
    """
    if not token_counters or max_model_tokens < 1 or max_whitespace_tokens < 1:
        raise ValueError("Positive budgets and at least one tokenizer are required.")
    if not 0 <= overlap_whitespace_tokens < max_whitespace_tokens:
        raise ValueError("Overlap must be non-negative and smaller than the word cap.")
    words: list[str] = []
    origins: list[PageText] = []
    for page in sorted(pages, key=lambda item: item.pdf_page):
        page_words = page.text.split()
        words.extend(page_words)
        origins.extend([page] * len(page_words))
    chunks = []
    start = 0
    while start < len(words):
        end = min(start + max_whitespace_tokens, len(words))
        while end > start:
            text = " ".join(words[start:end])
            if all(counter(text) <= max_model_tokens for counter in token_counters):
                break
            end -= 1
        if end == start:
            raise ValueError("One source whitespace unit exceeds the shared tokenizer budget.")
        source_pages = origins[start:end]
        printed_pages = [page.printed_page for page in source_pages if page.printed_page is not None]
        chunks.append(Chunk(
            chunk_id=f"{document_id}__shared512_{len(chunks):04d}",
            document_id=document_id, document_title=document_title,
            pdf_page_start=source_pages[0].pdf_page,
            pdf_page_end=source_pages[-1].pdf_page,
            printed_page_start=min(printed_pages) if printed_pages else None,
            printed_page_end=max(printed_pages) if printed_pages else None,
            section_path=None, text=text, token_count=end - start,
            text_sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(),
            chunk_method="experimental_shared_tokenizer_budget",
            extraction_methods=sorted({page.extraction_method for page in source_pages}),
            token_start=start, token_end=end,
        ))
        if end == len(words):
            break
        start = max(start + 1, end - overlap_whitespace_tokens)
    return chunks


def input_signature(chunks: list[Chunk]) -> str:
    """Content and interval signature; changes cannot hide behind stable chunk IDs."""
    canonical = "\n".join(
        f"{chunk.chunk_id}\t{chunk.token_start}\t{chunk.token_end}\t{chunk.text_sha256}"
        for chunk in chunks
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
