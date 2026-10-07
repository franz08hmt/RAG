from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import re
import statistics
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from rag_hcmute.evaluation.evidence_spans import (  # noqa: E402
    evaluate_exact_evidence_retrieval,
    load_exact_evidence_spans,
    map_spans_to_chunks,
)
from rag_hcmute.evaluation.reranker import LocalCrossEncoderReranker  # noqa: E402
from rag_hcmute.evaluation.run_pilot import PilotQuestion, load_pilot_questions  # noqa: E402
from rag_hcmute.ingestion.chunk import (  # noqa: E402
    DEFAULT_CHUNK_TOKENS,
    DEFAULT_OVERLAP_TOKENS,
    Chunk,
    chunk_document,
)
from rag_hcmute.ingestion.clean import clean_document_pages  # noqa: E402
from rag_hcmute.ingestion.extract import read_pages_jsonl  # noqa: E402
from rag_hcmute.retrieval.bm25_index import BM25Retriever  # noqa: E402
from rag_hcmute.retrieval.common import RetrievalHit, load_chunks  # noqa: E402
from rag_hcmute.retrieval.dense_index import DenseRetriever  # noqa: E402
from rag_hcmute.retrieval.hybrid import ReciprocalRankFusionRetriever  # noqa: E402

EXPECTED_SNAPSHOT_ID = "5da3bd4d5de54492"
RERANKER_REPOSITORY = "BAAI/bge-reranker-v2-m3"
RERANKER_REVISION = "953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e"
RERANKER_WEIGHT_SHA256 = "d9e3e081faff1eefb84019509b2f5558fd74c1a05a2c7db22f74174fcedb5286"
RERANKER_WEIGHT_SIZE = 2_271_071_852
RRF_RANK_CONSTANT = 60
RRF_CANDIDATE_K = 20
CANDIDATE_DEPTH = 20
METRIC_TOP_K = 10
METRIC_HIT_K = 5


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _git_revision() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=PROJECT_ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unavailable"


def _chunk_content_signature(chunks: list[Chunk]) -> list[tuple]:
    return [
        (
            chunk.chunk_id,
            chunk.text_sha256,
            chunk.token_count,
            chunk.section_path,
            chunk.chunk_method,
            chunk.pdf_page_start,
            chunk.pdf_page_end,
        )
        for chunk in chunks
    ]


def _validate_corpus(source_root: Path) -> tuple[dict, list[Chunk], dict, str]:
    manifest_path = PROJECT_ROOT / "data/manifests/corpus_manifest.csv"
    manifest_hash = _sha256(manifest_path)
    with manifest_path.open("r", encoding="utf-8-sig", newline="") as stream:
        manifest_rows = list(csv.DictReader(stream))
    for row in manifest_rows:
        source_path = (PROJECT_ROOT / row["local_path"]).resolve()
        if not source_path.is_file() or _sha256(source_path) != row["file_sha256"].strip().lower():
            raise SystemExit("A corpus source is missing or its SHA-256 differs from the manifest.")

    snapshot_path = source_root / "snapshot.json"
    chunks_path = source_root / "chunks" / "chunks.jsonl"
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    if snapshot.get("snapshot_id") != EXPECTED_SNAPSHOT_ID:
        raise SystemExit("Reranker evaluation is pinned to the approved native-only G0 snapshot.")
    if snapshot.get("config", {}).get("ocr", {}).get("enabled", False):
        raise SystemExit("G0 must remain native-only for this retrieval ablation.")

    stored_chunks = load_chunks(chunks_path)
    pages_by_document = {}
    regenerated_chunks = []
    for document in snapshot["documents"]:
        document_id = document["document_id"]
        pages_by_document[document_id], _ = clean_document_pages(
            read_pages_jsonl(source_root / "pages" / f"{document_id}.jsonl")
        )
        regenerated_chunks.extend(
            chunk_document(
                pages_by_document[document_id],
                document_id,
                document["document_title"],
                chunk_tokens=DEFAULT_CHUNK_TOKENS,
                overlap_tokens=DEFAULT_OVERLAP_TOKENS,
            )
        )
    if _chunk_content_signature(stored_chunks) != _chunk_content_signature(regenerated_chunks):
        raise SystemExit("Regenerated G0 chunks do not match the approved content signature.")

    metadata = {
        "snapshot_id": snapshot["snapshot_id"],
        "manifest_sha256": manifest_hash,
        "snapshot_sha256": _sha256(snapshot_path),
        "chunks_sha256": _sha256(chunks_path),
        "manifest_rows": manifest_rows,
        "snapshot": snapshot,
    }
    return metadata, regenerated_chunks, pages_by_document, _sha256(chunks_path)


