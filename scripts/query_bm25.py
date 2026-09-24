from __future__ import annotations

import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_ROOT))

from rag_hcmute.retrieval.bm25_index import BM25Retriever  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Truy van BM25 tren corpus da chunk.")
    parser.add_argument("--chunks", type=Path, default=PROJECT_ROOT / "data/processed/chunks/chunks.jsonl")
    parser.add_argument("--query", type=str, required=True)
    parser.add_argument("--top-k", type=int, default=5)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if not args.chunks.is_file():
        print(f"Khong tim thay file chunks: {args.chunks}. Hay chay scripts/build_corpus.py truoc.")
        return 1

    retriever = BM25Retriever.from_snapshot(args.chunks)
    result = retriever.query(args.query, top_k=args.top_k)

    print(f"Query: {args.query!r} | latency_ms={result.latency_ms:.2f} | corpus_chunks={len(retriever.chunks)}")
    for hit in result.hits:
        print(
            f"  #{hit.rank} score={hit.score:.4f} chunk_id={hit.chunk_id} "
            f"doc={hit.document_id} page={hit.pdf_page_start}-{hit.pdf_page_end} "
            f"section={hit.section_path}"
        )
        print(f"      preview: {hit.text_preview}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
