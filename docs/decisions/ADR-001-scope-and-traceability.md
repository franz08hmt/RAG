# ADR-001: Giới hạn miền dữ liệu và yêu cầu truy ngược nguồn

## Trạng thái

Đã chấp nhận cho baseline đầu tiên.

## Bối cảnh

Đề tài cần chứng minh chất lượng của RAG trên một miền dữ liệu có thể kiểm tra bằng văn bản gốc. Tài liệu học vụ HCMUTE phù hợp vì câu trả lời có thể được đối chiếu theo tên văn bản, số trang và điều khoản.

## Quyết định

- Chỉ sử dụng tài liệu học vụ được công bố từ nguồn chính thức và đã ghi nhận phiên bản trong corpus manifest.
- Không đưa dữ liệu cá nhân, dữ liệu nghiệp vụ nội bộ hoặc thông tin thay đổi liên tục vào baseline.
- Mỗi chunk phải mang `document_id`, `document_title`, `page_number`, cấu trúc điều khoản nếu trích xuất được và `chunk_id` ổn định.
- Hệ thống phải có trạng thái từ chối khi không đủ bằng chứng.

## Hệ quả

Chất lượng demo không chỉ được đánh giá bằng độ trôi chảy của câu trả lời. Corpus, metadata, retrieval log và trích dẫn trở thành các đầu ra bắt buộc của quá trình thực nghiệm.

