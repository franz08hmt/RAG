# Tóm tắt metric retrieval - đợt 1

Nguồn: `docs/evidence/runs/bm25_5da3bd4d5de54492_20260924T112003Z.json`
Lệnh tái tạo: `python scripts/run_pilot_eval.py --method bm25`
Snapshot corpus: `5da3bd4d5de54492` (xem `data/manifests/corpus_snapshot.json`)

## Định nghĩa

- **Gold chunk**: chunk chứa đoạn bằng chứng đã xác minh thủ công cho câu hỏi (cột `expected_chunk_id`
  trong `pilot_questions.csv`), một số câu có 2 gold chunk (nội dung nằm ở cả Điều theo tín chỉ và
  theo niên chế).
- **"Truy xuất đúng"**: chunk trả về có `chunk_id` trùng với một trong các gold chunk đã gán cho câu
  hỏi đó (khớp ở mức chunk, đồng thời cũng là khớp đúng trang PDF vì mỗi gold chunk chỉ ứng với 1
  văn bản/1 khoảng trang cụ thể).
- **Recall@5**: tỉ lệ câu hỏi có ít nhất 1 gold chunk xuất hiện trong Top-5 kết quả.
- **MRR@10**: trung bình 1/hạng của gold chunk đầu tiên xuất hiện trong Top-10; bằng 0 nếu không xuất
  hiện trong Top-10.
- **Mẫu số**: chỉ tính trên các câu có gold evidence đã xác minh (answerable và có `expected_chunk_id`
  khác rỗng) = 7/10 câu (P001, P002, P003, P004, P005, P007, P008). P006 chưa có gold evidence trong
  corpus hiện tại (xem lý do trong `pilot_questions.csv`); P009, P010 cố tình unanswerable.

## Kết quả BM25 (baseline)

| Metric | Giá trị | Ghi chú |
|---|---|---|
| Recall@5 | 3/7 = 0.429 | P002, P007 đúng hạng 1; P001 đúng hạng 2 |
| MRR@10 | 0.371 | P003, P004, P005 không lọt Top-10 (đóng góp 0); P008 đúng ở hạng 10 (đóng góp 0.1) |

## Chi tiết theo câu hỏi

| ID | Answerability | Hit rank (Top-10) | Ghi chú |
|---|---|---|---|
| P001 | answerable | 2 | Top-1 là chunk số tay SV (mục lục/học bổng), gần đúng chủ đề |
| P002 | answerable | 1 | Đúng ngay, cách biệt điểm số rõ với hạng 2 |
| P003 | answerable | không lọt Top-10 (hạng thật 22-26/156) | lệch từ vựng "tiêu chí" vs "điều kiện"; xem case study |
| P004 | answerable | không lọt Top-10 | trùng gold chunk với P002 nhưng câu hỏi không đủ từ khóa đặc trưng |
| P005 | answerable | không lọt Top-10 (hạng thật 27/156) | corpus lệch kích thước tài liệu; xem case study |
| P006 | unanswerable-trong-corpus | (không tính) | không có gold evidence trong corpus hiện tại, xem notes |
| P007 | answerable | 1 | Đúng ngay |
| P008 | answerable | 10 | lọt Top-10 ở vị trí cuối, không lọt Top-5 |
| P009 | unanswerable | (không tính) | kiểm tra hành vi từ chối, xem phần dưới |
| P010 | unanswerable | (không tính) | kiểm tra hành vi từ chối, xem phần dưới |

## Quan sát trên câu hỏi unanswerable (P006, P009, P010)

Với corpus và câu hỏi hiện tại, điểm BM25 Top-1 của các câu unanswerable dao động 13.2-20.1, **không
tách biệt rõ ràng** khỏi điểm Top-1 của một số câu answerable khó (ví dụ P003 có Top-1 = 14.33, thấp
hơn cả điểm Top-1 của P006 = 20.12). Vì vậy **chưa thể dùng một ngưỡng điểm số BM25 đơn giản để tự
động từ chối trả lời** ở mốc này - hệ thống hiện tại CHƯA có refusal guard đã hiệu chỉnh/kiểm thử,
đúng như phạm vi đã nêu trong báo cáo. Việc hiệu chỉnh ngưỡng (hoặc dùng tín hiệu khác, ví dụ điểm sau
rerank) là công việc dự kiến ở mốc kế tiếp.