def _metric_summary(result: dict) -> dict:
    return {
        "metric_scope": result["metric_scope"],
        "top_k": result["top_k"],
        "hit_k": result["hit_k"],
        "evidence_span_recall": result["evidence_span_recall_at_k"],
        "complete_evidence_hit": result["complete_evidence_hit_at_k"],
        "first_evidence_mrr": result["first_evidence_mrr_at_top_k"],
        "per_question": result["per_question"],
    }


def _latency_summary(values: list[float]) -> dict:
    if not values:
        raise ValueError("At least one latency measurement is required.")
    ordered = sorted(values)
    p95_index = max(0, math.ceil(0.95 * len(ordered)) - 1)
    return {
        "count": len(ordered),
        "mean_ms": statistics.fmean(ordered),
        "median_ms": statistics.median(ordered),
        "p95_ms_nearest_rank": ordered[p95_index],
    }


def _ranked_metrics(
    *,
    questions: list[PilotQuestion],
    question_ids: list[str],
    hits_by_question: dict[str, list[RetrievalHit]],
    spans_by_question: dict,
    chunks: list[Chunk],
    top_k: int,
    hit_k: int,
) -> dict:
    question_by_id = {question.question_id: question for question in questions}
    ordered_questions = [question_by_id[question_id] for question_id in question_ids]
    retriever = _ReplayRetriever(ordered_questions, hits_by_question)
    result = evaluate_exact_evidence_retrieval(
        questions=ordered_questions,
        spans_by_question=spans_by_question,
        chunks=chunks,
        retriever=retriever,
        top_k=top_k,
        hit_k=hit_k,
    )
    return _metric_summary(result)


@dataclass
class _ReplayResult:
    hits: list[RetrievalHit]
    latency_ms: float = 0.0


class _ReplayRetriever:
    """Replays cached rankings in annotation order without retaining query text in outputs."""

    def __init__(self, questions: list[PilotQuestion], hits_by_question: dict[str, list[RetrievalHit]]):
        self.questions = questions
        self.hits_by_question = hits_by_question
        self.index = 0

    def query(self, query_text: str, top_k: int = 5) -> _ReplayResult:
        if self.index >= len(self.questions):
            raise RuntimeError("Evaluation requested more cached rankings than available.")
        question = self.questions[self.index]
        self.index += 1
        if query_text != question.question:
            raise RuntimeError("Cached ranking order does not match the question order.")
        return _ReplayResult(self.hits_by_question[question.question_id][:top_k])


def _evidence_ranges_by_chunk(
    *,
    spans: list,
    candidate_hits: list[RetrievalHit],
    chunk_ids_by_span: dict[str, frozenset[str]],
    chunks_by_id: dict[str, Chunk],
) -> dict[str, list[tuple[str, int, int]]]:
    candidate_ids = {hit.chunk_id for hit in candidate_hits}
    result: dict[str, list[tuple[str, int, int]]] = {}
    for span in spans:
        matching_ids = chunk_ids_by_span[span.span_id] & candidate_ids
        for chunk_id in matching_ids:
            chunk = chunks_by_id[chunk_id]
            if chunk.token_start is None:
                raise ValueError(f"Chunk {chunk_id} lacks document-wide token offsets.")
            local_start = span.token_start - chunk.token_start
            local_end = span.token_end - chunk.token_start
            whitespace_tokens = list(re.finditer(r"\S+", chunk.text))
            if not (0 <= local_start < local_end <= len(whitespace_tokens)):
                raise ValueError(f"Evidence span {span.span_id} is outside candidate chunk {chunk_id}.")
            result.setdefault(chunk_id, []).append(
                (
                    span.span_id,
                    whitespace_tokens[local_start].start(),
                    whitespace_tokens[local_end - 1].end(),
                )
            )
    return result


def _verify_reranker_model(model_path: Path) -> str:
    model_path = model_path.resolve()
    if model_path.name != RERANKER_REVISION:
        raise SystemExit("Use the pinned BAAI/bge-reranker-v2-m3 snapshot revision only.")
    weight_path = model_path / "model.safetensors"
    if not weight_path.is_file() or weight_path.stat().st_size != RERANKER_WEIGHT_SIZE:
        raise SystemExit("Pinned reranker weight is missing or has an unexpected size.")
    weight_sha = _sha256(weight_path)
    if weight_sha != RERANKER_WEIGHT_SHA256:
        raise SystemExit("Pinned reranker weight SHA-256 mismatch; refusing to evaluate.")
    return weight_sha


