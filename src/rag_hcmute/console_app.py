from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Sequence

from rag_hcmute.retrieval.bm25_index import BM25Retriever
from rag_hcmute.retrieval.common import RetrievalHit, load_chunks
from rag_hcmute.retrieval.reranked import RerankedRetriever
from rag_hcmute.generation.ollama import (
    DEFAULT_BASE_URL,
    DEFAULT_MODEL,
    generate_grounded_answer,
    sources_from_hits,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CHUNKS_PATH = PROJECT_ROOT / "data/processed/g0_reproduction/chunks/chunks.jsonl"
APPROVED_RERANKER_REVISION = "953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e"
RERANKER_CANDIDATE_DEPTH = 20


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Console PoC để quan sát retrieval và thử generation local trên corpus học vụ HCMUTE; "
            "chất lượng câu trả lời, citation ngữ nghĩa và refusal chưa được xác nhận."
        )
    )
    parser.add_argument("--chunks", type=Path, default=DEFAULT_CHUNKS_PATH)
    parser.add_argument(
        "--method",
        choices=("bm25", "dense", "hybrid", "dense-rerank", "hybrid-rerank"),
        default="bm25",
    )
    parser.add_argument("--dense-model", type=Path, help="Thư mục model BGE-M3 đã có sẵn; không tải model.")
    parser.add_argument(
        "--reranker-model",
        type=Path,
        help="Thư mục snapshot BGE-Reranker-v2-m3 đã tải sẵn; không tải model.",
    )
    parser.add_argument("--reranker-max-length", type=int, default=512)
    parser.add_argument("--reranker-batch-size", type=int, default=4)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument(
        "--answer",
        action="store_true",
        help="Sinh câu trả lời bám nguồn bằng Ollama chạy cục bộ (không gọi cloud API).",
    )
    parser.add_argument("--generator-model", default=DEFAULT_MODEL)
    parser.add_argument("--ollama-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--query", help="Chạy một truy vấn rồi thoát; nếu bỏ trống thì mở chế độ tương tác.")
    return parser


def create_retriever(
    *,
    method: str,
    chunks_path: Path,
    dense_model: Path | None = None,
    reranker_model: Path | None = None,
    reranker_max_length: int = 512,
    reranker_batch_size: int = 4,
):
    if not chunks_path.is_file():
        raise FileNotFoundError(f"Không tìm thấy chunks file: {chunks_path}")
    chunks = load_chunks(chunks_path)
    if method == "bm25":
        if reranker_model is not None:
            raise ValueError("--reranker-model chỉ dùng với dense-rerank hoặc hybrid-rerank.")
        return BM25Retriever(chunks)
    supported_methods = {"dense", "hybrid", "dense-rerank", "hybrid-rerank"}
    if method not in supported_methods:
        raise ValueError(f"Phương thức retrieval không được hỗ trợ: {method}")
    use_reranker = method.endswith("-rerank")
    if not use_reranker and reranker_model is not None:
        raise ValueError("--reranker-model chỉ dùng với dense-rerank hoặc hybrid-rerank.")
    if dense_model is None:
        raise ValueError("Dense/Hybrid cần --dense-model trỏ tới thư mục model đã tải sẵn.")

    model_path = dense_model.resolve()
    if not model_path.is_dir():
        raise FileNotFoundError(f"Không tìm thấy model local: {model_path}; không có tải tự động.")
    reranker_path = None
    if use_reranker:
        if reranker_model is None:
            raise ValueError("Dense/Hybrid rerank cần --reranker-model trỏ tới snapshot local đã duyệt.")
        reranker_path = reranker_model.resolve()
        if not reranker_path.is_dir():
            raise FileNotFoundError(
                f"Không tìm thấy reranker local: {reranker_path}; không có tải tự động."
            )
        if (
            reranker_path.name != APPROVED_RERANKER_REVISION
            or not (reranker_path / "model.safetensors").is_file()
        ):
            raise ValueError(
                "Reranker phải là snapshot BAAI/bge-reranker-v2-m3 đã duyệt "
                f"(revision {APPROVED_RERANKER_REVISION}) với model.safetensors local."
            )

    # Chỉ dùng model có trên máy; không cho thư viện tự tải từ Hugging Face.
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    from rag_hcmute.retrieval.dense_index import DenseRetriever  # noqa: PLC0415

    dense = DenseRetriever(chunks, model_name=str(model_path))
    base_method = method.removesuffix("-rerank")
    if base_method == "dense":
        base_retriever = dense
    else:
        from rag_hcmute.retrieval.hybrid import ReciprocalRankFusionRetriever  # noqa: PLC0415

        base_retriever = ReciprocalRankFusionRetriever(
            BM25Retriever(chunks), dense, rank_constant=60, candidate_k=RERANKER_CANDIDATE_DEPTH
        )

    if not use_reranker:
        return base_retriever

    from rag_hcmute.evaluation.reranker import LocalCrossEncoderReranker  # noqa: PLC0415

    reranker = LocalCrossEncoderReranker(
        reranker_path,
        max_length=reranker_max_length,
        batch_size=reranker_batch_size,
    )
    return RerankedRetriever(
        base_retriever, reranker, chunks, candidate_depth=RERANKER_CANDIDATE_DEPTH
    )


