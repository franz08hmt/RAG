# Kiểm tra bàn giao Mốc 2 ngày 25/10/2026

Commit gói thực nghiệm và báo cáo: `df73d34`. Chỉ lưu cục bộ, chưa push/merge/tạo PR.

## Kiểm thử và số liệu

- Toàn bộ suite: **138 passed**, 1,63 s. JUnit cục bộ:
  `artifacts/results/m2_validation_20261025.xml` (không đưa XML vào repo vì không cần
  công bố thông tin máy). Không có test lỗi hoặc skip.
- `compileall` cho src và scripts: đạt. `git diff --cached --check`: đạt sau khi chuẩn
  hóa các JSON xuất bản thành UTF-8/LF và tính lại manifest. Nội dung kết quả không đổi.
- `scripts/verify_m2_delivery.py`: 6 evidence JSON đúng SHA-256, 20 case duy nhất,
  không có khóa chứa question/answer/text/sources trong bản JSON xuất bản, không holdout.
- Kiểm tra 44 file staged: không phát hiện mẫu khóa API/private key; không có data/raw,
  data/processed, .env, trọng số hoặc log chứa full context được đưa vào commit.
- SHA-256 của Mốc 1 v6 vẫn là
  `8e06f4bf57dc4dcabc810b296ce5438bc04bb435ea21f1d073aaaa8f0b39654b`.

## Báo cáo và kiểm tra hình thức

File sử dụng: `reports/22110068_RAG_Bao_Cao_Tien_Do_Moc_2_v3.docx`.
SHA-256: `882e62679efb02718cc61690e654c6d5772251deb269896253732b8fd22183f0`.

Renderer đóng gói không có LibreOffice khả dụng trên máy. Dùng Word xuất PDF từ bản
sao QA mở read-only, sau đó PyMuPDF tạo ảnh của từng trang. Đã xem đủ **15 trang** của
bản v3 ở `artifacts/results/m2_report/qa_v3/pages`; không dùng ảnh của v1/v2 để chốt v3.

Các lỗi tìm ở bản đầu đã sửa: bảng nhỏ bị chia trang, chú thích tách bảng, ảnh cắt mất
nhãn bên phải, phần trên ảnh bảng còn mảnh của bảng khác, tên class chưa khớp code.
Ở bản v3, các bảng không vượt lề; chữ và bảng đen trên nền trắng; cỡ chữ trực tiếp chỉ
12/13/14; có Heading thật; không trường PAGE/NUMPAGES. Bìa và logo giữ theo bản v6,
không thêm khung cho thân bài. Ảnh nguồn là vùng trích PDF có chú thích, không giả thành
ảnh chụp terminal hoặc bằng chứng đã hiểu hình.

## Giới hạn của biên bản

QA layout và unit test không xác nhận độ đúng học vụ hoặc chất lượng tổng quát của RAG.
Chưa có nhãn chấm người mới, chưa có holdout, và refusal còn lỗi đã ghi trong Mục10
của báo cáo. Duyệt nội dung trước nộp vẫn là trách nhiệm của người học. Bản v1/v2 QA
được giữ tại máy nhưng không chọn làm bản nộp; các file untracked cũ không bị sửa/xóa.
