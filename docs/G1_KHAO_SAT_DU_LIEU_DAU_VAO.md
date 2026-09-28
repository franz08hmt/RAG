# Giai đoạn 1 — Khảo sát xử lý tài liệu đầu vào

**Trạng thái:** Đã kiểm tra corpus, cài OCR cục bộ và chạy khảo sát thử trên các trang nghi scan; chưa tích hợp OCR vào pipeline.
**Phạm vi:** YC4 — tài liệu PDF có lớp chữ, trang scan, bảng và hình ảnh.
**Snapshot khảo sát:** `5da3bd4d5de54492` — 3 tài liệu, 182 trang.

## 1. Kết quả kiểm tra corpus

Các số liệu dưới đây được đo cục bộ bằng PyMuPDF 1.28.2. Chỉ ghi nhận số trang, ký tự, ảnh và hình dạng bảng; không trích nội dung tài liệu vào nhật ký hay gửi ra ngoài.

| Tài liệu | Trang | Trang có lớp chữ trích xuất được | Trang nghi scan/ít chữ | Trang có ảnh raster | Ứng viên bảng từ PyMuPDF |
|---|---:|---:|---:|---:|---:|
| Quy chế 1727 | 32 | 32 | 0 | 2 | 11 bảng trên 8 trang |
| Hướng dẫn thực tập tốt nghiệp | 1 | 1 | 0 | 0 | 0 |
| Sổ tay Sinh viên 2024 | 149 | 148 | 26 | 149 | 28 bảng trên 25 trang |

“Nghi scan/ít chữ” là heuristic hiện có: trang có dưới 15 ký tự trích xuất và có ảnh, hoặc không trích xuất được chữ. Trong Sổ tay, các trang ứng viên là 1, 107, 109–112, 116–117, 121, 123–127, 129–139 và 149; cả 26 trang đều có ảnh phủ gần toàn trang. Tuy nhiên, vì ảnh raster cũng xuất hiện trên nhiều trang vẫn có lớp chữ, không thể kết luận chỉ dựa vào việc trang có ảnh. Các trang này cần được thử OCR cục bộ rồi đối chiếu chất lượng.

PyMuPDF đánh dấu 11 và 28 **ứng viên** bảng bằng `Page.find_tables()`; đây chưa phải số bảng đúng đã được con người xác nhận. Một số ứng viên nằm ở các trang danh bạ đã được ADR-002 ghi nhận có thông tin liên hệ cá nhân. Không ghi cell text của các trang này vào tài liệu, log hoặc dịch vụ cloud.

Ở lượt audit cấu trúc tiếp theo, chỉ lưu trang và số hàng/cột, đồng thời bỏ qua trang PDF 140–147 của Sổ tay để tránh xử lý phần danh bạ. Kết quả còn 20 ứng viên bảng trên 17 trang của Sổ tay; Quy chế có 11 ứng viên trên 8 trang; tài liệu hướng dẫn thực tập không có ứng viên. Ứng viên lớn nhất trong phần đã khảo sát là 36 hàng × 4 cột. Đây vẫn là kết quả heuristic của `find_tables()`, chưa xác nhận bằng mắt hay chứng minh mọi ô được trích đúng. Metadata nằm ở `artifacts/results/g1_table_audit.json` và file này bị Git ignore.

## 2. Pipeline hiện tại đang làm gì

- `extract_pdf_pages()` dùng `page.get_text("text")` để đọc lớp chữ PDF. Hàm chỉ gắn cờ `is_probable_scan`; hiện chưa gọi OCR, chưa bóc tách bảng thành hàng/cột và chưa nhận diện nội dung hình.
- `PageText` giữ `document_id`, trang PDF, text, `char_count`, cờ scan và số trang in nếu nhận diện được. Chưa có trường cho phương thức trích xuất, confidence OCR hoặc tọa độ block.
- `chunk_document()` dùng whitespace token, mặc định 500 token và overlap 80. Tài liệu nhận diện được cấu trúc Điều thì ưu tiên ranh giới Điều; tài liệu không nhận diện được cấu trúc dùng cửa sổ trượt trên luồng trang. Trang đầu/cuối mỗi chunk được lưu, nhưng hàng bảng chưa được bảo vệ khỏi việc bị tách giữa các chunk.
- Bản sao pipeline thử nghiệm Giai đoạn 0 nằm trong vùng Git ignore; snapshot và baseline đợt 1 không bị ghi đè.

