# Phân tích trường hợp truy xuất - BM25 baseline

Nguồn dữ liệu: `docs/evidence/runs/bm25_5da3bd4d5de54492_20260924T112003Z.json`
(snapshot `5da3bd4d5de54492`, cấu hình BM25 mặc định trong `rag_hcmute.retrieval.bm25_index`).
Mọi số liệu trong tài liệu này lấy trực tiếp từ file kết quả thô trên, không chỉnh sửa tay.

## 2 trường hợp truy xuất đúng (hit_rank = 1)

### P002 - "Sinh viên được rút bớt học phần trong trường hợp nào?"

- Top-1: `HCMUTE_QCDT_1727_2021__c0021`, score 27.26, trang PDF 12, `Chương II > Điều 9`.
- Gold evidence (đã xác minh thủ công): Điều 9, mục 7 "Rút bớt học phần đã đăng ký" - cùng trang, cùng chunk.
- Nguyên nhân đúng: câu hỏi dùng gần như nguyên văn cụm "rút bớt học phần" xuất hiện lặp lại nhiều lần
  trong đúng đoạn văn bản gốc, nên trọng số từ khóa BM25 (term frequency trong chunk, hiếm gặp ở các
  chunk khác) đẩy đúng chunk lên hạng 1 với khoảng cách điểm số khá xa hạng 2 (27.26 so với 25.60).

### P007 - "Thủ tục xin nghỉ học tạm thời được quy định ra sao?"

- Top-1: `HCMUTE_QCDT_1727_2021__c0038`, score 23.53, trang PDF 23-24, `Chương IV > Điều 17`.
- Gold evidence: Điều 17 "Nghỉ học tạm thời, thôi học" - đúng chunk, đúng trang.
- Nguyên nhân đúng: tương tự P002, cụm "nghỉ học tạm thời" là cụm từ khóa đặc trưng, ít lặp lại ở nơi
  khác trong corpus, nên BM25 (vốn mạnh về khớp từ khóa hiếm) xác định đúng ngay từ lượt truy vấn đầu.

## 2 trường hợp truy xuất sai / chưa rõ (không lọt Top-10)

### P005 - "Điều kiện để sinh viên đăng ký học phần Thực tập tốt nghiệp là gì?"

- Gold evidence: `HCMUTE_FIT_TTTN_2022__c0000` (toàn bộ tài liệu hướng dẫn của khoa CNTT, 1 trang) -
  **hạng thật sự trong danh sách xếp hạng đầy đủ là 27/156** (không lọt Top-10 lẫn Top-5).
- Top-1 thực tế: `HCMUTE_QCDT_1727_2021__c0018` (Điều 9, trang 10) - nói về khối lượng học tập nói
  chung, có nhắc "học kỳ thực tập tốt nghiệp" như một trường hợp đặc biệt, nhưng không phải nội dung
  chính trả lời câu hỏi.
- Nguyên nhân sai (đã truy về PDF gốc để xác minh): tài liệu `HCMUTE_FIT_TTTN_2022` chỉ có đúng 1
  trang/1 chunk trong khi hai tài liệu còn lại (`HCMUTE_QCDT_1727_2021`, `HCMUTE_SOTAYSV_2024`) chiếm
  155/156 chunk và cũng nhắc đến các từ phổ biến trong câu hỏi ("học phần", "đăng ký", "điều kiện").
  Với một corpus nhỏ và mất cân bằng như vậy, IDF của các từ khóa này không đủ thấp để bù lại việc
  chunk đích chỉ xuất hiện đúng 1 lần, khiến BM25 xếp hạng nó thấp dù về mặt chủ đề đây là tài liệu
  đúng nhất. Đây là giới hạn thực tế của BM25 trên corpus nhỏ/lệch kích thước tài liệu, không phải lỗi
  trích xuất hay chunking (nội dung chunk vẫn nguyên vẹn, đã kiểm tra bằng `test_every_chunk_traces_back_to_its_declared_pdf_pages`).

### P003 - "Cảnh báo học tập được xác định theo những tiêu chí nào?"

- Gold evidence: `HCMUTE_QCDT_1727_2021__c0032` (Điều 13, hạng thật 26/156) và `...__c0033`
  (Điều 14, hạng thật 22/156) - cả hai đều không lọt Top-10.
- Top-1 thực tế: `HCMUTE_QCDT_1727_2021__c0030`, trang 18-19, `Chương III > Điều 12` - "Đánh giá kết
  quả học tập theo học kỳ, năm học" - Điều ngay TRƯỚC Điều 13, bàn về điểm trung bình học kỳ/năm học.
- Nguyên nhân sai (đã đối chiếu nguyên văn cả hai đoạn): đây là lỗi **lệch từ vựng giữa câu hỏi và văn
  bản gốc** - câu hỏi dùng từ "tiêu chí", còn Điều 13/14 dùng cụm "khi thuộc một trong các điều kiện
  sau". Điều 12 (chunk thắng) lại dùng nhiều từ liên quan đến "đánh giá kết quả học tập", "điểm trung
  bình học kỳ" - trùng từ vựng bề mặt với ngữ cảnh cảnh báo học tập (vốn cũng dựa trên điểm trung bình)
  nhưng không phải đúng Điều trả lời câu hỏi. Đây đúng là giới hạn mà bản DEMO đã dự đoán cho BM25:
  "Nếu câu hỏi dùng từ khác với văn bản gốc, BM25 sẽ bỏ sót hoàn toàn tài liệu liên quan" - trường hợp
  này bỏ sót một phần (không "hoàn toàn", vì đúng chunk vẫn nằm trong corpus và có thể truy xuất được
  ở Top-30, chỉ là không đủ điểm để vào Top-5/Top-10).

## Ghi chú giới hạn

- Cỡ mẫu đánh giá Recall@5/MRR hiện chỉ có 7 câu answerable có gold evidence (P001-P002-P003-P004-
  P005-P007-P008); P006 chưa có gold evidence trong corpus hiện tại (xem `pilot_questions.csv`), P009/
  P010 cố tình không có gold evidence vì ngoài phạm vi. Với mẫu số nhỏ như vậy, mỗi câu hỏi ảnh hưởng
  khoảng 14% giá trị Recall@5, nên chưa nên coi kết quả này là ước lượng ổn định cho toàn hệ thống -
  cần mở rộng bộ câu hỏi ở các mốc sau.
