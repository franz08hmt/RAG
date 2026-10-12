# Nhật ký Giai đoạn 0

## 2026-09-28 — Khởi tạo, thiết lập môi trường và tái lập baseline

- Clone repository từ nhánh `moc1-progress-report` (commit gốc `4d60860e7a5c27571f5b8e4612e191e653978c4b`) vào `D:\RAG\rag-hcmute-dot2`; tạo nhánh làm việc `tim-hieu-rag-dot2`.
- Tạo Conda env `rag-hcmute` với Python 3.11.16. Sau khi được duyệt, cài Torch CUDA `2.14.0+cu126` trước extras `dev,dense`, cùng `python-dotenv`.
- Xác minh Torch/CUDA: `torch.cuda.is_available() == True`, CUDA runtime 12.6, GPU NVIDIA GeForce RTX 3060 Laptop GPU; phép tính CUDA nhỏ chạy thành công.
- Xác minh import các gói chính và `pip check` (không có dependency bị hỏng). `pytest`: 20 passed; smoke tests: 2/2 passed.
- Đưa PDF Quy chế 1727 đã có vào `data/raw/`, tải hai PDF còn lại từ URL trong manifest; cả ba SHA-256 đều khớp manifest.
- Chạy `scripts/audit_corpus.py`: 3 tài liệu, 0 lỗi; manifest báo corpus sẵn sàng.
- Xác nhận ba PDF trong `data/raw/` được `.gitignore` loại khỏi Git. Không in nội dung văn bản có thể chứa dữ liệu cá nhân.
- Dựng corpus vào thư mục scratch bị ignore để tránh ghi đè snapshot có sẵn: 3 tài liệu, 182 trang, 156 chunks; snapshot ID `5da3bd4d5de54492`.
- Tái lập BM25 trên pilot set: Hit@5 = 3/7 (0.429), MRR@10 = 0.371; khớp baseline trước đó. Ghi rõ Hit@5 thay vì Recall@5 để đúng định nghĩa triển khai hiện tại.
- Sau khi được duyệt, tải 10 tệp PyTorch/Sentence Transformers của BGE-M3 revision `5617a9f61b028005a4858fdac845db406aefb181` vào cache ngoài repo `D:\RAG\models\huggingface` (2.136 GiB); không tải ONNX checkpoint thứ hai. `pytorch_model.bin` 2,271,145,830 byte, SHA-256 `b5e0ce3470abf5ef3831aa1bd5553b486803e83251590ab7ff35a117cf6aad38`.
- Tái lập Dense trên snapshot scratch: script in `Recall@5 = 0.857 (6/7)` và `MRR@10 = 0.643`; khớp bản ghi Dense lịch sử. Do metric hiện tại đếm câu hỏi có ít nhất một gold chunk ở Top-5, nhật ký diễn giải đúng là Hit@5, không coi đây là recall theo số lượng gold chunks.
- Chưa gọi Gemini do khóa đã dán trong hội thoại phải được thu hồi/đổi trước; chưa cài Tesseract vì thuộc Giai đoạn 1.
- Chỉnh `.gitignore` để bỏ qua thư mục `*.egg-info/` do editable install tạo ra.
- Không sửa báo cáo đã nộp, không commit, không push, không merge và không tạo PR.

## Trạng thái checkpoint Giai đoạn 0 — hoàn tất

1. Môi trường, test suite, corpus hashes, snapshot scratch, BM25 và Dense baseline đều đã được kiểm tra/tái lập. BM25: Hit@5 3/7 (0.429), MRR@10 0.371; Dense: Hit@5 6/7 (0.857), MRR@10 0.643.
2. Các tài liệu nguồn và kết quả thô nằm trong các thư mục bị ignore; cache model đặt ngoài repo. Không gửi nội dung corpus lên dịch vụ ngoài.
3. Gemini không thuộc các bước Giai đoạn 0 đã chạy và vẫn tạm dừng cho tới khi khóa cũ được thu hồi/đổi, khóa mới được cấu hình an toàn và các tác vụ được giới hạn theo phê duyệt chi phí. OCR/Tesseract bắt đầu ở Giai đoạn 1 sau khi đề xuất cài đặt.
4. Mọi thay đổi còn local trên `tim-hieu-rag-dot2`; chưa commit/push/merge/tạo PR. Giữ nguyên `main` và PR #2.

## 2026-09-28 — Giai đoạn 1: khảo sát xử lý PDF đầu vào

