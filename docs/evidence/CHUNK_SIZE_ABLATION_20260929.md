# Thử nghiệm độ nhạy kích thước chunk trên corpus HCMUTE

## Mục tiêu và phạm vi

Kiểm tra bước đầu việc thay đổi kích thước chunk có ảnh hưởng thế nào đến số lượng đơn vị lập chỉ mục và thứ hạng truy xuất. Thử nghiệm dùng snapshot native-only G0 `5da3bd4d5de54492`, cùng bộ pilot hiện có; không bật OCR, không thêm câu hỏi/gold và không thay snapshot mặc định.

Đây là **phân tích độ nhạy trên tập phát triển nhỏ**, không phải benchmark cuối. Trong bộ 10 câu hiện tại có 7 câu answerable đã có gold và 3 câu unanswerable; chỉ 7 câu answerable được dùng tính retrieval hit/MRR.

## Cấu trúc tài liệu và cách chunk hiện tại

Snapshot có 3 tài liệu, 182 trang, 156 chunk ở cấu hình 500/80:

| Nhóm tài liệu | Cách xử lý hiện tại | Chunk ở 500/80 | Quan sát cấu trúc |
|---|---|---:|---|
| Quy chế đào tạo 1727 | Nhận diện cấu trúc Điều; chia theo Điều, Điều dài mới dùng cửa sổ trượt | 52 | 31 mốc Điều; `section_path` giữ Chương/Điều |
| Sổ tay Sinh viên 2024 | Cửa sổ trượt | 103 | Chỉ có 2 dòng khớp mẫu Điều, thấp hơn ngưỡng 4; 26 trang scan không có text native trong G0 |
| Hướng dẫn thực tập tốt nghiệp | Cửa sổ trượt | 1 | Một trang, một chunk 388 đơn vị whitespace |

`chunk_tokens` hiện được đếm bằng `text.split()`, tức đơn vị tách theo khoảng trắng, **không phải** subword token của BGE-M3. Quy chế được giữ theo ranh giới Điều; hai tài liệu còn lại dùng cửa sổ trên luồng văn bản.

Một vấn đề truy vết đã thấy trong metadata: chunk lớn nhất của Sổ tay ở G0 có khoảng trang PDF 36 trang, dù nội dung native bị thưa do các trang scan không được OCR trong snapshot này. Ở snapshot thử G1 có OCR, khoảng lớn nhất giảm còn 8 trang; điều đó cho thấy chỉ lưu `pdf_page_start/end` có thể tạo khoảng citation rộng khi trang giữa không có text. Cấu trúc citation theo danh sách trang thực tế hoặc offset nguồn cần được xem như một quyết định riêng; bước này chưa sửa schema.

## Thiết kế thử nghiệm

Giữ cùng snapshot, bước làm sạch, thuật toán nhận diện Điều, tokenizer BM25, BGE-M3 và bộ câu hỏi. Chỉ thay target size/overlap, giữ overlap xấp xỉ 16%:

| Cấu hình | Mô tả |
|---|---|
| 250/40 | Chunk nhỏ hơn, nhiều đơn vị retrieval hơn |
| 500/80 | Cấu hình hiện tại và baseline tái dựng |
| 750/120 | Chunk lớn hơn, ít đơn vị hơn nhưng có thể kéo dài ngữ cảnh/trang nguồn |

Quy tắc gộp chunk cuối ngắn (ngưỡng 60 đơn vị whitespace) của chunker hiện tại được giữ nguyên ở cả ba cấu hình. Vì vậy đây là so sánh cấu hình thực tế của implementation hiện tại, không phải phép thử cô lập toán học chỉ một tham số.

### Ánh xạ gold và giới hạn metric

Gold chunk ID đổi khi chia chunk lại nên không thể dùng nguyên ID cũ. Runner lấy `expected_chunk_id` đã xác minh trong pilot rồi ánh xạ sang `section_path` gốc cho câu thuộc Quy chế; với tài liệu không có section marker thì dùng khoảng trang của gold chunk. Một chunk mới được tính là khớp nếu thuộc cùng Điều đã gán hoặc chạm trang gold.

