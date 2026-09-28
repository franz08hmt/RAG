# Phiếu chuẩn bị đánh giá truy xuất thông tin trong bảng

## Mục đích

Thử nghiệm này kiểm tra liệu cách biểu diễn bảng có giúp retriever tìm đúng dòng dữ liệu hơn so với cách lập chỉ mục hiện tại hay không. Phạm vi chỉ là truy xuất bằng chứng từ corpus HCMUTE; chưa đánh giá câu trả lời do LLM sinh ra và chưa thay đổi pipeline mặc định.

## Các cấu hình cần đối chiếu

- **B0 — Baseline hiện tại:** dùng snapshot/chunk hiện có, không bổ sung biểu diễn bảng.
- **T1 — Bảng Markdown:** mỗi bảng được lưu thành một khối có tiêu đề, tên cột và nội dung bảng.
- **T2 — Bản ghi theo dòng có ngữ cảnh:** mỗi dòng được chuyển thành một bản ghi văn bản, kèm tên tài liệu, trang, tiêu đề bảng, nhóm hàng và tên cột cần thiết.

T1 và T2 chỉ là hai cách biểu diễn ứng viên, chưa phải quyết định thiết kế. Cần kiểm tra bảng nguồn trước khi đưa vào index; ô gộp, hàng tiêu đề nhiều tầng, đơn vị và ghi chú phải được giữ đúng. Không suy diễn giá trị cho ô trống nếu tài liệu không thể hiện rõ quan hệ đó.

## Cách giữ phép so sánh công bằng

1. Dùng cùng một bản corpus đầu vào và cùng danh sách câu hỏi đã được người học rà soát.
2. Ghim cấu hình retrieval (BM25 hoặc dense), `top_k`, tokenizer/model embedding và các tham số còn lại trong từng lượt chạy; không thay nhiều yếu tố cùng lúc.
3. Đối chiếu gold evidence theo vị trí ổn định trong tài liệu gốc — mã tài liệu, số trang PDF, mã bảng nếu có, hàng/nhóm hàng và ô liên quan. Sau khi tạo từng snapshot, ánh xạ vị trí này sang `chunk_id` riêng của B0, T1 và T2.
4. Chạy retrieval trước, chưa đưa generation vào phép so sánh. Ghi lại thứ hạng và nội dung bằng chứng để có thể kiểm tra thủ công.
5. Báo cáo Hit@5 và MRR@10 theo cách bộ đánh giá hiện tại tính; kèm số câu có gold evidence và nêu rõ câu nào chưa thể gán gold. Không dùng kết quả của mẫu nhỏ để kết luận cách biểu diễn tốt hơn trong mọi loại bảng.
6. Nếu một bảng không thể xác định chắc cấu trúc hàng/cột bằng trích xuất tự động, đánh dấu cần kiểm tra thủ công hoặc loại khỏi lượt đo; không biến đầu ra heuristic thành ground truth.

## Phiếu câu hỏi cần người học tự điền

Nên bắt đầu với khoảng 5–10 câu hỏi có thể trả lời trực tiếp từ một hoặc một vài bảng đã kiểm tra. Chọn câu hỏi cần tra cứu giá trị, điều kiện, nhóm hàng hoặc đối chiếu cột; tránh chỉ hỏi nội dung đã có nguyên văn ở phần văn bản thường. Mỗi câu phải có vị trí bằng chứng đủ cụ thể để người khác mở PDF và xác minh.

Sao chép khối dưới đây cho mỗi câu hỏi. Chưa đưa các câu đang để trống vào bộ đánh giá hoặc chạy script.

```text
question_id:
question:                         [Do người học tự viết]
answerability:                    answerable | unanswerable
expected_document:
pdf_page:                         [Số trang PDF, không phải số trang in nếu khác]
table_title_or_identifier:
row_or_group:
column_or_cell:
expected_evidence:                [Trích ngắn đúng phần cần đối chiếu]
expected_answer_or_acceptance:    [Những dữ kiện tối thiểu cần có trong kết quả]
review_status:                    draft | verified
notes:
```

### Ánh xạ bằng chứng sau khi tạo từng biểu diễn

| Câu hỏi | Vị trí gold trong PDF (trang/bảng/hàng) | B0 chunk ID | T1 chunk ID | T2 chunk ID | Đã đối chiếu PDF? |
|---|---|---|---|---|---|
|  |  |  |  |  |  |

Không cần điền `chunk_id` trước khi snapshot T1/T2 tồn tại. Một câu có thể cần nhiều gold chunk nếu đáp án phụ thuộc vào nhiều hàng hoặc nhiều bảng; ghi đầy đủ các bằng chứng đó thay vì chọn một chunk gần đúng.

## Khi nào mới chuyển sang hiện thực

Sau khi danh sách câu hỏi và gold evidence được rà soát, bước kế tiếp là chọn một bảng không chứa PII, kiểm tra extraction thủ công với trang PDF, rồi tạo T1/T2 thành snapshot riêng. Sau đó chạy cùng retriever và cùng câu hỏi trên B0/T1/T2, lưu cấu hình, kết quả từng câu và các trường hợp lỗi. Chỉ cân nhắc tích hợp một biểu diễn vào pipeline chính nếu bằng chứng đo được đủ rõ và không làm mất khả năng truy nguyên nguồn.

## Giới hạn hiện tại

- Chưa có bộ câu hỏi bảng được người học xác nhận; phiếu này không chứa câu hỏi hay gold answer dựng sẵn.
- Chưa tích hợp table chunks vào retrieval mặc định.
- Kết quả trước đây về một bảng ở Quy chế 1727 (PDF page 3, 14×5 theo PyMuPDF) chỉ xác nhận hình dạng trích xuất; chưa chứng minh mọi ô được đọc đúng và không tự động được dùng làm dữ liệu đánh giá.
- Chỉ dùng tài liệu thuộc corpus HCMUTE đã cho phép. Bỏ qua vùng chứa dữ liệu cá nhân; không gửi PDF, trích đoạn nhạy cảm hoặc câu hỏi có PII lên dịch vụ cloud.
