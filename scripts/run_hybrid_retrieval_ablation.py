from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from rag_hcmute.evaluation.evidence_spans import (  # noqa: E402
    evaluate_exact_evidence_retrieval,
    load_exact_evidence_spans,
)
from rag_hcmute.evaluation.run_pilot import PilotQuestion, load_pilot_questions  # noqa: E402
from rag_hcmute.ingestion.chunk import (  # noqa: E402
    DEFAULT_CHUNK_TOKENS,
    DEFAULT_OVERLAP_TOKENS,
    chunk_document,
)
from rag_hcmute.ingestion.clean import clean_document_pages  # noqa: E402
from rag_hcmute.ingestion.extract import read_pages_jsonl  # noqa: E402
from rag_hcmute.retrieval.bm25_index import BM25Retriever  # noqa: E402
from rag_hcmute.retrieval.common import load_chunks  # noqa: E402
from rag_hcmute.retrieval.hybrid import ReciprocalRankFusionRetriever  # noqa: E402

EXPECTED_SNAPSHOT_ID = "5da3bd4d5de54492"
TOP_K = 10
HIT_K = 5
RRF_RANK_CONSTANT = 60
RRF_CANDIDATE_K = 20


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
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


def _load_and_validate_manifest() -> tuple[dict[str, dict[str, str]], str]:
    manifest_path = PROJECT_ROOT / "data/manifests/corpus_manifest.csv"
    with manifest_path.open("r", encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    for row in rows:
        source_path = (PROJECT_ROOT / row["local_path"]).resolve()
        if not source_path.is_file() or _sha256(source_path) != row["file_sha256"].strip().lower():
            raise SystemExit("A corpus source is missing or its SHA-256 differs from the manifest.")
    return {row["document_id"]: row for row in rows}, _sha256(manifest_path)


def _chunk_content_signature(chunks: list) -> list[tuple]:
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


def _metric_summary(result: dict) -> dict:
    return {
        "metric_scope": result["metric_scope"],
        "top_k": result["top_k"],
        "hit_k": result["hit_k"],
        "evidence_span_recall_at_5": result["evidence_span_recall_at_k"],
        "complete_evidence_hit_at_5": result["complete_evidence_hit_at_k"],
        "first_evidence_mrr_at_10": result["first_evidence_mrr_at_top_k"],
    }


def _metrics_by_document_type(
    *,
    result: dict,
    spans_by_question: dict,
    questions: list[PilotQuestion],
    document_types: dict[str, str],
) -> dict[str, dict]:
    question_by_id = {question.question_id: question for question in questions}
    result_by_id = {row["question_id"]: row for row in result["per_question"]}
    grouped: dict[str, dict] = defaultdict(
        lambda: {
            "question_count": 0,
            "evidence_spans": 0,
            "evidence_span_hits_at_5": 0,
            "complete_evidence_questions_at_5": 0,
        }
    )

    for question_id, spans in spans_by_question.items():
        question = question_by_id[question_id]
        group = grouped[document_types[question.expected_document]]
        row = result_by_id[question_id]
        ranks = row["span_ranks"].values()
        group["question_count"] += 1
        group["evidence_spans"] += len(spans)
        group["evidence_span_hits_at_5"] += sum(rank is not None and rank <= HIT_K for rank in ranks)
        group["complete_evidence_questions_at_5"] += int(
            row["all_required_spans_hit_at_k"]
            and all(rank is not None and rank <= HIT_K for rank in row["span_ranks"].values())
        )

    return {
        document_type: {
            **counts,
            "evidence_span_recall_at_5": (
                counts["evidence_span_hits_at_5"] / counts["evidence_spans"]
                if counts["evidence_spans"] else 0.0
            ),
            "complete_evidence_hit_at_5": (
                counts["complete_evidence_questions_at_5"] / counts["question_count"]
                if counts["question_count"] else 0.0
            ),
        }
        for document_type, counts in grouped.items()
    }


def run_ablation(*, source_root: Path, dense_model: str) -> dict:
    manifest_by_id, manifest_hash = _load_and_validate_manifest()
    snapshot_path = source_root / "snapshot.json"
    chunks_path = source_root / "chunks" / "chunks.jsonl"
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    if snapshot.get("snapshot_id") != EXPECTED_SNAPSHOT_ID:
        raise SystemExit("Hybrid ablation is pinned to the approved native-only G0 snapshot.")
    if snapshot.get("config", {}).get("ocr", {}).get("enabled", False):
        raise SystemExit("G0 must remain native-only for this retrieval ablation.")

    stored_chunks = load_chunks(chunks_path)
    pages_by_document = {}
    regenerated_chunks = []
    for document in snapshot["documents"]:
        document_id = document["document_id"]
        pages = read_pages_jsonl(source_root / "pages" / f"{document_id}.jsonl")
        pages_by_document[document_id], _ = clean_document_pages(pages)
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
        raise SystemExit(
            "The current default chunker does not match the pinned G0 content signature; stopping."
        )
    # The approved G0 predates document-wide token offsets. Recreate them in memory only;
    # exact-evidence evaluation runs on these regenerated chunks after signature validation.
    chunks = regenerated_chunks

    questions_path = PROJECT_ROOT / "data/question_sets/pilot_questions.csv"
    annotations_path = PROJECT_ROOT / "data/question_sets/pilot_evidence_annotations.json"
    questions = load_pilot_questions(questions_path)
    spans_by_question, annotation_metadata = load_exact_evidence_spans(
        questions_path=questions_path,
        annotations_path=annotations_path,
        pages_by_document=pages_by_document,
        snapshot_id=snapshot["snapshot_id"],
    )

    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    model_path = Path(dense_model).resolve()
    if not model_path.is_dir():
        raise SystemExit("Dense retrieval requires the approved local model directory; downloads are disabled.")
    import torch

    if not torch.cuda.is_available():
        raise SystemExit("Dense retrieval requires the approved CUDA environment; CUDA is unavailable.")

    from rag_hcmute.retrieval.dense_index import (  # noqa: PLC0415
        MAX_SEQ_LENGTH,
        NORMALIZATION,
        DenseRetriever,
    )

    lexical = BM25Retriever(chunks)
    dense = DenseRetriever(chunks, model_name=str(model_path))
    hybrid = ReciprocalRankFusionRetriever(
        lexical,
        dense,
        rank_constant=RRF_RANK_CONSTANT,
        candidate_k=RRF_CANDIDATE_K,
    )

    document_types = {
        document_id: row["document_type"] for document_id, row in manifest_by_id.items()
    }
    method_retrievers = {
        "bm25": (lexical, {"method": "BM25Okapi", "tokenizer": "unicode_word_regex_lowercase"}),
        "dense": (
            dense,
            {
                "method": "BGE-M3 + FAISS IndexFlatIP",
                "model_label": "BGE-M3 local snapshot",
                "embedding_dim": dense._dim,
                "max_seq_length": MAX_SEQ_LENGTH,
                "normalization": NORMALIZATION,
                "device": str(dense._model.device),
                "network_access": "disabled",
            },
        ),
        "hybrid_rrf": (
            hybrid,
            {
                "method": "BM25 + BGE-M3 rank fusion",
                "fusion": "Reciprocal Rank Fusion",
                "rank_constant": RRF_RANK_CONSTANT,
                "candidate_k_per_branch": RRF_CANDIDATE_K,
                "final_top_k": TOP_K,
            },
        ),
    }

    results = {}
    for name, (retriever, config) in method_retrievers.items():
        exact = evaluate_exact_evidence_retrieval(
            questions=questions,
            spans_by_question=spans_by_question,
            chunks=chunks,
            retriever=retriever,
            top_k=TOP_K,
            hit_k=HIT_K,
        )
        results[name] = {
            "config": config,
            "metrics": _metric_summary(exact),
            "metrics_by_document_type": _metrics_by_document_type(
                result=exact,
                spans_by_question=spans_by_question,
                questions=questions,
                document_types=document_types,
            ),
        }

    return {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "git_revision": _git_revision(),
        "script_sha256": _sha256(Path(__file__).resolve()),
        "hybrid_module_sha256": _sha256(PROJECT_ROOT / "src/rag_hcmute/retrieval/hybrid.py"),
        "bm25_module_sha256": _sha256(PROJECT_ROOT / "src/rag_hcmute/retrieval/bm25_index.py"),
        "dense_module_sha256": _sha256(PROJECT_ROOT / "src/rag_hcmute/retrieval/dense_index.py"),
        "manifest_sha256": manifest_hash,
        "snapshot_id": snapshot["snapshot_id"],
        "snapshot_sha256": _sha256(snapshot_path),
        "chunks_sha256": _sha256(chunks_path),
        "questions_sha256": _sha256(questions_path),
        "evidence_annotations_sha256": _sha256(annotations_path),
        "evaluation": {
            "answerable_question_count": len(spans_by_question),
            "evidence_span_count": annotation_metadata["evidence_span_count"],
            "unanswerable_question_count": sum(
                question.answerability == "unanswerable" for question in questions
            ),
            "metric_scope": "exact source-token evidence span; retrieval only, not generation",
            "top_k": TOP_K,
            "hit_k": HIT_K,
            "corpus_chunk_count": len(chunks),
            "baseline_content_signature_matches": True,
            "note": "Pilot is development data, not an independent holdout; no question or source text is serialized.",
        },
        "methods": results,
        "privacy_note": "Aggregate metrics/configuration/hashes only; no query, source text, preview, or vector is written.",
    }


def main() -> int:
    print(f"Python executable: {sys.executable}")
    parser = argparse.ArgumentParser(
        description="Compare BM25, local Dense BGE-M3, and RRF fusion on the approved G0 pilot."
    )
    parser.add_argument(
        "--source-root",
        type=Path,
        default=PROJECT_ROOT / "data/processed/g0_reproduction",
    )
    parser.add_argument("--dense-model", required=True, help="Existing local model directory; no downloads are allowed.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROJECT_ROOT / "artifacts/results/hybrid_retrieval_ablation",
    )
    args = parser.parse_args()

    report = run_ablation(
        source_root=args.source_root.resolve(),
        dense_model=args.dense_model,
    )
    output_dir = args.output_dir.resolve()
    ignored_root = (PROJECT_ROOT / "artifacts/results").resolve()
    if not output_dir.is_relative_to(ignored_root):
        raise SystemExit("--output-dir must remain under Git-ignored artifacts/results.")
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_path = output_dir / f"hybrid_{report['snapshot_id']}_{timestamp}.json"
    with output_path.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write("\n")

    print(f"Snapshot: {report['snapshot_id']} | answerable: {report['evaluation']['answerable_question_count']} | spans: {report['evaluation']['evidence_span_count']}")
    for name, method in report["methods"].items():
        metrics = method["metrics"]
        recall = metrics["evidence_span_recall_at_5"]
        complete = metrics["complete_evidence_hit_at_5"]
        mrr = metrics["first_evidence_mrr_at_10"]
        print(
            f"{name} | evidence Recall@5={recall['hits']}/{recall['denominator']} ({recall['value']:.3f}) | "
            f"complete Hit@5={complete['hits']}/{complete['denominator']} ({complete['value']:.3f}) | "
            f"first-evidence MRR@10={mrr['value']:.3f}"
        )
    print(f"Metrics-only output (Git-ignored): {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
