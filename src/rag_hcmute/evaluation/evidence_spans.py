from __future__ import annotations

import csv
import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

from rag_hcmute.evaluation.run_pilot import PilotQuestion
from rag_hcmute.ingestion.chunk import Chunk
from rag_hcmute.ingestion.extract import PageText

_WORD_PATTERN = re.compile(r"\w+", re.UNICODE)
_FRAGMENT_SEPARATOR = re.compile(r"(?:\.{3,}|…+)")


@dataclass(frozen=True)
class EvidenceSpan:
    """A source-grounded evidence interval, expressed in document token offsets."""

    question_id: str
    span_id: str
    document_id: str
    pdf_page: int
    token_start: int
    token_end: int
    normalized_anchor_sha256: str
    label: str = ""

    @property
    def token_count(self) -> int:
        return self.token_end - self.token_start


def normalized_words(text: str) -> list[str]:
    normalized = unicodedata.normalize("NFC", text).casefold()
    return _WORD_PATTERN.findall(normalized)


def split_evidence_fragments(evidence_text: str) -> list[str]:
    return [
        fragment.strip()
        for fragment in _FRAGMENT_SEPARATOR.split(evidence_text)
        if fragment.strip()
    ]


def _word_positions_in_page(text: str) -> tuple[list[str], list[int]]:
    words: list[str] = []
    whitespace_positions: list[int] = []
    for whitespace_index, token in enumerate(text.split()):
        for word in normalized_words(token):
            words.append(word)
            whitespace_positions.append(whitespace_index)
    return words, whitespace_positions


def _find_word_sequence(haystack: list[str], needle: list[str]) -> list[int]:
    if not needle or len(needle) > len(haystack):
        return []
    width = len(needle)
    return [
        index
        for index in range(len(haystack) - width + 1)
        if haystack[index : index + width] == needle
    ]


def locate_excerpt_on_page(page_text: str, excerpt: str) -> list[tuple[int, int]]:
    """Return unique whitespace-token intervals matching an excerpt on one page."""
    page_words, whitespace_positions = _word_positions_in_page(page_text)
    excerpt_words = normalized_words(excerpt)
    matches = _find_word_sequence(page_words, excerpt_words)
    intervals = {
        (whitespace_positions[index], whitespace_positions[index + len(excerpt_words) - 1] + 1)
        for index in matches
    }
    return sorted(intervals)