- Khảo sát cục bộ metadata của 3 PDF trong snapshot hiện tại; không đưa text hoặc nội dung ảnh vào output.
- Xác định 26 trang trong Sổ tay Sinh viên có ảnh phủ gần toàn trang nhưng lớp chữ native dưới 15 ký tự; đây là scan candidates, không phải xác nhận chất lượng OCR.
- PyMuPDF `find_tables()` phát hiện 11 ứng viên trên 8 trang của Quy chế 1727 và 28 ứng viên trên 25 trang của Sổ tay. Các con số chưa được người kiểm tra xác nhận; một số trang ứng viên giao với mục danh bạ có PII nêu ở ADR-002.
- Đối chiếu code: extractor hiện chỉ lấy text native và gắn cờ scan; chưa OCR, chưa lưu block/layout, chưa trích bảng có cấu trúc. Chunker chưa giữ header bảng khi chia hàng.
- Tạo `docs/G1_KHAO_SAT_DU_LIEU_DAU_VAO.md` ghi số liệu audit, giới hạn hiện tại, hướng xử lý và kế hoạch kiểm chứng. Đã đối chiếu tài liệu chính thức của PyMuPDF, Tesseract, Conda-forge và pytesseract.
- Sau khi sinh viên duyệt phương án, chạy dry-run và cài Tesseract 5.5.3 + pytesseract 0.3.13 trong env `rag-hcmute`; transaction tải 217.060.448 byte, link 34 package và thay phiên bản 2 dependency (OpenSSL/XZ). Python 3.11 và Torch 2.14.0+cu126 không bị thay đổi; `torch.cuda.is_available()` vẫn là `True`.
- Vì Conda không cung cấp model ngôn ngữ trong transaction, tải riêng `vie.traineddata` từ repo chính thức `tesseract-ocr/tessdata_best`; file đặt tại `D:\RAG\models\tesseract\tessdata\vie.traineddata`, ngoài repo, 12.435.550 byte, SHA-256 `b6b49293d95d0b6dbd8780174627e82c75be957b6f4ed9862155540d6b00bb45`.
- Chạy OCR cục bộ trên 26 trang nghi scan của Sổ tay ở 200 DPI, `lang=vie`, `psm=6`. Native text median = 3 ký tự; OCR trả về 3.650 từ, median của confidence trung bình theo trang = 86,06/100. Confidence là chỉ số của engine, không phải accuracy; chưa tạo ground truth nên chưa công bố CER/WER. File khảo sát `artifacts/results/g1_ocr_survey.json` chỉ có metric; OCR text của snapshot được giữ cục bộ trong `data/processed/g1_ocr/` (Git ignored).
- Audit `find_tables()` chỉ lưu trang và số hàng/cột, loại trang PDF 140–147 của Sổ tay khỏi lượt này. Kết quả: Quy chế 1727 có 11 ứng viên trên 8 trang; Sổ tay có 20 ứng viên trên 17 trang còn lại; hướng dẫn thực tập có 0. Ứng viên lớn nhất 36×4. Chưa xác nhận bằng kiểm tra trực quan; metadata tại `artifacts/results/g1_table_audit.json` (Git ignored, không chứa cell text).
- Kiểm tra trực quan bảng Quy chế PDF page 3: một bảng phân cấp được nhận shape 14×5 cả ở detector và extraction; 53 ô có text, 17 ô rỗng. Không coi ô rỗng là lỗi đơn giản vì ảnh trang có nhóm hàng/ô gộp; serialize bảng thành chunk vẫn là việc tiếp theo.
- Tích hợp OCR fallback có điều kiện vào ingestion: chỉ khi `--ocr` bật, native text dưới 15 ký tự và trang có raster image; lưu phương thức trích xuất và confidence trong PageText/chunk, đồng thời fingerprint traineddata vào config snapshot. Relative output paths ban đầu làm lỗi lúc ghi snapshot manifest; chuẩn hóa đường dẫn ở pipeline và thêm test regression.
- Dựng snapshot riêng `cc57c028f3816a3d`: 3 tài liệu, 182 trang, 165 chunks; 26 trang OCR, 12 chunks có provenance OCR. Không thay snapshot/baseline G0. Không phát hiện printed page trên 26 trang OCR; vẫn truy vết được đủ 26 PDF page và không tự suy đoán số trang in.
- Chạy lại pilot 10 câu (7 câu có gold evidence) trên cùng chunk labels, sau khi xác minh document/PDF-page range. BM25: Hit@5 3/7, MRR@10 0.351 (baseline 0.371); BGE-M3: Hit@5 6/7, MRR@10 0.786 (baseline 0.643). Kết quả nhỏ, không phải test độc lập, chưa chứng minh OCR cải thiện tổng quát; chưa chạy RAGAS/generation.
- Sau cài đặt và code change ban đầu, `pytest`: 25 passed; smoke test: 2/2 passed; CUDA tiếp tục khả dụng. Mã OCR chạy local; không gọi Gemini hay API trả phí.
- Kiểm tra cuối sau khi bổ sung tự tìm Tesseract trong env: `pytest` 26 passed; smoke tests 2/2 passed; `pip check` không có dependency lỗi. CUDA vẫn `True`. Gọi OCR thật trên PDF page 1 qua Python executable đầy đủ trả 232 ký tự với confidence 61,55; chỉ ghi metric, không in text ra terminal. Đây là smoke test tích hợp, không phải ground-truth accuracy.
- Tạo bộ ground truth thủ công local cho PDF page 107, 109 và 136 của Sổ tay (không có dữ liệu cá nhân); thêm hàm CER/WER, CLI `scripts/evaluate_ocr_sample.py` và test metric. `pytest`: 29 passed. PSM 6 so với 11 trên ba trang: CER/WER tổng hợp có trọng số 35,1%/42,9% so với 28,6%/39,3%; mẫu nhỏ, chưa đổi mặc định. Reference JSON bị ignore, không đưa nội dung handbook vào Git.
- Prototype bảng Quy chế PDF page 3: `find_tables()` trả 14×5; 53 ô có text/17 ô trống; quy tắc nhóm hàng tạo được 11 bản ghi chi tiết. Chỉ khảo sát một bảng, chưa nối vào retrieval. Tài liệu PyMuPDF lưu ý cách phát hiện phụ thuộc đường kẻ/cách dựng bảng; bảng không viền có thể cần `strategy="text"` hoặc logic không gian riêng.
- Commit checkpoint tài liệu ban đầu: `316dd63` (`docs: record G1 input and OCR survey`). Các thay đổi code và cập nhật tài liệu sau checkpoint còn local trên `tim-hieu-rag-dot2`; không push, không tạo PR, `main` và PR #2 không đổi.

## 2026-09-28 — Prototype table variants có kiểm soát

- Đối chiếu trực quan PDF page 20–21 vì câu P003/P008 trỏ vào vùng này. Bảng 5 ở PDF page 20 (printed page 19) là bảng 6×2 về xếp hạng năm đào tạo; bằng chứng cho P003/P008 là văn bản ở Điều 13–14, không phải bảng này. Pilot hiện chưa có câu hỏi tra bảng phù hợp.
- Thêm `scripts/prepare_table_variants.py`: chỉ đọc PDF được chọn trong manifest sau khi kiểm SHA-256; người chạy phải chỉ định document, PDF page, table index, header row đầu tiên và title đã kiểm chứng. Đầu ra T1/T2 cùng `selection.json` chỉ được ghi trong `artifacts/results/table_variants/` (Git-ignored), không in full table text và không thay snapshot mặc định.
- Chạy lệnh trên HCMUTE Quy chế 1727, PDF page 20, table index 2. PyMuPDF trích bảng 6×2; đối chiếu trực quan khớp header và 5 dòng. Sidecar có 1 T1 Markdown chunk và 5 T2 row-context chunks; JSONL đọc lại được qua schema `Chunk`.
- BM25 smoke probe theo cụm từ của dòng “năm thứ ba” xếp row 3 lên đầu ở T2. Đây chỉ là kiểm tra chức năng trên một bảng nhỏ; không phải benchmark hay kết luận T2 tốt hơn T1.
- Thêm kiểm thử cho SHA guard/path guard và adapter chunk; test suite: 39 passed, smoke tests: 2/2 passed. Cần chạy ablation B0/T1/T2 sau khi có câu hỏi bảng do sinh viên xác nhận và gold location.

## 2026-09-28 — Mở rộng OCR PSM pilot

- Xác minh SHA-256 Sổ tay Sinh viên khớp manifest; dùng ba trang đã có reference thủ công (PDF page 107, 109, 136), không tạo reference mới và không in/lưu OCR hypothesis.
- Giữ DPI 200, chạy `scripts/evaluate_ocr_sample.py` với PSM 3, 4, 6, 11, 13 trên từng trang. Reference nội bộ vẫn ở thư mục Git-ignored.
- CER/WER gộp có trọng số theo PSM: 3 = 0,2624/0,3589; 4 = 0,2632/0,3620; 6 = 0,3511/0,4294; 11 = 0,2855/0,3926; 13 = 0,9986/1,0000. PSM 3 tốt nhất trên hai trang văn bản; PSM 11 tốt nhất trên trang sơ đồ nhưng CER/WER còn rất cao.
- Không đổi mặc định PSM 6 vì mẫu chỉ có ba trang và kết quả phụ thuộc loại layout. Ghi chi tiết từng trang, cách tính và giới hạn tại `docs/evidence/OCR_PSM_SWEEP_20260928.md`.

## 2026-09-28 — Bổ sung OCR reference và so sánh PSM trên page 116

