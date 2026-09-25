# Phân tích trường hợp truy xuất - BM25 và Dense Retrieval (BGE-M3)

Nguồn dữ liệu:
- BM25: `docs/evidence/runs/bm25_5da3bd4d5de54492_20260924T112003Z.json`
- Dense: `docs/evidence/runs/dense_bge_m3_5da3bd4d5de54492_20260925T040111Z.json`

(cùng snapshot corpus `5da3bd4d5de54492`, cùng bộ câu hỏi). Mọi số liệu trong tài liệu này lấy trực
tiếp từ 2 file kết quả thô trên, không chỉnh sửa tay.

## 2 trường hợp truy xuất đúng ở cả hai phương pháp (hit_rank = 1)

### P002 - "Sinh viên được rút bớt học phần trong trường hợp nào?"

- BM25 top-1: `HCMUTE_QCDT_1727_2021__c0021`, score 27,26 - đúng gold ngay, cách biệt rõ với hạng 2
  (25,60).
- Dense: cùng gold chunk nhưng chỉ ở **hạng 3** (cosine 0,657), thua 2 chunk khác có nội dung liên
  quan đến "lớp học" nói chung (`HCMUTE_SOTAYSV_2024__c0026` cosine 0,670, `HCMUTE_QCDT_1727_2021__c0037`
  cosine 0,659). Đây là ví dụ Dense **kém hơn BM25**: khi câu hỏi dùng gần như nguyên văn cụm từ khóa
  đặc trưng ("rút bớt học phần"), so khớp từ vựng chính xác của BM25 có lợi thế rõ so với so khớp ngữ
  nghĩa của Dense (vốn có thể bị nhiễu bởi các đoạn cùng chủ đề "lớp học/học phần" nói chung).

### P007 - "Thủ tục xin nghỉ học tạm thời được quy định ra sao?"

- BM25 top-1: `HCMUTE_QCDT_1727_2021__c0038`, score 23,53 - đúng gold.
- Dense top-1: cùng gold chunk, cosine 0,750 - đúng gold. Cả hai phương pháp đều đúng ngay hạng 1 vì
  cụm "nghỉ học tạm thời" vừa là từ khóa đặc trưng (lợi cho BM25) vừa mang ngữ nghĩa rõ ràng, không có
  từ đồng nghĩa gây nhiễu (lợi cho Dense).

## 2 trường hợp BM25 sai nhưng Dense sửa đúng

### P005 - "Điều kiện để sinh viên đăng ký học phần Thực tập tốt nghiệp là gì?"

- BM25: gold chunk `HCMUTE_FIT_TTTN_2022__c0000` (toàn bộ tài liệu hướng dẫn của khoa CNTT, 1 trang)
  **không lọt Top-10** (hạng thật 27/156) - xem nguyên nhân đầy đủ ở mục dưới.
- **Dense: cùng gold chunk lên hạng 1** (cosine 0,721), vượt xa hạng 2 (0,678). Vì Dense so khớp theo
  ngữ nghĩa toàn câu thay vì tần suất từ khóa riêng lẻ, việc tài liệu chỉ có 1 chunk không còn là bất
  lợi (không bị pha loãng bởi IDF thấp như BM25) - đây đúng là trường hợp DEMO dự đoán Dense sẽ mạnh
  hơn khi corpus nhỏ/mất cân bằng.

### P003 - "Cảnh báo học tập được xác định theo những tiêu chí nào?"

- BM25: 2 gold chunk (Điều 13, Điều 14) đều **không lọt Top-10** (hạng thật 26/156 và 22/156) do lệch
  từ vựng "tiêu chí" (câu hỏi) so với "điều kiện" (văn bản gốc) - xem phân tích đầy đủ ở mục dưới.
