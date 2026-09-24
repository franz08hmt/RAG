# HCMUTE Academic Documents RAG PoC

Đây là mã nguồn thực nghiệm cho đề tài **Nghiên cứu, thiết kế và hiện thực hóa hệ thống Retrieval-Augmented Generation (RAG)**. PoC được giới hạn ở bài toán hỏi đáp trên tài liệu học vụ chính thức của HCMUTE.

## Phạm vi phiên bản đầu

- Đầu vào: câu hỏi tiếng Việt về quy chế đào tạo và thủ tục học vụ.
- Đầu ra: câu trả lời ngắn, đoạn bằng chứng, tên văn bản và vị trí trang/điều khoản.
- Ngoài phạm vi: chatbot hội thoại mở, dữ liệu cá nhân, lịch học hoặc lịch thi thay đổi theo thời gian nếu corpus không chứa dữ liệu đó.
- Quy tắc an toàn: khi không có bằng chứng phù hợp, hệ thống trả về trạng thái chưa đủ căn cứ.

## Nguyên tắc triển khai

1. Mọi tài liệu phải có nguồn, phiên bản, ngày hiệu lực và mã băm trước khi được đưa vào corpus.
2. Mỗi chunk phải truy ngược được về tài liệu và số trang gốc.
3. Retrieval và generation được đánh giá riêng.
4. Cấu hình thí nghiệm, log và kết quả thô phải được lưu lại để đối chiếu trong báo cáo.

## Cấu trúc dự án

```text
rag-hcmute-poc/
├── configs/                 Cấu hình dự án và thí nghiệm
├── data/
│   ├── raw/                 PDF gốc (gitignored, tự tải lại theo manifest)
│   ├── manifests/           corpus_manifest.csv (metadata+hash) và corpus_snapshot.json (config build)
│   ├── processed/           Text theo trang và chunks đã xử lý (gitignored, tự sinh lại)
│   └── question_sets/       Bộ câu hỏi pilot có gold evidence
├── docs/
│   ├── decisions/           Nhật ký quyết định kỹ thuật (ADR)
│   └── evidence/            Kết quả retrieval thô + phân tích case study đã chọn để đối chiếu
├── src/rag_hcmute/
│   ├── ingestion/            extract.py, clean.py, sectioning.py, chunk.py, pipeline.py, manifest.py
│   ├── retrieval/             bm25_index.py, dense_index.py, common.py
│   └── evaluation/            metrics.py, run_pilot.py
├── scripts/                  CLI mỏng gọi vào src/rag_hcmute (build_corpus, query_bm25, query_dense, run_pilot_eval, audit_corpus)
├── tests/                    pytest thực chất (extract/chunk/BM25/manifest) + run_smoke_tests.py
└── artifacts/                Log và index tạm (gitignored)
```

## Cài đặt

```bash
pip install -e ".[dev]"          # pymupdf, rank-bm25, pytest
pip install -e ".[dense]"        # thêm sentence-transformers, faiss-cpu (tuỳ chọn, cho Dense Retrieval)
```

## Bước 1 - Chuẩn bị corpus

1. Đặt các PDF chính thức vào `data/raw/` (tên file khớp cột `local_path` trong manifest).
2. Điền một dòng cho mỗi tài liệu trong `data/manifests/corpus_manifest.csv` (đã có sẵn 3 văn bản đã
   xác minh - xem `docs/decisions/ADR-002-corpus-sourcing-and-redistribution.md`).
3. Chạy kiểm tra:

```bash
python scripts/audit_corpus.py --manifest data/manifests/corpus_manifest.csv --project-root .
```

Kết quả hợp lệ phải xác nhận được file tồn tại, định dạng PDF, không trùng `document_id`, không trùng
SHA-256 và đủ metadata bắt buộc. Manifest rỗng vẫn "PASSED" về schema nhưng được báo rõ là
**CHƯA SẴN SÀNG** (không được coi là đã hoàn thành bước thu thập corpus) - manifest có tài liệu hợp lệ
mới được báo **SẴN SÀNG**.