## 3. Cách xử lý đề xuất

1. **Ưu tiên lớp chữ PDF.** Giữ PyMuPDF native extraction cho trang có chữ có thể chọn được. Việc có ảnh trên trang không tự động kích hoạt OCR, vì trang Sổ tay có ảnh lớn nhưng phần lớn vẫn có lớp chữ.
2. **OCR có điều kiện, chạy hoàn toàn local.** Chỉ OCR trang có tín hiệu thiếu chữ sau bước native extraction. Lưu song song nguồn trích xuất (`native`/`ocr`), trang PDF, ngôn ngữ, phiên bản engine và confidence nếu lấy được; không âm thầm thay thế text native. OCR chỉ giúp lấy chữ từ ảnh, không bảo đảm hiểu bố cục hay quan hệ giữa các cột.
3. **Bảng thành dữ liệu có cấu trúc.** Dùng `Page.find_tables()` để tạo ứng viên, kiểm tra số hàng/cột và đối chiếu thủ công trên các trang phù hợp. Khi đưa vào retrieval, giữ tiêu đề bảng, header cột, nhóm hàng cùng đơn vị; nếu phải chia bảng dài thì lặp header và lưu `table_id`, trang nguồn, chỉ số hàng. Bảng không viền hoặc chỉ phân tách bằng màu nền có thể bị bỏ sót; không xem kết quả detector là ground truth.
4. **Hình ảnh và sơ đồ.** Lưu metadata vị trí/loại ảnh và trang nguồn. Với hình có chữ, thử OCR cục bộ; với hình chỉ mang thông tin thị giác, ghi nhận là chưa diễn giải được cho retrieval cho tới khi có caption được kiểm chứng. Không gửi Sổ tay hoặc nội dung phát sinh từ nó tới Gemini/LLM cloud.
5. **Giữ tương thích với baseline.** Mọi trường schema mới nên là optional hoặc có `schema_version`; giữ nguyên cách tạo snapshot/baseline cũ để so sánh trên snapshot mới riêng. Kết quả OCR/table được lưu trong `data/processed/` (đang Git ignore), không commit PDF hay toàn văn.

## 4. Kế hoạch kiểm chứng trong Giai đoạn 1

- Tạo bảng audit theo trang: ký tự native, ảnh phủ trang, trạng thái OCR, số bảng/shape và số trang chưa có nguồn trích xuất usable. Chỉ xuất metadata, không xuất nội dung nhạy cảm.
- Đã chạy thử OCR cục bộ trên cả 26 trang nghi scan của Sổ tay Sinh viên, ở 200 DPI, ngôn ngữ `vie`, page segmentation mode 6. Các trang có trung vị 3 ký tự native; OCR nhận tổng cộng 3.650 từ, median của confidence trung bình theo từng trang là 86,06/100. Đây là chỉ số confidence do engine ước lượng, **không phải** accuracy/CER/WER và chưa chứng minh từng từ được nhận dạng đúng.
- Các trang có confidence trung bình thấp nhất trong lượt khảo sát là trang 1 (61,55), 136 (73,66), 149 (75,80), 137 (77,44) và 109 (79,08). Đây là danh sách ưu tiên rà soát, không phải ngưỡng loại trang. Trước khi đưa OCR text vào corpus cần chọn trang không chứa PII để tạo ground truth ngắn, đối chiếu thủ công và ghi nhận lỗi chữ, dấu tiếng Việt, số hiệu cùng bố cục.
- Audit `find_tables()` đã thu được số trang và shape hàng/cột nhưng chưa kiểm tra trực quan. Bước đánh giá tiếp theo là chọn một vài bảng không nhạy cảm, so số hàng/cột và header theo PDF gốc, rồi thử cách giữ header/nhóm hàng khi chunking. Không dùng các trang danh bạ làm mẫu benchmark.
- Sau khi pipeline thay đổi, tạo snapshot mới và chạy lại cùng bộ câu hỏi pilot; báo rõ thay đổi đến từ extraction/chunking, không so trực tiếp các snapshot khác nhau như thể cùng dữ liệu.

