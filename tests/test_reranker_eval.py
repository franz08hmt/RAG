from rag_hcmute.evaluation.reranker import evidence_span_was_truncated, sort_hits_by_scores
from rag_hcmute.retrieval.common import RetrievalHit
from scripts.run_reranker_ablation import _metric_summary


def _hit(chunk_id: str, rank: int) -> RetrievalHit:
    return RetrievalHit(
        rank=rank,
        chunk_id=chunk_id,
        document_id="DOC",
        document_title="Synthetic document",
        pdf_page_start=1,
        pdf_page_end=1,
        section_path=None,
        score=0.0,
        text_preview="synthetic preview",
    )


def test_reranker_scores_sort_descending_and_keep_input_order_for_ties() -> None:
    ranked = sort_hits_by_scores(
        [_hit("C1", 1), _hit("C2", 2), _hit("C3", 3)],
        [0.2, 0.8, 0.8],
    )

    assert [(hit.chunk_id, hit.rank, hit.score) for hit in ranked] == [
        ("C2", 1, 0.8),
        ("C3", 2, 0.8),
        ("C1", 3, 0.2),
    ]


def test_reranker_rejects_invalid_score_or_duplicate_candidate_counts() -> None:
    import pytest

    with pytest.raises(ValueError, match="counts must match"):
        sort_hits_by_scores([_hit("C1", 1)], [])
    with pytest.raises(ValueError, match="unique"):
        sort_hits_by_scores([_hit("C1", 1), _hit("C1", 2)], [0.2, 0.1])


def test_evidence_truncation_checks_span_end_against_retained_passage() -> None:
    assert evidence_span_was_truncated(evidence_char_end=51, retained_passage_char_end=50)
    assert not evidence_span_was_truncated(evidence_char_end=50, retained_passage_char_end=50)


def test_metric_summary_keeps_cutoffs_explicit_instead_of_mislabeling_candidate_recall() -> None:
    summary = _metric_summary(
        {
            "metric_scope": "exact_source_token_span",
            "top_k": 20,
            "hit_k": 20,
            "evidence_span_recall_at_k": {"hits": 10, "denominator": 10, "value": 1.0},
            "complete_evidence_hit_at_k": {"hits": 7, "denominator": 7, "value": 1.0},
            "first_evidence_mrr_at_top_k": {"denominator": 7, "value": 1.0},
            "per_question": [],
        }
    )

    assert summary["top_k"] == summary["hit_k"] == 20
    assert summary["evidence_span_recall"]["hits"] == 10
    assert summary["complete_evidence_hit"]["hits"] == 7
