# Ngân hàng câu hỏi nháp để mở rộng pilot

## Mục đích

Tạo thêm câu hỏi ứng viên dựa trên corpus HCMUTE hiện có, nhằm giúp người học rà soát độ phủ theo loại tài liệu, chủ đề và kiểu truy vấn. Đây là tài liệu làm việc; các câu hỏi trong `data/question_sets/question_candidates_for_student_review.csv` **chưa được duyệt, chưa có nhãn answerability/gold evidence và không thuộc pilot đang chạy**.

Pilot chính thức hiện giữ nguyên `pilot_questions.csv` cùng annotation exact-span version 2. Không chạy metric trên các ứng viên và không sửa tập pilot khi chưa đối chiếu, chỉnh câu hỏi và xác nhận từng nhãn.

## Phạm vi ứng viên

- 10 câu lấy từ các điều khoản khác nhau của Quyết định 1727/QĐ-ĐHSPKT, bao gồm định nghĩa/chỉ số, điều kiện, giới hạn định lượng và xử lý vi phạm.
- 1 câu lấy từ hướng dẫn học phần thực tập tốt nghiệp của Khoa Công nghệ Thông tin.
- 1 câu lấy từ mục học bổng trong Sổ tay Sinh viên 2024. Đây là tài liệu tổng hợp/trích dẫn thứ cấp, không được mặc định là căn cứ hiện hành; cần kiểm tra văn bản gốc và trạng thái áp dụng trước khi dùng làm câu hỏi chính thức.

Các số trang ghi trong CSV là số trang PDF để tra cứu nhanh. Khi xác nhận nhãn, cần đọc cả trang liền kề nếu điều khoản hoặc câu trả lời tiếp tục qua trang.

## Quy trình duyệt đề xuất

1. Mở nguồn PDF theo `source_document_id` và `source_reference`; xác nhận chủ đề, phạm vi câu hỏi và số trang thực tế.
2. Người học tự viết lại hoặc chấp nhận câu hỏi sau khi đã hiểu nội dung. Xác nhận câu hỏi được trả lời từ đúng phiên bản tài liệu được chỉ định, không phải từ trí nhớ hoặc một nguồn web khác.
3. Chỉ sau bước 2 mới gán `answerable`/`unanswerable`, tài liệu đích và exact evidence span. Với câu hỏi có nhiều điều kiện, ghi đủ các span cần thiết; không coi cùng trang hoặc cùng Điều là bằng chứng đầy đủ nếu đoạn cần thiết không nằm trong chunk.
4. Kiểm tra trùng lặp ngữ nghĩa với P001-P010. Câu trùng chủ đề chỉ được giữ nếu kiểm tra một kỹ năng retrieval khác và có lý do rõ ràng.
5. Tách câu phát triển khỏi câu test cuối. Không dùng câu test để lựa chọn chunk size, ngưỡng từ chối hoặc prompt; giữ lại câu test sau khi đã chốt cấu hình.
6. Cập nhật pilot bằng một thay đổi riêng có kiểm tra hash/annotation; sau đó mới chạy lại evaluation và lưu cấu hình, log metadata-only, kết quả từng câu và phân tích lỗi.

## Quy tắc dùng trong báo cáo

- Không trình bày các ứng viên này như kết quả benchmark hoặc như câu hỏi đã được người học kiểm chứng.
- Khi đối chiếu nội dung quy chế 1727, nêu rõ đúng tên, số hiệu và phiên bản tài liệu trong corpus; chưa khẳng định văn bản còn hiệu lực nếu trạng thái thay thế chưa được xác nhận.
- Với Sổ tay Sinh viên 2024, thể hiện rõ đây là nguồn thứ cấp. Nếu mục tiêu là trả lời chính sách đang áp dụng, cần tìm và xác minh văn bản gốc mới nhất trước khi đưa vào corpus đánh giá.
- Chưa phát sinh câu unanswerable mới. Những câu này cần được kiểm tra trên toàn corpus và truy xuất thử trước khi được gán nhãn từ chối.

## Trạng thái

Ngày lập: 2026-09-29. Số ứng viên: 12. Đã được sinh viên duyệt: 0. Được phép dùng trong evaluation: 0.
