# Bàn giao mốc 1 (4 tuần đầu) — RAG HCMUTE PoC

Ngày viết: 24/09/2026, cập nhật 25/09/2026 (kết quả Dense Retrieval thật + gộp báo cáo). Branch:
`claude/nifty-dirac-h6u5b6`. Nhánh tiếp tục triển khai hiện tại là `tim-hieu-rag-dot2`; xem `git log`
để biết commit mới nhất.

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

## Cập nhật tiếp nối — 05/10/2026

- Bảng 5 ở `HCMUTE_QCDT_1727_2021` PDF page 20 (số in page 19) được kiểm tra trực quan và khớp SHA-256 trong manifest. Năm câu TB001–TB005 và answer/evidence được người học chấp thuận cho **ablation bảng riêng**, lưu tại `data/question_sets/table_questions_reviewed_ablation_20261005.csv` và `table_question_variant_evidence_20261005.csv`; không nhập vào pilot chung.
- Lượt table-only đầu (T1=1, T2=5 chunk) chỉ là debug. Lượt matched-background giữ 155 chunk nền, thay riêng biểu diễn Bảng 5; corpus B0/T1/T2 có 156/157/161 chunk. Kết quả retrieval-only bằng BM25 và Dense/BGE-M3 ghi trong `docs/evidence/TABLE_RETRIEVAL_APPROVED_ABLATION_20261005.md`; kết quả smoke trước đó vẫn lưu riêng.
- Complete-evidence Hit@5: BM25 B0=4/5, T1=1/5, T2=0/5; Dense đạt 5/5 ở cả ba. Dense MRR của evidence đầu tiên @5: B0=0,600; T1=1,000; T2=0,867. N=5 nên chỉ là kết quả mô tả cho một bảng, chưa đủ để đổi default hay tổng quát hóa.
- Script `scripts/evaluate_table_ablation.py`; raw JSON Git-ignored trong `artifacts/results/table_retrieval_ablation/`. Dense dùng BGE-M3 local/CUDA, không gọi API. Kiểm thử sau cập nhật: pytest 51 passed, smoke test 2/2 passed.
- BGE-M3 nằm ngoài repo tại `D:\RAG\models\huggingface\hub\models--BAAI--bge-m3\snapshots\5617a9f61b028005a4858fdac845db406aefb181`; truyền đường dẫn local cho `scripts/smoke_table_candidate_retrieval.py --dense-model ...` để tránh tải lại. Đã xác nhận CUDA hoạt động; không gọi API.
- QĐ 3116/2025 chưa có trong `D:\RAG\nguon_bo_sung`; nội dung/hiệu lực hiện hành chưa được xác nhận. Kết quả trên đây chỉ theo QĐ 1727/2021 của snapshot G0.
- Chưa đánh giá generation, citation correctness, refusal hoặc chất lượng toàn pipeline; chưa thay đổi pipeline mặc định. Báo cáo DOCX mốc 1 chưa cập nhật vì mốc này còn đang rà soát minh chứng.
- Tiếp tục làm local trên `tim-hieu-rag-dot2`; không push, merge hoặc đụng PR #2.

## Rà soát theo góp ý của giảng viên — cập nhật 05/10/2026

Giảng viên yêu cầu tìm hiểu kỹ từng giai đoạn, nêu dữ liệu và cách tổ chức, phân tích phương án rồi so sánh bằng số liệu; không chỉ liệt kê tên công nghệ. Đối chiếu YC và câu hỏi cụ thể hiện tại:

- **YC4 — tài liệu đầu vào (PDF scan, bảng, hình): đã khảo sát, chưa khép kín.** Có thử OCR trên một số trang scan (`OCR_PSM_SWEEP_20260928.md`, `OCR_PSM_PAGE116_20260928.md`) và có phép thử biểu diễn Bảng 5 thành khối Markdown/hàng có ngữ cảnh B0/T1/T2. Chưa có pipeline tổng quát cho ảnh/hình hoặc bảng nhiều tầng, ô gộp và các loại scan khác; kết quả một bảng không được khái quát hóa cho mọi tài liệu.
- **Document Class và Document Chunk: có cấu trúc cơ sở, còn thiếu phân tích theo lớp.** Corpus manifest/snapshot định danh nguồn và có đánh giá chunk size/exact evidence (`CHUNK_SIZE_EXACT_EVIDENCE_20260929.md`). Bảng mới được phân tích riêng theo ba biểu diễn, nhưng chưa so sánh có hệ thống lớp tài liệu (văn xuôi, quy chế có cấu trúc, bảng, scan) với chiến lược chunk phù hợp cho từng lớp.
- **Chunking và BM25/Dense retrieval: đã có phép đo, nhưng phạm vi nhỏ.** Đã đo retrieval trên pilot và ablation bảng; diagnostic mới cho thấy hạng BM25 nhạy với cách hỏi/tên cột. Dense đang dùng một embedding BGE-M3; chưa phải so sánh nhiều dense embedding hoặc benchmark riêng để kết luận model nào phù hợp tiếng Việt hơn.
- **Vector store, hybrid và reranker: chưa có so sánh thực nghiệm.** Hiện tại Dense dùng FAISS; BM25 là baseline từ vựng riêng. Chưa có kết quả so sánh vector store, BM25+dense/RRF hay reranker. Bất kỳ benchmark tiếng Việt hoặc dữ liệu ngoài nào cũng phải đề xuất nguồn/giấy phép để người học duyệt trước.
- **YC11 — đánh giá RAG: mới có đánh giá retrieval.** Chưa đo end-to-end generation, độ đúng trích dẫn, refusal, Faithfulness/Answer Relevance hoặc các lỗi nối giữa retrieval và generation; các phần này không được ghi như đã hoàn thành.
- **YC12 — ứng dụng console: chưa hoàn thiện.** Mục tiêu là chương trình console có thể chạy và minh họa từng bước, không phải làm UI bóng bẩy.
- **YC13 — tìm hiểu sâu: vẫn là yêu cầu xuyên suốt, chưa thể tuyên bố hoàn thành.** Báo cáo cần giải thích lý do chọn phương án, phương án thay thế, kết quả đo, ví dụ lỗi và giới hạn ở từng bước. Một ablation năm câu trên một bảng là minh chứng cụ thể cho việc đào sâu, nhưng chưa thay thế khảo sát toàn quy trình RAG.
- **Trạng thái mốc:** vẫn đang làm sâu và bổ sung minh chứng cho Mốc 1, chưa chuyển sang Mốc 2 và chưa đóng mốc. Chưa sửa DOCX nộp giảng viên; khi Mốc 1 được chốt, cần cập nhật DOCX đúng font/màu/căn chỉnh đã thống nhất và chỉ đưa kết quả đã xác minh.

Kết quả chẩn đoán BM25 mới nhất: `docs/evidence/BM25_QUERY_SENSITIVITY_DIAGNOSTIC_20261005.md`. Truy vấn biến thể chỉ dùng để phân tích, không thay câu hỏi đã duyệt hoặc pipeline mặc định.

Kiểm kê Document Class/đầu vào mới nhất: `docs/evidence/INPUT_DOCUMENT_CLASS_AUDIT_20261007.md`; audit được tái lập bằng `scripts/audit_document_input_profile.py`. G0 có 3 loại nguồn nhưng chỉ một quy chế đạt cấu trúc Điều; 26 trang Sổ tay là cảnh báo scan theo heuristic, OCR bốn trang đang là phép thử riêng, chưa tích hợp vào G0. Page 107 đã được rà soát ở mức metadata OCR và có nhãn làm việc infographic/nội dung thị giác hỗn hợp với độ tin cậy vừa phải. Báo cáo này không chứa nội dung PDF hoặc thông tin cá nhân.

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

## Quy ước cập nhật báo cáo theo từng đợt

- Khi hoàn tất một mốc tiến độ, cập nhật DOCX của đúng mốc đó ngay trong cùng lượt bàn giao; nội dung phải phản ánh góp ý mới nhất của giảng viên và chỉ đưa vào các kết quả đã có minh chứng.
- Giữ nguyên định dạng, font, cỡ chữ, màu đơn sắc, căn chỉnh và cấu trúc đã thống nhất của báo cáo. Không biến kế hoạch thành kết quả đã làm; nêu rõ cấu hình thử nghiệm, phạm vi dữ liệu và giới hạn.
- Mốc 1 hiện vẫn đang được bổ sung/đối chiếu theo phản hồi của giảng viên. Chưa cập nhật DOCX cho đến khi phần nội dung và minh chứng của mốc này được rà soát xong; sau đó chỉnh DOCX mốc 1 trước khi bàn giao/nộp lại.
- Việc cập nhật DOCX không đồng nghĩa với push, merge hay tạo PR; các thao tác Git bên ngoài local chỉ thực hiện khi được cho phép riêng.

## Cập nhật tiếp nối — 07/10/2026

