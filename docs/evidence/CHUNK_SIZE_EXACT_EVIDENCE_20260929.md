# Đánh giá kích thước chunk bằng nhãn đoạn bằng chứng

## Mục tiêu và phạm vi

Lượt thử trước dùng `section_path` hoặc trang PDF làm proxy cho gold chunk. Cách đó hữu ích để khảo sát sơ bộ nhưng một chunk cùng Điều/trang chưa chắc chứa đúng đoạn trả lời. Lượt này gắn nhãn bằng khoảng token cụ thể trên trang nguồn để so sánh chunking theo khả năng đưa đủ bằng chứng vào Top-k.

Thử nghiệm dùng snapshot native-only G0 `5da3bd4d5de54492`, corpus HCMUTE hiện tại và các cấu hình 250/40, 500/80, 750/120. Không bật OCR, không thay cấu hình mặc định, không chạy generation và không gọi API ngoài.

## Cách tạo nhãn

Chunker ghi thêm `token_start`/`token_end`: khoảng nửa mở `[start, end)` theo đơn vị whitespace-token trên luồng văn bản đã làm sạch của từng tài liệu. Offset trong nhãn là token tương đối trên một trang PDF; khi đọc, chương trình cộng offset các trang trước để chuyển sang tọa độ tài liệu. Nhờ vậy cùng một đoạn nguồn giữ nguyên vị trí khi thay kích thước chunk.

Năm span ban đầu được đối chiếu với những mảnh trích dẫn đã có trong pilot. Các span còn lại được xác định theo ranh giới điều/khoản trong chính PDF nguồn, phù hợp với yêu cầu của từng câu hỏi. Sidecar `data/question_sets/pilot_evidence_annotations.json` chỉ lưu ID, mô tả điều/khoản, trang, offset và SHA-256 đã chuẩn hóa; không lưu văn bản nguồn. Mỗi lần chạy, mã kiểm tra đúng snapshot, đủ câu answerable và hash của từng span; sai lệch khiến chương trình dừng.

| Phạm vi pilot | Số lượng | Cách xử lý |
|---|---:|---|
| Câu answerable có gold trong pilot | 7 | P001–P005, P007–P008 |
| Câu có nhãn exact-source-span | 7 | Đủ toàn bộ câu answerable hiện có |
| Span bằng chứng | 10 | Câu đơn giản có một span; câu cần hai chế độ/quy định có hai span |
| Câu unanswerable | 3 | Không dùng tính retrieval evidence recall |

Hai câu về cảnh báo và buộc thôi học có span riêng cho quy định theo tín chỉ và theo niên chế. P004 dùng cả mục đăng ký học lại; P007 cần bằng chứng ở PDF page 23 và 24, trong khi trường `evidence_page` cũ chỉ ghi `23`. CSV gốc không bị sửa; sidecar mới lưu đúng hai trang.

## Metric

- **Evidence-span Recall@5:** số span gold được bao phủ trọn vẹn bởi ít nhất một chunk trong Top-5, chia cho tổng số span (10). Mỗi span được tính một lần.
- **Complete-evidence Hit@5:** số câu có đủ mọi span bắt buộc trong Top-5, chia cho bảy câu được gắn nhãn.
- **First-evidence MRR@10:** thứ hạng đầu tiên của một span gold cho mỗi câu; là metric bổ sung, không thay cho việc tìm đủ bằng chứng.

Đây là retrieval evaluation, không đánh giá độ đúng câu trả lời do LLM tạo. Pilot còn nhỏ nên mọi tỷ lệ đều mang tính phát triển, không phải benchmark tổng quát.

## Kết quả

| Retriever | Chunk / overlap | Tổng chunk | Evidence-span Recall@5 | Complete-evidence Hit@5 | First-evidence MRR@10 |
|---|---:|---:|---:|---:|---:|
| BM25 | 250 / 40 | 297 | 5/10 (0,500) | 3/7 (0,429) | 0,348 |
| BM25 | 500 / 80 | 156 | 4/10 (0,400) | 3/7 (0,429) | 0,371 |
| BM25 | 750 / 120 | 111 | 4/10 (0,400) | 3/7 (0,429) | 0,372 |
| Dense BGE-M3 | 250 / 40 | 297 | 10/10 (1,000) | 7/7 (1,000) | 0,814 |
| Dense BGE-M3 | 500 / 80 | 156 | 9/10 (0,900) | 6/7 (0,857) | 0,762 |
| Dense BGE-M3 | 750 / 120 | 111 | 9/10 (0,900) | 6/7 (0,857) | 0,719 |

Dense dùng BGE-M3 local, revision `5617a9f61b028005a4858fdac845db406aefb181`, FAISS `IndexFlatIP`, `max_seq_length=1024`, chạy trên CUDA. Số chunk vượt giới hạn encoder lần lượt là 0/297, 4/156 và 20/111. Transformers có cảnh báo với một số chuỗi dài hơn giới hạn; không tăng giới hạn trong lượt này.

## Nhận xét

- Nhãn exact evidence phân biệt các cấu hình rõ hơn proxy section/page. BM25 bỏ lỡ span cảnh báo học tập ở cả ba cấu hình và còn bỏ lỡ nhiều span khác; Dense tìm đủ mọi span ở 250/40.
- Ở 500/80 và 750/120, Dense bỏ lỡ một span thuộc câu P008 trong Top-5 (span đó ở hạng 7). Các câu còn lại đủ bằng chứng. Kết quả này phù hợp với việc chunk lớn hơn và việc encoder bị giới hạn 1.024 subword, nhưng không thể tách riêng tác động của từng yếu tố trong lượt thử này.
- 250/40 là cấu hình đáng giữ lại để thử tiếp: trong pilot này Dense không bị truncation và đạt 7/7 câu đủ bằng chứng. Tuy nhiên, cấu hình đó tạo 297 chunk, gần gấp đôi 500/80; chưa đo latency/reranking cost, và bộ câu hỏi quá nhỏ để đổi default.
- Vì vậy giữ nguyên 500/80 làm cấu hình mặc định hiện tại. Cần tăng bộ câu hỏi do người học tự kiểm chứng, đo latency/chi phí và bổ sung bài thử retrieval khác trước khi kết luận.

Các lần chạy annotation version 1 (4 câu/5 span) là lượt thử sơ bộ và đã được thay bằng kết quả version 2 bên trên. Raw output version 2 nằm trong `artifacts/results/chunking_ablation/` (Git-ignored); mỗi JSON chỉ ghi metric, question ID, offset/hash và cấu hình, không ghi câu hỏi hay nội dung chunk.

## Tái lập

Chạy bằng Python 3.11 trong env dự án; script in interpreter khi bắt đầu. `snapshot_id` và hash trong sidecar được kiểm tra trước khi chạy.

```powershell
$py = 'C:\Users\Dell\anaconda3\envs\rag-hcmute\python.exe'
& $py scripts/run_chunking_ablation.py --method bm25

$env:HF_HUB_OFFLINE = '1'
$env:TRANSFORMERS_OFFLINE = '1'
$model = 'D:\RAG\models\huggingface\hub\models--BAAI--bge-m3\snapshots\5617a9f61b028005a4858fdac845db406aefb181'
& $py scripts/run_chunking_ablation.py --method dense --dense-model $model
```
