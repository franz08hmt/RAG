# Mốc 3 · Hồ sơ thực nghiệm và bàn giao ngày 05/11/2026

[Báo cáo tiến độ tổng hợp từ Mốc 1 đến Mốc 3](../reports/22110068_RAG_Bao_Cao_Tien_Do_Tong_Hop_Moc_1_2_3_v1.docx) là bản đọc liền mạch gồm 24 trang. Bản này tổ chức theo năm chương, bổ sung phần nền tảng, xử lý tài liệu, chỉ mục và console từ các mốc trước vào các kết quả mới. Cấu hình và cách tính chỉ số được ghi riêng cho mỗi phép thử. Phụ lục B đối chiếu YC1–YC13 với nội dung hiện có. Đã kiểm bố cục bằng Microsoft Word và rà toàn bộ 24 trang.

[Bản Word để đọc trước khi nộp](../reports/22110068_RAG_Bao_Cao_Tien_Do_Moc_3_v1.docx) gồm tám trang. Nội dung theo tiếp Mốc 2, dùng bìa đã duyệt và snapshot G0 `5da3bd4d5de54492`. Nhánh cục bộ là `tim-hieu-rag-dot2`. Mở báo cáo từ thư mục reports. Đối chiếu bảng với [manifest minh chứng](evidence/m3/manifest.json) và các tệp dưới đây. Bản Mốc 3 hiện ở máy làm việc. Khi bàn giao qua email, có thể đính kèm bộ số liệu đã lọc cùng DOCX nếu nhánh GitHub chưa chứa commit này.

| Câu cần giải thích | Minh chứng | Phạm vi kết luận |
|---|---|---|
| Trang scan hoặc nhiều hình cho ra nội dung gì? | [10 trang OCR](evidence/m3/runs/ocr.json) | Tesseract tiếng Việt ở 180 dpi, PSM 6. Trang 116 cho 1.428 ký tự OCR so với 3 ký tự lớp chữ. Cần bản chép chuẩn để đo CER/WER. |
| Chia đoạn có làm mất điều kiện khi cấp ngữ cảnh? | [Sáu cách chia](evidence/m3/runs/chunking.json) | Mười khoảng bằng chứng, bảy câu dev. So sánh Top-5 và ngân sách 1.000/2.000 token. Có kết quả theo câu và theo bộ truy xuất. |
| Mô hình embedding nào tìm đúng hơn trên tập học vụ này? | [Sáu mô hình cùng một tập đoạn](evidence/m3/runs/embeddings.json) | 1.175 đoạn vừa 128 token của cả sáu model, có thêm đối chứng E5 bỏ tiền tố. Trần này khác thí nghiệm chunking. |
| Xếp hạng lại còn tác dụng khi đã hợp hai nhánh? | [Fusion và reranker](evidence/m3/runs/ranking.json) | 4 phép hợp, 3 reranker, độ sâu 10/20/50, dùng 156 đoạn G0. Cùng ứng viên cho mỗi độ sâu. So kết quả với cấu hình trước rerank. |
| Trích đoạn khớp có đủ để tin câu trả lời? | [30 lượt Qwen3:4B](evidence/m3/runs/generation.json) | P006 vẫn trả lời khi câu thiếu căn cứ. P009 chủ động từ chối. P010 bị chặn ở phép khớp trích đoạn. Chấm ý nghĩa từng câu trong worksheet riêng. |
| Bộ câu hỏi đã dùng để chấm độc lập được chưa? | [Kiểm tra dữ liệu](evidence/m3/runs/review.json) | 27 mục trong hồ sơ mới đang đợi duyệt. Tập phát triển lịch sử được giữ riêng. Chưa khóa test hoặc chấm độc lập. |

## Demo trong buổi gặp giảng viên

Mở PowerShell ở thư mục dự án. Lệnh đầu chạy BM25 và in nguồn, có thể chạy khi Ollama tắt. Lệnh thứ hai cần Ollama phục vụ qwen3:4b cục bộ và các trọng số đã lưu.

```powershell
.\scripts\demo_m2.ps1 -Method bm25 -NoAnswer -Question 'Thủ tục xin nghỉ học tạm thời được quy định ra sao?'
.\scripts\demo_m2.ps1 -Question 'Thủ tục xin nghỉ học tạm thời được quy định ra sao?'
```

Lượt kiểm lại ngày 05/11 trả đúng đoạn c0038, Điều 17, PDF trang 23–24 ở hạng 1 cho lệnh đầu. Mở PDF để xem điều kiện được nghỉ và thủ tục nộp đơn. Tiếp theo, dùng trường hợp P006 ở trang 7 của báo cáo để giải thích vì sao một trích dẫn có thật vẫn cần kiểm nội dung. Ba chế độ sinh của thí nghiệm được so trong runner riêng với các nguồn đã lưu, tránh thay đổi đầu vào giữa các lần chạy.

