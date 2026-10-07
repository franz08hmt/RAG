from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Sequence

from rag_hcmute.retrieval.bm25_index import BM25Retriever
from rag_hcmute.retrieval.common import RetrievalHit, load_chunks

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CHUNKS_PATH = PROJECT_ROOT / "data/processed/g0_reproduction/chunks/chunks.jsonl"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Console PoC để quan sát retrieval trên corpus học vụ HCMUTE; chưa sinh câu trả lời."
    )
    parser.add_argument("--chunks", type=Path, default=DEFAULT_CHUNKS_PATH)
    parser.add_argument("--method", choices=("bm25", "dense", "hybrid"), default="bm25")
    parser.add_argument("--dense-model", type=Path, help="Thư mục model BGE-M3 đã có sẵn; không tải model.")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--query", help="Chạy một truy vấn rồi thoát; nếu bỏ trống thì mở chế độ tương tác.")
    return parser


def create_retriever(*, method: str, chunks_path: Path, dense_model: Path | None = None):
    if not chunks_path.is_file():
        raise FileNotFoundError(f"Không tìm thấy chunks file: {chunks_path}")
    chunks = load_chunks(chunks_path)
    if method == "bm25":
        return BM25Retriever(chunks)
    if method not in {"dense", "hybrid"}:
        raise ValueError(f"Phương thức retrieval không được hỗ trợ: {method}")
    if dense_model is None:
        raise ValueError("Dense/Hybrid cần --dense-model trỏ tới thư mục model đã tải sẵn.")

    model_path = dense_model.resolve()
    if not model_path.is_dir():
        raise FileNotFoundError(f"Không tìm thấy model local: {model_path}; không có tải tự động.")

    # Chỉ dùng model có trên máy; không cho thư viện tự tải từ Hugging Face.
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    from rag_hcmute.retrieval.dense_index import DenseRetriever  # noqa: PLC0415

    dense = DenseRetriever(chunks, model_name=str(model_path))
    if method == "dense":
        return dense

    from rag_hcmute.retrieval.hybrid import ReciprocalRankFusionRetriever  # noqa: PLC0415

    return ReciprocalRankFusionRetriever(
        BM25Retriever(chunks), dense, rank_constant=60, candidate_k=20
    )


def format_retrieval_result(*, method: str, result, top_k: int) -> str:
    method_label = {
        "bm25": "BM25Okapi (lexical retrieval)",
        "dense": "BGE-M3 + FAISS (dense retrieval)",
        "hybrid": "BM25 + BGE-M3, RRF k=60 (hybrid retrieval)",
    }.get(method, method)
    lines = [
        f"Phương thức: {method_label} | Top-{top_k} | thời gian truy xuất: {result.latency_ms:.2f} ms",
        f"Số chunk trả về: {len(result.hits)}",
    ]
    if not result.hits:
        lines.append("Retriever không trả về ứng viên trong lần chạy này.")
    for hit in result.hits:
        lines.extend(_format_hit(hit))
    lines.append("Lưu ý: đây là kết quả retrieval, chưa phải câu trả lời do LLM sinh.")
    return "\n".join(lines)


def _corpus_chunk_count(retriever) -> int:
    chunks = getattr(retriever, "chunks", None)
    if chunks is not None:
        return len(chunks)
    lexical_retriever = getattr(retriever, "lexical_retriever", None)
    if lexical_retriever is not None:
        return len(lexical_retriever.chunks)
    raise TypeError("Retriever does not expose its indexed corpus size.")


def _format_hit(hit: RetrievalHit) -> list[str]:
    page_label = (
        f"PDF trang {hit.pdf_page_start}"
        if hit.pdf_page_start == hit.pdf_page_end
        else f"PDF trang {hit.pdf_page_start}–{hit.pdf_page_end}"
    )
    section = hit.section_path or "(không có metadata điều/mục)"
    preview = " ".join(hit.text_preview.split())
    return [
        f"\n[{hit.rank}] {hit.document_title} | {page_label} | {section}",
        f"    document_id={hit.document_id} | chunk_id={hit.chunk_id} | score={hit.score:.4f}",
        f"    Trích đoạn: {preview}",
    ]


def _run_one(retriever, *, method: str, query: str, top_k: int) -> None:
    result = retriever.query(query, top_k=top_k)
    print(format_retrieval_result(method=method, result=result, top_k=top_k))


def _configure_console_encoding() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")


def main(argv: Sequence[str] | None = None) -> int:
    _configure_console_encoding()
    print(f"Python executable: {sys.executable}")
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.top_k < 1:
        parser.error("--top-k phải lớn hơn 0.")
    if args.query is not None and not args.query.strip():
        parser.error("--query không được để trống.")

    try:
        retriever = create_retriever(
            method=args.method,
            chunks_path=args.chunks.resolve(),
            dense_model=args.dense_model,
        )
    except (ImportError, OSError, RuntimeError, ValueError) as exc:
        print(f"Không khởi tạo được retrieval: {exc}", file=sys.stderr)
        return 2

    print("HCMUTE RAG PoC — Retrieval Console")
    print(f"Corpus chunks: {_corpus_chunk_count(retriever)} | method: {args.method}")
    print("Phạm vi bản hiện tại: truy xuất và hiển thị nguồn, chưa có generation/refusal guard.")
    if args.query is not None:
        _run_one(retriever, method=args.method, query=args.query.strip(), top_k=args.top_k)
        return 0

    print("Nhập câu hỏi tiếng Việt; gõ :q để thoát.")
    while True:
        try:
            query = input("\nCâu hỏi> ").strip()
        except EOFError:
            print("\nĐã kết thúc phiên console.")
            break
        if query.lower() in {":q", ":quit", "quit", "exit"}:
            print("Đã kết thúc phiên console.")
            break
        if not query:
            continue
        _run_one(retriever, method=args.method, query=query, top_k=args.top_k)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