## Bước 2 - Trích xuất, làm sạch, chia chunk, đóng snapshot

```bash
python scripts/build_corpus.py
```

Lệnh này: trích xuất PDF theo từng trang bằng PyMuPDF (`data/processed/pages/<document_id>.jsonl`),
làm sạch có kiểm soát (loại dòng header/footer lặp lại, giữ nguyên nội dung điều khoản), chia chunk
~500 token/chunk, overlap ~80 token (token = tách theo khoảng trắng, xem lý do trong
`src/rag_hcmute/ingestion/chunk.py`), ưu tiên giữ nguyên ranh giới Chương/Điều khi nhận diện được
(`data/processed/chunks/chunks.jsonl`), rồi ghi `data/manifests/corpus_snapshot.json` (cấu hình +
hash, không chứa text) và `artifacts/logs/build_corpus.log` (log per-document: trang nghi scan, trang
chưa xác định số in, số chunk...).

## Bước 3 - Retrieval baseline

```bash
python scripts/query_bm25.py --query "Điều kiện để sinh viên được xét công nhận tốt nghiệp gồm những gì?" --top-k 5
python scripts/query_dense.py --query "..." --top-k 5   # BGE-M3 + FAISS, cần tải model từ huggingface.co
```

`query_dense.py` sẽ in `DENSE_RETRIEVAL_UNAVAILABLE` kèm lý do cụ thể (thiếu thư viện hoặc không tải
được model) thay vì lỗi khó hiểu, nếu môi trường không có mạng/tài nguyên phù hợp - xem giới hạn ở
mục "Trạng thái hiện tại" bên dưới.

## Bước 4 - Đánh giá trên bộ câu hỏi pilot

```bash
python scripts/run_pilot_eval.py --method bm25
python scripts/run_pilot_eval.py --method dense   # tương tự, cần Dense Retrieval khả dụng
```

Ghi kết quả thô (top-k từng câu, thời gian, cấu hình) vào `docs/evidence/runs/<run_id>.json` và in
Recall@5 / MRR@10 kèm mẫu số ra màn hình. Xem `docs/evidence/runs/metrics_summary.md` và
`docs/evidence/case_studies.md` cho bản tóm tắt và phân tích đã chọn của lần chạy gần nhất.

## Kiểm thử

```bash
pytest                          # 20 test: manifest, extract, chunk (bao gồm test truy ngược chunk → trang gốc), BM25
python tests/run_smoke_tests.py # smoke test không cần pytest, dùng được trong môi trường tối giản
```

## Trạng thái hiện tại (mốc báo cáo tiến độ đợt 1)

- Đã hoàn thành: corpus manifest có 3 tài liệu thật đã xác minh nguồn/hash, pipeline trích xuất →
  làm sạch → chunk có metadata → snapshot tái lập được, retrieval baseline BM25 chạy được qua CLI, bộ
  10 câu hỏi pilot đã rà soát với gold evidence (7/10 có bằng chứng xác nhận được trong corpus hiện
  tại), Recall@5/MRR đã tính trên tập đó, 20 test tự động.
- Đã thử nhưng chưa đạt: Dense Retrieval (BGE-M3 + FAISS) - mã nguồn đã viết đầy đủ và tự kiểm tra
  được tính khả dụng, nhưng môi trường phiên làm việc này không được cấp quyền truy cập
  `huggingface.co` để tải model, nên chưa có kết quả Dense thật. Xem
  `docs/evidence/runs/dense_unavailable_*.json`.
- Dự kiến mốc sau: xác nhận hiệu lực đầy đủ của `HCMUTE_QCDT_1727_2021` (có dấu hiệu văn bản 2025 mới
  hơn), bổ sung nguồn cho câu hỏi về khóa luận/đồ án tốt nghiệp (P006), chạy Dense Retrieval khi có
  quyền mạng phù hợp, mở rộng bộ câu hỏi pilot, và triển khai hybrid + reranker + refusal guard đã
  hiệu chỉnh.

