# Console PoC cho giai đoạn Retrieval — 07/10/2026

## Mục đích và phạm vi

Tạo một giao diện console nhỏ để có thể chạy truy vấn và quan sát các bước retrieval trên snapshot G0 đã có. Phần này hiện thực YC12 ở mức một ứng dụng truy xuất có thể chạy; chưa phải chatbot RAG hoàn chỉnh và không thay thế benchmark retrieval đã báo cáo riêng.

## Cách chạy

Mặc định mở chế độ tương tác bằng BM25 trên G0:

```powershell
python -m rag_hcmute.console_app
```

Một câu hỏi có thể truyền qua `--query`; nếu bỏ trống, nhập câu hỏi trong console và gõ `:q` để kết thúc. Chọn `--method dense` hoặc `--method hybrid` để dùng BGE-M3 + FAISS. Hai chế độ này bắt buộc truyền `--dense-model` là thư mục model local có sẵn. Console bật `HF_HUB_OFFLINE` và `TRANSFORMERS_OFFLINE`, nên không tự tải model. Có thể chọn `dense-rerank` hoặc `hybrid-rerank` để lấy candidate Top-20 rồi chạy cross-encoder; hai biến thể này cần cả `--dense-model` và `--reranker-model`.

Ví dụ dùng Hybrid:

```powershell
python -m rag_hcmute.console_app --method hybrid --dense-model 'D:\RAG\models\huggingface\hub\models--BAAI--bge-m3\snapshots\5617a9f61b028005a4858fdac845db406aefb181' --top-k 5
```

Ví dụ Hybrid RRF + reranker đã tải local:

```powershell
python -m rag_hcmute.console_app --method hybrid-rerank --dense-model '<duong-dan-snapshot-BGE-M3>' --reranker-model 'D:\RAG\models\huggingface\hub\models--BAAI--bge-reranker-v2-m3\snapshots\953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e' --query "Điều kiện để sinh viên được xét công nhận tốt nghiệp gồm những gì?" --top-k 5
```

Snapshot reranker được ghim ở revision `953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e`. Mặc định `max_length=512`, batch size 4; kết quả console nêu candidate count và số cặp bị cắt. Có thể thử `--reranker-max-length 1024` để so sánh vận hành, nhưng pilot development nhỏ chưa đủ căn cứ chọn cấu hình chất lượng chung.

## Kiểm tra thực tế

- Chạy one-shot trên G0 native-only với BM25 và câu P001 đã có trong pilot: tiến trình trả mã 0, hiển thị document/page/section và excerpt, không echo câu hỏi.
- Chạy smoke test tích hợp qua đúng lệnh `python -m rag_hcmute.console_app` với Hybrid RRF, BGE-M3 local và cùng file chunks: tiến trình trả mã 0, nhận đúng 156 chunks, hiển thị nguồn và excerpt; không echo câu hỏi.
- Chạy one-shot thật với `hybrid-rerank` trên G0 và hai model local đã duyệt: exit code 0, nạp 156 chunks, trả 5 hit; candidate pool đủ 20, reranker mất 909,14 ms và 14/20 cặp bị cắt ở `max_length=512`. Output được capture trong bộ nhớ; chỉ giữ lại các số kỹ thuật này, không lưu đoạn nguồn hoặc câu hỏi. Đây là smoke test đường chạy, không phải benchmark mới hay đánh giá chất lượng answer.
- Tích hợp hai tùy chọn `dense-rerank` và `hybrid-rerank`: wrapper giữ candidate depth 20, nạp snapshot reranker local đã ghim rồi xếp hạng lại. Console hiển thị tổng latency, thời gian retrieval/reranker và số cặp bị cắt; BM25 vẫn là mặc định.
- Lệnh `--help` ban đầu gặp lỗi code page Windows khi in tiếng Việt. Console hiện cấu hình stdout/stderr UTF-8 khi stream hỗ trợ; `python -m rag_hcmute.console_app --help` đã chạy thành công trong PowerShell.
- Output của các lượt được capture trong bộ nhớ để kiểm tra cấu trúc rồi bỏ đi; không lưu văn bản nguồn vào artifact, log hay tài liệu. Smoke test chỉ xác nhận lệnh chạy và metadata nguồn được hiển thị, không phải đo chất lượng retrieval hoặc generation.
- Kiểm thử tự động toàn repo: 83 passed. Riêng console có kiểm thử tạo BM25 từ chunks local, yêu cầu model local cho Dense/Hybrid, nhận diện các lựa chọn rerank, định dạng nguồn và truncation metadata, trường hợp không có hit, kích thước corpus và thứ tự gọi retrieval → reranking.

## Ý nghĩa và giới hạn

Kết quả mỗi hit gồm hạng, điểm của phương thức, tên văn bản, PDF page, section nếu có, chunk ID và excerpt ngắn. Đây là thông tin để xem retriever đưa đoạn nào lên và truy ngược về nguồn.

Console chưa sinh câu trả lời, chưa có ngưỡng từ chối đã hiệu chỉnh và chưa xác minh citation gắn với một câu trả lời. Trường hợp retriever trả về ứng viên không chứng minh câu hỏi có thể trả lời; trường hợp không có hit cũng chưa phải một refusal được đánh giá. RRF và reranking vẫn là phương án thử nghiệm, không phải mặc định của ứng dụng. Không gọi Gemini/Ollama, không phát sinh phí API và không tải thêm package/model.

## Mã nguồn liên quan

- Console: [`src/rag_hcmute/console_app.py`](../../src/rag_hcmute/console_app.py)
- Retrieval: [`src/rag_hcmute/retrieval/`](../../src/rag_hcmute/retrieval/)
- Reranker wrapper: [`src/rag_hcmute/retrieval/reranked.py`](../../src/rag_hcmute/retrieval/reranked.py)
- Unit test: [`tests/test_console_app.py`](../../tests/test_console_app.py)
- Kết quả so sánh retrieval: [`HYBRID_RRF_ABLATION_20261007.md`](HYBRID_RRF_ABLATION_20261007.md)