## Chạy lại trên máy dự án

Môi trường thực nghiệm dùng Python 3.11.16, Torch 2.14.0+cu126 và GPU RTX 3060 Laptop. Mỗi bảng ghi kết quả của lần chạy đã lưu. Độ trễ phụ thuộc máy và trạng thái bộ nhớ. Các lệnh cần G0 đã tái tạo, model trong cache cục bộ và bộ nguồn Mốc 2 trong private_eval. Model chuyên tiếng Việt dùng PyVi 0.1.1.

```powershell
$ragPython = 'C:\Users\Dell\anaconda3\envs\rag-hcmute\python.exe'
& $ragPython -c "import sys; print(sys.executable); import torch; assert torch.cuda.is_available()"
& $ragPython scripts/prepare_m3_model_registry.py
& $ragPython scripts/run_m3_chunking_study.py
& $ragPython scripts/run_m3_embedding_study.py
& $ragPython scripts/run_m3_ranking_study.py
& $ragPython scripts/run_m3_generation_study.py
& $ragPython scripts/run_m3_ocr_review.py --package 'D:\RAG\private_eval\m3_review\20261104T140545Z'
```

Chạy từng lệnh GPU nối tiếp. Lần chạy mới được ghi vào artifacts/results/m3 với thời điểm UTC mới. Dùng [script thu minh chứng](../scripts/collect_m3_evidence.py) để đối chiếu đúng những lượt lịch sử ghi trong báo cáo, bảo toàn hash đầu vào và bản xuất. Sáu tệp của báo cáo chỉ chứa thông số, mã câu, mã đoạn và thống kê. Bản chép, câu sinh và dữ liệu gắn nhãn chi tiết nằm ngoài Git.

## Phần còn cần sinh viên thực hiện

1. Mở `D:\RAG\private_eval\m3_review\20261104T140545Z\START_HERE.html`. So đáp án của P006 với đoạn nguồn trước. Ghi nhận cụ thể nguồn có nêu đủ điều kiện làm khóa luận hay chỉ nhắc đến khóa luận. Duyệt tiếp 30 kết quả sinh trong generation_review.csv và ghi người chấm.
2. Dùng ảnh trang để điền 10 bản gold OCR và ocr_review.csv. Với bảng, kiểm tra cả quan hệ hàng–cột và số liệu. Khi có bản chép chuẩn, đo CER/WER và so phương án OCR thứ hai trên cùng ảnh. Khả năng hiểu nội dung hình cần bài kiểm riêng.
3. Duyệt 27 mục của gói mới và bổ sung câu hỏi. Mục tiêu 100, tối thiểu 80 câu, ít nhất 30% do sinh viên tự viết. Câu tương đương hoặc cùng nhóm bằng chứng không được rải sang cả dev và test. Chọn cấu hình trên dev và lưu hash danh sách trước khi mở test. [Giao thức duyệt](evaluation/MOC3_GIAO_THUC_DUYET.md)
4. Trước báo cáo cuối kỳ, kiểm độ nhạy kích thước/overlap trên tập rộng hơn, đối chiếu những trường hợp có hình/bảng, chạy baseline và cấu hình chọn trên cùng test rồi chấm câu trả lời và trích dẫn. Báo rõ mẫu, độ trễ và từng nhóm lỗi. Việc mở rộng vector store hoặc dùng benchmark ngoài HCMUTE cần xét nguồn và giấy phép riêng.

## Nguồn để giải thích lựa chọn mô hình

Revision thực chạy nằm trong từng tệp JSON. Thông số model lấy từ thẻ của tác giả, còn so sánh trên tiếng Việt lấy từ dữ liệu phát triển của dự án.

- Họ BGE và E5. [BGE-M3](https://huggingface.co/BAAI/bge-m3), [E5-small](https://huggingface.co/intfloat/multilingual-e5-small), [E5-base](https://huggingface.co/intfloat/multilingual-e5-base)
- Hai bộ mã hóa tiếng Việt và đối chứng MiniLM. [BKAI](https://huggingface.co/bkai-foundation-models/vietnamese-bi-encoder), [Vietnamese Embedding](https://huggingface.co/dangvantuan/vietnamese-embedding), [MiniLM đa ngôn ngữ](https://huggingface.co/sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2)
- Ba cross-encoder. [BGE v2-m3](https://huggingface.co/BAAI/bge-reranker-v2-m3), [mMARCO MiniLM](https://huggingface.co/cross-encoder/mmarco-mMiniLMv2-L12-H384-v1), [BGE-base](https://huggingface.co/BAAI/bge-reranker-base)
- Tokenizer dùng để đếm ngân sách và hợp đồng đầu ra cục bộ. [Qwen3-4B](https://huggingface.co/Qwen/Qwen3-4B), [Ollama Structured Outputs](https://docs.ollama.com/capabilities/structured-outputs)
