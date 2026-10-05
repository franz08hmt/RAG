# Thăm dò truy xuất câu hỏi bảng — 05/10/2026

## Phạm vi

Đây là lượt chạy thăm dò tiếp nối smoke test ngày 03/10. Năm câu TB001–TB005 và mapping chunk vẫn đang là bản nháp; mục tiêu chỉ là xem thứ hạng các chunk được đề xuất ở B0/T1/T2, không đánh giá câu trả lời do LLM sinh và không tính metric tổng hợp.

## Cấu hình và tái lập

- Corpus baseline: snapshot G0 `5da3bd4d5de54492`, 156 chunks.
- B0: chunks G0; T1: một chunk Markdown chứa toàn Bảng 5; T2: năm chunk theo hàng.
- Top-k = 5; BM25 dùng `BM25Okapi`; Dense dùng BGE-M3 + FAISS với L2-normalized embeddings, chạy trên `cuda:0`.
- BGE-M3 được đọc trực tiếp từ snapshot local `5617a9f61b028005a4858fdac845db406aefb181` trong `D:\RAG\models\huggingface`; không tải lại model và không gọi API.
- Lệnh đã chạy trong môi trường `rag-hcmute`:

```powershell
python scripts/smoke_table_candidate_retrieval.py --method both --top-k 5 `
  --dense-model 'D:\RAG\models\huggingface\hub\models--BAAI--bge-m3\snapshots\5617a9f61b028005a4858fdac845db406aefb181'
```

- Kết quả máy cục bộ (Git-ignored): `artifacts/results/table_retrieval_smoke/table_candidates_both_20261005T111133Z.json`.

## Thứ hạng chunk đích được đề xuất

`BM25 / Dense`; với T2 ghi riêng thứ hạng của từng hàng đích.

| Câu nháp | B0 (156 chunks) | T1 (1 chunk) | T2 (5 hàng) |
|---|---:|---:|---:|
| TB001 — 85 tín chỉ thuộc năm nào? | #1 / #1 | #1 / #1 | hàng 3: #2 / #4 |
| TB002 — khoảng của năm thứ hai | #1 / #1 | #1 / #1 | hàng 2: #1 / #1 |
| TB003 — khoảng của năm thứ tư | #1 / #4 | #1 / #1 | hàng 4: #1 / #1 |
| TB004 — mức tín chỉ của năm thứ năm | #1 / #1 | #1 / #1 | hàng 5: #5 / #1 |
| TB005 — ranh giới năm thứ hai/thứ ba | #2 / #1 | #1 / #1 | hàng 2: #1 / #1; hàng 3: #2 / #2 |

## Nhận xét có giới hạn

- B0 ánh xạ cả năm câu vào cùng chunk chứa toàn bảng (`c0031`), nên thứ hạng của chunk này chưa cho biết retriever có khoanh đúng hàng hay không.
- T1 chỉ có một chunk; vì vậy hạng #1 là hệ quả của tập ứng viên chỉ có một phần tử, không phải bằng chứng T1 tốt hơn.
- Ở T2, hàng đích của TB001 đứng #2 với BM25 và #4 với Dense; hàng đích TB004 đứng #5 với BM25 nhưng #1 với Dense. Đây là những ví dụ hữu ích để xem lại cách hỏi và cách biểu diễn dữ liệu, không phải kết luận về mô hình.
- Các câu hỏi, đáp án và vị trí gold chưa được người học duyệt. Không báo Recall@k/MRR, không xếp hạng phương án theo điểm tổng hợp và không dùng kết quả này để khẳng định biến thể nào tốt hơn.

## Bước kế tiếp

Người học xác nhận hoặc viết lại câu hỏi; xác nhận đáp án chấp nhận và hàng/cột nguồn trong [`table_question_review_proposals_20261003.csv`](../../data/question_sets/table_question_review_proposals_20261003.csv). Sau khi các nhãn đó được duyệt, mới chạy ablation có metric và quyết định có đưa T1/T2 vào pipeline hay không.
