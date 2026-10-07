# Rà soát nhãn bố cục OCR cho PDF page 107 — 07/10/2026

## Mục đích và giới hạn riêng tư

Hai ghi chú OCR trước đây gán loại bố cục khác nhau cho PDF page 107 của Sổ tay Sinh viên 2024: một ghi là trang scan chữ, ghi còn lại gọi là infographic. Để xử lý bất nhất, trang được kiểm tra cục bộ bằng trích xuất cấu trúc PDF và thống kê hộp OCR. Nội dung OCR, ảnh trang, tọa độ chi tiết và bản chép tham chiếu không được đưa vào tài liệu này hay hội thoại.

PDF cục bộ có SHA-256 `99940caca9799b5de43b9e6386304261a80f42b11fbd76acc13904786d738e47`, khớp manifest. Thống kê OCR được tạo với Tesseract 5.5.3, model tiếng Việt, DPI 200. Không thay đổi file PDF hay pipeline.

## Tín hiệu bố cục được ghi nhận

Các số dưới đây là số đơn vị OCR được phân đoạn ở PSM 4, không phải số từ chính xác và không đánh giá nội dung đúng/sai.

| PDF page | OCR units | OCR lines | OCR blocks | Trung vị units/line |
|---:|---:|---:|---:|---:|
| 107 | 86 | 15 | 8 | 5 |
| 109 | 160 | 25 | 8 | 6 |
| 116 | 325 | 38 | 17 | 8,5 |
| 136 | 79 | 13 | 7 | 5 |

Page 107 có mật độ và số khối OCR gần page 136 hơn so với hai trang chữ nhiều hơn trong mẫu. Tín hiệu này phù hợp với mô tả “infographic/nội dung thị giác hỗn hợp” ở ghi chú OCR cập nhật sau; nó không đủ để khẳng định page 107 chỉ chứa đồ họa hoặc không có đoạn chữ dạng văn bản.

## Kết luận dùng trong tài liệu

- Nhãn làm việc cho page 107: **infographic hoặc trang có nội dung thị giác hỗn hợp, có chữ OCR đọc được**.
- Độ tin cậy: **vừa phải**. Đây là phân loại suy ra từ đặc trưng bố cục OCR và đối chiếu nhất quán giữa các ghi chú, không phải xác nhận trực quan của con người.
- Mô tả cũ “hai trang scan văn bản (107, 109)” trong báo cáo sweep ban đầu được thay bằng: **page 109 là trang chữ có minh họa; page 107 là infographic/nội dung thị giác hỗn hợp; page 136 là sơ đồ**.
- Các CER/WER đã tính không bị thay đổi. Tuy nhiên, không dùng page 107 làm mẫu “scan chữ thuần” và không diễn giải lại kết quả gộp thành phép so sánh thuần giữa các loại layout.

Nếu cần nhãn vàng có độ tin cậy cao hơn cho báo cáo chính thức, người học vẫn nên xác nhận trang bằng mắt trên máy cá nhân; không cần gửi ảnh hoặc nội dung trang ra ngoài máy.
