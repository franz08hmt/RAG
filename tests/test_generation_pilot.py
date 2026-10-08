from __future__ import annotations

import pytest

from rag_hcmute.evaluation.generation_pilot import summarize_generation_pilot


def test_generation_pilot_metrics_distinguish_answer_coverage_and_refusal() -> None:
    summary = summarize_generation_pilot(
        [
            {"answerability": "answerable", "abstained": False, "cited_expected_document": True, "citation_ids_valid": True},
            {"answerability": "answerable", "abstained": True, "cited_expected_document": False, "citation_ids_valid": True},
            {"answerability": "unanswerable", "abstained": True, "cited_expected_document": False, "citation_ids_valid": True},
            {"answerability": "unanswerable", "abstained": False, "cited_expected_document": False, "citation_ids_valid": False},
        ]
    )

    assert summary["answerable_response_rate"] == {"count": 1, "denominator": 2, "value": 0.5}
    assert summary["unanswerable_refusal_rate"] == {"count": 1, "denominator": 2, "value": 0.5}
    assert summary["answerable_citing_expected_document_rate"]["count"] == 1
    assert summary["valid_citation_id_rate"] == {"count": 1, "denominator": 2, "value": 0.5}


def test_generation_pilot_rejects_unknown_answerability_label() -> None:
    with pytest.raises(ValueError, match="answerability"):
        summarize_generation_pilot(
            [{"answerability": "unknown", "abstained": False, "cited_expected_document": False, "citation_ids_valid": True}]
        )
