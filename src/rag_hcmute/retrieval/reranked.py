from __future__ import annotations

from dataclasses import dataclass

from rag_hcmute.ingestion.chunk import Chunk
from rag_hcmute.retrieval.common import RetrievalHit


@dataclass(frozen=True)
class RerankedQueryResult:
    hits: list[RetrievalHit]
    latency_ms: float
    retrieval_latency_ms: float
    reranker_latency_ms: float
    candidate_count: int
    candidate_depth: int
    pair_count: int
    truncated_pair_count: int


class RerankedRetriever:
    """Apply a local cross-encoder to a fixed-depth candidate list."""

    def __init__(
        self,
        base_retriever,
        reranker,
        chunks: list[Chunk],
        *,
        candidate_depth: int = 20,
    ) -> None:
        if candidate_depth < 1:
            raise ValueError("candidate_depth must be positive.")
        self.base_retriever = base_retriever
        self.reranker = reranker
        self.chunks = chunks
        self.chunks_by_id = {chunk.chunk_id: chunk for chunk in chunks}
        self.candidate_depth = candidate_depth

    def query(self, query: str, *, top_k: int = 5) -> RerankedQueryResult:
        if top_k < 1:
            raise ValueError("top_k must be positive.")
        base_result = self.base_retriever.query(
            query, top_k=max(top_k, self.candidate_depth)
        )
        candidates = base_result.hits
        if not candidates:
            return RerankedQueryResult(
                hits=[],
                latency_ms=base_result.latency_ms,
                retrieval_latency_ms=base_result.latency_ms,
                reranker_latency_ms=0.0,
                candidate_count=0,
                candidate_depth=self.candidate_depth,
                pair_count=0,
                truncated_pair_count=0,
            )

        rerank_result = self.reranker.rerank(
            query=query,
            candidates=candidates,
            chunks_by_id=self.chunks_by_id,
        )
        return RerankedQueryResult(
            hits=rerank_result.hits[:top_k],
            latency_ms=base_result.latency_ms + rerank_result.latency_ms,
            retrieval_latency_ms=base_result.latency_ms,
            reranker_latency_ms=rerank_result.latency_ms,
            candidate_count=len(candidates),
            candidate_depth=self.candidate_depth,
            pair_count=rerank_result.pair_count,
            truncated_pair_count=rerank_result.truncated_pair_count,
        )
