# Thử nghiệm generation và refusal cục bộ trên development pilot

Ngày chạy: 08/10/2026. Mục tiêu là kiểm tra đường đi từ retrieval tới câu trả lời trên console, không phải chứng nhận chất lượng câu trả lời hoặc đóng YC11.

## Cấu hình

- Snapshot G0 `5da3bd4d5de54492`: 3 tài liệu, 182 trang, 156 chunk. Đây là snapshot cố định dùng cho so sánh lịch sử, không phải kho quy chế hiện hành đã cập nhật.
- Partition: `development`, 10 câu đã duyệt (7 answerable, 3 unanswerable); không có holdout.
- Retriever: Hybrid RRF với candidate Top-20 mỗi nhánh, sau đó BGE-Reranker-v2-m3, trả Top-5 cho generation. BGE-M3 và reranker dùng snapshot local đã ghim.
- Generator: Ollama 0.40.0, `qwen3:4b`, chạy qua `127.0.0.1` trên máy. Digest model nhìn thấy trong `/api/tags`: `359d7dd4bcda3b86b87d73ac27966f4dbb9f5efdfcc75d34a8764a09474fae7`. Không dùng Gemini, cloud API hoặc API tính phí.
- Prompt chỉ cho phép trả lời từ nguồn được cung cấp, coi văn bản nguồn là dữ liệu chứ không phải chỉ dẫn, yêu cầu trích citation ID và từ chối khi thiếu căn cứ. Bộ kiểm tra chỉ xác nhận JSON/citation ID có thuộc các chunk đã truy xuất; không xác nhận citation có entail khẳng định trong câu trả lời.

## Kết quả trên 10 câu

| Chỉ số vận hành | Kết quả | Cách đọc |
|---|---:|---|
| Answerable được mô hình trả lời | 7/7 | Độ bao phủ câu trả lời trên development, không phải độ đúng nội dung |
| Câu unanswerable bị từ chối | 1/3 | Refusal chưa đạt; 2/3 câu thiếu căn cứ vẫn được trả lời |
| Câu answerable có citation tới đúng loại tài liệu kỳ vọng | 7/7 | Chỉ so khớp document ID; không kiểm chứng đoạn trích hỗ trợ từng claim |
| Citation ID hợp lệ trong các câu đã sinh | 9/9 | Citation thuộc danh sách Top-5 đã đưa cho model; không đồng nghĩa citation đúng ngữ nghĩa |
| Median retrieval + rerank | 2.246 giây/câu | Trung vị tính trên cả 10 record trong raw run; local, có thời gian khởi tạo model trong phiên |
| Median generation | 7.837 giây/câu | Trung vị tính trên cả 10 record trong raw run; Ollama local, phụ thuộc máy và độ dài câu trả lời |

Kết quả cho thấy đường tích hợp có thể chạy cục bộ và tạo citation ID theo nguồn đã truy xuất, nhưng từ chối chưa đáng tin. Lượt duy nhất được ghi là abstain có output JSON không hợp lệ; do đó tỷ lệ 1/3 không được diễn giải là một từ chối được diễn đạt thành công theo chính sách. Hai câu unanswerable còn lại vẫn có nội dung được sinh. Không dùng các tỷ lệ này để khẳng định RAG trả lời đúng hay chống hallucination. Câu trả lời, truy vấn, excerpt và nội dung PDF không được lưu trong JSON; raw result metrics-only Git-ignored tại `artifacts/results/generation_pilot/generation_hybrid-rerank_5da3bd4d5de54492_20261008T124010Z.json`.

## Vì sao chưa đặt ngưỡng từ chối

Trong cùng development set, điểm top-1 của reranker ở các câu answerable trải từ 1,84 đến 6,41; ba câu unanswerable trải từ -3,92 đến 2,41. Hai nhóm chồng lấn: một câu answerable có điểm 2,44, còn câu unanswerable về cùng nhóm văn bản có điểm 2,41. Một ngưỡng đủ cao để chặn câu thiếu căn cứ cũng sẽ làm rơi một số câu answerable có điểm thấp. Đây là quan sát trên 10 câu, không phải hiệu chỉnh tổng quát; vì chưa có holdout, không chọn ngưỡng từ chối dựa trên lượt này.

## Giới hạn và bước còn lại

- Bộ đánh giá là development pilot; chưa có holdout độc lập.
- Chưa có đánh giá thủ công đầy đủ về answer correctness, faithfulness, relevance hay mức hỗ trợ ngữ nghĩa của citation. Ragas/TruLens hoặc LLM-as-a-judge chưa chạy; Gemini không được gọi vì ngân sách API vẫn là 0 USD nếu chưa có phê duyệt ước tính.
- Refusal rate 1/3 trên unanswerable chỉ là kết quả quan sát và cho thấy vấn đề còn tồn tại, không phải mục tiêu đạt được.
- Corpus dùng QĐ 1727/2021 theo snapshot G0. QĐ 3116/2025 đã tìm được ngoài repo nhưng OCR chưa được kiểm tra thủ công đủ để dùng làm nguồn trả lời. Không dùng app hiện tại như tư vấn quy định hiện hành.
- Latency là một lần chạy đơn trên máy cá nhân, không phải SLA; retrieval/rerank/GPU và Ollama có thể tranh chấp tài nguyên.

## Tái lập

```powershell
& 'C:\Users\Dell\anaconda3\envs\rag-hcmute\python.exe' scripts/run_generation_pilot.py `
  --method hybrid-rerank `
  --dense-model 'D:\RAG\models\huggingface\hub\models--BAAI--bge-m3\snapshots\5617a9f61b028005a4858fdac845db406aefb181' `
  --reranker-model 'D:\RAG\models\huggingface\hub\models--BAAI--bge-reranker-v2-m3\snapshots\953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e' `
  --partition development --top-k 5
```

Runner chỉ serialize mã câu hỏi, nhãn, trạng thái abstain, số citation, citation ID validity, document-level overlap và latency; không lưu câu trả lời hoặc text nguồn.
