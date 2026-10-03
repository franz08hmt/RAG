# Câu hỏi nháp cho phép thử truy xuất bảng

## Vì sao chọn bảng này

Phép thử đầu tiên dùng Bảng 5, “Xếp hạng năm đào tạo sinh viên”, ở PDF page 20 của Quy chế 1727. Bảng đã được kiểm tra trực quan trong lượt trước; sidecar T1 giữ toàn bảng dạng Markdown, còn T2 biểu diễn năm hàng dữ liệu thành năm chunk có tên cột và ngữ cảnh bảng. Đây là bảng nhỏ, hai cột, không có ô gộp phức tạp. Vì vậy phép thử phù hợp để kiểm tra truy xuất theo hàng/ngưỡng, nhưng không đại diện cho mọi loại bảng trong corpus.

## Câu hỏi ứng viên

Năm câu trong `data/question_sets/table_question_candidates_for_student_review.csv` là gợi ý để người học đọc trang nguồn, tự viết lại hoặc xác nhận. Chúng được thiết kế để kiểm tra truy vấn khoảng giá trị, ngưỡng và đối chiếu hai hàng. `row_location_candidate` chỉ là vị trí cần xem lại, chưa phải gold label.

Sau khi đối chiếu trực quan PDF gốc có SHA-256 khớp manifest, một phiếu đáp án và cách diễn đạt đề xuất được chuẩn bị tại [`data/question_sets/table_question_review_proposals_20261003.csv`](../../data/question_sets/table_question_review_proposals_20261003.csv). Đây vẫn là đề xuất chờ người học xác nhận; không dùng làm gold hoặc benchmark. TB002 được đổi thành câu hỏi về cả khoảng để tránh hiểu nhầm chỉ hỏi cận dưới; TB005 yêu cầu trả lời hai hàng liền kề.

Để chuẩn bị cho ablation mà không gắn nhãn quá sớm, ánh xạ chunk ứng viên B0/T1/T2 được lưu riêng tại `data/question_sets/table_candidate_chunk_mapping.csv`. Trên snapshot G0, nội dung Bảng 5 nằm trong B0 chunk `HCMUTE_QCDT_1727_2021__c0031`; T1 có một chunk toàn bảng; T2 có một chunk cho mỗi hàng. Các ánh xạ vẫn mang trạng thái `draft_candidate_mapping` và cần người học xác nhận cùng câu hỏi trước khi được xem là gold.

Các câu hiện đều ở trạng thái `draft_not_in_pilot`: chưa ghi đáp án, chưa gắn chunk ID cho B0/T1/T2, chưa chạy benchmark và không được gộp vào bộ câu hỏi chính. Cần giữ cả trường hợp cận khoảng (ví dụ ngưỡng phân nhóm) đúng như bảng thể hiện, tránh tự diễn giải khi dấu `<`, `>` hoặc khoảng giá trị chưa được xác nhận trực tiếp.

## Phép thử dự kiến sau khi người học duyệt

Sau khi câu hỏi và vị trí hàng/cột được xác minh, chạy cùng BM25 trước trên ba cách biểu diễn:

- B0: baseline không thêm table chunk;
- T1: một chunk Markdown chứa toàn bảng;
- T2: mỗi hàng có ngữ cảnh riêng.

Giữ nguyên corpus còn lại, tokenizer, `top_k` và pipeline BM25; chỉ thay cách biểu diễn bảng. So sánh Hit@5/MRR@10 trên số câu đã được xác nhận và kiểm tra thủ công các kết quả. Nếu số câu hợp lệ còn ít, trình bày đây là smoke/ablation pilot, không kết luận T1 hay T2 tốt hơn tổng quát và không tích hợp vào snapshot mặc định.

Phép thử này chỉ khảo sát truy xuất giá trị từ một bảng native-text đơn giản. Nó không thay thế đánh giá OCR, hình ảnh, bảng phân cấp nhiều tầng hoặc bảng không có đường kẻ; các nội dung đó cần bộ kiểm tra riêng.