def format_retrieval_result(
    *, method: str, result, top_k: int, include_generation_note: bool = True
) -> str:
    method_label = {
        "bm25": "BM25Okapi (lexical retrieval)",
        "dense": "BGE-M3 + FAISS (dense retrieval)",
        "hybrid": "BM25 + BGE-M3, RRF k=60 (hybrid retrieval)",
        "dense-rerank": "BGE-M3 Top-20 + BGE-Reranker-v2-m3",
        "hybrid-rerank": "BM25 + BGE-M3 Top-20, RRF k=60 + BGE-Reranker-v2-m3",
    }.get(method, method)
    latency_label = (
        "retrieval + rerank"
        if hasattr(result, "candidate_count")
        else "truy xuất"
    )
    lines = [
        f"Phương thức: {method_label} | Top-{top_k} | thời gian {latency_label}: {result.latency_ms:.2f} ms",
        f"Số chunk trả về: {len(result.hits)}",
    ]
    if hasattr(result, "candidate_count"):
        lines.append(
            f"Candidate pool: {result.candidate_count}/{result.candidate_depth} | "
            f"retrieval: {result.retrieval_latency_ms:.2f} ms | "
            f"reranker: {result.reranker_latency_ms:.2f} ms | "
            f"cặp bị cắt do max_length: {result.truncated_pair_count}/{result.pair_count}"
        )
    if not result.hits:
        lines.append("Retriever không trả về ứng viên trong lần chạy này.")
    for hit in result.hits:
        lines.extend(_format_hit(hit))
    if include_generation_note:
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


def _chunks_by_id(retriever) -> dict:
    chunks = getattr(retriever, "chunks", None)
    if chunks is None:
        lexical_retriever = getattr(retriever, "lexical_retriever", None)
        chunks = getattr(lexical_retriever, "chunks", None)
    if chunks is None:
        raise TypeError("Retriever does not expose chunks needed for source-grounded generation.")
    return {chunk.chunk_id: chunk for chunk in chunks}


def _run_one(
    retriever,
    *,
    method: str,
    query: str,
    top_k: int,
    answer: bool = False,
    generator_model: str = DEFAULT_MODEL,
    ollama_url: str = DEFAULT_BASE_URL,
) -> None:
    result = retriever.query(query, top_k=top_k)
    print(
        format_retrieval_result(
            method=method,
            result=result,
            top_k=top_k,
            include_generation_note=not answer,
        )
    )
    if not answer:
        return

    sources = sources_from_hits(result.hits, _chunks_by_id(retriever))
    try:
        generated = generate_grounded_answer(
            query,
            sources,
            model=generator_model,
            base_url=ollama_url,
        )
    except (RuntimeError, ValueError) as exc:
        print(f"\nKhông tạo được câu trả lời: {exc}")
        return

    print(f"\nCâu trả lời ({generated.model}, {generated.latency_ms:.0f} ms):")
    print(generated.answer)
    if generated.citations:
        print("Nguồn được trích dẫn:")
        for source in generated.citations:
            print(f"  [{source.source_id}] {source.location_label}")
    if generated.abstained:
        print(f"Trạng thái: lượt chạy từ chối ({generated.status}); quyết định chưa được hiệu chỉnh.")
    else:
        print("Lưu ý: cú pháp và phạm vi citation đã được kiểm tra; mức độ hỗ trợ ngữ nghĩa chưa được xác nhận.")


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
    if args.reranker_max_length < 8:
        parser.error("--reranker-max-length phải tối thiểu 8 token.")
    if args.reranker_batch_size < 1:
        parser.error("--reranker-batch-size phải lớn hơn 0.")
    if not args.generator_model.strip():
        parser.error("--generator-model không được để trống.")

    try:
        retriever = create_retriever(
            method=args.method,
            chunks_path=args.chunks.resolve(),
            dense_model=args.dense_model,
            reranker_model=args.reranker_model,
            reranker_max_length=args.reranker_max_length,
            reranker_batch_size=args.reranker_batch_size,
        )
    except (ImportError, OSError, RuntimeError, ValueError) as exc:
        print(f"Không khởi tạo được retrieval: {exc}", file=sys.stderr)
        return 2

    print("HCMUTE RAG PoC — Retrieval Console")
    print(f"Corpus chunks: {_corpus_chunk_count(retriever)} | method: {args.method}")
    if args.answer:
        print(
            f"Generation: Ollama cục bộ ({args.generator_model}); refusal chưa được hiệu chỉnh, "
            "citation chỉ được kiểm tra cấu trúc."
        )
    else:
        print("Chế độ hiện tại: retrieval và hiển thị nguồn; bật --answer để thử generation cục bộ.")
    if args.query is not None:
        _run_one(
            retriever,
            method=args.method,
            query=args.query.strip(),
            top_k=args.top_k,
            answer=args.answer,
            generator_model=args.generator_model,
            ollama_url=args.ollama_url,
        )
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
        _run_one(
            retriever,
            method=args.method,
            query=query,
            top_k=args.top_k,
            answer=args.answer,
            generator_model=args.generator_model,
            ollama_url=args.ollama_url,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
