import csv
import hashlib
import json

from rag_hcmute.evaluation.evidence_spans import (
    EvidenceSpan,
    evaluate_exact_evidence_retrieval,
    load_exact_evidence_spans,
    locate_excerpt_on_page,
    map_spans_to_chunks,
)
from rag_hcmute.evaluation.run_pilot import PilotQuestion
from rag_hcmute.ingestion.chunk import Chunk
from rag_hcmute.ingestion.extract import PageText
from rag_hcmute.retrieval.common import RetrievalHit


def _chunk(
    chunk_id: str,
    *,
    document_id: str,
    token_start: int,
    token_end: int,
) -> Chunk:
    return Chunk(
        chunk_id=chunk_id,
        document_id=document_id,
        document_title="Test document",
        pdf_page_start=1,
        pdf_page_end=1,
        printed_page_start=None,
        printed_page_end=None,
        section_path=None,
        text="test content",
        token_count=token_end - token_start,
        text_sha256="test",
        chunk_method="test",
        token_start=token_start,
        token_end=token_end,
    )


def _span(question_id: str, span_id: str, document_id: str, start: int, end: int) -> EvidenceSpan:
    return EvidenceSpan(
        question_id=question_id,
        span_id=span_id,
        document_id=document_id,
        pdf_page=1,
        token_start=start,
        token_end=end,
        normalized_anchor_sha256="test",
    )


def _hit(rank: int, chunk: Chunk) -> RetrievalHit:
    return RetrievalHit(
        rank=rank,
        chunk_id=chunk.chunk_id,
        document_id=chunk.document_id,
        document_title=chunk.document_title,
        pdf_page_start=chunk.pdf_page_start,
        pdf_page_end=chunk.pdf_page_end,
        section_path=chunk.section_path,
        score=1.0,
        text_preview="metadata-only test",
    )


def test_excerpt_location_returns_whitespace_token_offsets() -> None:
    page = "Điều 5.\nSinh viên được rút bớt học phần."

    assert locate_excerpt_on_page(page, "Sinh viên được rút bớt học phần") == [(2, 9)]


def test_annotation_loader_resolves_offsets_without_emitting_excerpt(tmp_path) -> None:
    questions_path = tmp_path / "questions.csv"
    annotations_path = tmp_path / "annotations.json"
    with questions_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=(
                "question_id",
                "answerability",
                "expected_document",
                "expected_chunk_id",
                "evidence_text",
            ),
        )
        writer.writeheader()
        writer.writerow(
            {
                "question_id": "Q1",
                "answerability": "answerable",
                "expected_document": "DOC",
                "expected_chunk_id": "GOLD",
                "evidence_text": "Heading ... Evidence phrase exactly.",
            }
        )
    annotations_path.write_text(
        json.dumps(
            {
                "annotation_version": 2,
                "snapshot_id": "SNAP",
                "offset_unit": "page-local whitespace tokens",
                "questions": {
                    "Q1": {
                        "document_id": "DOC",
                        "spans": [
                            {
                                "span_id": "Q1-S1",
                                "pdf_page": 1,
                                "page_token_start": 2,
                                "page_token_end": 5,
                                "label": "test clause",
                                "normalized_anchor_sha256": hashlib.sha256(
                                    b"evidence phrase exactly"
                                ).hexdigest(),
                            }
                        ],
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    page_text = "Front matter. Evidence phrase exactly."
    pages = {
        "DOC": [
            PageText(
                document_id="DOC",
                pdf_page=1,
                text=page_text,
                char_count=len(page_text),
                is_probable_scan=False,
                printed_page=None,
                printed_page_confidence="unknown",
            )
        ]
    }

    spans, metadata = load_exact_evidence_spans(
        questions_path=questions_path,
        annotations_path=annotations_path,
        pages_by_document=pages,
        snapshot_id="SNAP",
    )

    span = spans["Q1"][0]
    assert (span.token_start, span.token_end, span.pdf_page) == (2, 5, 1)
    assert metadata["evidence_span_count"] == 1
    assert "Evidence phrase exactly" not in json.dumps(metadata)


def test_span_maps_only_to_chunks_that_fully_contain_its_offsets() -> None:
    span = _span("Q1", "Q1-S1", "DOC", 12, 18)
    chunks = [
        _chunk("partial-left", document_id="DOC", token_start=10, token_end=16),
        _chunk("full", document_id="DOC", token_start=10, token_end=20),
        _chunk("partial-right", document_id="DOC", token_start=16, token_end=20),
    ]

    assert map_spans_to_chunks({"Q1": [span]}, chunks) == {"Q1-S1": frozenset({"full"})}


def test_exact_evidence_metrics_require_every_span_for_complete_hit() -> None:
    q1 = PilotQuestion("Q1", "question one", "test", "answerable", "DOC1", "", "1")
    q2 = PilotQuestion("Q2", "question two", "test", "answerable", "DOC2", "", "1")
    spans = {
        "Q1": [_span("Q1", "Q1-S1", "DOC1", 2, 5), _span("Q1", "Q1-S2", "DOC1", 7, 9)],
        "Q2": [_span("Q2", "Q2-S1", "DOC2", 4, 7)],
    }
    chunks = [
        _chunk("q1-first", document_id="DOC1", token_start=0, token_end=6),
        _chunk("q1-second", document_id="DOC1", token_start=6, token_end=10),
        _chunk("q2-only", document_id="DOC2", token_start=0, token_end=10),
    ]

    class FakeRetriever:
        def query(self, query: str, top_k: int):
            hits = [chunks[0], chunks[1]] if query == "question one" else [chunks[2]]
            return type("QueryResult", (), {"hits": [_hit(i + 1, chunk) for i, chunk in enumerate(hits[:top_k])]})()

    result = evaluate_exact_evidence_retrieval(
        questions=[q1, q2],
        spans_by_question=spans,
        chunks=chunks,
        retriever=FakeRetriever(),
        top_k=3,
        hit_k=2,
    )

    assert result["evidence_span_recall_at_k"] == {"value": 1.0, "hits": 3, "denominator": 3}
    assert result["complete_evidence_hit_at_k"] == {"value": 1.0, "hits": 2, "denominator": 2}


def test_missing_evidence_span_chunk_fails_closed() -> None:
    span = _span("Q1", "Q1-S1", "DOC", 12, 18)

    try:
        map_spans_to_chunks({"Q1": [span]}, [_chunk("short", document_id="DOC", token_start=10, token_end=15)])
    except ValueError as error:
        assert "no chunk fully contains" in str(error)
    else:
        raise AssertionError("A span split across all candidate chunks must not count as exact evidence.")
