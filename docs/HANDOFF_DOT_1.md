# Bàn giao mốc 1 (4 tuần đầu) — RAG HCMUTE PoC

Ngày viết ban đầu: 24/09/2026; tài liệu được nối tiếp qua các lần cập nhật. Nhánh tiếp tục triển khai
hiện tại: `tim-hieu-rag-dot2` (không push/merge; xem `git log` để biết commit mới nhất). Các mục có ngày
trước đây ghi lại trạng thái tại thời điểm đó; phần cập nhật cuối file là trạng thái mới nhất.

## Checkpoint hiện tại — 12/10/2026 (cập nhật sau checkpoint kiến trúc)

- DEMO ban đầu đã duyệt được giữ riêng, không ghi đè; báo cáo tiến độ Mốc 1 hiện hành là `reports/22110068_RAG_Bao_Cao_Tien_Do_Dot_1_v6.docx`.
- Đang triển khai bước đầu Mốc 2 song song với các phần Mốc 1 còn thiếu xác minh; chưa tuyên bố Mốc 1 đã đóng. Bản thiết kế làm việc `docs/ARCHITECTURE_M2_DRAFT.md` và quyết định kiến trúc dựa trên các ablation hiện có tại `docs/decisions/ADR-004-current-poc-architecture.md` bám vào code thật, không gọi cấu hình nào là tối ưu.
- Xác minh trong env `rag-hcmute`: `pytest` **113 passed**, `compileall src scripts tests` và `git diff --check` đạt, `torch.cuda.is_available() == True`. Có test tích hợp metadata từ PDF fixture đến citation; đây không phải kiểm tra citation entailment hay benchmark.
- Chạy smoke test trực tiếp console bằng BM25 trên corpus 156 chunks. Với truy vấn P007, nguồn Quy chế 1727/2021, Điều 17, PDF trang 23–24 lên hạng 1 và console hiển thị metadata provenance. Với một truy vấn thử về điều kiện tốt nghiệp, nguồn Điều 16 chỉ lên hạng 3; hai lần chạy chỉ xác nhận console và nguồn có thể quan sát, không phải benchmark mới hay chứng nhận chất lượng trả lời.
- Thêm rubric chấm thủ công cấp câu trả lời và claim, private bundle cục bộ có opt-in, biểu mẫu và bộ tổng hợp chỉ xuất số liệu. Schema chống nhãn mâu thuẫn, ID trùng, trộn run/snapshot/partition; hiện chưa có nhãn semantic nào được điền.
- Chạy lại generation pilot cùng cấu hình cũ trên G0 development 10 câu bằng Qwen3:4B local: 7/7 answerable có phản hồi, 1/3 unanswerable bị từ chối; 9 câu sinh có citation ID hợp lệ, chưa đánh giá citation support. Đây là lần tái lập cùng tập, không phải benchmark mới.
- Bundle nội dung và phiếu chấm `pending` được lưu ngoài repo tại `D:\RAG\private_eval\`; không đưa câu hỏi, câu trả lời, excerpt nguồn hay nhãn chưa duyệt vào Git.
- Mốc 1 có báo cáo v6 nhưng các phần holdout và gold cần người học duyệt, đánh giá correctness/faithfulness/citation entailment, refusal đáng tin cậy và độ bao phủ input class vẫn còn mở.
- Bước phụ thuộc người học tiếp theo: rà 10 dòng answer review và lập claim review từ bundle cục bộ theo `docs/evaluation/manual_review_protocol.md`. Không có nhãn này thì chưa thể kết luận generation semantic hoặc cập nhật phần kết quả tương ứng trong DOCX.
- Nhánh `tim-hieu-rag-dot2`; không push, merge hoặc tạo PR. Các thư mục/file untracked có từ trước được giữ nguyên.

## Checkpoint nối tiếp — 12/10/2026 (khung đánh giá thủ công Mốc 2)

- Hướng dẫn: `docs/evaluation/manual_review_protocol.md`; code: `src/rag_hcmute/evaluation/manual_review.py`; CLI: `scripts/prepare_manual_review.py`, `scripts/summarize_manual_reviews.py`.
- Bundle generation nằm ngoài repository tại `D:\RAG\private_eval\m2_generation_reviews\generation_hybrid-rerank_5da3bd4d5de54492_20261012T030902Z.jsonl`. Kiểm tra metadata: 10 record/10 question ID, snapshot `5da3bd4d5de54492`, gồm 7 answerable + 3 unanswerable, retrieved sources có ở 10/10; không in nội dung câu hỏi hay nguồn.
- Phiếu answer/claim cũng ở ngoài repo. Answer sheet có 10 dòng `pending`; claim sheet chỉ có header chờ người chấm tách claim. Chưa có đánh giá thủ công nào được thực hiện hoặc đưa vào metric.
- Lượt chạy là tái lập local trên cùng corpus/query/config; kết quả vận hành khớp lượt 08/10: 7/7 answerable có phản hồi, 1/3 unanswerable bị từ chối; 9 output sinh, 1 output JSON không hợp lệ. Không gọi Gemini/cloud API, không dùng model 8B.
- Test khung đánh giá và tạo phiếu; toàn repo đạt **113 passed**. Compileall và `git diff --check` đạt.
- Đây là hạ tầng đánh giá cho Mốc 2, chưa phải kết quả semantic hay đóng Mốc 1/YC11. Chưa cập nhật DOCX mốc vì chưa có nhãn review được sinh viên xác minh; giữ nguyên demo và báo cáo Mốc 1.

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
8. Hybrid RRF đã có runner ablation và console retrieval dùng được; chưa đưa RRF thành mặc định.
   Reranker, refusal guard đã hiệu chỉnh, generation (LLM) và API: **chưa triển khai**; console hiện
   chỉ hiển thị kết quả retrieval và nguồn, không phải ứng dụng RAG end-to-end.

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
- **Vector store và reranker: chưa so sánh nhiều vector store; đã có pilot reranker trên một cấu hình.** Dense hiện dùng FAISS. Trên development pilot 7 câu/10 span, exact evidence Recall@5 là BM25 4/10, Dense 9/10, RRF 6/10; reranker đưa Dense/RRF lên 10/10 trong chính pilot này, nhưng mẫu nhỏ và chưa phải holdout nên chưa đủ căn cứ chọn mặc định. Dense/RRF candidate Top-20 đều chứa 10/10 span. Chi tiết ablation và giới hạn ở `docs/evidence/HYBRID_RRF_ABLATION_20261007.md` và `docs/evidence/RERANKER_RESOURCE_AND_EVAL_PLAN_20261007.md`. Mọi so sánh vector store khác hoặc benchmark tiếng Việt ngoài corpus vẫn cần tách phạm vi và duyệt nguồn/giấy phép trước.
- **YC11 — đánh giá RAG: mới có đánh giá retrieval.** Chưa đo end-to-end generation, độ đúng trích dẫn, refusal, Faithfulness/Answer Relevance hoặc các lỗi nối giữa retrieval và generation; các phần này không được ghi như đã hoàn thành.
- **YC12 — ứng dụng console: mới hiện thực retrieval/reranking, chưa hoàn thiện.** `python -m rag_hcmute.console_app` chạy BM25 mặc định; có thể chọn Dense/Hybrid và hai biến thể rerank khi chỉ định model local. App hiển thị hạng, điểm, PDF page, section, preview ngắn, latency và truncation của reranker. Chưa có generation, refusal guard hay câu trả lời kèm citation đã kiểm chứng; vì vậy chưa được gọi là RAG end-to-end.
- **YC13 — tìm hiểu sâu: vẫn là yêu cầu xuyên suốt, chưa thể tuyên bố hoàn thành.** Báo cáo cần giải thích lý do chọn phương án, phương án thay thế, kết quả đo, ví dụ lỗi và giới hạn ở từng bước. Một ablation năm câu trên một bảng là minh chứng cụ thể cho việc đào sâu, nhưng chưa thay thế khảo sát toàn quy trình RAG.
- **Trạng thái mốc:** vẫn đang làm sâu và bổ sung minh chứng cho Mốc 1, chưa chuyển sang Mốc 2 và chưa đóng mốc. Chưa sửa DOCX nộp giảng viên; khi Mốc 1 được chốt, cần cập nhật DOCX đúng font/màu/căn chỉnh đã thống nhất và chỉ đưa kết quả đã xác minh.

Kết quả chẩn đoán BM25 mới nhất: `docs/evidence/BM25_QUERY_SENSITIVITY_DIAGNOSTIC_20261005.md`. Truy vấn biến thể chỉ dùng để phân tích, không thay câu hỏi đã duyệt hoặc pipeline mặc định.

Kiểm kê Document Class/đầu vào mới nhất: `docs/evidence/INPUT_DOCUMENT_CLASS_AUDIT_20261007.md`; audit được tái lập bằng `scripts/audit_document_input_profile.py`. G0 có 3 loại nguồn nhưng chỉ một quy chế đạt cấu trúc Điều; 26 trang Sổ tay là cảnh báo scan theo heuristic, OCR bốn trang đang là phép thử riêng, chưa tích hợp vào G0. Page 107 đã được rà soát ở mức metadata OCR và có nhãn làm việc infographic/nội dung thị giác hỗn hợp với độ tin cậy vừa phải. Báo cáo này không chứa nội dung PDF hoặc thông tin cá nhân.

## File và deliverable hiện hành

- Code: `src/rag_hcmute/{ingestion,retrieval,evaluation}/`, `scripts/*.py`.
- Corpus manifest + snapshot: `data/manifests/`.
- Câu hỏi pilot + gold evidence: `data/question_sets/pilot_questions.csv`.
- Bằng chứng thực nghiệm: `docs/evidence/` (case studies BM25 vs Dense, metrics summary, raw run logs
  của cả 2 phương pháp, figures).
- Quyết định kỹ thuật: `docs/decisions/ADR-001-*.md`, `ADR-002-*.md`.
- Bản DEMO ban đầu đã được giảng viên chốt: `D:\RAG\22110068_RAG_IT_Project_DEMO.docx`. Giữ nguyên làm mốc tham chiếu; không ghi đè khi phát triển báo cáo tiến độ.
- Báo cáo tiến độ Mốc 1 hiện hành: `reports/22110068_RAG_Bao_Cao_Tien_Do_Dot_1_v6.docx`. Đây là tài liệu riêng, phản ánh kết quả và giới hạn đã kiểm chứng; không thay thế DEMO và không tuyên bố mọi YC1–YC13 đã hoàn thành.
- Các mốc sau được phát triển nối tiếp từ kết quả/thay đổi thực tế của mốc trước, nhưng phải tạo bản DOCX mới, giữ nguyên các bản đã nộp và không tự động gộp DEMO với báo cáo tiến độ. Nếu cần một bản tổng hợp cuối cùng, tạo bản mới từ các nguồn đã duyệt.
- Bản thiết kế kiến trúc làm việc cho Mốc 2: `docs/ARCHITECTURE_M2_DRAFT.md`; đây là tài liệu Markdown nội bộ, chưa thay thế báo cáo DOCX.
- Hướng dẫn chạy đầy đủ: `README.md`.

## Quy ước cập nhật báo cáo theo từng đợt

- Khi hoàn tất một mốc tiến độ, cập nhật DOCX của đúng mốc đó ngay trong cùng lượt bàn giao; nội dung phải phản ánh góp ý mới nhất của giảng viên và chỉ đưa vào các kết quả đã có minh chứng.
- Giữ nguyên định dạng, font, cỡ chữ, màu đơn sắc, căn chỉnh và cấu trúc đã thống nhất của báo cáo. Không biến kế hoạch thành kết quả đã làm; nêu rõ cấu hình thử nghiệm, phạm vi dữ liệu và giới hạn.
- Báo cáo Mốc 1 v6 đã được tạo và kiểm tra trình bày; các câu hỏi/gold, đánh giá ngữ nghĩa, input-class tổng quát và một số so sánh công nghệ vẫn là giới hạn nghiên cứu. Không ghi các mục này như đã hoàn thành nếu chưa có minh chứng.
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
- BM25/Dense raw JSON metrics-only tại `artifacts/results/chunk_strategy_ablation/` bị Git-ignore. Sau khi thêm retrieval console và xử lý UTF-8 console, test suite hiện đạt 74 passed; `compileall` và `git diff --check` đạt. Mốc 1 vẫn mở, chưa cập nhật DOCX, chưa chuyển Mốc 2. Không gọi API, không push/merge/PR.
- Thêm RRF combiner và runner so sánh BM25/Dense/Hybrid; RRF đạt 6/10 span, thấp hơn Dense 9/10 nhưng cao hơn BM25 4/10. Bổ sung chẩn đoán theo mã câu/span và hạng: đủ evidence Top-5 là BM25 3/7, Dense 6/7, RRF 4/7; RRF có một ca evidence chỉ ở hạng 6–10 và một ca không thấy trong Top-10. JSON Git-ignored có cấu hình/hash, metric, mã định danh và hạng, không chứa văn bản câu hỏi/nguồn. Kết quả tại `docs/evidence/HYBRID_RRF_ABLATION_20261007.md`; chưa đổi retrieval mặc định.
- Kiểm kê read-only cache/env: hiện chỉ có model BGE-M3 trong Hugging Face cache; `sentence-transformers` và FAISS đã cài, còn ChromaDB, Qdrant client và Milvus client chưa có. Chưa tải/cài thêm gì; so sánh vector store hoặc embedding model khác cần đề xuất cấu hình/tài nguyên rồi xin duyệt trước.
- Thêm retrieval console tương tác/one-shot ở `src/rag_hcmute/console_app.py`, mặc định BM25 trên G0; Dense/Hybrid chỉ dùng model local truyền rõ qua `--dense-model` và bật offline. Hiển thị metadata truy vết cùng excerpt ngắn; thông báo rõ đây chưa phải generation hay refusal. Chưa dùng Gemini/Ollama, không tải model/gói.
- Smoke test console trên G0 native-only đạt với BM25 và Hybrid BGE-M3/RRF, 156 chunks; output được capture để xác nhận metadata/excerpt, không echo hoặc lưu câu hỏi/văn bản nguồn. Chi tiết phạm vi và cách chạy tại `docs/evidence/RETRIEVAL_CONSOLE_20261007.md`. YC12 mới đạt phần retrieval console; generation, citation correctness và refusal vẫn chưa có.

## Cập nhật tiếp nối — 07/10/2026 (reranker local)

- Sau khi người học duyệt tải model, tải `BAAI/bge-reranker-v2-m3` từ Hugging Face tại revision cố định `953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e`, lưu ngoài Git ở `D:\RAG\models\huggingface\hub\models--BAAI--bge-reranker-v2-m3\snapshots\953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e`.
- Trọng số `model.safetensors` có kích thước 2,271,071,852 bytes; SHA-256 `d9e3e081faff1eefb84019509b2f5558fd74c1a05a2c7db22f74174fcedb5286` khớp metadata Hugging Face. Không cài thêm package, không gọi API.
- Nạp model FP16 bằng env `rag-hcmute` và chạy smoke scoring offline trên hai cặp văn bản tổng hợp: cặp liên quan được xếp trên cặp không liên quan; peak CUDA allocation 1.067 GiB trên RTX 3060 Laptop GPU. Đây chỉ là kiểm tra kỹ thuật, không phải benchmark chất lượng trên dữ liệu HCMUTE.
- Thêm `src/rag_hcmute/evaluation/reranker.py` và `scripts/run_reranker_ablation.py`; runner xác minh corpus/gold annotations và model revision/hash, rồi so sánh Dense Top-20 và RRF Top-20 trước/sau rerank. Kiểm thử cuối toàn repo: 80 passed; compileall và `git diff --check` đạt.
- Trên development pilot 7 câu answerable/10 exact spans, Dense tăng từ Recall@5 9/10, Complete Hit@5 6/7, MRR@10 0,762 lên 10/10, 7/7, 0,857. RRF tăng từ 6/10, 4/7, 0,524 lên 10/10, 7/7, 0,857. Candidate coverage@20 của cả hai là 10/10 span, 7/7 câu đủ evidence. Đây là pilot nhỏ, không phải holdout; không đổi retriever mặc định.
- Với `max_length=512`, truncation chỉ ở cuối passage: 99/140 cặp Dense và 110/140 cặp RRF bị cắt token; 0/10 candidate occurrence của gold evidence bị cắt ở mỗi phương pháp. Rerank median/query là 446,1 ms (Dense) và 445,2 ms (RRF); peak CUDA allocated 1,110 GiB trong lượt chạy này. Giới hạn và raw metrics-only result Git-ignored được ghi tại `docs/evidence/RERANKER_RESOURCE_AND_EVAL_PLAN_20261007.md`.
- Chạy sensitivity check `max_length=1024` trên cùng dữ liệu và candidate pools: không còn cặp bị cắt (max raw pair length 723 Dense/812 RRF), thứ hạng evidence theo câu và metric trước/sau không đổi so với 512; median rerank/query tăng lên 560,8/571,4 ms. Không chọn 1024 làm mặc định do mẫu dev nhỏ; raw result Git-ignored `artifacts/results/reranker_ablation/reranker_5da3bd4d5de54492_20261007T095831Z.json`.
- Chưa có đánh giá generation, citation correctness, refusal, holdout hoặc độ ổn định hiệu năng; reranking chưa được đặt làm mặc định.
- Mốc 1 vẫn mở, chưa cập nhật DOCX, chưa chuyển Mốc 2. Làm local trên `tim-hieu-rag-dot2`; không push, merge hoặc tạo PR.

## Cập nhật tiếp nối — 07/10/2026

- Mở rộng runner Hybrid để đo độ phủ exact evidence ở candidate depth 20, nhằm kiểm tra giới hạn dữ liệu đầu vào trước một thử nghiệm reranker. Trên cùng pilot 7 câu/10 span: BM25 có 7/10 span và đủ toàn bộ span ở 5/7 câu; Dense BGE-M3 và RRF đều có 10/10 span, đủ ở 7/7 câu.
- Đây chỉ là candidate coverage: reranker chưa chạy và phép đo không cho biết nó sẽ xếp hạng tốt hơn ra sao. Tập dữ liệu vẫn là development pilot, không phải holdout; không đổi retriever mặc định và không chọn model.
- Bổ sung kiểm thử cutoff candidate; toàn bộ pytest 76 passed, `compileall` và `git diff --check` đạt. Bằng chứng tại `docs/evidence/HYBRID_RRF_ABLATION_20261007.md`, raw JSON metrics-only tiếp tục Git-ignored. Không cập nhật DOCX, không gọi API, không tải/cài model hoặc gói, không push/merge/PR; Mốc 1 vẫn mở.
- Lập phương án thử reranker ở `docs/evidence/RERANKER_RESOURCE_AND_EVAL_PLAN_20261007.md`: model ứng viên BAAI/bge-reranker-v2-m3 (repo 2,29 GB), GPU local RTX 3060 Laptop 6 GiB, cùng thiết kế so sánh Dense/RRF Top-20 trước/sau rerank và kiểm soát truncation. Đây mới là đề xuất, chưa tải/chạy model; cần phê duyệt riêng trước download.

## Cập nhật hiện trạng — 07/10/2026 (console có reranking tùy chọn)

- Console có thêm `dense-rerank` và `hybrid-rerank`. Luồng là Dense hoặc Hybrid RRF lấy candidate tối đa 20, sau đó BGE-Reranker-v2-m3 xếp hạng lại; `bm25` vẫn là mặc định. Model path phải là snapshot local đã ghim, không tải tự động. `max_length=512`, batch size 4; output tách latency retrieval/reranker và báo số cặp bị truncate.
- One-shot integration trên G0 native-only, BGE-M3 và reranker local trả exit code 0; 156 chunks, candidate 20, top-5 được hiển thị, reranker latency 909,14 ms; 14/20 cặp bị truncate ở cấu hình 512. Output chỉ được capture trong bộ nhớ; không lưu câu hỏi hoặc văn bản nguồn. Đây là xác nhận luồng phần mềm, không thay benchmark pilot trước đó.
- Unit tests sau cập nhật: 83 passed; smoke test fixture 2/2 passed. Kết quả pilot reranker trước/sau vẫn chỉ là development set 7 câu/10 span, không phải holdout. Chưa chọn reranker làm mặc định, chưa có generation/citation/refusal, chưa đóng Mốc 1.
- Chưa sửa DOCX vì Mốc 1 vẫn mở. Không cài thêm package, không gọi Gemini/Ollama/API, không push/merge/PR; thay đổi được lưu local trên `tim-hieu-rag-dot2` sau khi kiểm tra.

## Trạng thái bàn giao hiện tại — 08/10/2026

- Bản report Mốc 1 mới: `reports/22110068_RAG_Bao_Cao_Tien_Do_Dot_1_v6.docx`; tạo từ template v2, giữ nguyên mẫu bìa/logo/khung, nội dung thân bài được thay mới theo năm chương. Bản v2 không bị ghi đè.
- Đã chạy thêm phép thử embedding BGE-M3 vs multilingual-E5-small; vector store FAISS IndexFlatIP vs Qdrant local exact; nối Ollama/Qwen3:4B cho generation pilot. Raw output nằm trong `artifacts/results/` Git-ignored; report builder dựng bảng từ raw JSON và ghi run ID.
- Tài liệu học tập/đọc tiếp: `docs/tim_hieu/`, `docs/hoc_tap/`, `CAU_HOI_BAO_VE.md`, `docs/TRUY_VET_YC.md`, `data/eval/README.md`.
- YC1–YC13 được truy vết nguyên số thứ tự; nhiều YC vẫn một phần. Chưa có holdout độc lập; câu hỏi mới/gold chưa được người học duyệt; mới đo hai embedding, một reranker, hai store exact; OCR/table/image chưa tổng quát; semantic correctness, faithfulness, citation support và refusal policy chưa đạt.
- Ràng buộc giữ nguyên: branch `tim-hieu-rag-dot2`, không push/merge/PR; `main` và PR #2 không đổi; không dùng Gemini/API trả phí; corpus/PII/model weights/raw text ở ngoài Git. QĐ 3116/2025 không đưa vào G0 do scan/OCR chưa được kiểm chứng đủ.
- Sau khi report được kiểm tra: chạy pytest/compileall/style audit; nếu có lỗi, sửa trên chính working copy mới này, không đụng report đã nộp trước.

## Bàn giao sau kiểm tra DOCX — 08/10/2026

- Bản DOCX hiện hành là `reports/22110068_RAG_Bao_Cao_Tien_Do_Dot_1_v6.docx`, dựng từ template v2 không ghi đè. Word xuất PDF thành công; kiểm tra trực quan cả 13 trang. Khung chỉ nằm ở bìa, thân bài Times New Roman, đen trắng, không số trang; sửa được đoạn chunking bị tách giữa trang và căn trái phụ lục có đường dẫn dài. Phụ lục ghi rõ 104 test và compileall đạt.
- Report chứa retrieval/embedding/vector-store/reranker/OCR/generation pilot và truy vết YC1–YC13. Đây là báo cáo tiến độ có bằng chứng, không phải tuyên bố đã hoàn tất Mốc 1: chưa có holdout, mở rộng benchmark embedding/reranker, parser tổng quát cho bảng/hình, đánh giá semantic correctness/faithfulness/citation entailment/refusal.
- V3–v5 là bản dựng trung gian; dùng v6 nếu cần tiếp tục chỉnh. Nguồn mẫu v2 vẫn nguyên hash đã ghi trong artifact metadata.
- Trạng thái repo vẫn local trên `tim-hieu-rag-dot2`; không push, merge hoặc tạo PR. Giữ nguyên `main` và PR #2.

## Cập nhật — 08/10/2026 (audit độ bao phủ câu hỏi)

- Tạo `scripts/audit_question_coverage.py` và `src/rag_hcmute/evaluation/question_coverage.py` để thống kê metadata, không in câu hỏi, đáp án hay text nguồn. Kết quả ở `docs/evidence/QUESTION_SET_COVERAGE_AUDIT_20261008.md`.
- Audit trên snapshot G0 cho thấy pilot chung có 10 câu đã duyệt (7 answerable, 3 unanswerable), 7 câu answerable có đủ exact-evidence annotation với 10 span. Câu answerable phân bố ở Quy chế (6) và Hướng dẫn thực tập (1), không có câu nào từ Sổ tay. Năm câu Bảng 5 vẫn là ablation riêng trên một tham chiếu nguồn.
- CSV pilot chưa có trường split; hiện không ghi nhận holdout độc lập. Không tạo hay thay đổi câu hỏi; phần mở rộng và duyệt gold evidence cần người học đối chiếu tài liệu. Vì thế các kết quả reranker/pilot hiện có vẫn chỉ là development evidence.
- Sau khi thêm audit: toàn bộ test suite 84 passed, compileall `src/scripts/tests` đạt và `git diff --check` đạt.

## Cập nhật tiếp nối — 08/10/2026 (phân hoạch tập câu hỏi)

- Tạo sidecar `data/question_sets/question_partition_manifest.csv`: 10 câu P001–P010 được ghi là `development`; năm câu TB001–TB005 tiếp tục tách thành `ablation_only`. Tất cả trỏ tới snapshot G0 `5da3bd4d5de54492`; chưa có holdout và không sửa nội dung câu hỏi/nhãn gold.
- Thêm validator `scripts/audit_question_partitions.py` và `src/rag_hcmute/evaluation/question_partitions.py`. Validator đối chiếu ID đã duyệt trong CSV, partition, trạng thái duyệt và snapshot, đồng thời chỉ in số lượng metadata.
- Manifest có thêm SHA-256 fingerprint từng dòng đã duyệt; nếu câu chữ, gold/evidence hoặc metadata bị đổi mà chưa qua rà soát, các runner dừng. Hash không thay cho việc người học duyệt nội dung và không lưu văn bản.
- Bộ nạp pilot hiện chỉ lấy ID thuộc partition được yêu cầu (mặc định `development`); CLI `run_pilot_eval.py` có lựa chọn partition. Exact-evidence loader và các ablation BM25/Dense/Hybrid/reranker được giới hạn theo cùng ID để tránh trộn annotation của partition khác.
- Hai script đọc trực tiếp câu hỏi Bảng 5 (`evaluate_table_ablation.py`, `diagnose_bm25_query_sensitivity.py`) cũng kiểm tra partition `ablation_only`; không còn đường đánh giá trực tiếp nào bỏ qua manifest trong các runner hiện tại.
- Chưa có holdout để đo; registry không tự tạo câu hỏi hoặc gold evidence. Khi có tập holdout, cần do người học đối chiếu nguồn và duyệt, rồi chỉ dùng cho đánh giá độc lập; không đưa vào tune/ablation development.
- Kiểm thử mục tiêu: 12 passed; toàn bộ suite: 91 passed; `compileall` trên `src/scripts/tests` đạt; `git diff --check` đạt (chỉ có thông báo chuẩn hóa line ending của Git). Mốc 1 vẫn mở; chưa cập nhật DOCX, chưa chuyển Mốc 2, không gọi API và không push/merge/PR.
- Mốc 1 tiếp tục mở, chưa cập nhật DOCX. Không cài thêm package, không dùng API, không push/merge/PR.

## Cập nhật tiếp nối — 08/10/2026 (rà soát lựa chọn công nghệ)

- Tạo `docs/TECHNICAL_OPTIONS_REVIEW_MOC1_20261008.md` từ model cards, tài liệu chính thức và VN-MTEB. Tài liệu phân biệt thông số công bố, kết quả đã đo trên G0 và việc chưa đo; đề xuất tiêu chí so sánh thêm embedding/vector store nhưng không tải model, cài package hay dùng corpus ngoài.
- Kết luận hiện tại không đổi: giữ BM25 + Dense BGE-M3/FAISS làm baseline; RRF và reranker vẫn là biến thể đã đo trên development, không phải mặc định. FAISS/Chroma/Qdrant/Milvus/Pinecone được so sánh về capability và phù hợp triển khai, không gán số hiệu năng chưa đo.
- Kiểm tra lại nguồn corpus: manifest 3 tài liệu qua, 0 lỗi; partition registry ghi nhận 10 câu `development`, 5 câu `ablation_only`, 0 holdout; coverage vẫn là 7 câu answerable/10 span và 3 unanswerable. Thư mục `D:\RAG\nguon_bo_sung` chưa có QĐ 3116/2025.
- Chạy lại toàn bộ suite trong env `rag-hcmute`: `91 passed`. Lần chạy đầu dùng thư mục temp mặc định bị Windows từ chối quyền; lượt xác nhận với `--basetemp` riêng và tắt cache plugin chạy thành công. Không sửa code.
- Các việc còn chặn chốt Mốc 1: người học cần tự kiểm tra/bổ sung câu hỏi và gold evidence để phủ thêm Sổ tay cùng các loại scan/bảng/hình; cần phê duyệt riêng trước khi tải model embedding khác hoặc cài Chroma/Qdrant; tình trạng QĐ 3116 chưa rõ; generation, citation và refusal chưa được triển khai. YC10/YC11 không được ghi là hoàn tất.
- DOCX mốc 1 chưa cập nhật vì các bằng chứng và lựa chọn nêu trên chưa đủ để tuyên bố đóng mốc; không ghi thông số/model chưa chạy thành kết quả thực nghiệm. Nhánh `tim-hieu-rag-dot2`; không push, merge hoặc tạo PR.

## Cập nhật mới nhất — 08/10/2026 (OCR scan, generation local và bản báo cáo Mốc 1)

- Đã tải QĐ 3116/QĐ-ĐHSPKT từ trang Phòng Đào tạo HCMUTE, lưu ngoài Git ở `D:\RAG\nguon_bo_sung\3116_QD_Dao_Tao_2025.pdf`; SHA-256 khớp manifest làm việc riêng. Trang chính thức ghi văn bản áp dụng từ khóa tuyển sinh 2021, Điều 3 thay QĐ 3811; danh mục chính thức nối QĐ 3811 với QĐ 1727. Không suy rộng phạm vi áp dụng cho mọi khóa.
- Audit phát hiện PDF 3116 là scan có text layer OCR nhiễu: native-only không nhận diện scan trên 32/32 trang. `extract.py` nay gắn cờ ảnh phủ ≥70% trang; OCR toàn trang chỉ bật bằng `--ocr --ocr-full-page-images`, không đổi mặc định G0. Snapshot thử riêng `444e283ee11b64e6`: 32 trang OCR, 52 chunk, 28 dấu Điều; chưa có ground-truth transcript toàn tài liệu, không dùng QĐ3116 làm corpus/gold đầu ra.
- Console hỗ trợ generation local qua Ollama loopback bằng Qwen3:4B; không gọi cloud API. `scripts/run_generation_pilot.py` chạy 10 câu development G0, Hybrid RRF + reranker, Top-5: 7/7 answerable được trả lời; 1/3 unanswerable bị từ chối; 7/7 câu answerable có citation tới đúng loại tài liệu; 9/9 câu đã sinh có citation ID hợp lệ. Đây không phải correctness, faithfulness hay semantic citation evaluation. Median retrieval+rerank 2,255 ms, generation 8,720 ms/câu trong một lượt.
- Reranker score answerable (1,84–6,41) chồng lấn với unanswerable (-3,92–2,41; hai trường hợp sát nhau khoảng 0,03), nên không đặt threshold refusal trên development set. Kết quả, cấu hình và giới hạn ghi tại `docs/evidence/GENERATION_PILOT_20261008.md`; kết quả scan tại `docs/evidence/QD3116_SCAN_TEXT_LAYER_AUDIT_20261008.md`.
- Thay đổi unit mới kiểm tra scan có lớp OCR text; console generation fail-closed với nguồn/citation ID không hợp lệ; đánh giá chỉ lưu metrics, không lưu query/answer/source text. Toàn repo: **104 passed**; code không gọi API có phí.
- Bản DOCX mới sẽ được tạo từ v2, không ghi đè bản nộp trước; giữ Times New Roman, màu đen/trắng, khung bìa riêng, không đánh số trang. Báo cáo cập nhật phần kiến thức và tiến độ bằng số liệu mới, ghi rõ G0 là snapshot lịch sử, QĐ3116 chưa được xác thực OCR đầy đủ, refusal 1/3 và chưa có holdout.
- Trạng thái: Mốc 1 đã hoàn thiện phần kỹ thuật và biên tập được phép, nhưng chưa thể ghi là đã đánh giá RAG đáng tin cậy/đã khép YC10–YC11 vì refusal chưa đạt, answer/citation chưa được kiểm tra ngữ nghĩa, chưa có holdout và QĐ3116 OCR chưa được kiểm chứng đủ. DOCX sẽ trình bày các giới hạn này thay vì che đi.
- Tiếp tục trên `tim-hieu-rag-dot2`; main và PR #2 không đổi; không push, merge hoặc tạo PR.
