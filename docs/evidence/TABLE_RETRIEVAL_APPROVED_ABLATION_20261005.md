# Ablation truy xuất Bảng 5 với bộ câu hỏi đã duyệt — 05/10/2026

## Phạm vi

Đây là phép thử retrieval cho năm câu hỏi về Bảng 5 của Quyết định 1727/QĐ-ĐHSPKT năm 2021, không phải benchmark toàn hệ thống RAG. Câu hỏi, đáp án chấp nhận và các hàng bằng chứng đã được duyệt riêng cho phép ablation này; chúng chưa được nhập vào `pilot_questions.csv`. Phạm vi nguồn được giới hạn ở snapshot hiện có, không khẳng định QĐ 1727/2021 còn hiệu lực hiện hành.

PDF nguồn `HCMUTE_QCDT_1727_2021.pdf` có SHA-256 `71ed777e083b5b7be50e129f13dd714553fb8c53aead59d17db92f26b507eaaa`, khớp manifest. Bảng 5 ở PDF page 20 (printed page 19) ghi các khoảng `< 36`, `36–71`, `72–107`, `108–149` và `>149`. QĐ 3116/2025 chưa có trong thư mục nguồn bổ sung tại thời điểm chạy, nên kết quả chỉ áp dụng cho tài liệu 1727/2021 trong corpus.

## Thiết kế và cách chạy

- Bộ câu hỏi đã duyệt: [`table_questions_reviewed_ablation_20261005.csv`](../../data/question_sets/table_questions_reviewed_ablation_20261005.csv).
- Gold evidence theo từng biểu diễn: [`table_question_variant_evidence_20261005.csv`](../../data/question_sets/table_question_variant_evidence_20261005.csv). TB005 yêu cầu cả hai hàng năm thứ hai và năm thứ ba khi dùng T2.
- Corpus B0/T1/T2 dùng cùng 155 chunk nền; chỉ thay biểu diễn nội dung Bảng 5 trong chunk B0 chứa bảng. Kích thước lần lượt là 156, 157 và 161 chunk.
- Snapshot văn bản nền: `5da3bd4d5de54492`. Retrieval: BM25Okapi và Dense BGE-M3 + FAISS, `top_k=5`. Dense chạy bằng CUDA trên model snapshot local; không gọi API và không tải dữ liệu.
- Mã chạy: [`evaluate_table_ablation.py`](../../scripts/evaluate_table_ablation.py). Lượt đã thực hiện:

```powershell
python scripts/evaluate_table_ablation.py --method both `
  --dense-model 'D:\RAG\models\huggingface\hub\models--BAAI--bge-m3\snapshots\5617a9f61b028005a4858fdac845db406aefb181'
```

- Kết quả thô, Git-ignored: `artifacts/results/table_retrieval_ablation/table_ablation_both_20261005T114541Z.json`.
- Commit code/câu hỏi/evidence của lượt chạy: `2745cb6a3a2964ea8038cf2e22fe2b53241cc66d`.

## Kết quả

| Retriever | Biểu diễn | Đủ toàn bộ evidence trong Top-5 | Coverage đơn vị evidence | MRR của evidence đầu tiên @5 |
|---|---|---:|---:|---:|
| BM25 | B0 | 4/5 (0,80) | 0,80 | 0,550 |
| BM25 | T1 | 1/5 (0,20) | 0,20 | 0,100 |
| BM25 | T2 | 0/5 (0,00) | 0,00 | 0,000 |
| Dense | B0 | 5/5 (1,00) | 1,00 | 0,600 |
| Dense | T1 | 5/5 (1,00) | 1,00 | 1,000 |
| Dense | T2 | 5/5 (1,00) | 1,00 | 0,867 |

**Diễn biến chính:** Dense đưa chunk bảng T1 lên hạng 1 cho cả năm câu. Với T2, các hàng đích xếp hạng lần lượt #3, #1, #1, #1; riêng TB005 cần hai hàng và cả hai nằm trong Top-2. Với BM25, chunk đích có mặt trong Top-5 ở 4/5 câu trên B0, 1/5 trên T1 và 0/5 trên T2.

## Cách diễn giải và giới hạn

- `Đủ toàn bộ evidence trong Top-5` là tỷ lệ câu có tất cả chunk bắt buộc ở Top-5. Chỉ số này đặc biệt quan trọng với TB005: truy xuất được một trong hai hàng T2 chưa đủ để trả lời đầy đủ.
- `Coverage đơn vị evidence` là trung bình tỷ lệ chunk bắt buộc được tìm thấy trên mỗi câu. Do một chunk B0/T1 có thể chứa cả bảng trong khi T2 tách theo hàng, không diễn giải nó như so sánh trực tiếp cùng số lượng chunk giữa các cách biểu diễn.
- `MRR của evidence đầu tiên @5` đo vị trí của bằng chứng bắt buộc đầu tiên; nó không bảo đảm đã tìm thấy toàn bộ bằng chứng. Vì vậy phải đọc cùng chỉ số đầy đủ evidence.
- Trên đúng năm câu này, Dense có thứ hạng tốt hơn BM25 với T1/T2. Đây là dấu hiệu có ích để tiếp tục khảo sát, không đủ để kết luận T1/T2 nói chung tốt hơn, thay cấu hình mặc định, hay khẳng định Dense thắng trên corpus khác. Kết quả BM25 cho thấy các câu đang dùng chưa khớp từ vựng tốt với chunk hàng T2; cần kiểm tra thêm tác động của cách hỏi, metadata và xử lý truy vấn.
- Đây chỉ đánh giá retrieval. Chưa đo câu trả lời do LLM sinh, tính đúng của citation, khả năng từ chối, latency end-to-end hoặc chi phí.
- Năm câu là mẫu nhỏ, chỉ dành cho ablation bảng. Không gộp vào bộ pilot chung; chưa dùng để báo cáo như benchmark tổng quát. Chưa thay đổi pipeline mặc định.

## Bước tiếp theo

Mở rộng bộ câu hỏi bảng theo nhiều dạng truy vấn tự nhiên và thêm các trường hợp bảng khác trước khi kết luận về phương pháp. Nếu nhận được QĐ 3116/2025, phải xác minh hash, hiệu lực và tạo snapshot riêng; không trộn nhãn của hai phiên bản quy chế. Sau khi hoàn thiện minh chứng mốc 1, mới cập nhật một bản DOCX mới theo định dạng báo cáo đã thống nhất.