- Xác minh SHA-256 Sổ tay Sinh viên khớp manifest, render PDF page 116 (trang in 109) và chọn trang có các khối chữ/danh sách cùng minh họa; không chứa thông tin cá nhân nhận diện người học. Reference chép thủ công, rà theo trang nguồn, lưu ở `artifacts/results/g1_ocr_reference_page116.json` (Git-ignored).
- Chạy PSM 3/4/6/11/13 ở DPI 200, cùng Tesseract/model đã ghim; chỉ log số liệu CER/WER/confidence, không in hypothesis OCR.
- Page 116: PSM 6 CER thấp nhất (21,97%); PSM 4 WER thấp nhất (27,41%). Khi chạy lại cùng cấu hình trên cả 4 trang 107/109/116/136, PSM 4 đạt CER/WER gộp thấp nhất: 24,89%/32,21%. Page 116 chiếm 48,4% ký tự reference, do đó mẫu gộp còn bị ảnh hưởng bởi một trang dài; không đổi mặc định PSM 6.
- Ghi cấu hình, bảng kết quả và giới hạn tại `docs/evidence/OCR_PSM_PAGE116_20260928.md`; cập nhật checkpoint Giai đoạn 1. Không thay snapshot OCR, corpus baseline, chunk hay pipeline retrieval.
- Xác minh `pytest`: 39 passed; smoke tests: 2/2 passed; reference page 116 vẫn bị Git ignore. Không gọi Gemini, không push, không thay `main`/PR #2.

## 2026-09-29 — Khảo sát class tài liệu và độ nhạy kích thước chunk

- Phân loại sơ bộ theo cấu trúc: Quy chế 1727 có 31 mốc Điều và 52 chunk; Sổ tay có 2 dòng khớp mẫu Điều (dưới ngưỡng 4), nên fallback thành 103 sliding-window chunks ở native-only G0; hướng dẫn thực tập một trang tạo 1 chunk. Số liệu lấy từ snapshot, không in nội dung nguồn.
- Phát hiện page span tối đa của chunk Sổ tay là 36 trang ở G0 native-only do các trang scan thiếu text; snapshot G1 OCR có max 8 trang. Đây là giới hạn của citation `pdf_page_start/end` dạng khoảng; chưa thay schema.
- Thêm `src/rag_hcmute/evaluation/chunking_ablation.py`, CLI `scripts/run_chunking_ablation.py` và unit tests. Chạy 250/40, 500/80, 750/120 trên cùng native-only G0 `5da3bd4d5de54492`, giữ nguyên section-aware rule và 7 câu answerable hiện có. Do chunk ID thay đổi, ánh xạ gold theo `section_path` hoặc trang nguồn; metric chỉ là section/page proxy, không so trực tiếp với exact-chunk baseline.
- BM25 section/page Hit@5 giữ ở 4/7 cho cả ba cấu hình; MRR@10 là 0,500 / 0,419 / 0,399. BGE-M3 lần lượt 7/7, MRR 0,929 / 0,762 / 0,833. Không diễn giải thành kết luận chọn 250/40 vì gold location proxy tạo nhiều ứng viên cùng Điều ở chunk nhỏ.
- Ghi nhận giới hạn BGE-M3 `max_seq_length=1024`: 250/40 có 0/297 chunk quá dài; 500/80 có 4/156; 750/120 có 20/111 (max 1.626 subword). Dense results phản ánh cả truncation với cấu hình model hiện tại.
- Raw metadata-only output nằm trong `artifacts/results/chunking_ablation/` (Git-ignored). Chi tiết tại `docs/evidence/CHUNK_SIZE_ABLATION_20260929.md`; `pytest`: 42 passed; smoke tests: 2/2 passed. Model chạy local trên CUDA, không có mạng/cloud API. Baseline/snapshot không bị ghi đè; chưa push.

## 2026-09-29 — Định vị exact evidence span và chạy lại chunk-size ablation

- Bổ sung `token_start`/`token_end` zero-based, khoảng nửa mở, vào chunk để ánh xạ nhãn đoạn nguồn độc lập với kích thước chunk. Không đổi nội dung chunk, chunk ID hay cấu hình mặc định.
- Tạo sidecar `data/question_sets/pilot_evidence_annotations.json`; chọn các mảnh trích dẫn đã có trong pilot, xác thực khớp chuỗi từ trên đúng trang PDF rồi lưu offset và SHA-256 của anchor, không lưu nội dung nguồn vào sidecar/result.
- Chỉ 4/7 câu answerable có vị trí exact tự động kiểm chứng được (P001/P002/P005/P007; 5 span). P003/P004/P008 để pending manual review. Phát hiện P007 có bằng chứng trên PDF page 23 và 24 dù trường `evidence_page` hiện chỉ ghi 23; không sửa CSV gốc, sidecar ghi rõ từng trang.
- Cập nhật evaluator đo Evidence-span Recall@5, Complete-evidence Hit@5 và First-evidence MRR@10. BM25 theo 250/40, 500/80, 750/120: span recall 3/5, 4/5, 4/5; complete hit 2/4, 3/4, 3/4. Dense BGE-M3: lần lượt 5/5 và 4/4 ở cả ba cấu hình; đây là mẫu phát triển rất nhỏ, chưa dùng chọn default.
- Giữ nguyên snapshot G0, nhãn pilot gốc, default 500/80, OCR/generation và corpus. Dense dùng model local/CUDA/offline; không gọi Gemini hay API trả phí.
- `pytest`: 48 passed; smoke tests: 2/2 passed. Raw BM25/Dense metadata-only logs ở `artifacts/results/chunking_ablation/` (Git-ignored); chi tiết tại `docs/evidence/CHUNK_SIZE_EXACT_EVIDENCE_20260929.md`. Chưa push.

## 2026-09-29 — Hoàn thiện nhãn exact evidence cho toàn bộ pilot answerable

- Rà trực tiếp các đoạn tại PDF pages 12, 20 và 21 của Quy chế 1727; bổ sung nhãn cho P003 (tiêu chí cảnh báo theo hai chế độ), P004 (đăng ký học lại) và P008 (các trường hợp buộc thôi học theo hai chế độ).
- Chuẩn hóa sidecar thành annotation version 2: page-local whitespace-token offsets, điều/khoản, hash nội dung đã chuẩn hóa và `snapshot_id` G0. Loader kiểm tra coverage đủ 7/7 answerable, đúng document/page và hash trước khi tính điểm; không ghi trích đoạn nguồn vào repo/output.
- Sửa offset/hash P005 sau khi hash guard phát hiện offset nhầm sang trang cùng số của tài liệu khác; offset được tính lại từ đúng tài liệu Hướng dẫn Thực tập tốt nghiệp. P007 tiếp tục truy nguyên ra PDF pages 23–24; CSV cũ chỉ ghi page 23.
- Chạy lại BM25 và Dense trên 7 câu/10 span. BM25: Evidence-span Recall@5 = 5/10, 4/10, 4/10; Complete-evidence Hit@5 = 3/7 ở cả ba cấu hình. Dense: 10/10, 9/10, 9/10; Complete-evidence Hit@5 = 7/7, 6/7, 6/7 tương ứng 250/40, 500/80, 750/120.
- Số liệu bốn câu/năm span ở phiên bản annotation trước chỉ là bước trung gian, được ghi rõ là superseded trong báo cáo. Chưa đổi default 500/80 vì pilot nhỏ, Dense chunk lớn có truncation và chưa có số đo latency/chi phí.
- Xác nhận `pytest`: 48 passed, smoke tests: 2/2 passed; raw output Git-ignored và metadata-only. Không thay snapshot G0/corpus, không gọi API ngoài, không sửa DOCX và không push.

## 2026-09-29 — Quy ước bàn giao DOCX theo từng mốc

