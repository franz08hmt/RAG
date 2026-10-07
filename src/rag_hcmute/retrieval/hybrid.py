from __future__ import annotations

import time
from dataclasses import dataclass, replace

from rag_hcmute.retrieval.common import RetrievalHit


@dataclass
class HybridQueryResult:
    hits: list[RetrievalHit]
    latency_ms: float


class ReciprocalRankFusionRetriever:
    """Fuse lexical and dense result lists without mixing their raw scores."""

    method_name = "hybrid_rrf"

    def __init__(
        self,
        lexical_retriever,
        dense_retriever,
        *,
        rank_constant: int = 60,
        candidate_k: int = 20,
    ) -> None:
        if rank_constant < 0:
            raise ValueError("rank_constant must be non-negative")
        if candidate_k < 1:
            raise ValueError("candidate_k must be positive")

        lexical_content = {
            chunk.chunk_id: getattr(chunk, "text_sha256", None)
            for chunk in lexical_retriever.chunks
        }
        dense_content = {
            chunk.chunk_id: getattr(chunk, "text_sha256", None)
            for chunk in dense_retriever.chunks
        }
        if lexical_content != dense_content:
            raise ValueError("Lexical and dense retrievers must index the same chunk IDs and content")

        self.lexical_retriever = lexical_retriever
        self.dense_retriever = dense_retriever
        self.rank_constant = rank_constant
        self.candidate_k = candidate_k

    def query(self, query_text: str, top_k: int = 5) -> HybridQueryResult:
        if top_k < 1:
            raise ValueError("top_k must be positive")

        started = time.perf_counter()
        branch_k = max(top_k, self.candidate_k)
        lexical_result = self.lexical_retriever.query(query_text, top_k=branch_k)
        dense_result = self.dense_retriever.query(query_text, top_k=branch_k)

        rrf_scores: dict[str, float] = {}
        hit_by_id: dict[str, RetrievalHit] = {}
        for result in (lexical_result, dense_result):
            for hit in result.hits:
                hit_by_id.setdefault(hit.chunk_id, hit)
                rrf_scores[hit.chunk_id] = rrf_scores.get(hit.chunk_id, 0.0) + (
                    1.0 / (self.rank_constant + hit.rank)
                )

        ranked_ids = sorted(rrf_scores, key=lambda chunk_id: (-rrf_scores[chunk_id], chunk_id))
        hits = [
            replace(hit_by_id[chunk_id], rank=rank, score=rrf_scores[chunk_id])
            for rank, chunk_id in enumerate(ranked_ids[:top_k], start=1)
        ]
        return HybridQueryResult(
            hits=hits,
            latency_ms=(time.perf_counter() - started) * 1000,
        )
