# Đọc kết quả Mốc 2 trước khi trình bày

## Điểm cần hiểu từ số liệu

Phép thử cũ cho BGE-M3 context 1024 và E5-small 512 trên các chunk 500 đơn vị khoảng trắng.
E5 bị cắt nhiều hơn. Phép mới rút cửa sổ để cả hai tokenizer nhận đủ chuỗi; đổi đồng thời
ranh giới chunk nên chỉ so hai model **trong** phép mới, không nói phần trăm tăng/giảm giữa
hai phép hoàn toàn do embedding.

Ví dụ tính tay: span vàng từ ký tự 10 đến 30 có độ dài 20. Chunk A phủ 10–22,
chunk B phủ 18–30. Hợp A và B phủ đủ 20, không phải 12+12=24. Khi thêm chunk C
không liên quan, recall vẫn 1 nhưng precision giảm. Code: `evaluation/interval_metrics.py`.

RRF với hằng số 60: một đoạn đứng hạng 1 ở một nhánh có đóng góp 1/61, hạng 10
có đóng góp 1/70. Các nhánh cộng đóng góp khi ID trùng; điểm cosine không được cộng
thẳng với BM25. Code: `retrieval/hybrid.py`. Nhánh yếu vẫn có thể làm kết quả kém đi.

## Các câu thầy có thể hỏi

1. Vì sao 500 khoảng trắng không phải 500 token? Tokenizer chia âm tiết/ký tự thành
   các subword; phải đếm bằng tokenizer thực tế, cả prefix và token đặc biệt.
2. Vì sao đã không truncation vẫn thiếu evidence? Ranh giới chunk có thể cắt một điều kiện.
3. Recall ký tự khác tỷ lệ span chứa trọn ở đâu? Một phép đo phần giao của hợp các chunk,
   phép kia yêu cầu một chunk chứa đủ toàn bộ span. Tên và mẫu số phải tách rõ.
4. nDCG cao có chứng minh trả lời đúng không? Không; nó chấm xếp hạng theo nhãn retrieval,
   chưa chấm mệnh đề sinh ra.
5. ANN Recall@10 khác evidence Recall thế nào? ANN so ID láng giềng với Flat, evidence
   so nội dung nguồn đúng. Hai hệ tham chiếu khác nhau.
6. IVF nprobe tăng thì điều gì thay đổi? Nhiều danh sách được duyệt hơn, có thể tìm lại
   láng giềng bị bỏ sót; chi phí tìm tăng, không tự thay chất lượng embedding.
7. Vì sao rerank tăng Recall mà MRR giảm? Nó có thể đưa thêm nguồn vào Top-5 nhưng đẩy
   chunk đầu tiên đạt ngưỡng xuống hạng thấp hơn.
8. Vì sao JSON lỗi không tính là từ chối đúng? Model chưa đưa ra quyết định thiếu căn cứ
   hợp lệ; đó là lỗi giao thức, dù ứng dụng không hiển thị câu trả lời.
9. Cache mới tránh dùng nhầm vector bằng cách nào? Băm model và nội dung/thứ tự chunk,
   kiểm chữ ký cấu hình, kiểu/kích thước vector, tính hữu hạn, chuẩn L2 và digest.
10. Vì sao 129 hay nhiều test hơn không là độ chính xác RAG? Test chủ yếu kiểm hợp đồng
    phần mềm bằng ví dụ xác định; chất lượng trên câu hỏi mới cần bộ đánh giá độc lập.
11. Tại sao phát hiện ảnh chưa phải hiểu hình? Bbox là vị trí, OCR là chữ; quan hệ mũi tên,
    thứ tự thao tác hoặc chú giải đòi hỏi phân tích thêm.
12. Vì sao chưa thể nói đã hoàn tất mọi YC? Các mục khảo sát rộng và chấm người/holdout
    chưa đủ; mỗi nội dung chỉ được đánh dấu theo minh chứng thực tế.

## Cách tự kiểm tra

Chọn P007, chạy console rồi tự mở đúng trang. Dùng một câu chưa có trong bộ dev và ghi lại
nguồn, câu trả lời, điều kiện bị bỏ sót. Không sửa nhãn hoặc prompt theo câu đó rồi gọi nó là
test độc lập. Khi giải thích kết quả, nêu cả một trường hợp không cải thiện.