- Theo chỉ đạo của sinh viên, khi hoàn tất mỗi đợt/mốc tiến độ sẽ cập nhật DOCX tương ứng ngay trong lượt hoàn tất, bảo đảm trả lời góp ý mới nhất của giảng viên và chỉ đưa vào kết quả đã kiểm chứng.
- Giữ định dạng báo cáo đã thống nhất; phân biệt rõ việc đã làm, kết quả đo được, việc còn hạn chế và kế hoạch tiếp theo.
- Mốc 1 chưa đóng: chưa chỉnh DOCX trong bước này. Khi nội dung/minh chứng mốc 1 đã được rà soát và chốt, cập nhật DOCX mốc 1 trước khi chuyển sang bàn giao mốc kế tiếp.

## 2026-09-29 — Ánh xạ ứng viên bảng sang chunk B0/T1/T2

- Đối chiếu G0 `5da3bd4d5de54492` và sidecar Bảng 5 (PDF page 20). Toàn bộ nội dung bảng có trong B0 chunk `HCMUTE_QCDT_1727_2021__c0031`; T1 có một chunk toàn bảng; T2 có năm chunk theo hàng.
- Tạo `data/question_sets/table_candidate_chunk_mapping.csv` để ghi ánh xạ vị trí cho TB001-TB005. Trạng thái là `draft_candidate_mapping`; chưa coi là gold vì câu hỏi và vị trí hàng/cột vẫn cần người học xác nhận.
- Không chạy retrieval metric, không sửa pilot/corpus/default; chưa tích hợp T1/T2 vào pipeline mặc định. CSV được kiểm tra cấu trúc trước khi commit.

## 2026-10-03 — Smoke test truy xuất câu hỏi bảng

- Thêm `scripts/smoke_table_candidate_retrieval.py`: chạy thăm dò BM25/Dense trên B0/T1/T2 cho câu nháp, ghi thứ hạng từng câu và proposed chunk IDs; không tính metric, không nhập vào pilot. Đầu ra được giữ trong `artifacts/results/` (Git-ignored). Dense mặc định offline; chỉ truy cập mạng với cờ opt-in `--allow-model-download`.
- BM25 chạy thành công với top-k=5; chunk đích đề xuất xuất hiện trong top-5 cho cả năm câu ở cả ba biến thể. Báo cáo giới hạn tại `docs/evidence/TABLE_RETRIEVAL_SMOKE_20261003.md`; do tập ứng viên có kích thước khác nhau, không dùng thứ hạng này để tuyên bố biến thể nào tốt hơn.
- Dense được thử trong chế độ Hugging Face offline nhưng BGE-M3 không có trong cache của env `rag-hcmute`, nên đánh dấu chưa chạy; không tải model hay gọi API.
- Chưa khóa câu hỏi/gold, chưa tính metric, chưa đổi pilot hoặc pipeline mặc định; DOCX mốc 1 vẫn chờ hoàn tất rà soát nội dung và minh chứng.

## 2026-10-03 — Đối chiếu đề xuất câu hỏi với PDF nguồn

- Xác minh SHA-256 của `data/raw/HCMUTE_QCDT_1727_2021.pdf` khớp manifest (`71ed777e083b5b7be50e129f13dd714553fb8c53aead59d17db92f26b507eaa`); render và kiểm tra trực quan PDF trang 20 (số in 19), Bảng 5.
- Tạo `data/question_sets/table_question_review_proposals_20261003.csv` với câu chữ gợi ý, đáp án đề xuất, hàng nguồn và lưu ý chấp nhận. Sửa đề xuất TB002 để hỏi khoảng đầy đủ; TB005 yêu cầu hai hàng liền nhau.
- Tất cả giữ trạng thái `proposal_requires_student_review`; chưa sửa pilot/gold, không chạy metric và chưa cập nhật DOCX vì Mốc 1 chưa chốt.

## 2026-10-05 — Chạy Dense smoke test từ BGE-M3 local

- Tìm thấy snapshot BGE-M3 tại `D:\RAG\models\huggingface\hub\models--BAAI--bge-m3\snapshots\5617a9f61b028005a4858fdac845db406aefb181`. Lý do model ID không được nhận diện là cache local không được phân giải trong môi trường hiện tại; truyền đường dẫn snapshot trực tiếp đã hoạt động.
- Xác nhận trong env `rag-hcmute`: `torch.cuda.is_available() == True`, model nạp trên `cuda:0`, embedding dimension 1024. Không tải model hoặc gọi API.
- Thêm tham số `--dense-model` vào smoke-test script và chạy lại BM25/Dense trên B0/T1/T2. Kết quả từng câu ở `docs/evidence/TABLE_RETRIEVAL_SMOKE_20261005.md`; JSON đầy đủ trong `artifacts/results/` (Git-ignored).
- Kết quả vẫn chỉ là thăm dò: câu hỏi và gold chưa được người học xác nhận, không tính metric, không sửa pilot/pipeline mặc định và chưa cập nhật DOCX mốc 1.

## 2026-10-05 — Sửa thiết kế so sánh table retrieval

- Phát hiện lượt table-only so sánh corpus không cân đối (B0=156, T1=1, T2=5 chunks), nên hạng #1 của T1 không có ý nghĩa so sánh. Giữ lượt đó như smoke test ban đầu, không dùng làm kết luận.
- Cập nhật smoke script để giữ 155 chunk nền và chỉ tách phần Bảng 5 khỏi B0 `c0031`, bảo toàn nội dung trước bảng trong một chunk phần dư, rồi thay phần bảng bằng T1 hoặc năm hàng T2. Corpus kết quả: B0=156, T1=157, T2=161.
- Chạy lại BM25 và Dense BGE-M3 local top-5. Kết quả có thứ hạng từng câu tại `docs/evidence/TABLE_RETRIEVAL_MATCHED_CONTEXT_SMOKE_20261005.md`, JSON Git-ignored. Không tính metric vì câu hỏi/gold vẫn chưa được người học xác nhận.
- Không đổi default pipeline, không đưa câu nháp vào pilot/gold; DOCX mốc 1 chưa cập nhật.

## 2026-10-05 — Ablation retrieval với câu hỏi Bảng 5 đã duyệt

- Người học chấp thuận năm câu TB001–TB005 và đáp án/bằng chứng đề xuất để dùng trong ablation riêng trên QĐ 1727/2021. Đóng băng thành hai file versioned trong `data/question_sets/`; không sửa `pilot_questions.csv` và không khẳng định QĐ 1727 là quy định hiện hành.
- Tạo `src/rag_hcmute/evaluation/table_ablation.py` để dựng corpus matched-background và tính đủ-evidence Hit@5, coverage đơn vị evidence, MRR evidence đầu tiên. TB005 yêu cầu đủ hai hàng T2.
- Thêm `scripts/evaluate_table_ablation.py`; chạy BM25 và BGE-M3/FAISS local trên CUDA, `top_k=5`, snapshot G0 `5da3bd4d5de54492`, không gọi API. Raw JSON Git-ignored: `artifacts/results/table_retrieval_ablation/table_ablation_both_20261005T114541Z.json`.
- Kết quả đủ evidence Hit@5: BM25 B0/T1/T2 = 4/5, 1/5, 0/5; Dense = 5/5 ở cả ba. Dense MRR evidence đầu tiên @5 = 0,600/1,000/0,867. Đây chỉ là ablation trên năm câu; không đổi retrieval mặc định, không gộp thành benchmark chung.
- `pytest`: 51 passed; smoke tests: 2/2 passed (temp directory được chuyển vào workspace theo giới hạn sandbox). Ghi chi tiết kết quả tại `docs/evidence/TABLE_RETRIEVAL_APPROVED_ABLATION_20261005.md`. Chưa cập nhật DOCX mốc 1 do mốc chưa đóng.

