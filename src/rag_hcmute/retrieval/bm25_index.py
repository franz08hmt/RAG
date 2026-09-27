from __future__ import annotations

import re
import time
from dataclasses import dataclass
from pathlib import Path

from rank_bm25 import BM25Okapi

from rag_hcmute.ingestion.chunk import Chunk
from rag_hcmute.retrieval.common import RetrievalHit, hit_from_chunk, load_chunks

TOKEN_PATTERN = re.compile(r"\w+", re.UNICODE)
BM25_LIBRARY = "rank_bm25.BM25Okapi"


def bm25_tokenize(text: str) -> list[str]:
    return [t.lower() for t in TOKEN_PATTERN.findall(text)]


@dataclass
class BM25QueryResult:
    hits: list[RetrievalHit]
    latency_ms: float


class BM25Retriever:
    method_name = "bm25"

    def __init__(self, chunks: list[Chunk]):
        if not chunks:
            raise ValueError("Khong the xay dung BM25 index tu danh sach chunk rong.")
        self.chunks = chunks
        self._corpus_tokens = [bm25_tokenize(c.text) for c in chunks]
        self._bm25 = BM25Okapi(self._corpus_tokens)

    @classmethod
    def from_snapshot(cls, chunks_path: Path) -> "BM25Retriever":
        return cls(load_chunks(chunks_path))

    def query(self, query_text: str, top_k: int = 5) -> BM25QueryResult:
        start = time.perf_counter()
        query_tokens = bm25_tokenize(query_text)
        scores = self._bm25.get_scores(query_tokens)
        ranked_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
        hits = [
            hit_from_chunk(rank + 1, self.chunks[idx], float(scores[idx]))
            for rank, idx in enumerate(ranked_indices)
        ]
        latency_ms = (time.perf_counter() - start) * 1000
        return BM25QueryResult(hits=hits, latency_ms=latency_ms)
