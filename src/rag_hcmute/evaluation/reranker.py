from __future__ import annotations

import time
from dataclasses import dataclass, replace
from pathlib import Path

from rag_hcmute.ingestion.chunk import Chunk
from rag_hcmute.retrieval.common import RetrievalHit


@dataclass(frozen=True)
class RerankResult:
    hits: list[RetrievalHit]
    latency_ms: float
    pair_count: int
    truncated_pair_count: int
    max_untruncated_pair_tokens: int
    gold_evidence_candidate_count: int
    truncated_gold_evidence_candidate_count: int
    gold_evidence_truncation_by_span: dict[str, tuple[int, int]]


def evidence_span_was_truncated(*, evidence_char_end: int, retained_passage_char_end: int) -> bool:
    """Return whether the end of a source evidence span was cut from the passage input."""
    if evidence_char_end < 0 or retained_passage_char_end < 0:
        raise ValueError("Character offsets must be non-negative.")
    return evidence_char_end > retained_passage_char_end


def sort_hits_by_scores(
    candidates: list[RetrievalHit], scores: list[float]
) -> list[RetrievalHit]:
    """Sort scores descending, preserving incoming rank as a deterministic tie-breaker."""
    if len(candidates) != len(scores):
        raise ValueError("Candidate and score counts must match.")
    if len({candidate.chunk_id for candidate in candidates}) != len(candidates):
        raise ValueError("Candidate chunk IDs must be unique.")
    ranked = sorted(
        zip(candidates, scores),
        key=lambda pair: (-float(pair[1]), pair[0].rank, pair[0].chunk_id),
    )
    return [replace(hit, rank=rank, score=float(score)) for rank, (hit, score) in enumerate(ranked, 1)]


class LocalCrossEncoderReranker:
    """Offline CUDA cross-encoder wrapper with explicit truncation accounting."""

    def __init__(
        self,
        model_path: Path,
        *,
        max_length: int = 512,
        batch_size: int = 4,
    ) -> None:
        if max_length < 8:
            raise ValueError("max_length must be at least 8 tokens.")
        if batch_size < 1:
            raise ValueError("batch_size must be positive.")
        model_path = model_path.resolve()
        if not model_path.is_dir():
            raise FileNotFoundError(f"Local reranker directory does not exist: {model_path}")

        import os

        os.environ["HF_HUB_OFFLINE"] = "1"
        os.environ["TRANSFORMERS_OFFLINE"] = "1"
        os.environ["HF_HUB_DISABLE_IMPLICIT_TOKEN"] = "1"
        os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"

        import torch
        from transformers import AutoModelForSequenceClassification, AutoTokenizer

        if not torch.cuda.is_available():
            raise RuntimeError("Local reranker evaluation requires CUDA in the approved environment.")

        self.torch = torch
        self.device = torch.device("cuda")
        self.max_length = max_length
        self.batch_size = batch_size
        load_started = time.perf_counter()
        self.tokenizer = AutoTokenizer.from_pretrained(
            str(model_path), local_files_only=True
        )
        if not getattr(self.tokenizer, "is_fast", False):
            raise RuntimeError("A fast tokenizer is required to audit passage/evidence truncation.")
        self.model = AutoModelForSequenceClassification.from_pretrained(
            str(model_path), local_files_only=True, dtype=torch.float16
        ).to(self.device)
        self.model.eval()
        torch.cuda.synchronize()
        self.load_seconds = time.perf_counter() - load_started

    def rerank(
        self,
        *,
        query: str,
        candidates: list[RetrievalHit],
        chunks_by_id: dict[str, Chunk],
        evidence_ranges_by_chunk: dict[str, list[tuple[str, int, int]]] | None = None,
    ) -> RerankResult:
        if not candidates:
            raise ValueError("At least one candidate is required for reranking.")
        evidence_ranges_by_chunk = evidence_ranges_by_chunk or {}
        if len({candidate.chunk_id for candidate in candidates}) != len(candidates):
            raise ValueError("Candidate chunk IDs must be unique.")

        passages: list[str] = []
        for candidate in candidates:
            chunk = chunks_by_id.get(candidate.chunk_id)
            if chunk is None:
                raise KeyError(f"Candidate chunk is not available: {candidate.chunk_id}")
            passages.append(chunk.text)

        scores: list[float] = []
        truncated_pairs = 0
        max_raw_length = 0
        evidence_candidate_count = 0
        truncated_evidence_count = 0
        evidence_truncation_by_span: dict[str, list[int]] = {}
        started = time.perf_counter()

        for offset in range(0, len(candidates), self.batch_size):
            batch_hits = candidates[offset : offset + self.batch_size]
            batch_passages = passages[offset : offset + self.batch_size]
            batch_queries = [query] * len(batch_hits)
            raw_lengths = [
                len(self.tokenizer(q, passage, truncation=False)["input_ids"])
                for q, passage in zip(batch_queries, batch_passages)
            ]
            max_raw_length = max(max_raw_length, *raw_lengths)
            truncated_pairs += sum(length > self.max_length for length in raw_lengths)

            encoded = self.tokenizer(
                batch_queries,
                batch_passages,
                padding=True,
                truncation="only_second",
                max_length=self.max_length,
                return_offsets_mapping=True,
                return_tensors="pt",
            )
            for batch_index, hit in enumerate(batch_hits):
                sequence_ids = encoded.sequence_ids(batch_index)
                offsets = encoded["offset_mapping"][batch_index].tolist()
                retained_passage_end = max(
                    (
                        end
                        for (start, end), sequence_id in zip(offsets, sequence_ids)
                        if sequence_id == 1 and end > start
                    ),
                    default=0,
                )
                for span_id, _char_start, char_end in evidence_ranges_by_chunk.get(
                    hit.chunk_id, []
                ):
                    was_truncated = evidence_span_was_truncated(
                        evidence_char_end=char_end,
                        retained_passage_char_end=retained_passage_end,
                    )
                    evidence_candidate_count += 1
                    truncated_evidence_count += int(was_truncated)
                    counts = evidence_truncation_by_span.setdefault(span_id, [0, 0])
                    counts[0] += 1
                    counts[1] += int(was_truncated)

            model_inputs = {
                key: value.to(self.device)
                for key, value in encoded.items()
                if key != "offset_mapping"
            }
            with self.torch.inference_mode():
                logits = self.model(**model_inputs).logits.reshape(-1).float().cpu().tolist()
            scores.extend(float(score) for score in logits)

        self.torch.cuda.synchronize()
        latency_ms = (time.perf_counter() - started) * 1000
        if len(scores) != len(candidates):
            raise RuntimeError("The reranker returned a different number of scores than candidates.")
        if not all(self.torch.isfinite(self.torch.tensor(scores)).tolist()):
            raise RuntimeError("The reranker returned a non-finite score.")

        return RerankResult(
            hits=sort_hits_by_scores(candidates, scores),
            latency_ms=latency_ms,
            pair_count=len(candidates),
            truncated_pair_count=truncated_pairs,
            max_untruncated_pair_tokens=max_raw_length,
            gold_evidence_candidate_count=evidence_candidate_count,
            truncated_gold_evidence_candidate_count=truncated_evidence_count,
            gold_evidence_truncation_by_span={
                span_id: (counts[0], counts[1])
                for span_id, counts in evidence_truncation_by_span.items()
            },
        )