## 2026-10-05 — Chẩn đoán độ nhạy truy vấn của BM25 trên Bảng 5

- Giữ nguyên 5 câu TB001–TB005 đã duyệt, gold evidence, corpus B0/T1/T2, tokenizer và BM25; chỉ thử thêm ba dạng truy vấn chẩn đoán: nối tên cột vào câu gốc, rút gọn cụm dẫn chiếu văn bản, và kết hợp hai cách này. Không ghi các biến thể vào pilot hoặc dùng làm benchmark chính.
- Hạng evidence trong Top-5 đủ cho 4/5, 1/5, 0/5 câu ở canonical B0/T1/T2; với truy vấn rút gọn + tên cột là 5/5, 4/5, 3/5. T1/T2 vẫn có trường hợp evidence ngoài Top-5; TB001/TB004 của T2 ở hạng 7 và 9. Đây là kết quả mô tả trên năm câu, không chứng minh query expansion cải thiện tổng quát.
- Ghi truy vấn, hạng đầy đủ và giới hạn tại `docs/evidence/BM25_QUERY_SENSITIVITY_DIAGNOSTIC_20261005.md`. Không đổi index, metric chính, pipeline mặc định hay câu hỏi đã duyệt; chưa cập nhật DOCX vì Mốc 1 chưa đóng.
- Thêm `scripts/diagnose_bm25_query_sensitivity.py` để tái lập lượt chẩn đoán và lưu raw JSON Git-ignored với query, evidence rank, Top-5 IDs, hash bộ câu hỏi/evidence và revision code.

## 2026-10-07 — Kiểm kê document class và xử lý đầu vào

- Đối chiếu `corpus_manifest.csv`, snapshot/build log G0, page/chunk JSONL metadata và tham chiếu ảnh raster trong PDF. Ba source hash khớp manifest; snapshot G0 `5da3bd4d5de54492` có 3 tài liệu, 182 trang, 156 chunk.
- G0 gồm 1 quy chế có 31 dấu Điều/52 chunk, 1 hướng dẫn không cấu trúc/1 chunk và 1 sổ tay không đạt ngưỡng cấu trúc Điều/103 chunk. 26 trang Sổ tay bị heuristic gắn cờ nghi scan; đây không phải xác minh trực quan toàn bộ. Trong PDF có raster refs ở 2/32, 0/1, 149/149 trang tương ứng; đây không phải phân loại ngữ nghĩa ảnh.
- Build log G0 chỉ ghi PyMuPDF, không có cấu hình OCR; thí nghiệm OCR 4 trang đã ghi riêng trong evidence và chưa tích hợp vào snapshot. G0 JSONL thiếu extraction method, OCR confidence và token offsets. Table Bảng 5 đã thử riêng bằng dữ liệu rà soát thủ công; chưa có parser tự động tổng quát.
- Phát hiện mô tả PDF page 107 không nhất quán giữa hai báo cáo OCR (scan text so với infographic); đã đánh dấu cần xác nhận cục bộ, không đưa ảnh Sổ tay vào hội thoại vì ràng buộc riêng tư.
- Tạo `scripts/audit_document_input_profile.py` để tái lập audit metadata-only; JSON raw Git-ignored ở `artifacts/results/input_document_profile/`. Ghi nhận phương pháp và khoảng trống theo YC4/YC13 tại `docs/evidence/INPUT_DOCUMENT_CLASS_AUDIT_20261007.md`. Mốc 1 chưa đóng, chưa cập nhật DOCX.
- Tạo `docs/evidence/INPUT_CLASS_PROCESSING_MATRIX_20261007.md`, nối từng dạng đầu vào với cách xử lý hiện tại, minh chứng, giới hạn và phép thử kế tiếp. Phân biệt document class ở cấp nguồn với layout/modality ở cấp trang; không chạy thêm benchmark hay đổi code mặc định.
- Rà soát cục bộ metadata bố cục page 107 bằng Tesseract 5.5.3/PSM 4 (chỉ ghi số đơn vị, dòng, khối OCR; không ghi nội dung). Kết quả 86/15/8 gần page 136 (79/13/7) hơn các trang chữ nhiều hơn trong mẫu, ủng hộ nhãn infographic/nội dung thị giác hỗn hợp với độ tin cậy vừa phải. Ghi tại `docs/evidence/OCR_LAYOUT_LABEL_RECHECK_20261007.md`.
- Sửa mô tả phân loại và cách diễn giải trong `OCR_PSM_SWEEP_20260928.md`; không thay các CER/WER, không tuyên bố đã xác nhận bằng mắt. Nhãn chắc chắn hơn vẫn cần người học kiểm tra trực tiếp trên máy.
- Lập `docs/evidence/INPUT_CLASS_SAMPLE_PLAN_20261007.md` để chọn mẫu trang cho OCR, chunking và kiểm tra retrieval. Sổ tay page 10 chỉ là ứng viên theo metadata (char_count gần median), cần người học sàng lọc bố cục/riêng tư cục bộ trước khi đưa vào tập chia sẻ; chưa chạy benchmark mới.
- Chạy sweep DPI 200/300 x PSM 4/11 trên bốn trang OCR đã có reference bằng `scripts/run_ocr_dpi_sensitivity.py`. Weighted CER/WER: PSM 4 = 24,89%/32,21% ở 200 DPI và 28,73%/39,09% ở 300 DPI; PSM 11 = 32,19%/37,75% và 43,63%/53,36%. Lưu metrics-only JSON ở Git-ignored `artifacts/results/ocr_dpi_sensitivity/`; không lưu hypothesis/reference text.
- Ghi kết quả và giới hạn tại `docs/evidence/OCR_DPI_SENSITIVITY_20261007.md`. Không đổi DPI/PSM mặc định, không gọi API, không cập nhật DOCX; thí nghiệm chỉ mô tả bốn trang và PSM 6 không được so sánh trong lượt này.

## 2026-10-07 — Đo độ khôi phục token số và cue điều kiện trong OCR

- Mở rộng sweep DPI để đo exact occurrence precision/recall cho token chứa chữ số và một inventory cố định về phủ định/điều kiện; chỉ xuất số đếm/metric, không ghi token, cue hay text/reference OCR vào JSON. Raw metrics-only JSON mới ở Git-ignored `artifacts/results/ocr_dpi_sensitivity/ocr_dpi_sensitivity_20261007T074033Z.json`.
- Trên tổng 32 token số của bốn trang, recall theo DPI/PSM là 31,25% (200/4), 46,88% (200/11), 40,63% (300/4), 46,88% (300/11); precision tương ứng 71,43%, 62,50%, 72,22%, 60,00%. Cue đạt 4/4 ở cả cấu hình nhưng mẫu chỉ có bốn occurrence, nên không xem là bằng chứng đủ mạnh về xử lý điều kiện/phủ định.
- Kết luận thực dụng: CER/WER không đủ để kết luận độ an toàn của OCR ở mã/số/điều kiện. OCR trên bốn trang vẫn không thể làm nguồn cuối cùng cho chi tiết trọng yếu; cần đối chiếu trực tiếp hoặc mở rộng mẫu và kiểm tra lỗi theo từng loại tài liệu. Không đổi default OCR/ingestion và không tích hợp OCR vào G0.
- Thêm metric/helper và unit tests ở commit cục bộ `409d168`; toàn bộ `pytest`: 53 passed; `compileall` và `git diff --check` đạt. Không gọi API/Gemini, không push, không sửa DOCX; Mốc 1 vẫn mở.

