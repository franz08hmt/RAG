# Minh chứng mở rộng báo cáo v2

Các JSON ở thư mục này chứa mã đoạn, mã câu, cấu hình, thống kê và ID lượt chạy. PDF gốc, câu hỏi đầy đủ, đoạn nguồn, phiếu chấm và log console được giữ trong kho đánh giá cục bộ.

- chunk_example.json mô tả c0038 của Quyết định 1727 với khoảng ký tự trên văn bản đã chuẩn hóa.
- chunking43.json lưu sáu phương pháp chia đoạn trên 43 câu đề xuất; mỗi mục có độ phủ Top-5, độ phủ theo ngân sách nguồn, precision ký tự và số span không nằm trọn trong một chunk.
- embeddings43.json dùng cùng 1.175 đoạn vừa 128 token cho sáu model. embeddings43_native.json dùng 156 đoạn G0 với trần kiến trúc tương ứng. Lượt trần riêng có nối tiếp sau khi phát hiện cấu hình PhoBERT khai báo 512 nhưng kiến trúc chỉ hỗ trợ 256 vị trí nội dung; JSON giữ cả ID lần trước và hash mã nguồn.
- embedding_bootstrap.json lưu khoảng bootstrap cặp theo câu cho độ phủ, MRR và nDCG. Câu hỏi cùng điều khoản có thể phụ thuộc nhau nên khoảng này mang tính thăm dò.
- image_run.json và image_qa_schema.json là lượt OCR/mô tả ảnh và trả lời theo hai loại văn bản. image_status.json là số đếm trạng thái. image_review.json là nhãn sơ bộ do trợ lý AI đối chiếu, cần sinh viên kiểm lại.
- demo_console.json là metadata của năm lượt console. Các tệp log thật ở thư mục private_eval trên máy thực nghiệm.

Lệnh chạy, môi trường, đường dẫn dữ liệu cục bộ và giới hạn được ghi trong từng script run_v2_* tương ứng. Những số liệu trên bộ 43 câu dựa vào bản nháp do AI đề xuất và neo vị trí vào snapshot G0. Đó là tập phát triển mở rộng; sinh viên cần đối chiếu đáp án và làm tập test riêng trước khi kết luận độc lập.
