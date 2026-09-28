# ADR-003: OCR fallback có điều kiện cho PDF scan

- **Trạng thái:** Chấp nhận cho PoC; cần hiệu chỉnh sau khi có ground truth.
- **Ngày:** 2026-09-28.
- **Phạm vi:** YC4 — nhận diện và xử lý trang PDF không có lớp chữ usable.

## Bối cảnh

Corpus HCMUTE có cả PDF có text layer, trang chứa ảnh minh họa và trang scan. Audit ban đầu tìm thấy 26 trang trong Sổ tay Sinh viên có ảnh phủ gần toàn trang nhưng native text dưới 15 ký tự. OCR toàn bộ trang có text layer có nguy cơ tạo nội dung lặp; chỉ giữ native extraction lại bỏ sót các trang scan.

## Các phương án đã cân nhắc

1. **Chỉ native extraction:** đơn giản, ổn định cho PDF có text layer nhưng không lấy được nội dung ở trang scan.
2. **OCR mọi trang:** bao phủ cả ảnh, nhưng tốn thời gian và dễ lặp nội dung ở trang vốn đã có text; OCR cũng không hiểu tự động quan hệ giữa bảng/cột.
3. **OCR fallback theo tín hiệu thiếu text:** xử lý native trước, chỉ gọi OCR nếu trang có ít native text và có raster image; giữ native-only làm mặc định.

## Quyết định

PoC sử dụng phương án 3. `scripts/build_corpus.py` chỉ bật OCR khi truyền `--ocr`. Với mỗi trang, fallback chạy khi native text có ít hơn ngưỡng cấu hình (mặc định 15 ký tự) và trang có ảnh raster. Nếu OCR tạo được text, nội dung được chọn cho downstream; nếu OCR không trả text, giữ native result. Trang đủ text không bị OCR chỉ vì có ảnh.

OCR chạy local bằng Tesseract 5.5.3 và model tiếng Việt `vie.traineddata`; tham số khảo sát hiện tại là 200 DPI, PSM 6. Snapshot ghi lại engine/version, language, DPI, PSM, ngưỡng và SHA-256 của model. `PageText` và `Chunk` lưu phương thức trích xuất cùng mean OCR word confidence để kết quả có thể truy vết. Nguồn chuẩn để xác nhận vẫn là PDF gốc và số trang PDF.

## Hệ quả và giới hạn

- Baseline native-only không đổi; snapshot OCR được tạo riêng với config/fingerprint khác.
- Trên 26 trang nghi scan, native text có median 3 ký tự; OCR nhận 3.650 từ, median confidence trung bình theo trang 86,06/100. Confidence không phải accuracy; chưa có ground truth/CER/WER.
- Cả 26 trang OCR truy vết được PDF page, nhưng không trang nào nhận diện được printed page. Citation của các trang này phải ghi số trang PDF.
- Các trang có text native và hình minh họa không được OCR tự động; chữ trong hình nhỏ hoặc nội dung chỉ mang tính thị giác có thể chưa được index.
- OCR không thay thế table/layout extraction. Bảng phân cấp phải được chuyển đổi riêng, giữ title/header/group/row và provenance.
- PDF nguồn, OCR text và kết quả retrieval đầy đủ chỉ lưu cục bộ trong vùng bị Git ignore; không gửi văn bản corpus tới cloud model.

## Điều kiện xem xét lại

Sau khi có ground truth thủ công trên trang không nhạy cảm, đo lỗi nhận dạng và rà soát confidence thấp. Nếu ngưỡng 15 ký tự bỏ sót trang có text layer hỏng một phần, cân nhắc heuristic bổ sung theo tỷ lệ text/raster. Chỉ thay threshold hoặc OCR model sau khi chạy ablation trên snapshot riêng và giữ nguyên baseline.