## 2026-10-07 — Bổ sung PSM 6 và rà soát YC4/YC13

- Theo đề xuất rà soát, mở rộng cùng phép thử lên PSM 4/6/11 ở DPI 200/300 trên đúng bốn trang đã có reference; không mở rộng sang trang chưa được kiểm tra quyền riêng tư. Tesseract help xác nhận mô tả PSM 6 là một khối chữ thống nhất; PSM 4 là một cột có kích thước chữ thay đổi; PSM 11 là văn bản rải rác.
- Chạy 24 lượt sau commit `90fb837`. CER/WER gộp: PSM4 = 24,89%/32,21% (200 DPI), 28,73%/39,09% (300); PSM6 = 28,76%/36,91%, 30,92%/42,79%; PSM11 = 32,19%/37,75%, 43,63%/53,36%. PSM4 thấp nhất về CER/WER; PSM6 có recall token số cao nhất trong mẫu nhỏ: 53,13% và 62,50%, với precision 56,67% và 68,97%. Kết quả và JSON metrics-only Git-ignored tại `docs/evidence/OCR_DPI_SENSITIVITY_20261007.md` và `artifacts/results/ocr_dpi_sensitivity/ocr_dpi_sensitivity_20261007T074720Z.json`.
- Audit độc lập YC4/YC13 trên tài liệu Markdown: bằng chứng đủ để nói đã khảo sát và thử cục bộ một phần đầu vào, chưa đủ đóng YC4/YC13. Các giới hạn còn lại là tổng quát hóa theo lớp/layout, xử lý bảng nhiều cấu trúc, diễn giải hình/sơ đồ và khảo sát sâu các giai đoạn còn lại của RAG.
- Đồng bộ G1: làm rõ OCR chỉ được bật tùy chọn qua CLI trên snapshot riêng, G0 vẫn native-only; ghi rõ 3 trang là ground truth ban đầu trước khi thêm trang thứ tư; phân biệt 28 detector candidates ban đầu với 20 sau khi bỏ vùng trang danh bạ (không đồng nghĩa xác nhận thủ công). Cập nhật handoff, không cập nhật DOCX vì Mốc 1 chưa chốt.
- Giữ nguyên OCR default, snapshot G0 và câu hỏi/gold; không gọi API, không push. Test vẫn 53 passed; `compileall` đạt.

## 2026-10-07 — So sánh policy chunk theo cấu trúc với cửa sổ cố định

- Thêm cờ tùy chọn `force_sliding_window` vào `chunk_document()`; mặc định `False` giữ nguyên hành vi cũ. Tạo runner `scripts/run_chunk_strategy_ablation.py`, ghim G0 native-only `5da3bd4d5de54492`, xác minh hash corpus và so sánh policy theo Điều với cửa sổ 500/80 trên tài liệu có cấu trúc. Đơn vị chunk là whitespace token.
- Đánh giá lại đúng 7 câu answerable/10 span hiện có (6 câu/9 span ở Quy chế 1727; 1 câu/1 span ở Hướng dẫn thực tập; không có câu Sổ tay). Span không nằm trọn trong chunk vẫn ở mẫu số và tính là miss; đồng thời báo page-location proxy riêng, không coi proxy trang là exact evidence.
- BM25: policy theo Điều bao phủ 10/10 span, exact Recall@5 4/10, complete Hit@5 3/7, page proxy Hit@5 3/7; fixed windows bao phủ 9/10, lần lượt 6/10, 4/7 và 6/7. Dense BGE-M3 local/CUDA: policy theo Điều 10/10, 9/10, 6/7, 7/7; fixed windows 9/10, 8/10, 5/7, 7/7.
- BM25 và Dense cho thứ hạng khác nhau; fixed windows mất độ phủ một span. Không đổi default hoặc G0; kết quả trên pilot phát triển nhỏ, không phải holdout và chỉ có một tài liệu có cấu trúc cùng sáu câu answerable. Không đánh giá generation hay kết luận tổng quát theo document class.
- Ghi phương pháp/kết quả/giới hạn ở `docs/evidence/CHUNK_STRATEGY_ABLATION_20261007.md`; JSON metrics-only Git-ignored. Thêm hai kiểm thử cho cờ chunker và một kiểm thử bảo đảm span không được bao phủ tính là miss. `pytest`: 56 passed; `compileall` và `git diff --check` đạt. Không gọi API, không cập nhật DOCX, không push; Mốc 1 vẫn mở.

## 2026-10-07 — Hybrid Retrieval bằng RRF

- Bổ sung `ReciprocalRankFusionRetriever` để hợp nhất hạng BM25Okapi và Dense BGE-M3; raw BM25/cosine scores không cộng trực tiếp. Dùng công thức RRF với `k=60`, Top-20 mỗi nhánh, Top-10 đầu ra; kiểm tra hai index có cùng chunk ID set và tie-break theo chunk ID để kết quả lặp lại được.
- Tạo runner so sánh BM25, Dense và Hybrid trên G0 native-only. Vì snapshot G0 lưu trước token offsets, runner tái tạo chunk trong bộ nhớ và chỉ tiếp tục khi chữ ký nội dung khớp snapshot; không sửa G0. Dense dùng BGE-M3 local/CUDA/offline; không tải model hay gọi API.
- Trên 7 câu answerable/10 span, Evidence Recall@5: BM25 4/10, Dense 9/10, Hybrid 6/10; Complete-evidence Hit@5: 3/7, 6/7, 4/7; First-evidence MRR@10: 0,371, 0,762, 0,524. RRF cải thiện BM25 nhưng không vượt Dense trong mẫu này; không đổi default.
- Ghi kết quả/giới hạn tại `docs/evidence/HYBRID_RRF_ABLATION_20261007.md`; JSON metrics-only Git-ignored. Bài gốc RRF được dẫn theo DOI, không suy rộng hiệu quả từ benchmark tổng quát sang dữ liệu HCMUTE.
- Toàn bộ test suite: 61 passed; `compileall` và `git diff --check` đạt. Không cập nhật DOCX, không push; Mốc 1 vẫn mở.
- Kiểm tra cục bộ không tải/cài mới: Hugging Face cache chỉ có BGE-M3; env có sentence-transformers/FAISS nhưng chưa có ChromaDB, Qdrant client hoặc Milvus client. Ghi nhận để không tự ý tải thêm model hay dependency.

## 2026-10-07 — Chẩn đoán các trường hợp lỗi của Hybrid Retrieval

