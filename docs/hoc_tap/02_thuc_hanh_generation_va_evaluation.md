# Thực hành 2 — đọc generation và đánh giá có trách nhiệm

## Mục tiêu

Nhận ra ba loại kết quả khác nhau: câu trả lời, citation có ID hợp lệ và citation thực sự hỗ trợ phát biểu. Thực hành này không biến output thành lời khuyên học vụ; corpus G0 chỉ là snapshot lịch sử.

## Chạy local

Trước khi chạy, xác nhận Ollama đang hoạt động và model `qwen3:4b` đã có sẵn. Không dùng Gemini/API cloud. Dùng ví dụ generation trong `README.md` với đường dẫn BGE-M3/reranker local. Lệnh chỉ là smoke test, không phải benchmark độc lập.

## Đọc pilot đã lưu

Mở `docs/evidence/GENERATION_PILOT_20261008.md` và trả lời:

- 7/7 answerable có output có chứng minh output đúng không? Không; chưa chấm answer correctness.
- 9/9 citation ID hợp lệ có chứng minh citation hỗ trợ từng câu không? Không; chỉ kiểm tra ID thuộc context.
- 1/3 unanswerable bị ghi nhận non-answer có chứng minh refusal policy đạt không? Không; hai câu thiếu căn cứ vẫn được trả lời và một lượt abstain liên quan output JSON không hợp lệ.
- Vì sao không đặt threshold từ điểm reranker? Các điểm hai nhóm chồng lấn và mẫu chỉ có 10 câu; chọn ngưỡng trên dev rồi báo nó như khả năng tổng quát sẽ gây ảo tưởng chắc chắn.

## Thiết kế evaluation tiếp theo

Khi tạo câu hỏi mới, người học cần xác minh câu hỏi, answerability, gold answer, đoạn nguồn nhỏ nhất, trang, section và document hash. Chia dev/test theo chủ đề/tài liệu và các paraphrase trước khi tune; đóng băng test. Đánh giá retrieval và generation riêng; với generation, lấy mẫu để người đọc kiểm lại mỗi claim/citation. Có thể dùng RAGAS hoặc ARES như chỉ báo bổ sung nhưng phải nêu model judge, chi phí, phiên bản và giới hạn.

API judge/đề xuất câu hỏi/mô tả ảnh chỉ được cân nhắc trong phạm vi đã cho phép; trước mọi lượt gọi phải có ước tính token/chi phí và chờ duyệt. Trần hiện tại vẫn 0 USD.
