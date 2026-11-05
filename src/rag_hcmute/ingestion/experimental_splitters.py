"""Six source-aligned splitter policies for development ablations.

All policies retain whitespace-source intervals, use the same subword ceiling,
and have zero overlap in the initial controlled experiment. Character windows
round down to complete whitespace units. Sentence boundaries are a punctuation
heuristic, not a trained Vietnamese sentence segmenter. Semantic boundaries are
supplied from adjacent sentence embeddings, never from gold annotations.
"""
from __future__ import annotations

import re
from collections.abc import Callable

from rag_hcmute.ingestion.chunk import _build_token_stream, _slice_chunk
from rag_hcmute.ingestion.sectioning import find_section_markers

STRATEGIES = ("characters", "tokens", "recursive", "sentences", "structure", "semantic")


def boundary_levels(pages):
    """Document-wide word offsets for paragraphs/pages, lines and sentences."""
    paragraphs, lines, sentences = set(), set(), set()
    cursor = 0
    for page in sorted(pages, key=lambda p: p.pdf_page):
        for line in page.text.splitlines():
            if not line.strip():
                paragraphs.add(cursor)
            for word in line.split():
                cursor += 1
                if re.search(r'[.!?…][”"\)\]]*$', word) and not re.fullmatch(r'\d+\.', word):
                    sentences.add(cursor)
            lines.add(cursor)
        paragraphs.add(cursor)
        sentences.add(cursor)
    return [sorted(b for b in level if b > 0) for level in (paragraphs, lines, sentences)]


def fitted_end(words, start, stop, count_tokens: Callable[[str], int], budget: int):
    """Find a valid whole-word prefix without relying on monotonic token counts.

    Initial 400-word cap bounds tokenizer work. No claim of globally maximal
    subword packing is made; the exact accepted string is always checked.
    """
    end = min(stop, start + 400)
    while end > start and count_tokens(" ".join(words[start:end])) > budget:
        end -= 1
    if end == start:
        raise ValueError("A single source unit exceeds the tokenizer budget.")
    return end


def split_document(pages, document_id, document_title, *, strategy, count_tokens,
                   token_budget=384, character_budget=1200, semantic_boundaries=None):
    if strategy not in STRATEGIES or token_budget < 1 or character_budget < 1:
        raise ValueError("Unknown strategy or invalid budget.")
    pages = sorted(pages, key=lambda p: p.pdf_page)
    stream = _build_token_stream(pages)
    words = stream.tokens
    if not words:
        return []
    paragraphs, lines, sentences = boundary_levels(pages)
    markers = find_section_markers(pages, lambda text: text.split())
    sections = sorted({m.token_offset for m in markers if m.dieu_label is not None} | {len(words)})
    if strategy == "semantic":
        if semantic_boundaries is None:
            raise ValueError("Semantic boundaries must be computed from source embeddings.")
        if any(not isinstance(b, int) or b <= 0 or b > len(words) for b in semantic_boundaries):
            raise ValueError("Invalid semantic boundary.")
    chunks, start = [], 0
    while start < len(words):
        stop = len(words)
        if strategy in {"structure", "semantic"}:
            cuts = sections if strategy == "structure" else sorted(set(semantic_boundaries) | {len(words)})
            stop = next(b for b in cuts if b > start)
        end = fitted_end(words, start, stop, count_tokens, token_budget)
        if strategy == "characters":
            while end > start and len(" ".join(words[start:end])) > character_budget:
                end -= 1
            if end == start:
                raise ValueError("A source unit exceeds the character budget.")
        elif strategy in {"sentences", "recursive"}:
            levels = [sentences] if strategy == "sentences" else [paragraphs, lines, sentences]
            for level in levels:
                usable = [b for b in level if start < b <= end]
                if usable:
                    end = max(usable)
                    break
        # Shorter strings can tokenize differently: validate again, no truncation.
        end = fitted_end(words, start, end, count_tokens, token_budget)
        section = None
        if strategy == "structure":
            prior = [m for m in markers if m.dieu_label is not None and m.token_offset <= start]
            section = prior[-1].section_path if prior else None
        chunk = _slice_chunk(document_id, document_title, stream, start, end, len(chunks),
                             section, f"experimental_{strategy}")
        chunk.chunk_id = f"{document_id}__{strategy}_{len(chunks):04d}"
        chunks.append(chunk)
        start = end
    return chunks


def semantic_units(pages, count_tokens, token_budget=384):
    """Punctuation-based units, splitting overlong sentences before embedding."""
    words = [w for page in sorted(pages, key=lambda p: p.pdf_page) for w in page.text.split()]
    stops = boundary_levels(pages)[2]
    units, start = [], 0
    for stop in stops:
        while start < stop:
            end = fitted_end(words, start, stop, count_tokens, token_budget)
            units.append((start, end, " ".join(words[start:end])))
            start = end
    return units
