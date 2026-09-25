# Bàn giao mốc 1 (4 tuần đầu) — RAG HCMUTE PoC

Ngày viết: 24/09/2026, cập nhật 25/09/2026 (kết quả Dense Retrieval thật + gộp báo cáo). Branch:
`claude/nifty-dirac-h6u5b6`. Xem `git log` trên nhánh này cho commit cụ thể của đợt bàn giao (commit
ngay sau file này).

## Corpus snapshot dùng cho mọi số liệu trong báo cáo

- `snapshot_id = 5da3bd4d5de54492` (`data/manifests/corpus_snapshot.json`)
- 3 tài liệu, 182 trang, 156 chunk. Chi tiết từng tài liệu: `data/manifests/corpus_manifest.csv`.
- PDF gốc và text đầy đủ theo trang/chunk **không nằm trong git** (gitignored) — xem
  `docs/decisions/ADR-002-corpus-sourcing-and-redistribution.md` để biết lý do và cách tái lập.

## Lệnh chạy để tái lập từ đầu (cần có lại 3 PDF khớp SHA-256 trong manifest, đặt vào `data/raw/`)

```bash
pip install -e ".[dev]"
pip install -e ".[dense]"        # them cho Dense Retrieval (sentence-transformers, faiss-cpu)
python scripts/audit_corpus.py --manifest data/manifests/corpus_manifest.csv --project-root .
python scripts/build_corpus.py
python scripts/query_bm25.py --query "..." --top-k 5
python scripts/query_dense.py --query "..." --top-k 5
python scripts/run_pilot_eval.py --method bm25
python scripts/run_pilot_eval.py --method dense
pytest
python tests/run_smoke_tests.py
```

## Kết quả kiểm thử ở lần bàn giao này

- `pytest`: **20/20 PASSED** (tests/test_manifest.py, test_extract.py, test_chunk.py, test_bm25_retrieval.py).
- `python tests/run_smoke_tests.py`: **2/2 PASSED**.
- `python scripts/audit_corpus.py ...`: PASSED, "CORPUS SAN SANG" (3 tài liệu, 0 lỗi).
- `python scripts/run_pilot_eval.py --method bm25`: Recall@5 = 3/7 (0,429), MRR@10 = 0,371.
  Kết quả thô: `docs/evidence/runs/bm25_5da3bd4d5de54492_20260924T112003Z.json`.
- `python scripts/run_pilot_eval.py --method dense`: **chạy thành công** (cập nhật 25/09/2026, sau khi
  được cấp quyền mạng bổ sung) — Recall@5 = 6/7 (0,857), MRR@10 = 0,643. Kết quả thô:
  `docs/evidence/runs/dense_bge_m3_5da3bd4d5de54492_20260925T040111Z.json`. So sánh chi tiết với BM25:
  `docs/evidence/runs/metrics_summary.md`, `docs/evidence/case_studies.md`.

## Điểm chưa hoàn thành / cần làm ở mốc kế tiếp

1. **Hiệu lực `HCMUTE_QCDT_1727_2021` chưa xác định đầy đủ.** Có dấu hiệu Quyết định
   3116/QĐ-ĐHSPKT (22/08/2025) là bản thay thế nhưng chưa truy cập được toàn văn (thư viện số
   HCMUTE yêu cầu đăng nhập). Cần xác nhận trước khi coi văn bản này là nguồn hiệu lực đầy đủ.
2. **P006 (khóa luận/đồ án tốt nghiệp) chưa có gold evidence.** Nguồn đúng chủ đề nằm ở
   `fit.hcmute.edu.vn` (subdomain, bị egress-policy chặn trong phiên này, chỉ domain gốc
   `hcmute.edu.vn` được mở). Cần quyền mạng rộng hơn hoặc tự tải file rồi đính kèm.