## 5. Cấu hình OCR đã cài và phạm vi kết quả

OCR local là cần thiết để khảo sát các trang thiếu lớp chữ theo YC4. Cấu hình hiện tại:

- Cài `tesseract=5.5.3` và `pytesseract=0.3.13` bằng Conda-forge trong env `rag-hcmute`. Dry-run dự kiến 34 package link, 2 package thay phiên bản và 217.060.448 byte tải xuống; transaction không thay Python 3.11 hoặc Torch/CUDA. Cài đặt đã hoàn tất và project vẫn qua test suite.
- Tesseract không đi kèm bộ ngôn ngữ trong transaction; model `vie` được tải riêng từ [`tesseract-ocr/tessdata_best`](https://github.com/tesseract-ocr/tessdata_best/blob/main/vie.traineddata), bộ model ưu tiên độ chính xác hơn tốc độ và phát hành theo Apache-2.0 ([README/license](https://github.com/tesseract-ocr/tessdata_best)). File 12.435.550 byte nằm ngoài repo tại `D:\RAG\models\tesseract\tessdata\vie.traineddata`, SHA-256 `b6b49293d95d0b6dbd8780174627e82c75be957b6f4ed9862155540d6b00bb45`.
- Phiên bản kiểm tra: Tesseract 5.5.3, pytesseract 0.3.13, PyMuPDF 1.28.2. OCR dùng trực tiếp trên máy, không gọi API và không gửi văn bản corpus ra ngoài.
- Kết quả chỉ được ghi dưới dạng metadata trong `artifacts/results/g1_ocr_survey.json` (đã bị Git ignore); file không chứa OCR text. Thử nghiệm xác nhận engine có thể đọc các trang scan, nhưng chưa thay đổi `extract_pdf_pages()`, chưa tạo snapshot mới và chưa dùng OCR text để truy xuất.

**Giới hạn cần giữ rõ:** confidence 86,06 không được trình bày thành “OCR chính xác 86,06%”. Trước khi tích hợp, cần xác lập ground truth trên một trang phù hợp, rà soát các trang confidence thấp, kiểm tra cách giữ số trang và nguồn trích dẫn, sau đó mới so sánh chunk/retrieval trên snapshot riêng. Các trang có ảnh nhưng đã có text native không nên OCR tự động nếu việc đó làm lặp nội dung.

### Tài liệu kỹ thuật đã đối chiếu

- [PyMuPDF — table extraction và giới hạn của find_tables](https://pymupdf.readthedocs.io/en/latest/faq/index.html)
- [Tesseract — bản phát hành upstream](https://github.com/tesseract-ocr/tesseract/releases)
- [Conda-forge — Tesseract 5.5.3, Windows-64, giấy phép Apache-2.0](https://anaconda.org/conda-forge/tesseract)
- [pytesseract — cài wrapper và cấu hình đường dẫn executable](https://github.com/madmaze/pytesseract)
- [Tesseract — so sánh tessdata, tessdata_fast và tessdata_best](https://github.com/tesseract-ocr/tessdoc/blob/main/Data-Files.md)
- [tessdata_best — Vietnamese traineddata và giấy phép Apache-2.0](https://github.com/tesseract-ocr/tessdata_best)
- [ADR-002 — nguồn dữ liệu, tái phân phối và PII](decisions/ADR-002-corpus-sourcing-and-redistribution.md)

**Checkpoint hiện tại:** Hoàn tất audit metadata cho ba PDF, OCR cục bộ trên 26 trang nghi scan và audit shape bảng (không lưu cell text). Chưa tích hợp OCR vào ingestion code, chưa OCR bảng/hình riêng, chưa tạo snapshot mới, chưa thay baseline, chưa commit/push. Bước kỹ thuật kế tiếp là kiểm tra thủ công một trang scan và một bảng không nhạy cảm để chốt quy tắc OCR có điều kiện, provenance/confidence và cách giữ cấu trúc bảng trước khi sửa pipeline.
