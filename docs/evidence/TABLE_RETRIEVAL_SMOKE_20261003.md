# Thăm dò truy xuất câu hỏi bảng — 03/10/2026

## Phạm vi

Đây là smoke test định tính cho năm câu hỏi TB001–TB005 đang ở trạng thái nháp, nhằm kiểm tra lệnh truy xuất có trả về các chunk được đề xuất trong mapping B0/T1/T2 hay không. Phép chạy chỉ dùng BM25; không sinh câu trả lời, không tính metric tổng hợp và không đưa câu hỏi vào pilot.

## Cấu hình và tái lập

- Corpus baseline: snapshot G0 `5da3bd4d5de54492`, 156 chunks.
- B0: chunks G0 hiện có; T1: một chunk Markdown chứa toàn Bảng 5; T2: năm chunk theo hàng.
- BM25: `rank_bm25.BM25Okapi`, top-k = 5.
- Lệnh: `python scripts/smoke_table_candidate_retrieval.py --method both --top-k 5` trong môi trường `rag-hcmute`, với `HF_HUB_OFFLINE=1`.
- Script mặc định giữ Hugging Face offline khi chạy Dense; chỉ truy cập mạng nếu được gọi rõ ràng với `--allow-model-download`.
- Kết quả máy cục bộ (Git-ignored): `artifacts/results/table_retrieval_smoke/table_candidates_both_20261003T090313Z.json`.

## Thứ hạng chunk đích được đề xuất

| Câu nháp | B0 | T1 | T2 |
|---|---:|---:|---:|
| TB001 — tra khoảng có 85 tín chỉ | #1 | #1 | hàng 3: #2 |
| TB002 — ngưỡng của năm thứ hai | #1 | #1 | hàng 2: #1 |
| TB003 — khoảng của năm thứ tư | #1 | #1 | hàng 4: #1 |
| TB004 — mức tín chỉ của năm thứ năm | #1 | #1 | hàng 5: #5 |
| TB005 — ranh giới năm thứ hai và thứ ba | #2 | #1 | hàng 2: #1; hàng 3: #2 |

Các vị trí là thứ hạng của chunk được đề xuất trong mapping nháp, không phải nhãn gold đã duyệt. Kết quả cho thấy BM25 có thể tìm thấy các chunk mục tiêu trong top-5 cho cả năm truy vấn ở ba biến thể trong lượt chạy này. Không thể kết luận T1 tốt hơn B0 hoặc T2: số lượng chunk giữa các biến thể rất khác nhau (156, 1 và 5), và câu hỏi/nhãn tham chiếu chưa được người học xác nhận. Riêng T1 chỉ có một chunk nên hạng #1 là hệ quả của kích thước tập ứng viên, không phải bằng chứng về chất lượng vượt trội.

## Giới hạn và trạng thái Dense

Dense BGE-M3 chưa chạy được trong lượt này. Để tránh phát sinh tải mạng ngoài dự kiến, smoke test được chạy với Hugging Face offline; môi trường Python `rag-hcmute` không tìm thấy model trong cache cục bộ. Vì vậy không có kết quả Dense để đối chiếu, không có phép so sánh BM25–Dense và không phát sinh API call.

Kết quả hiện tại chỉ dùng để rà lệnh và phát hiện điểm cần xem lại (TB001 và TB004 có chunk T2 ở hạng thấp hơn). Bước tiếp theo là người học xác nhận câu hỏi, câu trả lời chấp nhận được và vị trí hàng/cột trên PDF; sau đó mới khóa gold annotation và chạy ablation có metric. Trước khi chạy Dense, cần xác định cache BGE-M3 hiện có hoặc chuẩn bị tải trọng số vào đúng môi trường.
