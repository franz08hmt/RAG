# Đánh giá kích thước chunk bằng nhãn đoạn bằng chứng

## Mục tiêu

Lượt thử trước dùng `section_path` hoặc trang PDF làm proxy cho gold chunk. Cách đó hữu ích để khảo sát sơ bộ nhưng có thể tính một chunk là liên quan dù chunk chỉ nằm trong cùng Điều/trang, chưa chứa đúng đoạn trả lời. Lượt này bổ sung tọa độ token nguồn để so sánh chunking theo khả năng đưa đúng đoạn bằng chứng vào Top-k.

Thử nghiệm chỉ dùng snapshot native-only G0 `5da3bd4d5de54492`, corpus HCMUTE hiện tại và ba cấu hình 250/40, 500/80, 750/120. Không bật OCR, không thay cấu hình mặc định, không chạy generation và không gọi API ngoài.

## Xây dựng nhãn bằng chứng

Chunker hiện ghi thêm `token_start`/`token_end`: khoảng nửa mở `[start, end)` theo đơn vị whitespace-token trên luồng văn bản đã làm sạch của từng tài liệu. Tọa độ này không đổi khi thay kích thước chunk, nên có thể xác định đoạn gold nào được một chunk bao phủ mà không dựa vào tên chunk đã thay đổi.

Các span được ánh xạ từ những mảnh trích dẫn đã có trong `pilot_questions.csv:evidence_text`. Script chuẩn hóa Unicode và chữ hoa/thường, tìm chuỗi từ khớp chính xác trên đúng trang PDF đã chọn, rồi chuyển vị trí thành offset token. Trước khi tính metric, chương trình dừng nếu không tìm được đúng một vị trí khớp hoặc cấu hình chunk không có chunk nào chứa trọn span. Sidecar `data/question_sets/pilot_evidence_annotations.json` chỉ ghi mã câu, chỉ số mảnh trích dẫn, document ID, trang PDF và tình trạng cần rà soát; không chép văn bản nguồn.

| Phạm vi pilot | Số lượng | Cách xử lý |
|---|---:|---|
| Câu answerable trong pilot hiện có | 7 | Là tập ứng viên ban đầu |
| Câu có span khớp chính xác để dùng ở lượt này | 4 | P001, P002, P005, P007 |
| Span bằng chứng đã định vị | 5 | Một span cho P001/P002/P005; hai span cho P007 |
| Chờ rà soát nhãn nguồn | 3 | P003, P004, P008 bị loại khỏi metric exact-evidence; không tự suy diễn vị trí |
| Câu unanswerable | 3 | Không dùng để tính retrieval evidence recall |

Đối chiếu nguồn cho thấy P007 cần hai đoạn trên PDF page 23 và 24. Trường `evidence_page` trong CSV hiện chỉ ghi `23`; sidecar mới giữ riêng hai trang đã khớp mà không sửa lịch sử CSV.

## Metric

- **Evidence-span Recall@5:** số span gold được bao phủ trọn vẹn bởi ít nhất một chunk trong Top-5, chia cho tổng số span gold (5). Mỗi span chỉ được tính một lần.
- **Complete-evidence Hit@5:** số câu có đủ tất cả span bắt buộc trong Top-5, chia cho số câu được gắn nhãn exact ở lượt này (4).
- **First-evidence MRR@10:** thứ hạng đầu tiên của một span gold cho mỗi câu; chỉ số bổ sung, không thay thế complete-evidence Hit.

Đây là phép đo truy xuất bằng chứng, chưa đánh giá chất lượng câu trả lời do LLM tạo. Các tỷ lệ trên bộ bốn câu được gắn nhãn chỉ nên xem là kết quả phát triển.

## Kết quả

| Retriever | Chunk / overlap | Tổng chunk | Evidence-span Recall@5 | Complete-evidence Hit@5 | First-evidence MRR@10 |
|---|---:|---:|---:|---:|---:|
| BM25 | 250 / 40 | 297 | 3/5 (0,600) | 2/4 (0,500) | 0,500 |
| BM25 | 500 / 80 | 156 | 4/5 (0,800) | 3/4 (0,750) | 0,625 |
| BM25 | 750 / 120 | 111 | 4/5 (0,800) | 3/4 (0,750) | 0,583 |
| Dense BGE-M3 | 250 / 40 | 297 | 5/5 (1,000) | 4/4 (1,000) | 0,875 |
| Dense BGE-M3 | 500 / 80 | 156 | 5/5 (1,000) | 4/4 (1,000) | 0,833 |
| Dense BGE-M3 | 750 / 120 | 111 | 5/5 (1,000) | 4/4 (1,000) | 0,833 |

Dense chạy bằng BGE-M3 local, revision `5617a9f61b028005a4858fdac845db406aefb181`, FAISS `IndexFlatIP`, `max_seq_length=1024`, CUDA khả dụng. Profile độ dài subword và nguy cơ truncation giữ nguyên như lượt trước: lần lượt 0/297, 4/156 và 20/111 chunk vượt giới hạn. Cảnh báo Transformers với chuỗi dài hơn giới hạn vẫn xuất hiện; không tăng giới hạn trong lượt này.

## Nhận xét có giới hạn

- Nhãn span chính xác làm metric chặt hơn proxy section/page. Với BM25, 250/40 bỏ lỡ một span mà hai cấu hình lớn hơn lấy được; tuy vậy khác biệt chỉ là một span trên mẫu năm span.
- Dense tìm được đủ năm span ở cả ba cấu hình. Điều đó chỉ cho thấy các câu và nguồn đã gắn nhãn này dễ tìm với Dense trong snapshot hiện tại; không chứng minh mức 100% trên các câu hỏi mới hoặc corpus khác.
- Ba câu P003/P004/P008 chưa có nhãn exact phù hợp. Không được so sánh hoặc quảng bá các metric như đại diện cho toàn bộ bảy câu answerable cho tới khi người thực hiện kiểm tra lại từng đoạn nguồn và cập nhật nhãn.
- Do chỉ có bốn câu exact, chưa chọn cấu hình tối ưu, chưa thay default 500/80 và chưa kết luận chunk nhỏ/lớn tốt hơn. Bước tiếp theo là hoàn thiện nhãn span còn thiếu, sau đó mở rộng câu hỏi đã được người học tự xác minh.

## Tái lập

Chạy bằng Python 3.11 trong env dự án; script in đường dẫn interpreter khi bắt đầu. Kết quả raw là JSON metadata-only trong thư mục Git-ignored `artifacts/results/chunking_ablation/`.

```powershell
$py = 'C:\Users\Dell\anaconda3\envs\rag-hcmute\python.exe'
& $py scripts/run_chunking_ablation.py --method bm25

$env:HF_HUB_OFFLINE = '1'
$env:TRANSFORMERS_OFFLINE = '1'
$model = 'D:\RAG\models\huggingface\hub\models--BAAI--bge-m3\snapshots\5617a9f61b028005a4858fdac845db406aefb181'
& $py scripts/run_chunking_ablation.py --method dense --dense-model $model
```

Không có nội dung câu hỏi, span trích dẫn hoặc preview chunk nào được ghi vào kết quả exact-evidence. Chỉ lưu question ID, trang PDF, token offset, hash neo bằng chứng, metric và thông tin cấu hình.