- Bổ sung phân loại retrieval theo từng câu answerable: đủ mọi span ở Top-5, một phần span ở Top-5, chỉ có span ở hạng 6–10, hoặc không có exact evidence trong Top-10. Kết quả lưu mã câu/span, loại tài liệu và hạng; không lưu câu hỏi, đáp án, văn bản nguồn, preview hay vector.
- Chạy lại BM25/Dense/RRF trên cùng G0 và 7 câu/10 span. Tổng metric không đổi: exact Recall@5 4/10, 9/10, 6/10; Complete-evidence Hit@5 3/7, 6/7, 4/7. RRF có đủ evidence Top-5 ở 4/7 câu; Dense ở 6/7. P004 được RRF đưa lên hạng 4 từ ngoài Top-10 của BM25; P003 chỉ còn một trong hai span ở Top-5, P005 không có span trong Top-10, P008 có các span ở hạng 6 và 8.
- Diễn giải chỉ ở mức mô tả pilot: có trường hợp Hybrid giúp BM25 và cũng có trường hợp kém Dense; không đổi RRF k/cutoff hoặc retrieval mặc định, không coi đây là holdout.
- Cập nhật báo cáo evidence, G1, README và handoff. Kiểm thử phân loại 6/6; toàn bộ pytest 67 passed; compileall đạt. Chưa cập nhật DOCX, chưa đóng Mốc 1/chuyển Mốc 2; không gọi API, không tải/cài model, không push/merge/PR.

## 2026-10-07 — Console PoC cho retrieval

- Bổ sung `src/rag_hcmute/console_app.py` với chế độ one-shot và tương tác; mặc định BM25 trên G0, có tùy chọn Dense và Hybrid RRF. Dense/Hybrid bắt buộc đường dẫn model local và bật chế độ offline; không cho tải tự động.
- Console hiển thị phương thức, thời gian, hạng, điểm, tên tài liệu, PDF page, section và excerpt ngắn; thông báo rõ phần hiện tại chỉ retrieval, không generation/refusal. Smoke test BM25 và Hybrid trên G0 156 chunks đều qua; kết quả capture trong bộ nhớ, không lưu câu hỏi hay trích đoạn nguồn.
- Smoke Hybrid phát hiện wrapper RRF không cung cấp `chunks` trực tiếp; sửa phần xác định kích thước corpus để đọc từ lexical retriever và thêm test hồi quy.
- Bằng chứng và giới hạn tại `docs/evidence/RETRIEVAL_CONSOLE_20261007.md`. Lệnh `python -m` Hybrid và `--help` UTF-8 trên PowerShell đã chạy thành công. Toàn bộ pytest hiện 74 passed; `compileall` và `git diff --check` đạt. Mốc 1 vẫn mở; chưa chỉnh DOCX, không gọi API, không tải model/gói, không push/merge/PR.

## 2026-10-07 — Độ phủ candidate trước reranker

- Mở rộng runner Hybrid để đo exact-evidence coverage ở độ sâu Top-20, tương ứng với candidate pool có thể đưa sang reranker. Lượt chạy dùng cùng G0 native-only, pilot 7 câu/10 span và BGE-M3 cục bộ; không gọi API hoặc tải model.
- Top-20 BM25 chứa 7/10 span và đủ toàn bộ evidence ở 5/7 câu; Dense BGE-M3 và RRF đều chứa 10/10 span, đủ ở 7/7 câu. Kết quả này chỉ cho thấy evidence có mặt trong candidate pool; chưa đo reranker và không chứng minh thứ hạng sau reranking.
- Pilot nhỏ vẫn là dữ liệu phát triển, không phải holdout độc lập; không đổi mặc định hay chọn reranker. Báo cáo chi tiết tại `docs/evidence/HYBRID_RRF_ABLATION_20261007.md`; raw JSON chỉ chứa metric và mã định danh, Git-ignored.
- Thêm hai test cho cutoff candidate; toàn bộ pytest 76 passed, `compileall` và `git diff --check` đạt. Mốc 1 vẫn mở, chưa cập nhật DOCX/chuyển Mốc 2; không tải/cài thêm model/gói, không push/merge/PR.

## 2026-10-07 — Chuẩn bị phương án reranker

- Kiểm tra read-only môi trường: ổ D còn khoảng 22,33 GiB; env project dùng Torch 2.14.0+cu126, CUDA khả dụng trên RTX 3060 Laptop GPU 6 GiB; `transformers` và `sentence-transformers` đã có.
- Đối chiếu model card và tài liệu inference chính thức. Đề xuất đánh giá duy nhất `BAAI/bge-reranker-v2-m3` trước: repo 2,29 GB, trọng số 2,27 GB, license Apache-2.0, model type multilingual cross-encoder. Không suy ra chất lượng tiếng Việt cho HCMUTE nếu chưa đo trên tập câu hỏi có gold.
- Soạn thiết kế benchmark cặp trước/sau rerank trên cùng Dense Top-20 và RRF Top-20, giữ G0/chunk/query/gold cố định; dự kiến đo exact-evidence Recall@5, Complete-evidence Hit@5, MRR@10, latency và VRAM. Cần thống kê truncation query–chunk vì ví dụ model dùng max length 512.
- Import-only smoke test cho `AutoTokenizer`, `AutoModelForSequenceClassification` và `CrossEncoder` đạt trong env project với chế độ offline; không nạp trọng số hoặc gọi mạng. Chưa tải model, không cài package, không gọi API; đề xuất và giới hạn ghi tại `docs/evidence/RERANKER_RESOURCE_AND_EVAL_PLAN_20261007.md`. Cần duyệt riêng trước khi tải; Mốc 1 vẫn mở, chưa cập nhật DOCX/chuyển Mốc 2.

## 2026-10-08 — Hoàn thiện gói tài liệu Mốc 1 và audit kỹ thuật

- Rà soát lại mọi YC1–YC13 theo yêu cầu giảng viên; tạo `docs/TRUY_VET_YC.md`, ba tài liệu nghiên cứu, hướng dẫn thực hành, question-data policy và 40 câu hỏi tự kiểm tra. Trạng thái YC được đánh dấu “một phần” khi chỉ có pilot hoặc thiếu xác minh; không tạo holdout/gold giả.
- Cập nhật tài liệu lựa chọn công nghệ từ “chưa đo” sang trạng thái hiện tại. Báo cáo evidence mới: BGE-M3 vs multilingual-E5-small và FAISS exact vs Qdrant local exact; QĐ 3116 scan vẫn ngoài G0.
- Nối Ollama/Qwen3:4B vào console để thử generation local. Raw run 10 câu development: output cho 7/7 answerable, non-answer ghi nhận 1/3 unanswerable (có một output JSON không hợp lệ), expected-document ID 7/7, citation ID hợp lệ 9/9; không chấm câu trả lời hoặc semantic citation.
- Tạo report mới `reports/22110068_RAG_Bao_Cao_Tien_Do_Dot_1_v4.docx` từ mẫu v2. Bảng số liệu được dựng từ raw JSON; bản render Word/PDF kiểm tra tại `artifacts/results/docx_m1_v3_template/` (Git-ignored). Không sửa bản nộp v2, không gọi API, không push/merge/PR.
- Rà render Word phát hiện hai điểm bố cục ở v4: đoạn chunking bị ngắt giữa trang và phụ lục căn đều làm giãn các đường dẫn. Tạo v5 để giữ nguyên đoạn chunking cùng trang và căn trái phụ lục; xác nhận lại PDF 13 trang. Bản hiện hành: `reports/22110068_RAG_Bao_Cao_Tien_Do_Dot_1_v5.docx`; v3/v4 giữ làm bản trung gian.
- Chạy pytest lại với `--basetemp` riêng do Temp/cache dùng chung bị từ chối quyền: 104 passed; `compileall` và `git diff --check` đạt. Ghi đúng kết quả kiểm tra vào phụ lục và tạo v6; v3–v5 là bản trung gian.

