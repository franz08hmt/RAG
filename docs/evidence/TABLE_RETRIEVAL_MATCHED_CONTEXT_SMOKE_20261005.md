# Thăm dò truy xuất bảng với corpus nền tương đương — 05/10/2026

> Lượt này dùng câu hỏi và mapping khi chúng còn ở trạng thái nháp. Kết quả thay thế với bộ câu hỏi/evidence đã được duyệt được ghi tại [`TABLE_RETRIEVAL_APPROVED_ABLATION_20261005.md`](TABLE_RETRIEVAL_APPROVED_ABLATION_20261005.md).

## Vì sao cần lượt chạy này

Lượt table-only ban đầu so B0 trên 156 chunk với T1 trên 1 chunk và T2 trên 5 chunk. Vì tập ứng viên khác kích thước, thứ hạng đó không phải so sánh retrieval công bằng. Lượt này giữ cùng phần nền corpus và chỉ thay cách biểu diễn Bảng 5 trong chunk B0 chứa bảng.

## Thiết kế corpus

- **B0:** snapshot G0 nguyên trạng, 156 chunk; bằng chứng bảng nằm trong chunk `HCMUTE_QCDT_1727_2021__c0031`.
- **T1:** từ chunk `c0031`, giữ lại phần ngữ cảnh và các nội dung trước Bảng 5 thành một chunk phần dư; thay riêng nội dung Bảng 5 bằng chunk Markdown T1. Giữ nguyên 155 chunk còn lại, tổng 157 chunk.
- **T2:** dùng cùng chunk phần dư và thay nội dung Bảng 5 bằng năm chunk theo hàng T2. Giữ nguyên 155 chunk còn lại, tổng 161 chunk.

Chunk `c0031` có phần nội dung trước Bảng 5 ngoài dữ liệu bảng; vì vậy không loại bỏ cả chunk khi tạo T1/T2. Chênh lệch 157/161 là do biểu diễn bảng tạo một hoặc năm chunk, không phải do thay corpus nền. Lượt này là smoke test thiết kế; chưa tính metric và không thay đổi pipeline mặc định.

## Cấu hình và tái lập

- Snapshot G0: `5da3bd4d5de54492`; top-k = 5.
- BM25: `rank_bm25.BM25Okapi`.
- Dense: BGE-M3 + FAISS, L2 normalization, model snapshot `5617a9f61b028005a4858fdac845db406aefb181`, chạy CUDA. Đọc từ local snapshot; không tải lại và không gọi API.
- Lệnh trong môi trường `rag-hcmute`:

```powershell
python scripts/smoke_table_candidate_retrieval.py --method both --top-k 5 `
  --dense-model 'D:\RAG\models\huggingface\hub\models--BAAI--bge-m3\snapshots\5617a9f61b028005a4858fdac845db406aefb181'
```

- Kết quả máy cục bộ, Git-ignored: `artifacts/results/table_retrieval_smoke/table_candidates_matched_both_20261005T112441Z.json`.

## Thứ hạng chunk đích đề xuất

Thứ hạng theo `BM25 / Dense`; ô T2 ghi riêng hàng cần bằng chứng. “Ngoài top-5” chỉ có nghĩa chunk đích không xuất hiện trong năm kết quả đầu của lượt thăm dò này.

| Câu nháp | B0 (156) | T1 (157) | T2 (161) |
|---|---:|---:|---:|
| TB001 — 85 tín chỉ thuộc năm nào? | #1 / #1 | #3 / #1 | hàng 3: ngoài top-5 / #4 |
| TB002 — khoảng của năm thứ hai | #1 / #1 | #3 / #1 | hàng 2: #4 / #1 |
| TB003 — khoảng của năm thứ tư | #1 / #4 | ngoài top-5 / #1 | hàng 4: ngoài top-5 / #1 |
| TB004 — mức tín chỉ của năm thứ năm | #1 / #1 | #4 / #1 | hàng 5: #4 / #1 |
| TB005 — ranh giới năm thứ hai/thứ ba | #2 / #1 | #2 / #1 | hàng 2: ngoài top-5 / #1; hàng 3: ngoài top-5 / #2 |

## Đọc kết quả thận trọng

- B0 tìm chunk tổng hợp c0031 rất cao; chunk này chứa cả Bảng 5 lẫn các đoạn khác của Điều 12. Hạng chunk không chứng minh hệ thống đã trích đúng hàng.
- T1 đứng #1 với Dense ở cả năm truy vấn trong mẫu thăm dò này. BM25 xếp T1 từ #2 đến #4 ở bốn truy vấn và không đưa chunk vào top-5 ở TB003. Đây là dấu hiệu đáng kiểm tra tiếp, không phải kết luận T1 thắng.
- T2 cho thấy khác biệt giữa hai retriever: Dense đưa hàng đích của TB002–TB005 vào top-2, nhưng hàng TB001 ở hạng #4; BM25 không đưa một số hàng đích vào top-5. Câu TB001 cần suy luận 85 thuộc khoảng 72–107, trong khi con số 85 không xuất hiện trong một hàng dữ liệu cụ thể.
- Mẫu chỉ có năm câu nháp; câu chữ, đáp án và evidence chưa được người học duyệt. Không tính Hit@k/Recall@k/MRR hoặc aggregate metric, không dùng kết quả để chọn phương án.

## Việc cần chốt trước benchmark

Người học cần xác nhận hoặc viết lại câu hỏi và đáp án chấp nhận trong [`table_question_review_proposals_20261003.csv`](../../data/question_sets/table_question_review_proposals_20261003.csv). Sau đó mới khóa evidence hàng/cột, chạy benchmark và phân tích lỗi theo nhãn đã xác nhận.