def run_ablation(*, source_root: Path, dense_model: Path, reranker_model: Path,
                 max_length: int, batch_size: int) -> dict:
    reranker_sha = _verify_reranker_model(reranker_model)
    metadata, chunks, pages_by_document, chunks_file_hash = _validate_corpus(source_root)
    snapshot = metadata["snapshot"]
    questions_path = PROJECT_ROOT / "data/question_sets/pilot_questions.csv"
    annotations_path = PROJECT_ROOT / "data/question_sets/pilot_evidence_annotations.json"
    questions = load_pilot_questions(questions_path)
    with questions_path.open("r", encoding="utf-8-sig", newline="") as stream:
        question_status = {row["question_id"]: row["status"] for row in csv.DictReader(stream)}
    spans_by_question, annotation_metadata = load_exact_evidence_spans(
        questions_path=questions_path,
        annotations_path=annotations_path,
        pages_by_document=pages_by_document,
        snapshot_id=snapshot["snapshot_id"],
    )
    question_ids = list(spans_by_question)
    question_by_id = {question.question_id: question for question in questions}
    if not question_ids:
        raise SystemExit("No reviewed answerable questions with exact evidence spans were found.")
    if any(question_status.get(qid) != "reviewed" for qid in question_ids):
        raise SystemExit("Only reviewed development questions may enter this pilot evaluation.")

    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    os.environ["HF_HUB_DISABLE_IMPLICIT_TOKEN"] = "1"
    os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
    dense_model = dense_model.resolve()
    if not dense_model.is_dir():
        raise SystemExit("Dense retrieval requires an existing local model directory; downloads are disabled.")

    import torch

    if not torch.cuda.is_available():
        raise SystemExit("This local evaluation requires CUDA; CUDA is unavailable.")
    torch.set_num_threads(2)

    lexical = BM25Retriever(chunks)
    dense = DenseRetriever(chunks, model_name=str(dense_model))
    hybrid = ReciprocalRankFusionRetriever(
        lexical,
        dense,
        rank_constant=RRF_RANK_CONSTANT,
        candidate_k=RRF_CANDIDATE_K,
    )
    retrievers = {"dense": dense, "hybrid_rrf": hybrid}

    candidates_by_method: dict[str, dict[str, list[RetrievalHit]]] = {}
    retrieval_latency_by_method: dict[str, list[float]] = {}
    for method, retriever in retrievers.items():
        candidates_by_method[method] = {}
        retrieval_latency_by_method[method] = []
        for question_id in question_ids:
            result = retriever.query(question_by_id[question_id].question, top_k=CANDIDATE_DEPTH)
            if len(result.hits) != CANDIDATE_DEPTH:
                raise RuntimeError(f"{method} returned fewer than {CANDIDATE_DEPTH} candidates.")
            candidates_by_method[method][question_id] = result.hits
            retrieval_latency_by_method[method].append(result.latency_ms)

    chunks_by_id = {chunk.chunk_id: chunk for chunk in chunks}
    chunk_ids_by_span = map_spans_to_chunks(spans_by_question, chunks)
    before_metrics = {}
    coverage_metrics = {}
    for method, candidates_by_question in candidates_by_method.items():
        before_metrics[method] = _ranked_metrics(
            questions=questions,
            question_ids=question_ids,
            hits_by_question=candidates_by_question,
            spans_by_question=spans_by_question,
            chunks=chunks,
            top_k=METRIC_TOP_K,
            hit_k=METRIC_HIT_K,
        )
        coverage_metrics[method] = _ranked_metrics(
            questions=questions,
            question_ids=question_ids,
            hits_by_question=candidates_by_question,
            spans_by_question=spans_by_question,
            chunks=chunks,
            top_k=CANDIDATE_DEPTH,
            hit_k=CANDIDATE_DEPTH,
        )

    del retrievers, retriever, hybrid, dense, lexical
    torch.cuda.synchronize()
    torch.cuda.empty_cache()

    reranker = LocalCrossEncoderReranker(
        reranker_model,
        max_length=max_length,
        batch_size=batch_size,
    )
    torch.cuda.reset_peak_memory_stats()
    reranked_by_method: dict[str, dict[str, list[RetrievalHit]]] = {}
    rerank_latency_by_method: dict[str, list[float]] = {}
    truncation_by_method: dict[str, dict] = {}

    for method, candidates_by_question in candidates_by_method.items():
        reranked_by_method[method] = {}
        rerank_latency_by_method[method] = []
        total_pairs = 0
        truncated_pairs = 0
        max_pair_tokens = 0
        evidence_candidate_count = 0
        truncated_evidence_candidate_count = 0
        span_candidate_counts: dict[str, list[int]] = {}
        for question_id in question_ids:
            candidates = candidates_by_question[question_id]
            evidence_ranges = _evidence_ranges_by_chunk(
                spans=spans_by_question[question_id],
                candidate_hits=candidates,
                chunk_ids_by_span=chunk_ids_by_span,
                chunks_by_id=chunks_by_id,
            )
            result = reranker.rerank(
                query=question_by_id[question_id].question,
                candidates=candidates,
                chunks_by_id=chunks_by_id,
                evidence_ranges_by_chunk=evidence_ranges,
            )
            reranked_by_method[method][question_id] = result.hits
            rerank_latency_by_method[method].append(result.latency_ms)
            total_pairs += result.pair_count
            truncated_pairs += result.truncated_pair_count
            max_pair_tokens = max(max_pair_tokens, result.max_untruncated_pair_tokens)
            evidence_candidate_count += result.gold_evidence_candidate_count
            truncated_evidence_candidate_count += result.truncated_gold_evidence_candidate_count
            for span_id, counts in result.gold_evidence_truncation_by_span.items():
                aggregate = span_candidate_counts.setdefault(span_id, [0, 0])
                aggregate[0] += counts[0]
                aggregate[1] += counts[1]

        truncation_by_method[method] = {
            "candidate_pair_count": total_pairs,
            "truncated_pair_count": truncated_pairs,
            "truncated_pair_rate": truncated_pairs / total_pairs if total_pairs else 0.0,
            "max_untruncated_pair_tokens": max_pair_tokens,
            "gold_evidence_candidate_occurrences": evidence_candidate_count,
            "truncated_gold_evidence_candidate_occurrences": truncated_evidence_candidate_count,
            "gold_evidence_candidate_occurrences_by_span": {
                span_id: {"candidate_occurrences": counts[0], "truncated_occurrences": counts[1]}
                for span_id, counts in sorted(span_candidate_counts.items())
            },
        }

    methods = {}
    for method in candidates_by_method:
        after = _ranked_metrics(
            questions=questions,
            question_ids=question_ids,
            hits_by_question=reranked_by_method[method],
            spans_by_question=spans_by_question,
            chunks=chunks,
            top_k=METRIC_TOP_K,
            hit_k=METRIC_HIT_K,
        )
        methods[method] = {
            "candidate_coverage_at_20": coverage_metrics[method],
            "before_reranking": before_metrics[method],
            "after_reranking": after,
            "retrieval_latency": _latency_summary(retrieval_latency_by_method[method]),
            "reranker_latency_per_query": _latency_summary(rerank_latency_by_method[method]),
            "truncation": truncation_by_method[method],
        }

    torch.cuda.synchronize()
    gpu = torch.cuda.get_device_name(0)
    peak_allocated = torch.cuda.max_memory_allocated() / (1024**3)
    peak_reserved = torch.cuda.max_memory_reserved() / (1024**3)
    dense_module = PROJECT_ROOT / "src/rag_hcmute/retrieval/dense_index.py"
    hybrid_module = PROJECT_ROOT / "src/rag_hcmute/retrieval/hybrid.py"
    reranker_module = PROJECT_ROOT / "src/rag_hcmute/evaluation/reranker.py"
    return {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "git_revision": _git_revision(),
        "script_sha256": _sha256(Path(__file__).resolve()),
        "reranker_module_sha256": _sha256(reranker_module),
        "dense_module_sha256": _sha256(dense_module),
        "hybrid_module_sha256": _sha256(hybrid_module),
        "snapshot_id": snapshot["snapshot_id"],
        "snapshot_sha256": metadata["snapshot_sha256"],
        "manifest_sha256": metadata["manifest_sha256"],
        "chunks_sha256": chunks_file_hash,
        "questions_sha256": _sha256(questions_path),
        "evidence_annotations_sha256": _sha256(annotations_path),
        "evaluation": {
            "scope": "retrieval-only reranking of a fixed candidate pool on the development pilot",
            "answerable_question_count": len(spans_by_question),
            "evidence_span_count": annotation_metadata["evidence_span_count"],
            "unanswerable_question_count": sum(q.answerability == "unanswerable" for q in questions),
            "candidate_depth": CANDIDATE_DEPTH,
            "metric_top_k": METRIC_TOP_K,
            "metric_hit_k": METRIC_HIT_K,
            "rrf_rank_constant": RRF_RANK_CONSTANT,
            "rrf_candidate_k_per_branch": RRF_CANDIDATE_K,
            "corpus_chunk_count": len(chunks),
            "baseline_content_signature_matches": True,
            "holdout_used": False,
            "note": "The pilot is small development data; results are exploratory and were not used to claim generalization or change a default.",
        },
        "models": {
            "dense": {
                "label": "local BGE-M3 snapshot",
                "model_directory": str(dense_model),
                "network_access": "disabled",
            },
            "reranker": {
                "repository": RERANKER_REPOSITORY,
                "revision": RERANKER_REVISION,
                "weight_size_bytes": RERANKER_WEIGHT_SIZE,
                "weight_sha256": reranker_sha,
                "model_directory": str(reranker_model.resolve()),
                "precision": "float16",
                "max_length": max_length,
                "truncation_strategy": "only_second (preserve query; truncate passage from right if necessary)",
                "batch_size": batch_size,
                "load_seconds": reranker.load_seconds,
                "network_access": "disabled; local_files_only",
            },
        },
        "runtime": {
            "python": sys.version.split()[0],
            "torch": torch.__version__,
            "cuda_runtime": torch.version.cuda,
            "gpu": gpu,
            "peak_cuda_allocated_gib_after_model_load": peak_allocated,
            "peak_cuda_reserved_gib_after_model_load": peak_reserved,
        },
        "methods": methods,
        "privacy_note": "Only hashes, aggregate metrics, synthetic question/span IDs, ranks, token-length/truncation counts, timings, and hardware metadata are written; no query text, answer, source excerpt, or vector is serialized.",
    }


