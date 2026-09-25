from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_ROOT))

from rag_hcmute.evaluation.run_pilot import run_pilot_evaluation  # noqa: E402
from rag_hcmute.retrieval.bm25_index import BM25Retriever  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Chay retrieval tren bo cau hoi pilot va tinh Recall@5 / MRR.")
    parser.add_argument("--questions", type=Path, default=PROJECT_ROOT / "data/question_sets/pilot_questions.csv")
    parser.add_argument("--chunks", type=Path, default=PROJECT_ROOT / "data/processed/chunks/chunks.jsonl")
    parser.add_argument("--snapshot-manifest", type=Path, default=PROJECT_ROOT / "data/manifests/corpus_snapshot.json")
    parser.add_argument("--method", choices=["bm25", "dense"], default="bm25")
    parser.add_argument("--dense-model", type=str, default=None)
    parser.add_argument("--output-dir", type=Path, default=PROJECT_ROOT / "docs/evidence/runs")
    return parser


def main() -> int:
    args = build_parser().parse_args()

    if not args.chunks.is_file():
        print(f"Khong tim thay {args.chunks}. Hay chay scripts/build_corpus.py truoc.")
        return 1

    snapshot_id = "unknown"
    if args.snapshot_manifest.is_file():
        snapshot_id = json.loads(args.snapshot_manifest.read_text(encoding="utf-8"))["snapshot_id"]

    config: dict = {}
    if args.method == "bm25":
        retriever = BM25Retriever.from_snapshot(args.chunks)
        method_name = "bm25"
        from rag_hcmute.retrieval.bm25_index import BM25_LIBRARY

        config = {"library": BM25_LIBRARY, "tokenizer": "regex_\\w+_unicode_lowercase"}
    else:
        from rag_hcmute.retrieval.dense_index import (
            DEFAULT_MODEL_NAME,
            MAX_SEQ_LENGTH,
            NORMALIZATION,
            DenseRetrievalUnavailable,
            DenseRetriever,
        )

        model_name = args.dense_model or DEFAULT_MODEL_NAME
        try:
            retriever = DenseRetriever.from_snapshot(args.chunks, model_name=model_name)
        except DenseRetrievalUnavailable as exc:
            args.output_dir.mkdir(parents=True, exist_ok=True)
            status_path = args.output_dir / f"dense_unavailable_{snapshot_id}.json"
            status_path.write_text(
                json.dumps({"status": "unavailable", "model": model_name, "reason": str(exc)}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            print("DENSE_RETRIEVAL_UNAVAILABLE")
            print(str(exc))
            print(f"Da ghi trang thai vao {status_path}")
            return 2
        method_name = "dense_bge_m3"
        config = {
            "model": model_name,
            "embedding_dim": retriever._dim,
            "normalization": NORMALIZATION,
            "faiss_index": "IndexFlatIP",
            "max_seq_length": MAX_SEQ_LENGTH,
            "query_instruction_prefix": "khong_can (theo model card BAAI/bge-m3, khac cac ban BGE truoc)",
        }

    report = run_pilot_evaluation(
        questions_path=args.questions,
        chunks_path=args.chunks,
        snapshot_id=snapshot_id,
        method_name=method_name,
        retriever=retriever,
        config=config,
    )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    raw_path = args.output_dir / f"{report['run_id']}.json"
    raw_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    recall = report["metrics"]["recall_at_5"]
    mrr = report["metrics"]["mrr"]
    print(f"Method: {method_name} | snapshot: {snapshot_id}")
    print(f"Recall@5 = {recall['value']:.3f} ({recall['hits']}/{recall['denominator']})")
    print(f"MRR@{report['metrics']['mrr']['considered_top_k']} = {mrr['value']:.3f} (n={mrr['denominator']})")
    print(f"Raw results: {raw_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
