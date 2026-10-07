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
- `CHUNK_STRATEGY_ABLATION_20261007.md`: so sánh policy chunk theo Điều với cửa sổ cố định 500/80 bằng BM25 và BGE-M3 trên cùng G0; tính span bị cắt qua ranh giới là miss và tách metric exact evidence khỏi page-location proxy.
- `QUESTION_CANDIDATE_EXPANSION_20260929.md`: 12 câu hỏi ứng viên để người học tự đối chiếu và duyệt; không thuộc pilot và chưa được dùng tính metric.
- `QUESTION_CANDIDATE_REVIEW_20260929.md`: rà soát mức độ khớp nguồn, tham chiếu trang, độ trùng và khoảng trống về bảng/scan/hình; không thay đổi ứng viên hay pilot.
- `TABLE_QUESTION_CANDIDATES_20260929.md`: 5 gợi ý câu hỏi cho ablation B0/T1/T2 trên một bảng đã kiểm tra; chỉ bản nháp, chưa dùng benchmark.
- `table_candidate_chunk_mapping.csv`: ánh xạ chunk B0/T1/T2 ở mức ứng viên cho 5 câu hỏi bảng; chưa phải gold label và chưa được dùng tính metric.
- [`data/question_sets/table_question_review_proposals_20261003.csv`](../../data/question_sets/table_question_review_proposals_20261003.csv): đáp án/bằng chứng và cách diễn đạt đề xuất cho TB001–TB005 sau khi đối chiếu trực quan Bảng 5; cần người học duyệt, chưa phải gold.
- `TABLE_RETRIEVAL_SMOKE_20261003.md`: ghi nhận lượt thăm dò BM25 ngày 03/10 và diễn biến Dense được khôi phục sau đó.
- `TABLE_RETRIEVAL_SMOKE_20261005.md`: kết quả thăm dò BM25/Dense top-5 cho câu hỏi nháp trên B0/T1/T2; không phải benchmark và không chứa metric tổng hợp.
- `TABLE_RETRIEVAL_MATCHED_CONTEXT_SMOKE_20261005.md`: lượt thăm dò có cùng corpus nền, chỉ thay cách biểu diễn Bảng 5; đây là kết quả phù hợp hơn để đọc thứ hạng, nhưng vẫn chưa phải benchmark vì câu hỏi/nhãn đang ở trạng thái nháp.
- `TABLE_RETRIEVAL_APPROVED_ABLATION_20261005.md`: kết quả retrieval-only trên năm câu hỏi bảng đã duyệt cho ablation riêng; có metric đủ-evidence, coverage và MRR evidence đầu tiên, nhưng không phải benchmark toàn hệ thống.
- `BM25_QUERY_SENSITIVITY_DIAGNOSTIC_20261005.md`: chẩn đoán thứ hạng BM25 với các biến thể cách hỏi và tên cột cho cùng năm câu; các truy vấn biến thể chỉ dùng phân tích, không thay câu hỏi/gold đã duyệt và không phải benchmark chính.
- `INPUT_DOCUMENT_CLASS_AUDIT_20261007.md`: kiểm kê ba lớp tài liệu, page/chunk/raster metadata, cách xử lý scan/bảng/hình hiện tại và các giới hạn của snapshot G0; báo cáo chỉ chứa metadata/tổng hợp, không chứa text nguồn.
- `INPUT_CLASS_PROCESSING_MATRIX_20261007.md`: ánh xạ từng dạng nội dung sang cách xử lý đang có, minh chứng, giới hạn và phép thử kế tiếp; phân biệt kết quả đo được với đề xuất.
- `OCR_LAYOUT_LABEL_RECHECK_20261007.md`: rà soát metadata bố cục của page 107 bằng số liệu OCR không chứa nội dung; nhãn làm việc được sửa thành infographic/nội dung thị giác hỗn hợp với độ tin cậy vừa phải.
- `INPUT_CLASS_SAMPLE_PLAN_20261007.md`: danh sách trang mẫu đề xuất theo input class/layout, căn cứ chọn, trạng thái nhãn, tiêu chí dùng và các kiểm tra quyền riêng tư cần thiết.
- `OCR_DPI_SENSITIVITY_20261007.md`: so sánh OCR tại 200/300 DPI với PSM 4/6/11 trên bốn trang có reference, gồm CER/WER và phép đo token số/cue điều kiện chỉ lưu số liệu tổng hợp; kèm script tái lập.

