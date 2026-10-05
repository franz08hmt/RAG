from __future__ import annotations

import hashlib
from dataclasses import replace
from pathlib import Path

from rag_hcmute.ingestion.chunk import Chunk
from rag_hcmute.retrieval.common import RetrievalHit, load_chunks


def build_matched_table_variants(project_root: Path) -> dict[str, list[Chunk]]:
    """Preserve the same corpus background while replacing only Table 5's representation."""
    variants_root = (
        project_root
        / "artifacts/results/table_variants/HCMUTE_QCDT_1727_2021_p020_t02"
    )
    baseline = load_chunks(
        project_root / "data/processed/g0_reproduction/chunks/chunks.jsonl"
    )
    t1_chunks = load_chunks(variants_root / "t1_markdown.jsonl")
    t2_chunks = load_chunks(variants_root / "t2_row_context.jsonl")

    target_chunk_id = "HCMUTE_QCDT_1727_2021__c0031"
    table_marker = "Bảng 5: Xếp hạng năm đào tạo sinh viên"
    target_positions = [
        index
        for index, chunk in enumerate(baseline)
        if chunk.chunk_id == target_chunk_id and table_marker in chunk.text
    ]
    if len(target_positions) != 1 or len(t1_chunks) != 1 or len(t2_chunks) != 5:
        raise ValueError(
            "Expected one B0 table chunk, one T1 chunk, and five T2 row chunks."
        )

    target_index = target_positions[0]
    source_chunk = baseline[target_index]
    context_text, table_text = source_chunk.text.split(table_marker, maxsplit=1)
    expected_rows = (
        ("Năm thứ nhất", "< 36"),
        ("Năm thứ hai", "36 – 71"),
        ("Năm thứ ba", "72 – 107"),
        ("Năm thứ tư", "108 – 149"),
        ("Năm thứ năm", "> 149"),
    )
    if not context_text.strip() or not all(
        year in table_text and value in table_text for year, value in expected_rows
    ):
        raise ValueError(
            "Cannot split B0 table chunk without losing surrounding or table content."
        )

    residual_text = context_text.rstrip()
    residual_tokens = len(residual_text.split())
    residual_chunk = replace(
        source_chunk,
        chunk_id=f"{target_chunk_id}__context_without_table05",
        text=residual_text,
        token_count=residual_tokens,
        text_sha256=hashlib.sha256(residual_text.encode("utf-8")).hexdigest(),
        chunk_method="table_ablation_context_remainder",
        token_end=(source_chunk.token_start + residual_tokens)
        if source_chunk.token_start is not None
        else None,
    )
    before = baseline[:target_index]
    after = baseline[target_index + 1 :]
    return {
        "B0": baseline,
        "T1": before + [residual_chunk, *t1_chunks] + after,
        "T2": before + [residual_chunk, *t2_chunks] + after,
    }


def evaluate_required_evidence(
    hits: list[RetrievalHit], expected_chunk_ids: list[str], top_k: int
) -> dict:
    ranks = {
        hit.chunk_id: hit.rank for hit in hits if hit.rank <= top_k
    }
    required_ranks = {
        chunk_id: ranks[chunk_id]
        for chunk_id in expected_chunk_ids
        if chunk_id in ranks
    }
    covered_count = len(required_ranks)
    required_count = len(expected_chunk_ids)
    first_rank = min(required_ranks.values()) if required_ranks else None
    return {
        "expected_chunk_ids": expected_chunk_ids,
        "expected_chunk_ranks": required_ranks,
        "required_evidence_units": required_count,
        "retrieved_evidence_units": covered_count,
        "evidence_coverage_at_k": covered_count / required_count,
        "complete_evidence_retrieved_at_k": covered_count == required_count,
        "first_required_evidence_rank": first_rank,
    }


def summarize_evidence_metrics(per_question: list[dict]) -> dict:
    if not per_question:
        raise ValueError("At least one question is required to summarize metrics.")
    question_count = len(per_question)
    complete_hits = sum(
        bool(result["complete_evidence_retrieved_at_k"])
        for result in per_question
    )
    mean_coverage = sum(
        result["evidence_coverage_at_k"] for result in per_question
    ) / question_count
    reciprocal_ranks = [
        1 / result["first_required_evidence_rank"]
        if result["first_required_evidence_rank"] is not None
        else 0.0
        for result in per_question
    ]
    return {
        "complete_evidence_hit_at_5": {
            "value": complete_hits / question_count,
            "hits": complete_hits,
            "denominator": question_count,
        },
        "mean_evidence_unit_coverage_at_5": {
            "value": mean_coverage,
            "denominator": question_count,
        },
        "mrr_first_required_evidence_at_5": {
            "value": sum(reciprocal_ranks) / question_count,
            "denominator": question_count,
        },
    }