Do đó chỉ số bên dưới là **section/page-location Hit@5 và MRR@10**, không phải exact evidence-chunk Recall@5. Một Điều có thể tạo ra nhiều chunk ứng viên cùng được tính liên quan; ví dụ câu P002/P004 có 10 ứng viên cùng Điều ở cấu hình 250/40, 5 ở 500/80 và 3 ở 750/120. Metric này có thể ưu ái cấu hình nhỏ do tăng số chunk trong một Điều, nên không dùng riêng nó để chọn cấu hình production. Kết quả baseline chunk-level cũ (BM25 Hit@5 3/7, MRR@10 0,371) không so trực tiếp với section/page proxy ở đây.

## Kết quả

| Kích thước/overlap | Tổng chunk | BM25 section/page Hit@5 | BM25 MRR@10 | Dense section/page Hit@5 | Dense MRR@10 | BGE chunk vượt 1.024 subword |
|---|---:|---:|---:|---:|---:|---:|
| 250/40 | 297 | 4/7 (0,571) | 0,500 | 7/7 (1,000) | 0,929 | 0/297; max 549 |
| 500/80 | 156 | 4/7 (0,571) | 0,419 | 7/7 (1,000) | 0,762 | 4/156; max 1.088 |
| 750/120 | 111 | 4/7 (0,571) | 0,399 | 7/7 (1,000) | 0,833 | 20/111; max 1.626 |

Dense dùng `BAAI/bge-m3` revision `5617a9f61b028005a4858fdac845db406aefb181`, embedding 1.024 chiều, FAISS `IndexFlatIP`, `max_seq_length=1024`, chạy trên CUDA local. Tokenizer đo độ dài đầu vào thực tế gồm special tokens; chunk dài hơn giới hạn bị cắt theo giới hạn hiện hành của encoder. Không gọi dịch vụ cloud.

Ở cấu hình lớn, số đơn vị lập chỉ mục giảm (297 → 111) nhưng số chunk vượt giới hạn encoder tăng (0 → 20). Profile khoảng trang của Sổ tay cũng mở rộng theo kích thước: page-span P95 lần lượt là 2, 3, 4; max lần lượt 36, 36, 38 trang. Những giá trị này nhắc rằng “chunk lớn hơn” không chỉ thay lượng ngữ cảnh mà còn ảnh hưởng chi phí index, nguy cơ truncation và độ cụ thể của citation.

## Diễn giải

- Trên bộ nhỏ này, Hit@5 theo vị trí nguồn không phân biệt được ba cấu hình với BM25; MRR giảm khi tăng kích thước trong lượt thử này.
- Dense đạt 7/7 theo vị trí nguồn ở cả ba cấu hình; MRR cao nhất ở 250/40, nhưng cấu hình đó cũng sinh nhiều ứng viên cùng Điều nên nhãn location proxy rộng hơn. Chưa thể kết luận 250/40 là tốt nhất.
- 500/80 có 4 chunk bị vượt giới hạn BGE; 750/120 có 20. Vì vậy khác biệt Dense ở hai cấu hình này phản ánh cả việc chunk dài bị encoder cắt, không chỉ khác biệt ngữ cảnh. 250/40 không có truncation trong snapshot này.
- Cấu hình 250/40 tạo gần gấp đôi chunk so với 500/80; đổi lại có thể tăng dung lượng index và số ứng viên cần rerank. Bước này chưa đo latency/chi phí reranking.
- Chưa đổi mặc định 500/80, chưa tích hợp cấu hình mới vào snapshot baseline. Cần gold evidence ổn định ở mức đoạn/offset và tập câu hỏi phát triển rộng hơn trước khi có quyết định.

## Tái lập

Chạy trong env `rag-hcmute`; đầu ra chỉ chứa metadata và metric, được ghi vào thư mục `artifacts/results/chunking_ablation/` (Git-ignored):

```powershell
$py = 'C:\Users\Dell\anaconda3\envs\rag-hcmute\python.exe'
& $py scripts/run_chunking_ablation.py --method bm25

$env:HF_HUB_OFFLINE = '1'
$env:TRANSFORMERS_OFFLINE = '1'
$model = 'D:\RAG\models\huggingface\hub\models--BAAI--bge-m3\snapshots\5617a9f61b028005a4858fdac845db406aefb181'
& $py scripts/run_chunking_ablation.py --method dense --dense-model $model
```

Runner kiểm tra snapshot đầu vào là native-only, ánh xạ gold theo section/page, không lưu câu hỏi, văn bản chunk hay preview kết quả. Thay đổi kích thước/overlap có thể tái lập bằng danh sách cấu hình trong `scripts/run_chunking_ablation.py`.