- Sau audit document class, lập ma trận `docs/evidence/INPUT_CLASS_PROCESSING_MATRIX_20261007.md`: phân biệt lớp nguồn với layout/modality theo trang; nối từng loại nội dung với cách xử lý hiện tại, minh chứng, giới hạn và phép thử tiếp theo.
- Điểm đã có minh chứng: chunk theo Điều cho QĐ 1727; fallback cho Hướng dẫn FIT và Sổ tay; thí nghiệm OCR bốn trang; ablation retrieval cho Bảng 5. Chưa có OCR tích hợp trong G0, parser bảng tổng quát hoặc xử lý ngữ nghĩa hình/sơ đồ.
- Rà soát cục bộ metadata OCR page 107: 86 đơn vị/15 dòng/8 khối ở PSM 4, gần page 136 (79/13/7) hơn các trang chữ nhiều hơn. Nhãn làm việc chuyển sang infographic/nội dung thị giác hỗn hợp với độ tin cậy vừa phải; đã sửa phần mô tả ban đầu ở sweep nhưng không đổi CER/WER. Không đưa ảnh hoặc chữ Sổ tay vào hội thoại/Git; xác nhận bằng mắt trên máy vẫn là bước tùy chọn nếu cần nhãn vàng chắc chắn.
- Lập danh sách mẫu trong `docs/evidence/INPUT_CLASS_SAMPLE_PLAN_20261007.md`: QĐ page 12 và 23–24 cho văn bản có cấu trúc/evidence nhiều trang; QĐ page 20 cho bảng; FIT page 1 cho tài liệu ngắn; Sổ tay pages 109/116/107/136 cho các dạng OCR/layout. Page 10 của Sổ tay được chọn theo metadata gần median nhưng chưa xác nhận nội dung/layout/riêng tư, chỉ dùng sau khi người học kiểm tra tại máy.
- Sweep sau đó được mở rộng thành 24 lượt trên cùng bốn trang/reference, thêm PSM 6: Tesseract 5.5.3, `vie`, DPI 200/300, PSM 4/6/11. PSM 4 thấp nhất về CER/WER gộp; PSM 6 cao nhất về recall token số trong mẫu (53,13% ở 200 DPI; 62,50% ở 300 DPI), nhưng CER/WER gộp cao hơn PSM 4. Kết quả mới nhất tại `docs/evidence/OCR_DPI_SENSITIVITY_20261007.md`; raw metrics-only JSON Git-ignored `artifacts/results/ocr_dpi_sensitivity/ocr_dpi_sensitivity_20261007T074720Z.json`.
- Có 32 occurrence token số và 4 occurrence cue trong cả mẫu; cue 4/4 ở các cấu hình nhưng mẫu quá nhỏ để khái quát. Không lưu token/text. Không chọn cấu hình tối ưu hay đổi default OCR; không tích hợp OCR vào G0.
- Audit read-only YC4/YC13 xác nhận có thể trình bày “đã khảo sát, đã thử cục bộ, đã nhận diện giới hạn”, chưa tuyên bố hoàn thành. Các phần còn thiếu gồm xử lý tổng quát bảng/hình và so sánh chiến lược theo document/input class. Đã làm rõ trong G1 rằng OCR chạy qua chế độ CLI tùy chọn trên snapshot riêng, G0 vẫn native-only; số liệu ground truth ba trang là lượt đầu, sau đó mới bổ sung trang thứ tư; chênh lệch 28/20 ứng viên bảng do lọc trang nhạy cảm, không phải xác nhận thủ công.
- Code/metric tại commit `409d168`, sweep PSM6 tại `90fb837`; 53 tests passed và `compileall` đạt. Không gọi API, không push, không sửa DOCX; Mốc 1 vẫn mở, chưa chuyển Mốc 2.
- So sánh policy chunk trên G0 bằng 7 câu answerable/10 span: policy theo Điều bao phủ 10/10; cửa sổ cố định 500/80 bao phủ 9/10. Exact Recall@5 BM25 là 4/10→6/10, Dense BGE-M3 là 9/10→8/10; page proxy không thay exact evidence. Kết quả trái chiều, mẫu pilot nhỏ, nên giữ default. Chi tiết và lệnh tái lập: `docs/evidence/CHUNK_STRATEGY_ABLATION_20261007.md`, `scripts/run_chunk_strategy_ablation.py`.
- BM25/Dense raw JSON metrics-only tại `artifacts/results/chunk_strategy_ablation/` bị Git-ignore. Test suite hiện đạt 56 passed; `compileall` và `git diff --check` đạt. Mốc 1 vẫn mở, chưa cập nhật DOCX, chưa chuyển Mốc 2. Không gọi API, không push/merge/PR.
