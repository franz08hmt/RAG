# Quay video demo console (khoảng 3 phút)

Video minh họa ứng dụng console với cấu hình đã chốt trong báo cáo: BM25 + BGE-M3, RRF k=60, 50 ứng viên mỗi nhánh, không reranker; Qwen3:4B + JSON Schema, context 8.192; toàn bộ chạy cục bộ.

## Chuẩn bị

1. Mở Ollama (kiểm tra bằng `ollama list` có `qwen3:4b`). Đóng các ứng dụng nặng GPU.
2. Mở PowerShell, phóng to cửa sổ, cỡ chữ khoảng 16 để video đọc được.
3. Chạy:

~~~powershell
Set-Location D:\RAG\rag-hcmute-dot2
& 'C:\Users\Dell\anaconda3\envs\rag-hcmute\python.exe' scripts\demo_video.py
~~~

Script nạp dữ liệu và model, chạy một câu warm-up (khoảng 45 giây), rồi dừng ở dòng "Sẵn sàng quay". Lúc này mới bật quay (`Win + Alt + R`), nhấn Enter: màn hình được xóa, đường dẫn máy và phần warm-up không xuất hiện trong video. Giữa các câu, script chờ Enter để có thời gian nói. Email và số điện thoại trong đoạn trích được che trên màn hình.

## Lời dẫn từng câu

Câu trả lời do mô hình sinh có thể khác giữa các lần chạy. Nói theo những gì hiện trên màn hình; phần dưới ghi kết quả của lượt chạy thử ngày 28/11/2026.

**Mở đầu (15 giây).** "Đây là ứng dụng console của đề tài Tìm hiểu RAG. Kho gồm 156 đoạn từ ba văn bản học vụ HCMUTE. Mỗi câu hỏi đi qua BM25 và BGE-M3, hợp thứ hạng bằng RRF, rồi Qwen3 chạy cục bộ trả lời kèm nguồn."

1. **Nghỉ học tạm thời — câu trả lời đúng có nguồn.** Nguồn hạng 1 là Điều 17, QĐ 1727, trang PDF 23–24; cả BM25 và BGE-M3 đều xếp đoạn này hạng 1. Câu trả lời nêu hai hạn nộp đơn (2 tuần trước khi kết thúc học kỳ khi xin nghỉ, 2 tuần trước khi đăng ký học phần khi học tiếp). Nói: "Trích dẫn trỏ đúng Điều và trang, người dùng mở lại PDF để kiểm."
2. **Bảng 1 — số đúng, nhãn Điều sai.** Câu trả lời đúng 4 năm / 5 năm và 120 tín chỉ, nhưng nguồn ghi "Điều 15". Nói: "Đoạn này bắt đầu bằng câu dẫn chiếu 'Điều 15 của Quy chế này' nên bộ nhận diện đề mục gắn nhầm nhãn; bảng thật ở trang 3. Đây là lỗi metadata đã phân tích trong báo cáo, cho thấy cần kiểm đề mục trước khi tin trích dẫn."
3. **Chương trình thứ hai — tìm đủ nguồn nhưng trả lời thiếu điều kiện.** Hạng 1 là Điều 20; nguồn hạng 3 còn có điều kiện "không đang là sinh viên năm thứ nhất hoặc năm cuối khóa...", nhưng câu trả lời chỉ nêu hai điều kiện học lực. Nói: "Truy xuất đã đúng; lỗi nằm ở bước sinh — mô hình bỏ một điều kiện có trong ngữ cảnh."
4. **Thư viện Cần Thơ — từ chối.** Các đoạn trả về đều không liên quan; mô hình trả trạng thái `model_abstained`. Chỉ vào phần thứ hạng từng nhánh: BM25 và BGE-M3 xếp các đoạn rất khác nhau (ví dụ BM25 #2 nhưng BGE-M3 #23), RRF chỉ gộp thứ hạng. Nói: "Điểm truy xuất không cho biết câu có trả lời được hay không, nên quyết định từ chối nằm ở bước sinh với schema hai nhánh."
5. **Học trước và tiên quyết — trả lời gộp sai hai khái niệm.** Nguồn hạng 1 đúng là Điều 3, nhưng câu trả lời nói phải "đã học và đạt môn A" cho cả hai trường hợp, trong khi học phần học trước và học phần tiên quyết có điều kiện khác nhau. Nói: "Đây là ví dụ vì sao báo cáo tách đánh giá truy xuất với đánh giá câu trả lời."

**Kết thúc (10 giây).** "Kết quả đầy đủ, số đo và giới hạn nằm trong báo cáo; mã nguồn ở link GitHub trong Phụ lục A."

## Nếu gặp sự cố

- Ollama không phản hồi hoặc thiếu VRAM: dừng, khởi động lại Ollama, chạy lại script.
- Muốn chạy thử không dừng: thêm `--no-pause --no-clear`.
- Không đưa log chạy (có nội dung đoạn nguồn) vào repo.
