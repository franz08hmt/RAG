from types import SimpleNamespace

from rag_hcmute.evaluation.evidence_spans import EvidenceSpan
from rag_hcmute.evaluation.run_pilot import PilotQuestion
from rag_hcmute.ingestion.chunk import Chunk
from scripts.run_chunk_strategy_ablation import _evidence_metrics_including_uncovered


def test_uncovered_evidence_span_counts_as_miss_in_ablation() -> None:
    chunks = [
        Chunk(
            chunk_id="DOC__c0000",
            document_id="DOC",
            document_title="Synthetic test document",
            pdf_page_start=1,
            pdf_page_end=1,
            printed_page_start=None,
            printed_page_end=None,
            section_path=None,
            text="synthetic fixture only",
            token_count=3,
            text_sha256="unused",
            chunk_method="test",
            token_start=0,
            token_end=3,
        )
    ]
    spans = {
        "Q1": [
            EvidenceSpan("Q1", "S1", "DOC", 1, 0, 2, "hash-1"),
            EvidenceSpan("Q1", "S2", "DOC", 1, 8, 10, "hash-2"),
        ]
    }
    questions = [
        PilotQuestion("Q1", "synthetic question", "test", "answerable", "DOC", "", "1")
    ]

    class StubRetriever:
        def query(self, _question: str, top_k: int):
            assert top_k == 10
            return SimpleNamespace(hits=[SimpleNamespace(rank=1, chunk_id="DOC__c0000")])

    result = _evidence_metrics_including_uncovered(
        questions=questions,
        spans_by_question=spans,
        chunks=chunks,
        retriever=StubRetriever(),
    )

    assert result["evidence_span_coverage"] == {"covered": 1, "denominator": 2, "value": 0.5}
    assert result["evidence_span_recall_at_5"] == {"hits": 1, "denominator": 2, "value": 0.5}
    assert result["complete_evidence_hit_at_5"] == {"hits": 0, "denominator": 1, "value": 0.0}
