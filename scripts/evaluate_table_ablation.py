from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


print(f"Python executable: {sys.executable}")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from rag_hcmute.evaluation.table_ablation import (  # noqa: E402
    build_matched_table_variants,
    evaluate_required_evidence,
    summarize_evidence_metrics,
)
from rag_hcmute.evaluation.question_partitions import question_ids_for_partition  # noqa: E402
from rag_hcmute.retrieval.bm25_index import BM25Retriever  # noqa: E402
from rag_hcmute.retrieval.common import RetrievalHit  # noqa: E402

TOP_K = 5
QUESTION_PATH = PROJECT_ROOT / (
    "data/question_sets/table_questions_reviewed_ablation_20261005.csv"
)
EVIDENCE_PATH = PROJECT_ROOT / (
    "data/question_sets/table_question_variant_evidence_20261005.csv"
)
EXPECTED_SNAPSHOT = "5da3bd4d5de54492"
VARIANTS = ("B0", "T1", "T2")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Evaluate reviewed Table 5 evidence retrieval across matched B0/T1/T2 corpora. "
            "This is a small table ablation, not a whole-system benchmark."
        )
    )
    parser.add_argument("--method", choices=("bm25", "dense", "both"), default="both")
    parser.add_argument(
        "--dense-model",
        default=None,
        help="Local model directory or Hugging Face model ID for Dense Retrieval.",
    )
    parser.add_argument(
        "--allow-model-download",
        action="store_true",
        help="Allow Hugging Face network access if the model is not local.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROJECT_ROOT / "artifacts/results/table_retrieval_ablation",
    )
    return parser


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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


def _load_reviewed_inputs() -> tuple[list[dict[str, str]], dict[tuple[str, str], dict]]:
    questions = _read_csv(QUESTION_PATH)
    evidence_rows = _read_csv(EVIDENCE_PATH)
    try:
        registered_ids = question_ids_for_partition(QUESTION_PATH, "ablation_only")
    except (OSError, ValueError) as exc:
        raise SystemExit(f"Question partition validation failed: {exc}") from exc
    if not questions or len(questions) != 5:
        raise SystemExit("Expected the five approved Table 5 questions TB001-TB005.")
    question_ids = [row["question_id"] for row in questions]
    if set(question_ids) != registered_ids:
        raise SystemExit("Table question IDs do not match the approved ablation partition.")
    if len(set(question_ids)) != len(question_ids):
        raise SystemExit("Question IDs must be unique.")
    if any(
        row["review_status"] != "approved_for_table_retrieval_ablation"
        or row["answerability"] != "answerable"
        or row["source_snapshot_id"] != EXPECTED_SNAPSHOT
        for row in questions
    ):
        raise SystemExit("Question status, answerability, or snapshot does not match this run.")

    evidence: dict[tuple[str, str], dict] = {}
    for row in evidence_rows:
        key = (row["question_id"], row["variant"])
        chunk_ids = [value for value in row["expected_chunk_ids"].split(";") if value]
        try:
            required_units = int(row["required_evidence_units"])
        except ValueError as error:
            raise SystemExit(f"Invalid evidence-unit count for {key}.") from error
        if (
            key in evidence
            or row["mapping_status"] != "approved_for_table_retrieval_ablation"
            or row["source_snapshot_id"] != EXPECTED_SNAPSHOT
            or not chunk_ids
            or required_units != len(chunk_ids)
        ):
            raise SystemExit(f"Invalid or duplicate evidence annotation for {key}.")
        evidence[key] = {**row, "expected_chunk_ids_list": chunk_ids}

    expected_keys = {
        (question_id, variant)
        for question_id in question_ids
        for variant in VARIANTS
    }
    if set(evidence) != expected_keys:
        raise SystemExit("Evidence map must contain exactly one row per question and variant.")
    return questions, evidence


def _validate_source_hash() -> str:
    manifest_path = PROJECT_ROOT / "data/manifests/corpus_manifest.csv"
    source_pdf = PROJECT_ROOT / "data/raw/HCMUTE_QCDT_1727_2021.pdf"
    manifest_rows = _read_csv(manifest_path)
    manifest = next(
        row
        for row in manifest_rows
        if row["document_id"] == "HCMUTE_QCDT_1727_2021"
    )
    actual_hash = _sha256(source_pdf)
    if actual_hash != manifest["file_sha256"]:
        raise SystemExit(
            "Source PDF hash differs from corpus manifest; stop before evaluating."
        )
    return actual_hash


def _validate_snapshot() -> dict:
    path = PROJECT_ROOT / "data/manifests/corpus_snapshot.json"
    snapshot = json.loads(path.read_text(encoding="utf-8"))
    if snapshot["snapshot_id"] != EXPECTED_SNAPSHOT:
        raise SystemExit("Current corpus snapshot does not match reviewed evidence labels.")
    return snapshot


def _make_retriever(method: str, chunks: list, model_name: str | None):
    if method == "bm25":
        return BM25Retriever(chunks), {
            "name": "BM25Okapi",
            "tokenizer": "regex_\\w+_unicode_lowercase",
        }

    import torch
    from rag_hcmute.retrieval.dense_index import (
        MAX_SEQ_LENGTH,
        NORMALIZATION,
        DenseRetriever,
    )

    cuda_available = torch.cuda.is_available()
    print(f"CUDA available: {cuda_available}")
    if not cuda_available:
        raise SystemExit("Dense evaluation requires the approved CUDA environment.")
    resolved_model = model_name or "BAAI/bge-m3"
    retriever = DenseRetriever(chunks, model_name=resolved_model)
    return retriever, {
        "name": "BGE-M3 + FAISS IndexFlatIP",
        "model": resolved_model,
        "device": str(retriever._model.device),
        "embedding_dimension": retriever._dim,
        "max_seq_length": MAX_SEQ_LENGTH,
        "normalization": NORMALIZATION,
    }