def load_exact_evidence_spans(
    *,
    questions_path: Path,
    annotations_path: Path,
    pages_by_document: dict[str, list[PageText]],
    snapshot_id: str,
    question_ids: set[str] | frozenset[str] | None = None,
) -> tuple[dict[str, list[EvidenceSpan]], dict]:
    """Load reviewed page-local offsets and verify them against the local snapshot.

    Only offsets, labels and hashes are emitted; source text is never copied.
    """
    annotation = json.loads(annotations_path.read_text(encoding="utf-8"))
    with questions_path.open("r", encoding="utf-8-sig", newline="") as stream:
        all_rows = {row["question_id"]: row for row in csv.DictReader(stream)}
    if question_ids is None:
        selected_ids = set(all_rows)
    else:
        selected_ids = set(question_ids)
        unknown_selected = selected_ids - set(all_rows)
        if unknown_selected:
            raise ValueError("Selected evaluation IDs are missing from the question set.")
    rows = {question_id: all_rows[question_id] for question_id in selected_ids}
    if annotation.get("snapshot_id") != snapshot_id:
        raise ValueError(
            "Evidence-span annotations target a different corpus snapshot; "
            "review the page offsets before using them."
        )
    answerable_ids = {
        question_id
        for question_id, row in rows.items()
        if row.get("answerability") == "answerable"
        and row.get("expected_chunk_id", "").strip()
    }
    annotation_questions = annotation.get("questions", {})
    if not isinstance(annotation_questions, dict):
        raise ValueError("Evidence annotations must contain a questions object.")
    unknown_annotation_ids = set(annotation_questions) - set(all_rows)
    if unknown_annotation_ids:
        raise ValueError("Evidence annotations reference IDs outside the question set.")
    scoped_annotations = {
        question_id: value
        for question_id, value in annotation_questions.items()
        if question_id in selected_ids
    }
    annotated_ids = set(scoped_annotations)
    if answerable_ids != annotated_ids:
        missing = sorted(answerable_ids - annotated_ids)
        extra = sorted(annotated_ids - answerable_ids)
        raise ValueError(
            f"Evidence annotation coverage mismatch; missing={missing}, extra={extra}."
        )

    resolved: dict[str, list[EvidenceSpan]] = {}
    serialized_spans: list[dict] = []
    all_span_ids: set[str] = set()
    for question_id, question_annotation in scoped_annotations.items():
        row = rows.get(question_id)
        if row is None:
            raise ValueError(f"Evidence annotation references unknown question {question_id}.")
        if row.get("answerability") != "answerable":
            raise ValueError(f"Evidence annotation {question_id} is not labeled answerable.")
        document_id = question_annotation["document_id"]
        if row.get("expected_document") != document_id:
            raise ValueError(f"Evidence annotation document mismatch for {question_id}.")
        pages = pages_by_document.get(document_id)
        if not pages:
            raise ValueError(f"No local extracted pages available for {document_id}.")

        page_token_starts: dict[int, int] = {}
        token_cursor = 0
        pages_by_number = {page.pdf_page: page for page in pages}
        for page in sorted(pages, key=lambda item: item.pdf_page):
            page_token_starts[page.pdf_page] = token_cursor
            token_cursor += len(page.text.split())

        question_spans: list[EvidenceSpan] = []
        for span_annotation in question_annotation["spans"]:
            pdf_page = int(span_annotation["pdf_page"])
            page = pages_by_number.get(pdf_page)
            if page is None:
                raise ValueError(f"{question_id}: source PDF page {pdf_page} is not available.")
            page_tokens = page.text.split()
            page_start = int(span_annotation["page_token_start"])
            page_end = int(span_annotation["page_token_end"])
            if not 0 <= page_start < page_end <= len(page_tokens):
                raise ValueError(
                    f"{question_id}: evidence token interval on PDF page {pdf_page} is invalid."
                )
            words = normalized_words(" ".join(page_tokens[page_start:page_end]))
            anchor_digest = hashlib.sha256(" ".join(words).encode("utf-8")).hexdigest()
            expected_digest = span_annotation["normalized_anchor_sha256"]
            if anchor_digest != expected_digest:
                raise ValueError(
                    f"{question_id}: evidence anchor hash mismatch on PDF page {pdf_page}; "
                    "the source snapshot or annotation may have changed."
                )
            span_id = span_annotation["span_id"]
            if span_id in all_span_ids:
                raise ValueError(f"Duplicate evidence span ID: {span_id}.")
            all_span_ids.add(span_id)
            span = EvidenceSpan(
                question_id=question_id,
                span_id=span_id,
                document_id=document_id,
                pdf_page=pdf_page,
                token_start=page_token_starts[pdf_page] + page_start,
                token_end=page_token_starts[pdf_page] + page_end,
                normalized_anchor_sha256=expected_digest,
                label=span_annotation.get("label", ""),
            )
            question_spans.append(span)
            serialized_spans.append(serialize_evidence_span(span))
        resolved[question_id] = question_spans

    metadata = {
        "annotation_version": annotation["annotation_version"],
        "snapshot_id": snapshot_id,
        "offset_unit": annotation["offset_unit"],
        "selected_question_count": len(selected_ids),
        "annotated_question_count": len(resolved),
        "evidence_span_count": len(serialized_spans),
        "spans": serialized_spans,
    }
    return resolved, metadata


def serialize_evidence_span(span: EvidenceSpan) -> dict:
    return {
        "question_id": span.question_id,
        "span_id": span.span_id,
        "document_id": span.document_id,
        "pdf_page": span.pdf_page,
        "token_start": span.token_start,
        "token_end": span.token_end,
        "token_count": span.token_count,
        "normalized_anchor_sha256": span.normalized_anchor_sha256,
        "label": span.label,
    }


