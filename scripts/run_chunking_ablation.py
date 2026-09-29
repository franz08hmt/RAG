from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

print(f"Python executable: {sys.executable}")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from rag_hcmute.evaluation.chunking_ablation import (  # noqa: E402
    chunk_profile,
    derive_gold_locations,
    evaluate_location_retrieval,
    serialize_location,
)
from rag_hcmute.evaluation.run_pilot import load_pilot_questions  # noqa: E402
from rag_hcmute.ingestion.chunk import chunk_document  # noqa: E402
from rag_hcmute.ingestion.clean import clean_document_pages  # noqa: E402
from rag_hcmute.ingestion.extract import read_pages_jsonl  # noqa: E402
from rag_hcmute.retrieval.bm25_index import BM25Retriever  # noqa: E402
from rag_hcmute.retrieval.common import load_chunks  # noqa: E402


CONFIGS = ((250, 40), (500, 80), (750, 120))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run a local chunk-size sensitivity test. Relevance is mapped from verified "
            "baseline chunk IDs to stable section/page locations."
        )
    )
    parser.add_argument(
        "--source-root",
        type=Path,
        default=PROJECT_ROOT / "data/processed/g0_reproduction",
        help="Native-only extracted pages, baseline chunks, and snapshot.json directory.",
    )
    parser.add_argument(
        "--questions",
        type=Path,
        default=PROJECT_ROOT / "data/question_sets/pilot_questions.csv",
    )
    parser.add_argument("--method", choices=("bm25", "dense"), default="bm25")
    parser.add_argument("--dense-model", default=None)
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROJECT_ROOT / "artifacts/results/chunking_ablation",
    )
    return parser


def _retriever_for(method: str, chunks, dense_model: str | None):
    if method == "bm25":
        return BM25Retriever(chunks), {"method": "BM25Okapi", "tokenizer": "unicode_word_regex_lowercase"}

    from rag_hcmute.retrieval.dense_index import (
        DEFAULT_MODEL_NAME,
        MAX_SEQ_LENGTH,
        NORMALIZATION,
        DenseRetriever,
    )

    model_name = dense_model or DEFAULT_MODEL_NAME
    retriever = DenseRetriever(chunks, model_name=model_name)
    return retriever, {
        "method": "BGE-M3 + FAISS IndexFlatIP",
        "model": model_name,
        "embedding_dim": retriever._dim,
        "max_seq_length": MAX_SEQ_LENGTH,
        "normalization": NORMALIZATION,
        "device": str(retriever._model.device),
    }


def _dense_input_profile(retriever, chunks) -> dict:
    """Measure model-tokenizer lengths without storing source text."""
    tokenizer = retriever._model.tokenizer
    limit = retriever._model.max_seq_length
    grouped: dict[str, list[int]] = {}
    for chunk in chunks:
        length = len(
            tokenizer(chunk.text, add_special_tokens=True, truncation=False)["input_ids"]
        )
        grouped.setdefault(chunk.document_id, []).append(length)

    all_lengths = [length for lengths in grouped.values() for length in lengths]
    ordered = sorted(all_lengths)
    return {
        "tokenizer_input_limit": limit,
        "chunks_over_limit": sum(length > limit for length in all_lengths),
        "chunk_count": len(all_lengths),
        "subword_min": ordered[0],
        "subword_median": ordered[len(ordered) // 2],
        "subword_p95": ordered[int(0.95 * (len(ordered) - 1))],
        "subword_max": ordered[-1],
        "by_document": {
            document_id: {
                "chunk_count": len(lengths),
                "chunks_over_limit": sum(length > limit for length in lengths),
                "subword_max": max(lengths),
            }
            for document_id, lengths in grouped.items()
        },
    }


def main() -> int:
    args = build_parser().parse_args()
    source_root = args.source_root.resolve()
    snapshot_path = source_root / "snapshot.json"
    chunks_path = source_root / "chunks" / "chunks.jsonl"
    if not snapshot_path.is_file() or not chunks_path.is_file():
        raise SystemExit(f"Missing baseline snapshot/chunks under {source_root}")

    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    if snapshot.get("config", {}).get("ocr", {}).get("enabled", False):
        raise SystemExit("This ablation expects the native-only G0 snapshot; OCR must be disabled.")
    baseline_chunks = load_chunks(chunks_path)
    questions = load_pilot_questions(args.questions)
    locations = derive_gold_locations(questions, baseline_chunks)
    if not locations:
        raise SystemExit("No answerable questions with verified baseline gold chunks were found.")

    report = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "snapshot_id": snapshot["snapshot_id"],
        "method": args.method,
        "retrieval_config": {},
        "gold_mapping": {
            "source": "verified expected_chunk_id values in the baseline pilot set",
            "rule": "same section_path for structured gold; source PDF page for unstructured gold",
            "metric_scope": "section/page location proxy; not exact evidence-chunk recall",
            "locations": {
                question_id: serialize_location(location)
                for question_id, location in locations.items()
            },
        },
        "configs": [],
    }

    for chunk_tokens, overlap_tokens in CONFIGS:
        config_chunks = []
        for document in snapshot["documents"]:
            document_id = document["document_id"]
            page_path = source_root / "pages" / f"{document_id}.jsonl"
            pages = read_pages_jsonl(page_path)
            cleaned_pages, _ = clean_document_pages(pages)
            config_chunks.extend(
                chunk_document(
                    cleaned_pages,
                    document_id,
                    document["document_title"],
                    chunk_tokens=chunk_tokens,
                    overlap_tokens=overlap_tokens,
                )
            )

        retriever, retrieval_config = _retriever_for(
            args.method, config_chunks, args.dense_model
        )
        if not report["retrieval_config"]:
            report["retrieval_config"] = retrieval_config
        result = evaluate_location_retrieval(
            questions=questions,
            locations=locations,
            chunks=config_chunks,
            retriever=retriever,
            top_k=args.top_k,
        )
        if args.method == "dense":
            result["encoder_input_profile"] = _dense_input_profile(retriever, config_chunks)
        report["configs"].append(
            {
                "chunk_tokens": chunk_tokens,
                "overlap_tokens": overlap_tokens,
                "chunk_count": len(config_chunks),
                "profile": chunk_profile(config_chunks),
                "retrieval": result,
            }
        )
        del retriever

    run_stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{args.method}_{snapshot['snapshot_id']}_{run_stamp}.json"
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Snapshot: {snapshot['snapshot_id']} | method: {args.method}")
    for item in report["configs"]:
        metric = item["retrieval"]["hit_at_5"]
        mrr = item["retrieval"]["mrr_at_10"]
        print(
            f"chunk={item['chunk_tokens']}/{item['overlap_tokens']} | "
            f"chunks={item['chunk_count']} | section/page Hit@5="
            f"{metric['hits']}/{metric['denominator']} ({metric['value']:.3f}) | "
            f"section/page MRR@10={mrr['value']:.3f}"
        )
        if args.method == "dense":
            profile = item["retrieval"]["encoder_input_profile"]
            print(
                f"  BGE subword max={profile['subword_max']} | "
                f"over {profile['tokenizer_input_limit']}={profile['chunks_over_limit']}"
            )
    print(f"Metadata-only results: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
