import pytest

from rag_hcmute.evaluation.run_pilot import PilotQuestion
from scripts.run_hybrid_retrieval_ablation import (
    _candidate_coverage_summary,
    _classify_question_evidence,
    _question_diagnostics,
)


@pytest.mark.parametrize(
    ("span_ranks", "expected"),
    [
        ({"S1": 1, "S2": 5}, "all_required_spans_in_top_5"),
        ({"S1": 2, "S2": 8}, "partial_evidence_in_top_5"),
        ({"S1": 6, "S2": None}, "evidence_only_at_ranks_6_to_10"),
        ({"S1": None, "S2": None}, "no_exact_evidence_in_top_10"),
    ],
)
def test_classifies_evidence_retrieval_by_exact_span_ranks(span_ranks, expected) -> None:
    assert _classify_question_evidence(span_ranks, hit_k=5, top_k=10) == expected


def test_classification_rejects_empty_or_out_of_range_span_ranks() -> None:
    with pytest.raises(ValueError, match="At least one"):
        _classify_question_evidence({}, hit_k=5, top_k=10)
    with pytest.raises(ValueError, match="within the evaluated"):
        _classify_question_evidence({"S1": 11}, hit_k=5, top_k=10)


def test_candidate_coverage_summary_uses_candidate_depth_as_recall_cutoff() -> None:
    summary = _candidate_coverage_summary(
        {
            "top_k": 20,
            "hit_k": 20,
            "evidence_span_recall_at_k": {"value": 0.8, "hits": 8, "denominator": 10},
            "complete_evidence_hit_at_k": {"value": 5 / 7, "hits": 5, "denominator": 7},
        }
    )

    assert summary == {
        "candidate_depth": 20,
        "evidence_span_candidate_recall": {"value": 0.8, "hits": 8, "denominator": 10},
        "complete_evidence_candidate_coverage": {
            "value": 5 / 7,
            "hits": 5,
            "denominator": 7,
        },
    }


def test_candidate_coverage_rejects_mismatched_evaluation_cutoff() -> None:
    with pytest.raises(ValueError, match="hit_k to equal"):
        _candidate_coverage_summary(
            {
                "top_k": 20,
                "hit_k": 5,
                "evidence_span_recall_at_k": {},
                "complete_evidence_hit_at_k": {},
            }
        )


def test_question_diagnostics_only_include_content_free_identifiers_and_ranks() -> None:
    question = PilotQuestion(
        "P001",
        "private synthetic question text",
        "test",
        "answerable",
        "DOC",
        "private synthetic answer",
        "1",
    )
    diagnostics, counts = _question_diagnostics(
        result={
            "hit_k": 5,
            "top_k": 10,
            "per_question": [
                {
                    "question_id": "P001",
                    "required_span_count": 2,
                    "span_ranks": {"S002": 8, "S001": 2},
                }
            ],
        },
        questions=[question],
        document_types={"DOC": "policy"},
    )

    assert diagnostics == [
        {
            "question_id": "P001",
            "document_type": "policy",
            "required_span_count": 2,
            "span_ranks": [
                {"span_id": "S001", "rank": 2},
                {"span_id": "S002", "rank": 8},
            ],
            "evidence_class": "partial_evidence_in_top_5",
        }
    ]
    assert counts == {
        "all_required_spans_in_top_5": 0,
        "partial_evidence_in_top_5": 1,
        "evidence_only_at_ranks_6_to_10": 0,
        "no_exact_evidence_in_top_10": 0,
    }
    serialized = str(diagnostics)
    assert "private synthetic question text" not in serialized
    assert "private synthetic answer" not in serialized
