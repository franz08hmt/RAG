from __future__ import annotations

import statistics
from collections import Counter
from dataclasses import dataclass

from rag_hcmute.evaluation.metrics import (
    QuestionOutcome,
    first_gold_rank,
    mean_reciprocal_rank,
    recall_at_k,
)
from rag_hcmute.evaluation.run_pilot import PilotQuestion
from rag_hcmute.ingestion.chunk import Chunk


@dataclass(frozen=True)
class GoldLocation:
    """Stable source location derived from verified baseline gold chunks."""

    document_id: str
    section_paths: frozenset[str]
    pdf_pages: frozenset[int]


def derive_gold_locations(
    questions: list[PilotQuestion], baseline_chunks: list[Chunk]
) -> dict[str, GoldLocation]:
    """Translate baseline chunk labels to section/page labels for chunk-size tests.

    Exact chunk IDs are not portable across chunk-size variants. Structured
    documents therefore use the verified section paths from the original gold
    chunks; unstructured documents fall back to the original gold page range.
    This intentionally measures section/page retrieval, not exact evidence-chunk
    retrieval.
    """
    chunks_by_id = {chunk.chunk_id: chunk for chunk in baseline_chunks}
    locations: dict[str, GoldLocation] = {}

    for question in questions:
        if question.answerability != "answerable" or not question.gold_chunk_ids:
            continue

        missing_ids = question.gold_chunk_ids - chunks_by_id.keys()
        if missing_ids:
            raise ValueError(
                f"{question.question_id}: baseline gold chunk(s) not found: {sorted(missing_ids)}"
            )

        gold_chunks = [chunks_by_id[chunk_id] for chunk_id in question.gold_chunk_ids]
        expected_document = question.expected_document.strip()
        if any(chunk.document_id != expected_document for chunk in gold_chunks):
            raise ValueError(f"{question.question_id}: gold chunk document does not match label")

        sections = frozenset(chunk.section_path for chunk in gold_chunks if chunk.section_path)
        pages = frozenset(
            page
            for chunk in gold_chunks
            for page in range(chunk.pdf_page_start, chunk.pdf_page_end + 1)
        )
        locations[question.question_id] = GoldLocation(
            document_id=expected_document,
            section_paths=sections,
            pdf_pages=pages,
        )

    return locations


def matching_gold_chunk_ids(chunks: list[Chunk], location: GoldLocation) -> frozenset[str]:
    """Find candidate chunks that overlap a gold section, or gold page fallback."""
    matched: set[str] = set()
    for chunk in chunks:
        if chunk.document_id != location.document_id:
            continue
        if location.section_paths:
            if chunk.section_path in location.section_paths:
                matched.add(chunk.chunk_id)
            continue
        if any(chunk.pdf_page_start <= page <= chunk.pdf_page_end for page in location.pdf_pages):
            matched.add(chunk.chunk_id)
    return frozenset(matched)


def chunk_profile(chunks: list[Chunk]) -> dict[str, dict]:
    """Return content-free per-document chunk statistics."""
    grouped: dict[str, list[Chunk]] = {}
    for chunk in chunks:
        grouped.setdefault(chunk.document_id, []).append(chunk)

    profile: dict[str, dict] = {}
    for document_id, document_chunks in grouped.items():
        sizes = sorted(chunk.token_count for chunk in document_chunks)
        page_spans = sorted(
            chunk.pdf_page_end - chunk.pdf_page_start + 1 for chunk in document_chunks
        )
        p95_index = int(0.95 * (len(page_spans) - 1))
        profile[document_id] = {
            "chunk_count": len(document_chunks),
            "whitespace_token_min": sizes[0],
            "whitespace_token_median": statistics.median(sizes),
            "whitespace_token_max": sizes[-1],
            "page_span_p95": page_spans[p95_index],
            "page_span_max": page_spans[-1],
            "chunks_by_method": dict(Counter(c.chunk_method for c in document_chunks)),
        }
    return profile


def evaluate_location_retrieval(
    *,
    questions: list[PilotQuestion],
    locations: dict[str, GoldLocation],
    chunks: list[Chunk],
    retriever,
    top_k: int = 10,
) -> dict:
    """Evaluate retrieval against stable source locations, without storing text."""
    outcomes: list[QuestionOutcome] = []
    per_question: list[dict] = []

    for question in questions:
        location = locations.get(question.question_id)
        if location is None:
            continue
        gold_ids = matching_gold_chunk_ids(chunks, location)
        if not gold_ids:
            raise ValueError(f"{question.question_id}: no candidate chunk maps to its gold location")

        result = retriever.query(question.question, top_k=top_k)
        rank = first_gold_rank(result.hits, gold_ids)
        outcomes.append(
            QuestionOutcome(
                question_id=question.question_id,
                gold_chunk_ids=gold_ids,
                hit_rank=rank,
            )
        )
        per_question.append(
            {
                "question_id": question.question_id,
                "gold_location_type": "section" if location.section_paths else "page",
                "gold_candidate_chunk_count": len(gold_ids),
                "first_gold_rank_at_10": rank,
                "top_k": top_k,
            }
        )

    hit_at_5, hit_count, denominator = recall_at_k(outcomes, 5)
    mrr_at_10, mrr_denominator = mean_reciprocal_rank(outcomes)
    return {
        "metric_scope": "section_or_page_location_proxy",
        "hit_at_5": {"value": hit_at_5, "hits": hit_count, "denominator": denominator},
        "mrr_at_10": {"value": mrr_at_10, "denominator": mrr_denominator},
        "per_question": per_question,
    }


def serialize_location(location: GoldLocation) -> dict:
    """Serialize a gold location without including source text."""
    return {
        "document_id": location.document_id,
        "section_paths": sorted(location.section_paths),
        "pdf_pages": sorted(location.pdf_pages),
    }