def map_spans_to_chunks(
    spans_by_question: dict[str, list[EvidenceSpan]], chunks: list[Chunk]
) -> dict[str, frozenset[str]]:
    """Map evidence spans to chunks that fully contain the source-token interval."""
    chunk_ids_by_span: dict[str, frozenset[str]] = {}
    all_spans = [span for spans in spans_by_question.values() for span in spans]
    for span in all_spans:
        matches = {
            chunk.chunk_id
            for chunk in chunks
            if chunk.document_id == span.document_id
            and chunk.token_start is not None
            and chunk.token_end is not None
            and chunk.token_start <= span.token_start
            and chunk.token_end >= span.token_end
        }
        if not matches:
            raise ValueError(
                f"{span.span_id}: no chunk fully contains the exact evidence span "
                f"at size/config under evaluation."
            )
        chunk_ids_by_span[span.span_id] = frozenset(matches)
    return chunk_ids_by_span


def evaluate_exact_evidence_retrieval(
    *,
    questions: list[PilotQuestion],
    spans_by_question: dict[str, list[EvidenceSpan]],
    chunks: list[Chunk],
    retriever,
    top_k: int = 10,
    hit_k: int = 5,
) -> dict:
    if top_k < hit_k:
        raise ValueError("top_k must be greater than or equal to hit_k.")
    question_text = {question.question_id: question.question for question in questions}
    chunk_ids_by_span = map_spans_to_chunks(spans_by_question, chunks)
    chunk_by_id = {chunk.chunk_id: chunk for chunk in chunks}
    per_question: list[dict] = []
    total_span_hits_at_k = 0
    total_spans = sum(len(spans) for spans in spans_by_question.values())
    complete_questions_at_k = 0
    first_span_reciprocals: list[float] = []

    for question_id, spans in spans_by_question.items():
        result = retriever.query(question_text[question_id], top_k=top_k)
        span_ranks: dict[str, int | None] = {span.span_id: None for span in spans}
        for hit in result.hits:
            chunk = chunk_by_id[hit.chunk_id]
            for span in spans:
                if chunk.chunk_id in chunk_ids_by_span[span.span_id]:
                    current = span_ranks[span.span_id]
                    span_ranks[span.span_id] = hit.rank if current is None else min(current, hit.rank)

        hits_at_k = sum(
            1 for rank in span_ranks.values() if rank is not None and rank <= hit_k
        )
        total_span_hits_at_k += hits_at_k
        complete = hits_at_k == len(spans)
        complete_questions_at_k += int(complete)
        first_rank = min((rank for rank in span_ranks.values() if rank is not None), default=None)
        first_span_reciprocals.append(
            (1.0 / first_rank) if first_rank is not None and first_rank <= top_k else 0.0
        )
        per_question.append(
            {
                "question_id": question_id,
                "required_span_count": len(spans),
                "span_hits_at_k": hits_at_k,
                "all_required_spans_hit_at_k": complete,
                "span_ranks": span_ranks,
            }
        )

    denominator_questions = len(spans_by_question)
    return {
        "metric_scope": "exact_source_token_span",
        "hit_k": hit_k,
        "top_k": top_k,
        "evidence_span_recall_at_k": {
            "value": total_span_hits_at_k / total_spans if total_spans else 0.0,
            "hits": total_span_hits_at_k,
            "denominator": total_spans,
        },
        "complete_evidence_hit_at_k": {
            "value": complete_questions_at_k / denominator_questions if denominator_questions else 0.0,
            "hits": complete_questions_at_k,
            "denominator": denominator_questions,
        },
        "first_evidence_mrr_at_top_k": {
            "value": sum(first_span_reciprocals) / denominator_questions if denominator_questions else 0.0,
            "denominator": denominator_questions,
        },
        "per_question": per_question,
        "candidate_chunks_per_span": {
            span_id: len(chunk_ids) for span_id, chunk_ids in chunk_ids_by_span.items()
        },
    }
