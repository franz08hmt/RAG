# Mốc 2 — khảo sát đầu vào theo vùng nguồn

`ingestion/page_artifacts.py` và `scripts/audit_m2_input_artifacts.py` bổ sung metadata
trang có chữ, ảnh raster và bảng ứng viên. Lưu SHA-256 nguồn, số trang PDF, kích thước trang,
bbox, số ký tự, hash block, xref ảnh, tỷ lệ ảnh phủ trang, số ô và ô null của bảng.
Không lưu toàn văn hoặc tự mô tả ý nghĩa ảnh trong JSON dùng cho Git.

Audit đã chạy trên 182 trang G0 và 32 trang QĐ3116 riêng; mọi source hash được kiểm trước
khi chạy. JSON đầy đủ nằm cục bộ tại `artifacts/results/m2_input/input_artifacts_metrics.json`.
Bản tóm tắt an toàn để theo dõi bằng Git: `m2/runs/input_artifacts_summary.json`.

## Những gì phép thử chứng minh

- Có thể mở lại vùng nguồn bằng PDF page + bbox; ảnh chồng được tính diện tích hợp.
- Trang chứa ảnh nền lớn và text layer được gắn nhãn cần xem lại, không mặc nhiên OCR lại.
- Bảng ứng viên được giữ tọa độ, số hàng/cột và cấu trúc ô trống/ô gộp để kiểm tra.
- Trang xoay không được xử lý bằng tọa độ sai: API báo lỗi yêu cầu biến đổi tọa độ.

## Những gì chưa được chứng minh

Chưa có gold bbox để tính precision/recall bộ dò bảng; số ứng viên không phải số bảng đúng.
OCR confidence không là độ chính xác; không phát hiện bảng trên scan không có nghĩa không có
bảng. Chưa chạy VLM, chưa đánh giá quan hệ mũi tên hoặc ngữ nghĩa ảnh.

Ảnh trang 20 QĐ1727 và các trang 107/109/116/136 Sổ tay, trang 3 QĐ3116 được mở xem trực quan.
Báo cáo chỉ dùng crop bảng ở QĐ1727 trang20 và sơ đồ Sổ tay trang136, render thẳng từ PDF ở
thang xám; không thêm chữ giả lên ảnh. Không thấy email/SĐT cá nhân trên hai vùng dùng.
Các ảnh khác không đưa vào báo cáo. QĐ3116 vẫn nằm ngoài G0 và ngoài repository.
