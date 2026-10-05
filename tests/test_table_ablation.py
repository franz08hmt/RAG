from pathlib import Path

from rag_hcmute.evaluation.table_ablation import (
    build_matched_table_variants,
    evaluate_required_evidence,
    summarize_evidence_metrics,
)
from rag_hcmute.retrieval.common import RetrievalHit


def _hit(rank: int, chunk_id: str) -> RetrievalHit:
    return RetrievalHit(
        rank=rank,
        chunk_id=chunk_id,
        document_id="doc",
        document_title="title",
        pdf_page_start=20,
        pdf_page_end=20,
        section_path=None,
        score=1.0 / rank,
        text_preview="preview",
    )


def test_matched_variants_keep_background_and_replace_only_table() -> None:
    project_root = Path(__file__).resolve().parents[1]
    variants = build_matched_table_variants(project_root)

    assert {name: len(chunks) for name, chunks in variants.items()} == {
        "B0": 156,
        "T1": 157,
        "T2": 161,
    }
    baseline_ids = {chunk.chunk_id for chunk in variants["B0"]}
    target_id = "HCMUTE_QCDT_1727_2021__c0031"
    shared_non_target_ids = baseline_ids - {target_id}
    assert shared_non_target_ids <= {chunk.chunk_id for chunk in variants["T1"]}
    assert shared_non_target_ids <= {chunk.chunk_id for chunk in variants["T2"]}
    assert f"{target_id}__context_without_table05" in {
        chunk.chunk_id for chunk in variants["T1"]
    }
    assert f"{target_id}__context_without_table05" in {
        chunk.chunk_id for chunk in variants["T2"]
    }


def test_complete_evidence_requires_every_required_chunk() -> None:
    result = evaluate_required_evidence(
        [_hit(1, "row002"), _hit(2, "other")],
        ["row002", "row003"],
        top_k=5,
    )

    assert result["retrieved_evidence_units"] == 1
    assert result["evidence_coverage_at_k"] == 0.5
    assert result["complete_evidence_retrieved_at_k"] is False
    assert result["first_required_evidence_rank"] == 1


def test_summary_distinguishes_complete_hit_from_first_evidence_mrr() -> None:
    partial = evaluate_required_evidence([_hit(1, "row002")], ["row002", "row003"], 5)
    complete = evaluate_required_evidence(
        [_hit(1, "row002"), _hit(3, "row003")], ["row002", "row003"], 5
    )
    summary = summarize_evidence_metrics([partial, complete])

    assert summary["complete_evidence_hit_at_5"] == {
        "value": 0.5,
        "hits": 1,
        "denominator": 2,
    }
    assert summary["mrr_first_required_evidence_at_5"]["value"] == 1.0
