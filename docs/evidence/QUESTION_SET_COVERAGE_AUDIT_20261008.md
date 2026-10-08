# Audit độ bao phủ bộ câu hỏi đánh giá — 08/10/2026

## Phạm vi

Audit này thống kê metadata của corpus G0 và các câu hỏi đã được duyệt. Nội dung câu hỏi, câu trả lời,
đoạn trích và văn bản nguồn không được chép vào kết quả audit. Các câu hỏi ứng viên chưa duyệt không
được tính. Năm câu hỏi về Bảng 5 được giữ thành ablation riêng, không gộp vào pilot tổng quát.

Có thể tái lập số liệu bằng lệnh:

```powershell
python scripts/audit_question_coverage.py
```

## Số liệu hiện có

Snapshot `5da3bd4d5de54492` có 3 tài liệu thuộc 3 loại trong manifest: một quyết định, một hướng dẫn
thực tập và một sổ tay sinh viên. Pilot chung có 10 câu đã duyệt; 7 câu answerable và 3 câu
unanswerable. Cả 7 câu answerable đều có annotation exact evidence, gồm 10 evidence span.

| Loại tài liệu trong corpus | Số câu answerable có nguồn ở loại đó |
| --- | ---: |
| Quyết định / quy chế | 6 |
| Hướng dẫn | 1 |
| Sổ tay sinh viên | 0 |

Ba câu unanswerable thuộc ba nhóm được gắn nhãn trong dữ liệu: điều kiện khóa luận/đồ án tốt nghiệp,
lịch thi cụ thể và học phí học kỳ tiếp theo. Các nhãn này không đồng nghĩa với cùng một nguyên nhân:
có câu thiếu quy định trong snapshot, có câu hỏi về dữ liệu thay đổi theo thời điểm. Khi đánh giá refusal,
cần phân biệt các tình huống này thay vì gộp thành một nhóm “không có kết quả”.

Năm câu hỏi về Bảng 5 đã được duyệt cho phép thử retrieval riêng. Chúng cùng thuộc một tài liệu và một
tham chiếu nguồn; đây là minh chứng hẹp cho cách biểu diễn bảng, không đại diện cho các loại bảng khác
hoặc cho nội dung hình/scan nói chung.

## Những gì số liệu chưa chứng minh

- Pilot hiện chưa có trường `split`; bộ câu hỏi được dùng như development/pilot trong các ablation và
  chưa có holdout độc lập được ghi nhận. Vì vậy các metric đang có không phải ước lượng cuối về khả năng
  khái quát của hệ thống.
- Câu answerable phân bố trên Quy chế và Hướng dẫn thực tập, chưa phủ Sổ tay. Việc corpus có tài liệu
  sổ tay không đồng nghĩa pipeline đã được đánh giá hỏi đáp trên tài liệu đó.
- Nhóm câu hỏi bảng nằm trong phép thử riêng về một bảng; không nên gộp số câu này vào mẫu số pilot chung
  khi so sánh BM25, Dense, Hybrid hoặc reranker.
- Audit này chỉ đo độ bao phủ nhãn và nguồn, không đo chất lượng retrieval, độ đúng câu trả lời, citation,
  khả năng từ chối hay độ đại diện của câu hỏi cho nhu cầu sinh viên.

## Bước chuẩn bị dữ liệu đánh giá tiếp theo

Trước khi dùng số liệu để chọn cấu hình, cần tiếp tục mở rộng câu hỏi trên các lớp dữ liệu còn thiếu và
đối chiếu từng câu với nguồn gốc. Câu answerable cần được gắn tài liệu, trang/điều hoặc hàng bảng và exact
evidence span; câu unanswerable cần ghi rõ là do thiếu trong corpus hay do dữ liệu động/ngoài phạm vi.
Sau khi các nhãn được rà soát, cần tách development và holdout trước khi chạy thử tham số tiếp theo.

Việc tạo và duyệt nội dung câu hỏi vẫn cần người học kiểm tra trực tiếp với tài liệu. Audit không tự tạo
câu hỏi, không tự đặt gold answer và không thay đổi các tệp câu hỏi hiện có.
