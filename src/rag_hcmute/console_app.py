from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Callable, Sequence

from rag_hcmute.retrieval.bm25_index import BM25Retriever
from rag_hcmute.retrieval.common import RetrievalHit, load_chunks
from rag_hcmute.retrieval.reranked import RerankedRetriever
from rag_hcmute.generation.ollama import (
    DEFAULT_BASE_URL,
    DEFAULT_MODEL,
    PROMPT_VARIANTS,
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
    parser.add_argument("--dense-batch-size", type=int, default=4)
    parser.add_argument("--dense-cache", type=Path, default=PROJECT_ROOT / "artifacts/indexes/dense_console")
    parser.add_argument("--no-dense-cache", action="store_true")
    parser.add_argument("--timing-json", type=Path, help="Lưu metadata thời gian, không lưu câu hỏi hoặc văn bản nguồn.")
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
    parser.add_argument("--prompt-variant", choices=PROMPT_VARIANTS, default="standard")
    parser.add_argument("--context-window", type=int, help="Cửa sổ num_ctx của Ollama khi dùng --answer.")
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
    dense_batch_size: int = 4,
    dense_cache: Path | None = None,
    progress: Callable[[str], None] | None = None,
):
    emit = progress or (lambda _message: None)
    startup_started = time.perf_counter()
    if not chunks_path.is_file():
        raise FileNotFoundError(f"Không tìm thấy chunks file: {chunks_path}")
    chunks = load_chunks(chunks_path)
    if method == "bm25":
        if reranker_model is not None:
            raise ValueError("--reranker-model chỉ dùng với dense-rerank hoặc hybrid-rerank.")
        retriever = BM25Retriever(chunks)
        retriever.startup_metrics = {"total_seconds": time.perf_counter() - startup_started}
        return retriever
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

    dense = DenseRetriever(chunks, model_name=str(model_path), batch_size=dense_batch_size,
                           cache_dir=dense_cache, progress=emit)
    base_method = method.removesuffix("-rerank")
    if base_method == "dense":
        base_retriever = dense
    else:
        from rag_hcmute.retrieval.hybrid import ReciprocalRankFusionRetriever  # noqa: PLC0415

        base_retriever = ReciprocalRankFusionRetriever(
            BM25Retriever(chunks), dense, rank_constant=60, candidate_k=RERANKER_CANDIDATE_DEPTH
        )

    if not use_reranker:
        base_retriever.startup_metrics = {"dense": dense.startup_metrics,
                                         "total_seconds": time.perf_counter() - startup_started}
        return base_retriever

    from rag_hcmute.evaluation.reranker import LocalCrossEncoderReranker  # noqa: PLC0415

    emit("Reranker: loading local cross-encoder...")
    reranker = LocalCrossEncoderReranker(
        reranker_path,
        max_length=reranker_max_length,
        batch_size=reranker_batch_size,
    )
    retriever = RerankedRetriever(
        base_retriever, reranker, chunks, candidate_depth=RERANKER_CANDIDATE_DEPTH
    )
    retriever.startup_metrics = {"dense": dense.startup_metrics,
                               "reranker_load_seconds": reranker.load_seconds,
                               "total_seconds": time.perf_counter() - startup_started}
    return retriever


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


def _retrieval_models(retriever) -> list:
    models = []
    dense_model = getattr(retriever, "_model", None)
    if dense_model is not None:
        models.append(dense_model)
    reranker = getattr(retriever, "reranker", None)
    if reranker is not None:
        models.append(reranker.model)
    for name in ("base_retriever", "dense_retriever"):
        nested = getattr(retriever, name, None)
        if nested is not None:
            models.extend(_retrieval_models(nested))
    return models


def _move_retrieval_models(retriever, device: str) -> float:
    """Share a small GPU sequentially between retrieval models and local LLM."""
    started = time.perf_counter()
    models = _retrieval_models(retriever)
    if models:
        import torch

        if device == "cuda" and not torch.cuda.is_available():
            device = "cpu"
        for model in models:
            model.to(device)
        if torch.cuda.is_available():
            torch.cuda.synchronize()
            if device == "cpu":
                torch.cuda.empty_cache()
    return (time.perf_counter() - started) * 1000


