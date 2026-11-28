"""Kịch bản demo console để quay video: năm câu, cấu hình RRF đã chốt, dừng giữa các câu.

Không đổi pipeline: dùng lại create_retriever và _run_one của console_app. Chỉ thêm
warm-up, che email/số điện thoại trên màn hình và in thứ hạng từng nhánh của RRF.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
import time
from pathlib import Path

from rag_hcmute import console_app
from rag_hcmute.console_app import DEFAULT_CHUNKS_PATH, FUSION_BRANCH_DEPTH, create_retriever

DEFAULT_DENSE_MODEL = Path(
    r"D:\RAG\models\huggingface\hub\models--BAAI--bge-m3\snapshots"
    r"\5617a9f61b028005a4858fdac845db406aefb181"
)

QUESTIONS = [
    ("Thủ tục xin nghỉ học tạm thời được quy định ra sao?",
     "Câu có căn cứ rõ: đối chiếu Điều 17, QĐ 1727, trang PDF 23–24."),
    ("So sánh thời gian thiết kế và số tín chỉ tối thiểu của cử nhân chính quy và vừa làm vừa học theo bảng 1.",
     "Câu đọc bảng: số liệu nằm ở Bảng 1, trang PDF 3; để ý nhãn Điều trong metadata."),
    ("Điều kiện để đăng ký học chương trình thứ hai là gì?",
     "Câu nhiều điều kiện: Điều 20, trang PDF 25–26; kiểm tra câu trả lời có đủ các điều kiện không."),
    ("Thư viện công cộng ở Cần Thơ mở cửa sáng Chủ nhật lúc mấy giờ?",
     "Câu ngoài phạm vi: kho HCMUTE không có thông tin này, hệ thống cần từ chối."),
    ("Đã học môn A nhưng chưa đạt, điều kiện đăng ký môn B khi A là học trước hoặc tiên quyết là gì?",
     "Câu phân biệt hai khái niệm: Điều 3, trang PDF 5; kiểm tra có tách học trước và tiên quyết không."),
]

_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
_PHONE = re.compile(r"(?<!\d)(?:\+?84|0)(?:[\s.]?\d){8,10}(?!\d)")


def mask_contacts(text: str) -> str:
    return _PHONE.sub("[SĐT đã che]", _EMAIL.sub("[email đã che]", text))


def _install_masking() -> None:
    original = console_app._format_hit

    def masked(hit):
        return [mask_contacts(line) for line in original(hit)]

    console_app._format_hit = masked


def _clear_screen() -> None:
    os.system("cls" if os.name == "nt" else "clear")


def _print_branch_ranks(retriever, query: str, top_k: int) -> None:
    lexical = {h.chunk_id: h.rank for h in retriever.lexical_retriever.query(query, top_k=FUSION_BRANCH_DEPTH).hits}
    dense = {h.chunk_id: h.rank for h in retriever.dense_retriever.query(query, top_k=FUSION_BRANCH_DEPTH).hits}
    fused = retriever.query(query, top_k=top_k).hits
    print("\nThứ hạng từng nhánh trước khi hợp bằng RRF (ngoài Top-50 ghi '-'):")
    for hit in fused:
        print(f"  RRF #{hit.rank}: BM25 #{lexical.get(hit.chunk_id, '-')} | "
              f"BGE-M3 #{dense.get(hit.chunk_id, '-')} | {hit.chunk_id}")


def main(argv=None) -> int:
    console_app._configure_console_encoding()
    print(f"Python executable: {sys.executable}", flush=True)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dense-model", type=Path, default=DEFAULT_DENSE_MODEL)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--no-pause", action="store_true", help="Chạy liền không chờ Enter (để chạy thử).")
    parser.add_argument("--no-clear", action="store_true", help="Không xóa màn hình sau warm-up.")
    args = parser.parse_args(argv)

    _install_masking()
    print("Warm-up: nạp dữ liệu, BGE-M3 và Qwen3 (không tính vào video)...", flush=True)
    started = time.perf_counter()
    retriever = create_retriever(method="hybrid", chunks_path=DEFAULT_CHUNKS_PATH.resolve(),
                                 dense_model=args.dense_model,
                                 dense_cache=console_app.PROJECT_ROOT / "artifacts/indexes/dense_console")
    console_app._run_one(retriever, method="hybrid", query="Học kỳ phụ là gì?", top_k=1, answer=True,
                         prompt_variant="scope_schema", context_window=8192)
    print(f"Warm-up xong sau {time.perf_counter() - started:.1f} giây.", flush=True)
    if not args.no_pause:
        input("\nSẵn sàng quay. Nhấn Enter để bắt đầu...")
    if not args.no_clear:
        _clear_screen()

    print("HCMUTE RAG — Tìm hiểu Retrieval Augmented Generation (RAG)")
    print(f"Cấu hình: BM25 + BGE-M3, RRF k=60, {FUSION_BRANCH_DEPTH} ứng viên mỗi nhánh, "
          "không reranker | Qwen3:4B + JSON Schema, context 8.192 | chạy cục bộ")
    print(f"Kho: {console_app._corpus_chunk_count(retriever)} đoạn từ 3 văn bản học vụ HCMUTE (snapshot G0)")

    timings = []
    for index, (question, note) in enumerate(QUESTIONS, start=1):
        print("\n" + "=" * 78)
        print(f"Câu {index}/{len(QUESTIONS)}: {question}")
        print(f"Điều cần quan sát: {note}")
        print("=" * 78, flush=True)
        t0 = time.perf_counter()
        console_app._run_one(retriever, method="hybrid", query=question, top_k=args.top_k, answer=True,
                             prompt_variant="scope_schema", context_window=8192)
        timings.append(time.perf_counter() - t0)
        _print_branch_ranks(retriever, question, args.top_k)
        if not args.no_pause and index < len(QUESTIONS):
            input("\nNhấn Enter để sang câu tiếp...")

    print("\nKết thúc demo. Thời gian từng câu (giây): " + "; ".join(f"{t:.1f}" for t in timings))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
