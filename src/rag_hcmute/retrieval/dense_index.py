from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from rag_hcmute.ingestion.chunk import Chunk
from rag_hcmute.retrieval.common import RetrievalHit, hit_from_chunk, load_chunks

DEFAULT_MODEL_NAME = "BAAI/bge-m3"
NORMALIZATION = "l2_normalize_embeddings_cosine_via_inner_product"
MAX_SEQ_LENGTH = 1024


class DenseRetrievalUnavailable(RuntimeError):
    """Raised when the dense pipeline cannot run in this environment (deps/model/resources)."""


@dataclass
class DenseQueryResult:
    hits: list[RetrievalHit]
    latency_ms: float


class DenseRetriever:
    method_name = "dense_bge_m3"

    def __init__(self, chunks: list[Chunk], model_name: str = DEFAULT_MODEL_NAME):
        if not chunks:
            raise ValueError("Khong the xay dung dense index tu danh sach chunk rong.")
        self.chunks = chunks
        self.model_name = model_name

        try:
            import faiss  # noqa: F401
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise DenseRetrievalUnavailable(
                f"Thieu thu vien can thiet cho dense retrieval: {exc}. "
                "Can 'pip install sentence-transformers faiss-cpu'."
            ) from exc

        try:
            self._model = SentenceTransformer(model_name)
            # BGE-M3 defaults to max_seq_length=8192 for long-document support; our chunks are
            # capped at ~560 whitespace-tokens by design (see ingestion/chunk.py), so encoding at
            # the full 8192-token budget only wastes CPU. 1024 leaves generous headroom for BPE
            # subword expansion over a 560-whitespace-token chunk without truncating real content.
            self._model.max_seq_length = MAX_SEQ_LENGTH
        except Exception as exc:
            raise DenseRetrievalUnavailable(
                f"Khong tai duoc model '{model_name}' (co the do moi truong khong co quyen "
                f"truy cap huggingface.co hoac khong du tai nguyen): {exc}"
            ) from exc

        import faiss

        try:
            embeddings = self._encode([c.text for c in chunks])
        except Exception as exc:
            raise DenseRetrievalUnavailable(f"Loi khi sinh embedding cho corpus: {exc}") from exc

        self._dim = embeddings.shape[1]
        self._index = faiss.IndexFlatIP(self._dim)
        self._index.add(embeddings)

    def _encode(self, texts: list[str]) -> np.ndarray:
        embeddings = self._model.encode(
            texts,
            normalize_embeddings=True,
            show_progress_bar=False,
            convert_to_numpy=True,
        )
        return np.asarray(embeddings, dtype="float32")

    @classmethod
    def from_snapshot(cls, chunks_path: Path, model_name: str = DEFAULT_MODEL_NAME) -> "DenseRetriever":
        return cls(load_chunks(chunks_path), model_name=model_name)

    def query(self, query_text: str, top_k: int = 5) -> DenseQueryResult:
        start = time.perf_counter()
        query_embedding = self._encode([query_text])
        scores, indices = self._index.search(query_embedding, top_k)
        hits = [
            hit_from_chunk(rank + 1, self.chunks[idx], float(score))
            for rank, (idx, score) in enumerate(zip(indices[0], scores[0]))
            if idx != -1
        ]
        latency_ms = (time.perf_counter() - start) * 1000
        return DenseQueryResult(hits=hits, latency_ms=latency_ms)
