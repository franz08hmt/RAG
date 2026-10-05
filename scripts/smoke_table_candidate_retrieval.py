from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sys
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path


print(f"Python executable: {sys.executable}")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from rag_hcmute.retrieval.bm25_index import BM25Retriever  # noqa: E402
from rag_hcmute.retrieval.common import load_chunks  # noqa: E402
from rag_hcmute.ingestion.chunk import Chunk  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run an exploratory retrieval smoke test for draft table questions. "
            "This script reports rankings only; it does not calculate benchmark metrics."
        )
    )
    parser.add_argument("--method", choices=("bm25", "dense", "both"), default="both")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument(
        "--dense-model",
        default=None,
        help="Optional local model directory or Hugging Face model ID for Dense Retrieval.",
    )
    parser.add_argument(
        "--allow-model-download",
        action="store_true",
        help="Allow Hugging Face to access the network if BGE-M3 is not cached.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROJECT_ROOT / "artifacts/results/table_retrieval_smoke",
    )
    return parser


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def _variant_chunks() -> dict[str, list[Chunk]]:
    variants_root = PROJECT_ROOT / "artifacts/results/table_variants/HCMUTE_QCDT_1727_2021_p020_t02"
    baseline = load_chunks(
        PROJECT_ROOT / "data/processed/g0_reproduction/chunks/chunks.jsonl"
    )
    t1_chunks = load_chunks(variants_root / "t1_markdown.jsonl")
    t2_chunks = load_chunks(variants_root / "t2_row_context.jsonl")

    target_chunk_id = "HCMUTE_QCDT_1727_2021__c0031"
    table_marker = "Bảng 5: Xếp hạng năm đào tạo sinh viên"
    target_positions = [
        index for index, chunk in enumerate(baseline)
        if chunk.chunk_id == target_chunk_id and table_marker in chunk.text
    ]
    if len(target_positions) != 1 or len(t1_chunks) != 1 or len(t2_chunks) != 5:
        raise SystemExit("Expected one B0 table chunk, one T1 chunk, and five T2 row chunks.")

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
        raise SystemExit("Cannot split B0 table chunk without losing surrounding or table content.")
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
    matched_t1 = before + [residual_chunk, *t1_chunks] + after
    matched_t2 = before + [residual_chunk, *t2_chunks] + after

    return {"B0": baseline, "T1": matched_t1, "T2": matched_t2}


def _candidate_targets(mapping: dict[str, str], variant: str) -> list[str]:
    if variant == "B0":
        return [mapping["b0_candidate_chunk_ids"]]
    if variant == "T1":
        return [mapping["t1_candidate_chunk_id"]]
    return [value for value in mapping["t2_candidate_chunk_ids"].split(";") if value]


def _build_retriever(method: str, chunks: list[Chunk], dense_model: str | None):
    if method == "bm25":
        return BM25Retriever(chunks), {"name": "BM25Okapi"}

    from rag_hcmute.retrieval.dense_index import (  # noqa: PLC0415
        DEFAULT_MODEL_NAME,
        DenseRetrievalUnavailable,
        DenseRetriever,
        MAX_SEQ_LENGTH,
        NORMALIZATION,
    )

    model_name = dense_model or DEFAULT_MODEL_NAME
    try:
        retriever = DenseRetriever(chunks, model_name=model_name)
    except DenseRetrievalUnavailable as error:
        return None, {
            "name": "BGE-M3 + FAISS IndexFlatIP",
            "model": model_name,
            "status": "unavailable",
            "reason": str(error),
        }
    return retriever, {
        "name": "BGE-M3 + FAISS IndexFlatIP",
        "model": model_name,
        "normalization": NORMALIZATION,
        "max_seq_length": MAX_SEQ_LENGTH,
        "device": str(retriever._model.device),
    }


