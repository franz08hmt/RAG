# Thực hành 1 — lần theo một truy vấn retrieval

## Mục tiêu

Giải thích được một câu truy vấn đi qua BM25 hoặc dense retriever như thế nào, phân biệt “có một kết quả liên quan” với “đủ tất cả bằng chứng”, và biết tìm nguyên nhân khi kết quả sai.

## Chạy console

Khởi động env riêng và kiểm tra Python đang dùng:

```powershell
$py = 'C:\Users\Dell\anaconda3\envs\rag-hcmute\python.exe'
& $py -c 'import sys; print(sys.executable)'
& $py -m rag_hcmute.console_app --query "Điều kiện để được công nhận tốt nghiệp là gì?" --method bm25 --top-k 5
```

Sau đó thử `--method dense` với đường dẫn BGE-M3 local. Dense/Hybrid không được phép tải model tự động; dùng đúng snapshot local như hướng dẫn trong README. Không nhập thông tin cá nhân.

## Tự đọc output

Với mỗi kết quả ghi lại (trong ghi chú cá nhân, không commit query/evidence text):

1. Chọn kết quả đầu tiên có vẻ liên quan. Tên document và PDF page có resolve được không?
2. Có `section_path` đủ để hiểu đoạn nằm trong Điều/Khoản nào không?
3. Nếu câu hỏi cần hai điều kiện, Top-5 có chứa cả hai gold spans hay chỉ một?
4. BM25 và dense có xếp cùng chunk lên đầu không? Nếu khác, hãy nhìn xem query dùng từ chính xác hay paraphrase.
5. Chunk bị cắt ở giới hạn model không? Xem log/evidence thay vì phỏng đoán từ độ dài ký tự.

## Ví dụ đọc số liệu của pilot

Ở G0, BM25 trả 4/10 gold spans ở Top-5; dense BGE-M3 trả 9/10. Nhưng số câu có đủ mọi span chỉ là BM25 3/7 và dense 6/7. Vì vậy “dense tìm được một span liên quan” không đồng nghĩa câu hỏi đã được trả lời đủ. RRF đạt 6/10 span, 4/7 câu đầy đủ; trên pilot này nó không vượt dense.

## Nếu truy xuất sai

Kiểm tra source/version/hash; page extraction; chunk section; tokenization/ngôn ngữ; query terms; candidate depth; reranker truncation. Chỉ sau khi biết evidence có trong index mới điều chỉnh retrieval. Không yêu cầu LLM bịa phần còn thiếu.
