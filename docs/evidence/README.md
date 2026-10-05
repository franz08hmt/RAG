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
- `CHUNK_SIZE_EXACT_EVIDENCE_20260929.md`: đánh giá chunk size theo exact evidence span; annotation version 2 đã phủ đủ 7 câu answerable/10 span và hash-verified theo snapshot G0.
- `QUESTION_CANDIDATE_EXPANSION_20260929.md`: 12 câu hỏi ứng viên để người học tự đối chiếu và duyệt; không thuộc pilot và chưa được dùng tính metric.
- `QUESTION_CANDIDATE_REVIEW_20260929.md`: rà soát mức độ khớp nguồn, tham chiếu trang, độ trùng và khoảng trống về bảng/scan/hình; không thay đổi ứng viên hay pilot.
- `TABLE_QUESTION_CANDIDATES_20260929.md`: 5 gợi ý câu hỏi cho ablation B0/T1/T2 trên một bảng đã kiểm tra; chỉ bản nháp, chưa dùng benchmark.
- `table_candidate_chunk_mapping.csv`: ánh xạ chunk B0/T1/T2 ở mức ứng viên cho 5 câu hỏi bảng; chưa phải gold label và chưa được dùng tính metric.
- [`data/question_sets/table_question_review_proposals_20261003.csv`](../../data/question_sets/table_question_review_proposals_20261003.csv): đáp án/bằng chứng và cách diễn đạt đề xuất cho TB001–TB005 sau khi đối chiếu trực quan Bảng 5; cần người học duyệt, chưa phải gold.
- `TABLE_RETRIEVAL_SMOKE_20261003.md`: ghi nhận lượt thăm dò BM25 ngày 03/10 và diễn biến Dense được khôi phục sau đó.
- `TABLE_RETRIEVAL_SMOKE_20261005.md`: kết quả thăm dò BM25/Dense top-5 cho câu hỏi nháp trên B0/T1/T2; không phải benchmark và không chứa metric tổng hợp.

