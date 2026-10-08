# HCMUTE Academic Documents RAG PoC

Đây là mã nguồn thực nghiệm cho đề tài **Nghiên cứu, thiết kế và hiện thực hóa hệ thống Retrieval-Augmented Generation (RAG)**. PoC được giới hạn ở bài toán hỏi đáp trên tài liệu học vụ chính thức của HCMUTE.

## Phạm vi mục tiêu của PoC

- Đầu vào: câu hỏi tiếng Việt về quy chế đào tạo và thủ tục học vụ.
- Đầu ra mục tiêu khi hoàn thiện: câu trả lời ngắn, đoạn bằng chứng, tên văn bản và vị trí trang/điều khoản.
- Ngoài phạm vi: chatbot hội thoại mở, dữ liệu cá nhân, lịch học hoặc lịch thi thay đổi theo thời gian nếu corpus không chứa dữ liệu đó.
- Quy tắc an toàn mục tiêu: khi không có bằng chứng phù hợp, hệ thống cần trả về trạng thái chưa đủ căn cứ; guard này chưa được triển khai/đánh giá ở hiện trạng.

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
│   └── evidence/            Báo cáo thực nghiệm và các minh chứng đã chọn
├── src/rag_hcmute/
│   ├── ingestion/            extract.py, clean.py, sectioning.py, chunk.py, pipeline.py, manifest.py
│   ├── retrieval/             bm25_index.py, dense_index.py, hybrid.py, reranked.py, common.py
│   ├── evaluation/            metrics.py, run_pilot.py, evidence_spans.py, reranker.py, question_coverage.py
│   └── console_app.py         Console explorer cho retrieval; chưa generation
├── scripts/                  CLI ingestion/retrieval/evaluation và runner thí nghiệm
├── tests/                    pytest cho ingestion, retrieval, evaluation và manifest
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
python scripts/query_dense.py --query "..." --top-k 5   # BGE-M3 + FAISS, cần tải model BAAI/bge-m3
```

`query_dense.py` cần cài `pip install -e ".[dense]"` và tải model `BAAI/bge-m3` (~2.2GB) lần đầu chạy.
Nếu môi trường lọc egress theo whitelist tên miền: cần mở **cả hai** `huggingface.co` (nơi khai báo
model) **và** tên miền lưu trọng số thật mà Hugging Face chuyển hướng tới khi tải file (ví dụ
`us.aws.cdn.hf.co` - hạ tầng "Xet storage"; dùng `curl -I` xem header `Location` để biết đúng tên miền
cần mở trong môi trường của bạn) - nếu chỉ mở `huggingface.co`, lệnh tải model vẫn thất bại. Nếu vẫn
thiếu thư viện hoặc không tải được model, lệnh in `DENSE_RETRIEVAL_UNAVAILABLE` kèm lý do cụ thể thay
vì lỗi khó hiểu.

## Console PoC (retrieval stage)

Sau khi G0 đã được dựng, chạy lệnh dưới từ thư mục repository để mở chế độ tương tác BM25:

```bash
python -m rag_hcmute.console_app
```

Có thể chạy một câu hỏi trực tiếp bằng `--query "..."`, tăng `--top-k`, hoặc chọn `--method dense`
hay `--method hybrid`. Dense/Hybrid yêu cầu `--dense-model` trỏ tới thư mục BGE-M3 có sẵn trên máy;
CLI bật chế độ offline và không tải model. Hai chế độ `dense-rerank` và `hybrid-rerank` là lựa chọn
thử nghiệm riêng: lấy tối đa 20 ứng viên từ Dense hoặc Hybrid RRF rồi xếp hạng lại bằng snapshot local
đã ghim của BGE-Reranker-v2-m3. Cần truyền thêm `--reranker-model`; mặc định `max_length=512`, batch
size 4. Console báo số cặp bị cắt để người chạy không nhầm kết quả rerank với đầu vào đầy đủ. Mô hình
reranker phải nằm sẵn trên máy và được nạp offline; không có tải tự động. Ví dụ trên máy đã chuẩn bị model:

```powershell
python -m rag_hcmute.console_app --method hybrid --dense-model 'D:\RAG\models\huggingface\hub\models--BAAI--bge-m3\snapshots\5617a9f61b028005a4858fdac845db406aefb181' --top-k 5
```

Ví dụ Hybrid + reranker (chỉ để quan sát, chưa chọn làm mặc định):

```powershell
python -m rag_hcmute.console_app --method hybrid-rerank --dense-model '<duong-dan-snapshot-BGE-M3>' --reranker-model 'D:\RAG\models\huggingface\hub\models--BAAI--bge-reranker-v2-m3\snapshots\953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e' --query "Điều kiện để sinh viên được xét công nhận tốt nghiệp gồm những gì?" --top-k 5
```

CLI hiện hiển thị hạng, điểm retriever, tên tài liệu, PDF page, section và đoạn trích ngắn để truy ngược
bằng chứng. Với hai biến thể rerank, CLI còn hiển thị kích thước candidate pool, thời gian reranker và
số cặp đầu vào bị cắt. Đây vẫn là **console cho retrieval**, chưa sinh câu trả lời, chưa có ngưỡng từ
chối đã hiệu chỉnh, và chưa đánh giá citation đầu ra; không trình bày nó như hệ thống RAG end-to-end.

## Bước 4 - Đánh giá trên bộ câu hỏi pilot

```bash
python scripts/run_pilot_eval.py --method bm25
python scripts/run_pilot_eval.py --method dense   # tương tự, cần Dense Retrieval khả dụng
```

Ghi kết quả thô (top-k từng câu, thời gian, cấu hình) vào `docs/evidence/runs/<run_id>.json` và in
Recall@5 / MRR@10 kèm mẫu số ra màn hình. Xem `docs/evidence/runs/metrics_summary.md` và
`docs/evidence/case_studies.md` cho bản tóm tắt và phân tích đã chọn của lần chạy gần nhất.

Có thể chạy phép so sánh BM25, Dense và Hybrid RRF trên snapshot G0 đã ghim bằng
`scripts/run_hybrid_retrieval_ablation.py`. Runner dùng câu hỏi và evidence span hiện có, BGE-M3 local,
không gọi API; kết quả được ghi dưới `artifacts/results/` (Git-ignored), chỉ gồm metric, mã câu/span,
loại tài liệu và thứ hạng để chẩn đoán; không ghi câu hỏi hoặc văn bản nguồn. Đây là benchmark retrieval
nhỏ, tách với console demo và không đánh giá generation. Runner cũng ghi độ phủ exact evidence ở candidate
Top-20 để ước lượng giới hạn đầu vào của reranker. Pilot reranker development nhỏ được ghi riêng tại
`docs/evidence/RERANKER_RESOURCE_AND_EVAL_PLAN_20261007.md`; chưa dùng kết quả này làm kết luận cuối.

Độ bao phủ bộ câu hỏi đã duyệt được thống kê riêng bằng `scripts/audit_question_coverage.py`; kết quả tại
`docs/evidence/QUESTION_SET_COVERAGE_AUDIT_20261008.md`. Audit không đưa nội dung câu hỏi hoặc đoạn nguồn
vào output và xác nhận hiện chưa có holdout được ghi trong metadata.

Phân hoạch câu hỏi được xác thực trước khi nạp vào các lượt pilot: `development` là mặc định, câu hỏi
Bảng 5 ở partition `ablation_only`, còn `holdout` hiện chưa có. Chạy `python scripts/audit_question_partitions.py`
để kiểm tra sidecar manifest, trạng thái duyệt và mã snapshot mà không in nội dung câu hỏi.
Runner pilot chọn rõ partition bằng `python scripts/run_pilot_eval.py --partition development`; chỉ dùng
`--partition holdout` sau khi có bộ câu hỏi độc lập đã được người học duyệt và đăng ký.

## Kiểm thử

```bash
pytest                          # kiểm thử manifest, ingestion/OCR, chunking, BM25/Dense/RRF/reranker, console và evaluation
python tests/run_smoke_tests.py # smoke test không cần pytest, dùng được trong môi trường tối giản
```

## Trạng thái hiện tại (mốc báo cáo tiến độ đợt 1)

- Đã có: corpus manifest 3 tài liệu đã xác minh nguồn/hash; pipeline trích xuất → làm sạch → chunk có
  metadata → snapshot tái lập được; BM25 và Dense BGE-M3/FAISS đã chạy trên cùng corpus. Pilot lịch sử
  dùng **question-level Hit@5** (được ghi là Recall@5 trong log cũ): BM25 3/7 (0,429), Dense 6/7
  (0,857), MRR@10 lần lượt 0,371 và 0,643. Đây là metric tính câu có ít nhất một gold chunk trong
  Top-5, không phải tỷ lệ evidence span được tìm thấy.
- Đã bổ sung đánh giá theo exact evidence span (7 câu answerable/10 span), ablation chunking và phép
  thử Hybrid RRF. Trên G0, RRF đạt Evidence Recall@5 6/10, so với BM25 4/10 và Dense 9/10;
  Complete-evidence Hit@5 lần lượt 4/7, 3/7 và 6/7 theo thứ tự Hybrid/BM25/Dense. Kết quả và giới
  hạn được tách riêng tại `docs/evidence/CHUNK_STRATEGY_ABLATION_20261007.md` và
  `docs/evidence/HYBRID_RRF_ABLATION_20261007.md`. Candidate Top-20 chứa đủ 10/10 span và 7/7 câu
  với Dense/RRF trong pilot. Đã chạy thêm reranker trên cùng development pilot: Recall@5 sau rerank
  đạt 10/10 với cả Dense và RRF; kết quả nhỏ, chưa phải holdout và chưa đủ căn cứ đổi mặc định. Xem
  `docs/evidence/RERANKER_RESOURCE_AND_EVAL_PLAN_20261007.md`.
- Phần còn mở của Mốc 1: mở rộng bộ câu hỏi độc lập/holdout; hoàn thiện khảo sát xử lý tổng quát cho
  scan, bảng, hình; xem xét embedding/vector store khác khi có phương án tài nguyên được duyệt; tiếp tục
  generation, citation/refusal và đánh giá end-to-end. Console hiện hỗ trợ BM25/Dense/Hybrid và hai
  biến thể rerank dạng opt-in; chưa phải ứng dụng RAG end-to-end.