3. **Dense Retrieval chưa tốt hơn BM25 ở mọi câu hỏi.** P002 bị Dense xếp hạng kém hơn BM25 (hạng 3
   so với hạng 1); P004 vẫn xếp ngoài Top-5 ở cả hai phương pháp. Xem `docs/evidence/case_studies.md`.
4. **Tái lập Dense Retrieval cần mở đúng 2 tên miền mạng, không chỉ 1** — `huggingface.co` (khai báo
   model) VÀ tên miền lưu trọng số thật mà Hugging Face chuyển hướng tới (trong phiên này là
   `us.aws.cdn.hf.co`, hạ tầng "Xet storage"; dùng `curl -I` xem header `Location` để xác nhận đúng
   tên miền trong môi trường khác). Chỉ mở `huggingface.co` là chưa đủ — đã mất thời gian dò lại việc
   này ở đợt 1, ghi lại đây để mốc sau/người khác không lặp lại.
5. **Không render được DOCX báo cáo thành ảnh để tự kiểm tra bằng mắt** — `soffice`/LibreOffice
   trong sandbox này không load được BẤT KỲ file nguồn nào (đã kiểm chứng cả với PDF fixture và cả
   một file .txt trơn, không riêng gì DOCX của đồ án — giới hạn ở tầng sandbox, không phải lỗi file).
   Đã thay bằng: xác thực schema OOXML (`validate.py`, PASSED), soi trực tiếp XML để xác nhận font
   Times New Roman/màu đen/không có màu nhấn/không đánh số trang/khung chỉ ở bìa/heading có
   `outlineLvl` đúng để lên Navigation Pane, và đọc lại toàn bộ nội dung qua `pandoc -t markdown`.
   **Chưa xem được bố cục trang thật (tràn chữ, ngắt trang, khoảng trắng)** — người nhận bàn giao
   nên mở thử bằng Word/LibreOffice thật trước khi nộp.
6. **Corpus nhỏ (156 chunk) và lệch kích thước tài liệu** — ảnh hưởng đến chất lượng xếp hạng BM25
   (xem case study P005 trong `docs/evidence/case_studies.md`). Nên mở rộng corpus ở mốc sau.
7. **Mẫu đánh giá nhỏ (7 câu answerable)** — cần bộ câu hỏi lớn hơn để số liệu ổn định cho cả BM25
   lẫn Dense.
8. Hybrid retrieval (RRF), reranker, refusal guard đã hiệu chỉnh (cho cả điểm BM25 lẫn cosine Dense),
   generation (LLM), API và giao diện: **hoàn toàn chưa triển khai**, đúng phạm vi đã khai báo cho
   mốc 1.

## File deliverable chính

- Code: `src/rag_hcmute/{ingestion,retrieval,evaluation}/`, `scripts/*.py`.
- Corpus manifest + snapshot: `data/manifests/`.
- Câu hỏi pilot + gold evidence: `data/question_sets/pilot_questions.csv`.
- Bằng chứng thực nghiệm: `docs/evidence/` (case studies BM25 vs Dense, metrics summary, raw run logs
  của cả 2 phương pháp, figures).
- Quyết định kỹ thuật: `docs/decisions/ADR-001-*.md`, `ADR-002-*.md`.
- Báo cáo nộp giảng viên: `reports/22110068_RAG_Bao_Cao_Tien_Do_Dot_1.docx` — theo yêu cầu mới nhất,
  file này đã gộp **Phần A** (định hướng và kế hoạch tổng thể, điều chỉnh từ bản trình bày ban đầu của
  đề tài — sửa lỗi đánh số, cập nhật tên trường, thay toàn bộ hình lấy từ Internet bằng hình tự vẽ) và
  **Phần B** (báo cáo tiến độ thật của Đợt 1, 7 mục như mô tả trong đề bài). Từ Đợt 2, mỗi đợt báo cáo
  tiến độ dự kiến sẽ được bổ sung làm Phần C, D, … tiếp theo trong cùng file này.
- Hướng dẫn chạy đầy đủ: `README.md`.