def main() -> int:
    print(f"Python executable: {sys.executable}")
    parser = argparse.ArgumentParser(
        description="Compare Dense and Hybrid RRF rankings before/after local reranking on the G0 development pilot."
    )
    parser.add_argument("--dense-model", type=Path, required=True, help="Existing local BGE-M3 snapshot; no downloads are allowed.")
    parser.add_argument("--reranker-model", type=Path, required=True, help="Pinned local BGE reranker snapshot; no downloads are allowed.")
    parser.add_argument("--source-root", type=Path, default=PROJECT_ROOT / "data/processed/g0_reproduction")
    parser.add_argument("--max-length", type=int, default=512)
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--output-dir", type=Path, default=PROJECT_ROOT / "artifacts/results/reranker_ablation")
    args = parser.parse_args()

    report = run_ablation(
        source_root=args.source_root.resolve(),
        dense_model=args.dense_model,
        reranker_model=args.reranker_model,
        max_length=args.max_length,
        batch_size=args.batch_size,
    )
    output_dir = args.output_dir.resolve()
    ignored_root = (PROJECT_ROOT / "artifacts/results").resolve()
    if not output_dir.is_relative_to(ignored_root):
        raise SystemExit("--output-dir must remain under Git-ignored artifacts/results.")
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_path = output_dir / f"reranker_{report['snapshot_id']}_{timestamp}.json"
    with output_path.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write("\n")

    print(f"Snapshot: {report['snapshot_id']} | answerable: {report['evaluation']['answerable_question_count']} | exact spans: {report['evaluation']['evidence_span_count']}")
    for method, result in report["methods"].items():
        for stage in ("before_reranking", "after_reranking"):
            metrics = result[stage]
            recall = metrics["evidence_span_recall"]
            complete = metrics["complete_evidence_hit"]
            mrr = metrics["first_evidence_mrr"]
            print(
                f"{method}/{stage} | Recall@5={recall['hits']}/{recall['denominator']} ({recall['value']:.3f}) | "
                f"Complete Hit@5={complete['hits']}/{complete['denominator']} ({complete['value']:.3f}) | "
                f"MRR@10={mrr['value']:.3f}"
            )
        truncation = result["truncation"]
        print(
            f"{method} | pair truncation={truncation['truncated_pair_count']}/"
            f"{truncation['candidate_pair_count']} | gold-evidence truncation="
            f"{truncation['truncated_gold_evidence_candidate_occurrences']}/"
            f"{truncation['gold_evidence_candidate_occurrences']}"
        )
    print(f"Reranker load: {report['models']['reranker']['load_seconds']:.2f} s | GPU peak allocated: {report['runtime']['peak_cuda_allocated_gib_after_model_load']:.3f} GiB")
    print(f"Content-free result output (Git-ignored): {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
