from __future__ import annotations

from dataclasses import dataclass

from rag_hcmute.retrieval.common import RetrievalHit


@dataclass
class QuestionOutcome:
    question_id: str
    gold_chunk_ids: frozenset[str]
    hit_rank: int | None  # 1-indexed rank of first gold chunk within the considered top-k, None if absent


def first_gold_rank(hits: list[RetrievalHit], gold_chunk_ids: frozenset[str]) -> int | None:
    for hit in hits:
        if hit.chunk_id in gold_chunk_ids:
            return hit.rank
    return None


def recall_at_k(outcomes: list[QuestionOutcome], k: int) -> tuple[float, int, int]:
    eligible = [o for o in outcomes if o.gold_chunk_ids]
    if not eligible:
        return 0.0, 0, 0
    hits = sum(1 for o in eligible if o.hit_rank is not None and o.hit_rank <= k)
    return hits / len(eligible), hits, len(eligible)


def mean_reciprocal_rank(outcomes: list[QuestionOutcome]) -> tuple[float, int]:
    eligible = [o for o in outcomes if o.gold_chunk_ids]
    if not eligible:
        return 0.0, 0
    total = sum((1.0 / o.hit_rank) if o.hit_rank is not None else 0.0 for o in eligible)
    return total / len(eligible), len(eligible)
