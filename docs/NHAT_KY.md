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
