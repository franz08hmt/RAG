# So sánh chính sách chia chunk trên cùng snapshot — 07/10/2026

## Câu hỏi và phạm vi thử nghiệm

Phép thử đối chiếu chính sách hiện tại — giữ ranh giới Điều khi tài liệu được nhận diện có cấu trúc — với cửa sổ trượt cố định 500/80 trên các tài liệu có cấu trúc. Hai biến thể dùng cùng snapshot G0, dữ liệu, câu hỏi, nhãn evidence, retriever và `top_k=10`; không thay nội dung snapshot hay cấu hình mặc định.

Trong code hiện tại, đơn vị “token” của chunk là từ tách bằng khoảng trắng (`str.split()`), không phải subword token của embedding model. G0 gồm ba tài liệu, 182 trang và 156 chunk. Bộ pilot có 7 câu answerable với 10 evidence span đã đối chiếu theo offset và hash: 6 câu/9 span thuộc Quy chế 1727, 1 câu/1 span thuộc Hướng dẫn thực tập; Sổ tay Sinh viên không có câu answerable trong bộ này. Chỉ một tài liệu trong corpus được nhận diện có cấu trúc Điều; vì vậy kết quả không đại diện cho nhiều document class.

Thử nghiệm dùng BM25Okapi và BGE-M3 local với FAISS IndexFlatIP trên `cuda:0` (embedding 1.024 chiều). Không gọi Gemini hay API khác. So sánh có hai cách đọc kết quả:

- **Exact evidence:** chunk phải chứa trọn khoảng token của span nguồn. Nếu một chính sách cắt span qua ranh giới chunk thì span đó vẫn nằm trong mẫu số và được tính là miss; không loại span khó để làm đẹp điểm.
- **Page-location proxy:** xem có chunk thuộc trang PDF nguồn xuất hiện trong Top-5 hay không. Chỉ số này dễ đạt hơn exact evidence và không chứng minh chunk chứa đúng đoạn cần trả lời.

## Kết quả

| Retriever | Chính sách chunk | Số chunk | Span nằm trọn trong chunk | Exact evidence Recall@5 | Đủ evidence Hit@5 | Page-location Hit@5 |
|---|---|---:|---:|---:|---:|---:|
| BM25 | Theo cấu trúc Điều | 156 | 10/10 | 4/10 (0,400) | 3/7 (0,429) | 3/7 (0,429) |
| BM25 | Cửa sổ cố định trên tài liệu có cấu trúc | 144 | 9/10 | 6/10 (0,600) | 4/7 (0,571) | 6/7 (0,857) |
| BGE-M3 | Theo cấu trúc Điều | 156 | 10/10 | 9/10 (0,900) | 6/7 (0,857) | 7/7 (1,000) |
| BGE-M3 | Cửa sổ cố định trên tài liệu có cấu trúc | 144 | 9/10 | 8/10 (0,800) | 5/7 (0,714) | 7/7 (1,000) |

Trong riêng nhóm Quy chế 1727, BM25 tìm được 4/9 span với chính sách theo Điều và 6/9 với cửa sổ cố định; BGE-M3 lần lượt tìm được 8/9 và 7/9. Cửa sổ cố định làm giảm số chunk 12, nhưng chỉ bao phủ trọn 8/9 span của Quy chế; chính sách theo Điều bao phủ đủ 9/9. Với tài liệu hướng dẫn một trang, BM25 không tìm được span trong Top-5 ở cả hai biến thể, còn BGE-M3 tìm được 1/1. Đây chỉ là một câu nên không đủ để kết luận theo loại tài liệu.

## Nhận xét kỹ thuật

Hai retriever không cho cùng một thứ hạng biến thể. Cửa sổ cố định tăng kết quả BM25 trong bộ pilot, nhưng giảm exact evidence recall và complete-evidence Hit@5 của BGE-M3. Chỉ số page-location của Dense đạt 7/7 ở cả hai cấu hình, cho thấy proxy theo trang không phân biệt được khác biệt về việc lấy đúng đoạn bằng chứng.

Vì vậy chưa có cơ sở thay chính sách hiện tại. Giữ section-aware làm mặc định là lựa chọn thận trọng: nó giữ trọn toàn bộ span đã gán nhãn và cho kết quả Dense tốt hơn trên mẫu này. Cửa sổ cố định vẫn là phương án đối chứng đáng theo dõi, nhất là khi dùng BM25; cần thêm câu hỏi độc lập và thêm tài liệu cấu trúc trước khi quyết định theo document class.

## Giới hạn diễn giải

- Bảy câu answerable là pilot phục vụ phát triển, không phải holdout độc lập; không dùng các tỷ lệ này để tuyên bố chất lượng tổng quát.
- Mẫu chỉ có một nguồn được nhận diện cấu trúc Điều, một nguồn hướng dẫn ngắn có một câu, và không có câu answerable cho Sổ tay. Chưa thể so sánh chunking một cách có ý nghĩa trên văn xuôi dài, scan, hình hoặc bảng.
- Đây là đánh giá retrieval và truy xuất bằng chứng; chưa đánh giá câu trả lời sinh, độ đúng trích dẫn đầu ra, refusal hay Faithfulness/Answer Relevance.
- Kết quả không chọn embedding model tốt nhất; Dense chỉ dùng BGE-M3 hiện có. Không thay default chunking, index G0, pilot hoặc corpus.

## Tái lập và minh chứng

Script: [`run_chunk_strategy_ablation.py`](../../scripts/run_chunk_strategy_ablation.py). Các file JSON chỉ chứa cấu hình, hash, ID câu hỏi và metric tổng hợp, được Git-ignore:

- BM25: `artifacts/results/chunk_strategy_ablation/bm25_5da3bd4d5de54492_20261007T080058Z.json`
- BGE-M3: `artifacts/results/chunk_strategy_ablation/dense_5da3bd4d5de54492_20261007T080215Z.json`

Lệnh chạy trong PowerShell, dùng Python của env dự án:

```powershell
& 'C:\Users\Dell\anaconda3\envs\rag-hcmute\python.exe' scripts/run_chunk_strategy_ablation.py --method bm25
& 'C:\Users\Dell\anaconda3\envs\rag-hcmute\python.exe' scripts/run_chunk_strategy_ablation.py --method dense --dense-model 'D:\RAG\models\huggingface\hub\models--BAAI--bge-m3\snapshots\5617a9f61b028005a4858fdac845db406aefb181'
```

Runner xác minh SHA-256 các nguồn theo manifest, ghim snapshot `5da3bd4d5de54492`, từ chối snapshot có OCR và so khớp đầu ra chính sách mặc định với chunk nội dung G0. Mã nguồn PDF, query, evidence text và vector không được ghi vào JSON kết quả.
