# Minh chứng dành cho báo cáo

Thư mục này lưu các kết quả đã được chọn để đối chiếu khi viết report. Không chỉnh sửa trực tiếp kết quả thô trong `artifacts/`.

Mỗi vòng thực nghiệm cần giữ lại:

- phiên bản corpus manifest và mã băm của các PDF;
- cấu hình chunking, embedding, retrieval và generation;
- lệnh chạy hoặc script tạo kết quả;
- log theo từng câu hỏi;
- bảng metric được tính từ kết quả thô;
- một số trường hợp đúng, sai và từ chối để phân tích nguyên nhân.

Các lượt thử OCR hiện có:

- `OCR_PSM_SWEEP_20260928.md`: sweep ban đầu trên ba trang (107, 109, 136).
- `OCR_PSM_PAGE116_20260928.md`: mở rộng thêm page 116 và tính lại số gộp trên cùng bốn trang. Reference đầy đủ vẫn lưu cục bộ trong thư mục Git-ignored `artifacts/results/`.
- `CHUNK_SIZE_ABLATION_20260929.md`: so sánh kích thước chunk trên snapshot G0 với nhãn vị trí section/page; có lưu ý proxy labels và truncation của Dense BGE-M3.