- **Dense: gold chunk Điều 13 lên hạng 2** (cosine 0,679), Điều 14 vào hạng 3 (cosine 0,645), chỉ thua
  đúng 1 chunk (`HCMUTE_SOTAYSV_2024__c0020`, một đoạn khác trong Sổ tay SV cũng nói về đánh giá học
  tập). Đây là bằng chứng thực nghiệm trực tiếp cho việc BGE-M3 nắm được quan hệ ngữ nghĩa "tiêu chí"
  ≈ "điều kiện" mà BM25 (so khớp từ khóa) không làm được - đúng như giới hạn BM25 mà DEMO đã dự đoán:
  "Nếu câu hỏi dùng từ khác với văn bản gốc, BM25 sẽ bỏ sót"; ở đây Dense đã lấp phần lớn khoảng trống
  đó (dù chưa lên hạng 1 tuyệt đối).

### Nguyên nhân gốc BM25 sai (giữ lại để đối chiếu, đã truy về PDF gốc để xác minh)

- **P005**: tài liệu `HCMUTE_FIT_TTTN_2022` chỉ có đúng 1 trang/1 chunk trong khi hai tài liệu còn lại
  chiếm 155/156 chunk và cũng nhắc các từ phổ biến trong câu hỏi ("học phần", "đăng ký", "điều kiện").
  IDF của các từ này không đủ thấp để bù cho việc chunk đích chỉ xuất hiện đúng 1 lần - giới hạn của
  BM25 trên corpus nhỏ/lệch kích thước tài liệu, không phải lỗi trích xuất hay chunking (đã kiểm tra
  bằng `test_every_chunk_traces_back_to_its_declared_pdf_pages`).
- **P003**: BM25 top-1 thực tế là `HCMUTE_QCDT_1727_2021__c0030` (Điều 12 - "Đánh giá kết quả học tập
  theo học kỳ, năm học", Điều liền kề Điều 13, cùng bàn về điểm trung bình) - trùng từ vựng bề mặt
  nhưng sai Điều.

## 1 trường hợp cả hai phương pháp đều chưa tốt

### P004 - "Quy định về đăng ký học lại được nêu như thế nào?"

- BM25: gold chunk (`HCMUTE_QCDT_1727_2021__c0021`, cùng chunk với P002) **không lọt Top-10**.
- Dense: cải thiện nhưng vẫn chỉ **hạng 6** (cosine 0,649 tại hạng 6, thua 5 chunk khác trong cùng
  Điều 9 hoặc lân cận nói chung về đăng ký học phần). Cả hai phương pháp đều nhầm lẫn "đăng ký học lại"
  với ngữ cảnh rộng hơn "đăng ký học phần" nói chung, vì Điều 9 có nhiều mục con dùng chung nhiều từ
  vựng ("đăng ký", "học phần"). Đây là trường hợp cho thấy retrieval một tầng (BM25 hoặc Dense đơn lẻ)
  chưa đủ phân biệt các mục con trong cùng một Điều dài - gợi ý giá trị của reranker (Cross-Encoder,
  đọc kỹ từng cặp câu hỏi-đoạn) ở mốc kế tiếp thay vì chỉ dựa vào điểm truy xuất ban đầu.

## Ghi chú giới hạn

- Cỡ mẫu đánh giá Recall@5/MRR hiện chỉ có 7 câu answerable có gold evidence (P001-P002-P003-P004-
  P005-P007-P008); P006 chưa có gold evidence trong corpus hiện tại (xem `pilot_questions.csv`), P009/
  P010 cố tình không có gold evidence vì ngoài phạm vi. Với mẫu số nhỏ như vậy, mỗi câu hỏi ảnh hưởng
  khoảng 14% giá trị Recall@5, nên chưa nên coi kết quả này là ước lượng ổn định cho toàn hệ thống -
  cần mở rộng bộ câu hỏi ở các mốc sau.
- Dense tốt hơn BM25 trên 2/7 câu và tệ hơn trên 1/7 câu trong mẫu nhỏ này - **chưa đủ căn cứ để kết
  luận Dense "luôn tốt hơn"**, chỉ đủ để xác nhận cả hai phương pháp có điểm mạnh/yếu bổ sung nhau,
  đúng hướng để đầu tư Hybrid (RRF) ở mốc kế tiếp thay vì thay thế hoàn toàn BM25 bằng Dense.
