# Chẩn đoán độ nhạy BM25 với cách diễn đạt truy vấn — 05/10/2026

## Mục đích và phạm vi

Sau ablation B0/T1/T2 trên Bảng 5 của QĐ 1727/2021, BM25 lấy đủ evidence trong Top-5 cho 4/5 câu ở B0, 1/5 ở T1 và 0/5 ở T2. Chẩn đoán này kiểm tra liệu thứ hạng thấp có nhạy với cách diễn đạt câu hỏi hay không; không đổi câu hỏi đã duyệt, gold evidence, corpus, tokenizer, BM25, top-k hay pipeline mặc định.

Năm câu TB001–TB005 và ánh xạ evidence đã duyệt vẫn là đầu vào gốc. Các biến thể dưới đây là truy vấn tạm do người thực hiện tạo chỉ để chẩn đoán; không được nhập vào pilot, không được dùng thay kết quả ablation chính và chưa đại diện cho cách hỏi của người dùng thật.

## Cách thử

BM25Okapi và tokenizer hiện tại (`\w+` Unicode, chuyển chữ thường) được chạy trên cùng corpus nền B0/T1/T2 có 156/157/161 chunk. Với mỗi câu, đo thứ hạng đầy đủ của chunk evidence trong toàn corpus, không chỉ cắt danh sách ở Top-5. TB005/T2 có hai chunk bắt buộc nên ghi cả hai hạng.

Lệnh tái lập (script in đường dẫn Python đang chạy trước khi xử lý):

```powershell
conda run -n rag-hcmute python scripts/diagnose_bm25_query_sensitivity.py
```

Raw JSON được ghi vào `artifacts/results/bm25_query_sensitivity/` (Git-ignored), gồm exact query, evidence ranks, Top-5 chunk IDs, hash câu hỏi/evidence và revision code.

Bốn cách tạo truy vấn:

1. **Canonical:** câu chữ chính thức đã được duyệt.
2. **Canonical + header:** nối tên hai cột gốc “Năm đào tạo sinh viên” và “Tổng số tín chỉ đã tích lũy” vào canonical; không thêm đáp án hoặc giá trị của hàng.
3. **Rút gọn:** lược cụm trích dẫn tên/số hiệu văn bản, giữ nội dung câu hỏi và dữ kiện vốn đã có trong câu.
4. **Rút gọn + header:** truy vấn rút gọn cộng hai tên cột trên.

Các câu rút gọn dùng trong lượt thử: TB001 “85 tín chỉ thuộc năm đào tạo nào”; TB002 “Khoảng tín chỉ tích lũy năm đào tạo thứ hai là bao nhiêu”; TB003 “Năm đào tạo thứ tư tương ứng với khoảng tổng số tín chỉ tích lũy nào”; TB004 “Điều kiện tín chỉ tích lũy cho năm đào tạo thứ năm như thế nào”; TB005 “71 tín chỉ và 72 tín chỉ lần lượt thuộc năm đào tạo nào”.

## Kết quả thứ hạng evidence

Mỗi ô ghi hạng của evidence bắt buộc; “7/8” nghĩa là TB005/T2 cần hai dòng và chúng lần lượt đứng hạng 7, 8.

| Corpus | Truy vấn | TB001 | TB002 | TB003 | TB004 | TB005 |
|---|---|---:|---:|---:|---:|---:|
| B0 | Canonical | 10 | 1 | 4 | 2 | 1 |
| B0 | Canonical + header | 3 | 1 | 2 | 1 | 1 |
| B0 | Rút gọn | 4 | 2 | 1 | 2 | 2 |
| B0 | Rút gọn + header | 1 | 1 | 1 | 1 | 2 |
| T1 | Canonical | 43 | 16 | 24 | 43 | 2 |
| T1 | Canonical + header | 13 | 6 | 7 | 17 | 2 |
| T1 | Rút gọn | 19 | 2 | 3 | 22 | 1 |
| T1 | Rút gọn + header | 4 | 3 | 3 | 8 | 1 |
| T2 | Canonical | 48 | 26 | 33 | 52 | 7/8 |
| T2 | Canonical + header | 20 | 8 | 11 | 24 | 4/5 |
| T2 | Rút gọn | 22 | 2 | 4 | 29 | 3/4 |
| T2 | Rút gọn + header | 7 | 3 | 3 | 9 | 2/3 |

Số câu lấy đủ toàn bộ evidence trong Top-5 khi dùng từng truy vấn (chỉ số chẩn đoán, **không phải kết quả benchmark chính**):

| Corpus | Canonical | Canonical + header | Rút gọn | Rút gọn + header |
|---|---:|---:|---:|---:|
| B0 | 4/5 | 5/5 | 5/5 | 5/5 |
| T1 | 1/5 | 1/5 | 3/5 | 4/5 |
| T2 | 0/5 | 1/5 | 3/5 | 3/5 |

Kết quả canonical khớp với số Hit@5 trong ablation đã duyệt. Những cột còn lại là phép thử độ nhạy riêng, không thay thế số liệu đó.

## Nhận xét có thể rút ra

- Xếp hạng BM25 thay đổi đáng kể theo cách đặt câu hỏi. Chỉ thêm tên cột vào canonical cải thiện TB001/TB005, nhưng chưa đủ kéo phần lớn các dòng T1/T2 vào Top-5.
- Bỏ cụm dẫn chiếu văn bản dài cải thiện một số truy vấn, nhưng riêng cách rút gọn vẫn để TB001 và TB004 ở ngoài Top-5 trên T1/T2.
- Khi vừa dùng câu rút gọn vừa bổ sung tên cột, T1 đạt 4/5 câu đủ evidence trong Top-5 và T2 đạt 3/5. TB001/TB004 trên T2 vẫn ở hạng 7 và 9. Vì vậy, cách hỏi có ảnh hưởng rõ, nhưng không giải thích hết khó khăn của BM25 với biểu diễn theo hàng.
- Trong Top-5 của nhiều câu canonical, các chunk đứng trước evidence đến từ `HCMUTE_SOTAYSV_2024`. Đây là dấu hiệu có cạnh tranh giữa các chunk trong corpus, chưa đủ để xác định đó là nguyên nhân duy nhất.
- Thử nghiệm có năm câu, một bảng và một cách tạo câu rút gọn. Chưa đo trên nhiều người viết truy vấn, bảng khác, corpus khác hoặc các thiết lập BM25 khác; không thể kết luận query expansion sẽ cải thiện tổng quát.

## Kết luận và bước tiếp theo

Chẩn đoán củng cố hai giả thuyết cần kiểm tra tiếp: BM25 nhạy với từ vựng câu hỏi, và cách biểu diễn hàng T2 có thể thiếu các từ khóa mà câu truy vấn đang dùng. Tên cột có ích trong một số trường hợp nhưng không xóa hết chênh lệch. Chưa sửa câu hỏi đã duyệt, chưa thay đổi index hoặc retrieval mặc định và chưa chọn T1/T2 làm thiết kế chung.

Bước tiếp theo phù hợp là mở rộng câu hỏi bảng do người học tự viết và kiểm chứng từng nhãn với PDF; sau đó chạy lại so sánh bằng cùng bộ truy vấn trên B0/T1/T2, đồng thời ghi nhận từ nào trong câu thực sự khớp hàng/metadata. Các câu mở rộng cần được duyệt và tách development/test trước khi tính số liệu chính thức. Việc này vẫn thuộc hoàn thiện Mốc 1; chưa cập nhật DOCX nộp thầy cho tới khi phần mốc được rà soát xong.