## 2026-10-12 — Bắt đầu thiết kế kiến trúc Mốc 2

- Giữ nguyên `D:\RAG\22110068_RAG_IT_Project_DEMO.docx` làm bản demo ban đầu đã được giảng viên chốt. Báo cáo Mốc 1 v6 tiếp tục là tài liệu riêng; không gộp tự động, không ghi đè demo hoặc DOCX đã nộp. Báo cáo ở các mốc sau sẽ được tạo nối tiếp từ kết quả có minh chứng.
- Đối chiếu code hiện tại ở ingestion, chunking, BM25/Dense/RRF, reranking, generation Ollama và console; tạo `docs/ARCHITECTURE_M2_DRAFT.md` để phân biệt luồng đang có với lựa chọn/kiểm chứng còn mở. Tài liệu bao gồm hợp đồng `PageText`/`Chunk`/`RetrievalHit`/`GroundingSource`, lớp đầu vào, giới hạn citation/refusal và các cổng đánh giá.
- Cập nhật `README.md` và `docs/HANDOFF_DOT_1.md` để trỏ đến bản thiết kế mới và sửa trạng thái bàn giao về cấu trúc tài liệu hiện hành.
- Chạy lại toàn bộ `pytest` bằng `C:\Users\Dell\anaconda3\envs\rag-hcmute\python.exe`: **104 passed**; `compileall src scripts tests` và `git diff --check` đạt. Torch `2.14.0+cu126`, CUDA khả dụng.
- Không sửa code hoặc DOCX, không chạy benchmark mới, không dùng API, không tải/cài model hay dependency; chưa push/merge/tạo PR. Mốc 1 có báo cáo v6 nhưng các phần holdout, câu hỏi/gold do người học duyệt, đánh giá ngữ nghĩa và tính tổng quát theo input class vẫn chưa được coi là hoàn tất.

## 2026-10-12 — Kiểm chứng chuỗi provenance đến citation

- Thêm `tests/test_rag_provenance_integration.py`: dùng PDF fixture tổng hợp để kiểm tra metadata `Chunk` → `RetrievalHit` → `GroundingSource` → citation sau generation mock. Các trường document/chunk ID, tiêu đề, trang PDF và section được so khớp xuyên suốt.
- Test tích hợp mục tiêu đạt 1/1; toàn bộ suite đạt **105 passed**; `compileall src scripts tests` và `git diff --check` đạt trong env `rag-hcmute`.
- Đây chỉ là kiểm chứng cấu trúc/truy vết, không đánh giá nguồn có entail câu trả lời hay không. Không chạy benchmark, không gọi model/API, không sửa DOCX; Mốc 1 vẫn còn các khoảng trống cần câu hỏi/gold do người học duyệt và đánh giá ngữ nghĩa.

## 2026-10-12 — Khung chấm thủ công generation cho bước đầu Mốc 2

- Bổ sung `docs/evaluation/manual_review_protocol.md` với rubric riêng cho correctness, faithfulness, relevance, citation location và mức hỗ trợ từng claim; hai template CSV không có câu trả lời/source text. Tạo `manual_review.py` để kiểm schema, ID, nhãn, quan hệ claim–answer và denominator; thêm CLI tạo phiếu `pending` và tổng hợp nhãn mà không ghi điểm RAG tổng hợp.
- Thêm tùy chọn rõ ràng `--review-bundle-dir` cho generation pilot. Nội dung câu hỏi/đáp án/các nguồn chỉ được lưu khi bật tùy chọn này và bắt buộc nằm ngoài repository; mặc định metrics-only không đổi.
- Chạy lại cùng generation pilot trên G0 development: Hybrid + reranker Top-5, Qwen3:4B qua Ollama local. Kết quả lặp lại 7/7 answerable có output, 1/3 unanswerable abstain, 7/7 expected-document ID, 9/9 citation ID hợp lệ; có 1 output JSON lỗi trong tổng 10 câu. Đây là tái lập trên cùng bộ, không phải benchmark độc lập hay semantic evaluation.
- Bundle kiểm tra metadata có đủ 10 record/10 question ID và 10/10 có nguồn truy xuất. File chứa văn bản nằm ngoài repo tại `D:\RAG\private_eval\m2_generation_reviews\`; answer sheet 10 dòng pending và claim sheet header-only ở `D:\RAG\private_eval\manual_review\`. Không đưa nội dung vào Git, không tự gán nhãn thay người học.
- Cập nhật `docs/ARCHITECTURE_M2_DRAFT.md`, YC11, README và handoff để phản ánh đúng trạng thái; Mốc 1/DOCX chưa đóng hay sửa vì còn thiếu nhãn semantic đã xác minh. Toàn repo: **113 passed**, `compileall` và `git diff --check` đạt. Không dùng 8B, Gemini/cloud API, dependency mới, push/merge/PR.

## 2026-10-12 — Chốt cấu hình kiến trúc làm việc và smoke test console

- Tổng hợp các ablation đã có thành `docs/decisions/ADR-004-current-poc-architecture.md`: cấu hình được giữ làm baseline/ứng viên, số liệu nguồn và giới hạn được nêu cạnh nhau. ADR không đổi default/code, không gọi cấu hình tối ưu và không dùng development pilot để tuyên bố tổng quát.
- Chạy trực tiếp `rag_hcmute.console_app` với BM25 trên snapshot G0 (156 chunks), không gọi LLM/API. Câu P007 đưa Quy chế 1727/2021, Điều 17, PDF trang 23–24 lên hạng 1; một truy vấn thử về điều kiện tốt nghiệp chỉ đưa Điều 16 lên hạng 3. Đây là kiểm tra luồng/metadata và một quan sát lỗi xếp hạng, không phải phép đo benchmark mới.
- Cập nhật ma trận YC12 và handoff để làm rõ đang bắt đầu Mốc 2, trong khi các yêu cầu Mốc 1 chưa có semantic review/holdout vẫn mở. Không sửa DOCX và không thay dữ liệu/gold.
- Chưa đụng tới phiếu chấm riêng ở `D:\RAG\private_eval\`; nhãn answer/claim vẫn do người học rà và điền. Không gọi Gemini/cloud API, không dùng model 8B, không push/merge/tạo PR.
- Sau đó thử đường console tích hợp Hybrid + reranker + generation ở chế độ cold-start. Lượt đầu Ollama chưa chạy; lượt sau khởi động Ollama loopback nhưng quá trình vẫn nạp model retrieval/reranker hơn hai phút và chưa phát request inference; đã dừng cả lần chạy lẫn server do agent khởi động. Không có output mới và không tính đây là kết quả benchmark; cần profiling/thời gian warm-up riêng trước khi trình diễn đường tích hợp.