def _run_one(
    retriever,
    *,
    method: str,
    query: str,
    top_k: int,
    answer: bool = False,
    generator_model: str = DEFAULT_MODEL,
    prompt_variant: str = "standard",
    context_window: int | None = None,
    ollama_url: str = DEFAULT_BASE_URL,
    metrics: dict | None = None,
) -> bool:
    metrics = metrics if metrics is not None else {}
    print("Đang truy xuất và xếp hạng nguồn...", flush=True)
    if answer:
        metrics["retrieval_gpu_restore_ms"] = _move_retrieval_models(retriever, "cuda")
    result = retriever.query(query, top_k=top_k)
    metrics.update({"retrieval_total_ms": result.latency_ms, "hit_count": len(result.hits),
                    "retrieved_chunk_ids": [hit.chunk_id for hit in result.hits]})
    if hasattr(result, "reranker_latency_ms"):
        metrics.update({"retrieval_ms": result.retrieval_latency_ms,
                        "reranker_ms": result.reranker_latency_ms,
                        "truncated_pairs": result.truncated_pair_count,
                        "candidate_count": result.candidate_count})
    print(
        format_retrieval_result(
            method=method,
            result=result,
            top_k=top_k,
            include_generation_note=not answer,
        )
    )
    if not answer:
        return True

    sources = sources_from_hits(result.hits, _chunks_by_id(retriever))
    print("Chuyển model retrieval sang CPU để dành GPU cho Ollama...", flush=True)
    metrics["retrieval_gpu_release_ms"] = _move_retrieval_models(retriever, "cpu")
    print(f"Đang sinh câu trả lời local bằng {generator_model}...", flush=True)
    try:
        generated = generate_grounded_answer(
            query,
            sources,
            model=generator_model,
            base_url=ollama_url,
            keep_alive=0,
            prompt_variant=prompt_variant,
            context_window=context_window,
        )
    except (RuntimeError, ValueError) as exc:
        print(f"\nKhông tạo được câu trả lời: {exc}")
        metrics["status"] = "generation_error"
        return False

    metrics.update({"generation_ms": generated.latency_ms, "status": generated.status,
                    "abstained": generated.abstained, "citation_count": len(generated.citations),
                    "citation_ids": [source.source_id for source in generated.citations]})

    print(f"\nCâu trả lời ({generated.model}, {generated.latency_ms:.0f} ms):")
    print(generated.answer)
    if generated.citations:
        print("Nguồn được trích dẫn:")
        for source in generated.citations:
            print(f"  [{source.source_id}] {source.location_label}")
    if generated.status.startswith(("invalid_", "inconsistent_")):
        print(f"Trạng thái: đầu ra model không hợp lệ ({generated.status}); đây là lỗi kỹ thuật, không phải từ chối ngữ nghĩa.")
        return False
    if generated.abstained:
        print(f"Trạng thái: lượt chạy từ chối ({generated.status}); quyết định chưa được hiệu chỉnh.")
    else:
        print("Lưu ý: cú pháp và phạm vi citation đã được kiểm tra; mức độ hỗ trợ ngữ nghĩa chưa được xác nhận.")
    return True


def _configure_console_encoding() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")


def main(argv: Sequence[str] | None = None) -> int:
    _configure_console_encoding()
    print(f"Python executable: {sys.executable}", flush=True)
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
    if args.dense_batch_size < 1:
        parser.error("--dense-batch-size phải lớn hơn 0.")
    if not args.generator_model.strip():
        parser.error("--generator-model không được để trống.")

    run_started = time.perf_counter()
    try:
        print("Khởi tạo retrieval từ dữ liệu và model local...", flush=True)
        retriever = create_retriever(
            method=args.method,
            chunks_path=args.chunks.resolve(),
            dense_model=args.dense_model,
            reranker_model=args.reranker_model,
            reranker_max_length=args.reranker_max_length,
            reranker_batch_size=args.reranker_batch_size,
            dense_batch_size=args.dense_batch_size,
            dense_cache=None if args.no_dense_cache else args.dense_cache,
            progress=lambda message: print(message, flush=True),
        )
    except (ImportError, OSError, RuntimeError, ValueError) as exc:
        print(f"Không khởi tạo được retrieval: {exc}", file=sys.stderr)
        return 2

    print("HCMUTE RAG PoC — Retrieval Console")
    print(f"Corpus chunks: {_corpus_chunk_count(retriever)} | method: {args.method}")
    print(f"Khởi tạo: {retriever.startup_metrics['total_seconds']:.2f} giây", flush=True)
    if args.answer:
        print(
            f"Generation: Ollama cục bộ ({args.generator_model}); refusal chưa được hiệu chỉnh, "
            "citation chỉ được kiểm tra cấu trúc."
        )
    else:
        print("Chế độ hiện tại: retrieval và hiển thị nguồn; bật --answer để thử generation cục bộ.")
    if args.query is not None:
        query_metrics = {}
        succeeded = _run_one(
            retriever,
            method=args.method,
            query=args.query.strip(),
            top_k=args.top_k,
            answer=args.answer,
            generator_model=args.generator_model,
            prompt_variant=args.prompt_variant,
            context_window=args.context_window,
            ollama_url=args.ollama_url,
            metrics=query_metrics,
        )
        if args.timing_json is not None:
            args.timing_json.parent.mkdir(parents=True, exist_ok=True)
            args.timing_json.write_text(json.dumps({
                "method": args.method, "top_k": args.top_k,
                "generator_model": args.generator_model if args.answer else None,
                "chunks": _corpus_chunk_count(retriever),
                "startup": retriever.startup_metrics, "query": query_metrics,
                "total_seconds": time.perf_counter() - run_started,
                "success": succeeded,
            }, indent=2, ensure_ascii=False), encoding="utf-8")
        return 0 if succeeded else 3

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
            prompt_variant=args.prompt_variant,
            context_window=args.context_window,
            ollama_url=args.ollama_url,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