def _query_result(
    question: dict[str, str], evidence: dict, hits: list[RetrievalHit]
) -> dict:
    required_ids = evidence["expected_chunk_ids_list"]
    evidence_result = evaluate_required_evidence(hits, required_ids, TOP_K)
    return {
        "question_id": question["question_id"],
        "question": question["question"],
        "expected_answer": question["expected_answer"],
        "source_rows": evidence["source_rows"],
        **evidence_result,
        "top_hits": [
            {
                "rank": hit.rank,
                "chunk_id": hit.chunk_id,
                "document_id": hit.document_id,
                "pdf_page_start": hit.pdf_page_start,
                "pdf_page_end": hit.pdf_page_end,
                "score": hit.score,
            }
            for hit in hits[:TOP_K]
        ],
    }


def main() -> int:
    args = build_parser().parse_args()
    if args.method in {"dense", "both"} and not args.allow_model_download:
        os.environ["HF_HUB_OFFLINE"] = "1"

    questions, evidence = _load_reviewed_inputs()
    source_hash = _validate_source_hash()
    snapshot = _validate_snapshot()
    corpora = build_matched_table_variants(PROJECT_ROOT)
    for variant, chunks in corpora.items():
        available_ids = {chunk.chunk_id for chunk in chunks}
        for question in questions:
            expected_ids = evidence[(question["question_id"], variant)][
                "expected_chunk_ids_list"
            ]
            if not set(expected_ids) <= available_ids:
                raise SystemExit(
                    f"Missing expected evidence chunks for {question['question_id']} / {variant}."
                )

    methods = ("bm25", "dense") if args.method == "both" else (args.method,)
    report = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "approved_question_set_exploratory_table_ablation",
        "scope": "Retrieval of evidence for five approved questions about QĐ 1727/2021 Table 5.",
        "not_a_full_system_benchmark": True,
        "snapshot_id": snapshot["snapshot_id"],
        "source_pdf_sha256": source_hash,
        "question_set_sha256": _sha256(QUESTION_PATH),
        "evidence_map_sha256": _sha256(EVIDENCE_PATH),
        "git_revision": _git_revision(),
        "top_k": TOP_K,
        "corpus_chunk_counts": {
            variant: len(chunks) for variant, chunks in corpora.items()
        },
        "methods": [],
        "metric_definitions": {
            "complete_evidence_hit_at_5": (
                "Fraction of questions for which every required evidence chunk is in top-5."
            ),
            "mean_evidence_unit_coverage_at_5": (
                "Mean across questions of required evidence chunks found in top-5 divided by required chunks."
            ),
            "mrr_first_required_evidence_at_5": (
                "MRR of the earliest required evidence chunk; it does not assert all evidence was retrieved."
            ),
        },
        "limitations": [
            "Five questions are a small table-specific evaluation set, not a general RAG benchmark.",
            "Questions and answers are scoped to QĐ 1727/2021; the possible later QĐ 3116/2025 was not in the local corpus.",
            "No generation, citation correctness, refusal, or end-to-end answer quality is evaluated.",
            "B0/T1/T2 have different table chunk granularity; compare complete answer evidence, not raw chunk counts alone.",
        ],
    }

    for method in methods:
        method_report = {"method": method, "variants": []}
        for variant, chunks in corpora.items():
            retriever, config = _make_retriever(method, chunks, args.dense_model)
            per_question = []
            for question in questions:
                query_result = retriever.query(question["question"], top_k=TOP_K)
                annotation = evidence[(question["question_id"], variant)]
                per_question.append(
                    _query_result(question, annotation, query_result.hits)
                )
            variant_report = {
                "variant": variant,
                "chunk_count": len(chunks),
                "retrieval_config": config,
                "metrics": summarize_evidence_metrics(per_question),
                "results": per_question,
            }
            method_report["variants"].append(variant_report)
            del retriever
        report["methods"].append(method_report)

    output_dir = args.output_dir.resolve()
    ignored_root = (PROJECT_ROOT / "artifacts/results").resolve()
    if not output_dir.is_relative_to(ignored_root):
        raise SystemExit("--output-dir must remain under Git-ignored artifacts/results.")
    output_dir.mkdir(parents=True, exist_ok=True)
    run_stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_path = output_dir / f"table_ablation_{args.method}_{run_stamp}.json"
    with output_path.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write("\n")

    print(f"Status: {report['status']}")
    print(f"Questions: {len(questions)} | methods: {', '.join(methods)} | top-k: {TOP_K}")
    for method_report in report["methods"]:
        print(f"\n{method_report['method'].upper()}")
        for variant_report in method_report["variants"]:
            metrics = variant_report["metrics"]
            complete = metrics["complete_evidence_hit_at_5"]
            coverage = metrics["mean_evidence_unit_coverage_at_5"]["value"]
            mrr = metrics["mrr_first_required_evidence_at_5"]["value"]
            print(
                f"  {variant_report['variant']} ({variant_report['chunk_count']} chunks): "
                f"complete={complete['hits']}/{complete['denominator']}, "
                f"coverage={coverage:.3f}, first-evidence-MRR={mrr:.3f}"
            )
            for result in variant_report["results"]:
                print(
                    f"    {result['question_id']}: "
                    f"complete={result['complete_evidence_retrieved_at_k']}, "
                    f"coverage={result['retrieved_evidence_units']}/"
                    f"{result['required_evidence_units']}, "
                    f"ranks={result['expected_chunk_ranks']}"
                )
    print(f"Raw output (Git-ignored): {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