def main() -> int:
    args = build_parser().parse_args()
    if args.top_k < 1:
        raise SystemExit("--top-k must be at least 1")
    if args.method in {"dense", "both"} and not args.allow_model_download:
        os.environ["HF_HUB_OFFLINE"] = "1"

    questions_path = PROJECT_ROOT / "data/question_sets/table_question_candidates_for_student_review.csv"
    mapping_path = PROJECT_ROOT / "data/question_sets/table_candidate_chunk_mapping.csv"
    questions = _read_csv(questions_path)
    mappings = {row["candidate_id"]: row for row in _read_csv(mapping_path)}
    if not questions or set(row["candidate_id"] for row in questions) != set(mappings):
        raise SystemExit("Draft questions and chunk mappings do not have matching candidate IDs.")
    if any(row["review_status"] != "draft_not_in_pilot" for row in questions):
        raise SystemExit("This smoke test accepts draft-only candidate questions.")
    if any(row["mapping_status"] != "draft_candidate_mapping" for row in mappings.values()):
        raise SystemExit("This smoke test accepts draft-only chunk mappings.")

    corpora = _variant_chunks()
    for variant, chunks in corpora.items():
        chunk_ids = {chunk.chunk_id for chunk in chunks}
        for candidate_id, mapping in mappings.items():
            missing = set(_candidate_targets(mapping, variant)) - chunk_ids
            if missing:
                raise SystemExit(
                    f"{variant} mapping for {candidate_id} refers to missing chunk IDs: "
                    f"{sorted(missing)}"
                )

    methods = ("bm25", "dense") if args.method == "both" else (args.method,)
    report = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "purpose": "exploratory retrieval smoke test for student-review draft questions",
        "status": "draft_only_no_benchmark_metrics",
        "corpus_design": "matched_background_replace_table_content_in_B0_chunk",
        "snapshot_id": "5da3bd4d5de54492",
        "top_k": args.top_k,
        "methods": [],
        "limitations": [
            "Question wording and proposed evidence locations have not been approved by the student.",
            "Per-query rankings are diagnostic only; no aggregate retrieval metric is calculated.",
            "Results do not establish that B0, T1, or T2 is generally superior.",
        ],
    }

    for method in methods:
        method_report = {"method": method, "status": "complete", "variants": []}
        for variant, chunks in corpora.items():
            retriever, config = _build_retriever(method, chunks, args.dense_model)
            if retriever is None:
                method_report["status"] = "unavailable"
                method_report["unavailable_config"] = config
                print(f"{method.upper()} unavailable; details recorded in the JSON output.")
                break
            variant_report = {
                "variant": variant,
                "chunk_count": len(chunks),
                "retrieval_config": config,
                "queries": [],
            }
            for question in questions:
                candidate_id = question["candidate_id"]
                result = retriever.query(question["question_draft"], top_k=args.top_k)
                draft_targets = _candidate_targets(mappings[candidate_id], variant)
                ranks = {
                    hit.chunk_id: hit.rank for hit in result.hits
                }
                variant_report["queries"].append(
                    {
                        "candidate_id": candidate_id,
                        "question": question["question_draft"],
                        "draft_target_chunk_ids": draft_targets,
                        "draft_target_ranks_if_retrieved": {
                            chunk_id: ranks[chunk_id]
                            for chunk_id in draft_targets
                            if chunk_id in ranks
                        },
                        "hits": [
                            {
                                "rank": hit.rank,
                                "chunk_id": hit.chunk_id,
                                "document_id": hit.document_id,
                                "pdf_page_start": hit.pdf_page_start,
                                "pdf_page_end": hit.pdf_page_end,
                                "section_path": hit.section_path,
                                "text_preview": hit.text_preview,
                            }
                            for hit in result.hits
                        ],
                    }
                )
            method_report["variants"].append(variant_report)
            del retriever
        report["methods"].append(method_report)

    run_stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_dir = args.output_dir.resolve()
    ignored_root = (PROJECT_ROOT / "artifacts/results").resolve()
    if not output_dir.is_relative_to(ignored_root):
        raise SystemExit("--output-dir must remain under artifacts/results (Git-ignored).")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"table_candidates_matched_{args.method}_{run_stamp}.json"
    with output_path.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write("\n")

    print(f"Status: {report['status']}")
    print(f"Candidates: {len(questions)} | methods: {', '.join(methods)} | top-k: {args.top_k}")
    for method_report in report["methods"]:
        print(f"\n{method_report['method'].upper()}")
        for variant_report in method_report["variants"]:
            print(f"  {variant_report['variant']} ({variant_report['chunk_count']} chunks)")
            for query in variant_report["queries"]:
                target_ranks = query["draft_target_ranks_if_retrieved"]
                rank_text = ", ".join(
                    f"{chunk_id}=#{rank}" for chunk_id, rank in target_ranks.items()
                ) or "proposed chunk not in top-k"
                print(f"    {query['candidate_id']}: {rank_text}")
    print(f"Metadata-only output: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
