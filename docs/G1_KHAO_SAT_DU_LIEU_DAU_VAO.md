# Giai đoạn 1 — Khảo sát xử lý tài liệu đầu vào

**Trạng thái:** Đã khảo sát corpus, tích hợp OCR fallback có điều kiện và dựng snapshot thử riêng; baseline Giai đoạn 0 được giữ nguyên.
**Phạm vi:** YC4 — tài liệu PDF có lớp chữ, trang scan, bảng và hình ảnh.
**Baseline:** `5da3bd4d5de54492` — 3 tài liệu, 182 trang. **Snapshot OCR thử:** `cc57c028f3816a3d`.

## 1. Kết quả kiểm tra corpus

Các số liệu dưới đây được đo cục bộ bằng PyMuPDF 1.28.2. Chỉ ghi nhận số trang, ký tự, ảnh và hình dạng bảng; không trích nội dung tài liệu vào nhật ký hay gửi ra ngoài.

| Tài liệu | Trang | Trang có lớp chữ trích xuất được | Trang nghi scan/ít chữ | Trang có ảnh raster | Ứng viên bảng từ PyMuPDF |
|---|---:|---:|---:|---:|---:|
| Quy chế 1727 | 32 | 32 | 0 | 2 | 11 bảng trên 8 trang |
| Hướng dẫn thực tập tốt nghiệp | 1 | 1 | 0 | 0 | 0 |
| Sổ tay Sinh viên 2024 | 149 | 148 | 26 | 149 | 28 bảng trên 25 trang |

“Nghi scan/ít chữ” là heuristic hiện có: trang có dưới 15 ký tự trích xuất và có ảnh, hoặc không trích xuất được chữ. Trong Sổ tay, các trang ứng viên là 1, 107, 109–112, 116–117, 121, 123–127, 129–139 và 149; cả 26 trang đều có ảnh phủ gần toàn trang. Tuy nhiên, vì ảnh raster cũng xuất hiện trên nhiều trang vẫn có lớp chữ, không thể kết luận chỉ dựa vào việc trang có ảnh. Các trang này cần được thử OCR cục bộ rồi đối chiếu chất lượng.

PyMuPDF đánh dấu 11 và 28 **ứng viên** bảng bằng `Page.find_tables()`; đây chưa phải số bảng đúng đã được con người xác nhận. Một số ứng viên nằm ở các trang danh bạ đã được ADR-002 ghi nhận có thông tin liên hệ cá nhân. Không ghi cell text của các trang này vào tài liệu, log hoặc dịch vụ cloud.

Ở lượt audit cấu trúc tiếp theo, chỉ lưu trang và số hàng/cột, đồng thời bỏ qua trang PDF 140–147 của Sổ tay để tránh xử lý phần danh bạ. Kết quả còn 20 ứng viên bảng trên 17 trang của Sổ tay; Quy chế có 11 ứng viên trên 8 trang; tài liệu hướng dẫn thực tập không có ứng viên. Ứng viên lớn nhất trong phần đã khảo sát là 36 hàng × 4 cột. Đây vẫn là kết quả heuristic của `find_tables()`, chưa xác nhận bằng mắt hay chứng minh mọi ô được trích đúng. Metadata nằm ở `artifacts/results/g1_table_audit.json` và file này bị Git ignore.

## 2. Pipeline hiện tại đang làm gì

- Mặc định, `extract_pdf_pages()` vẫn lấy text native bằng `page.get_text("text")` và không gọi OCR. Khi bật `OCRSettings`, fallback chỉ chạy nếu text native ít hơn ngưỡng cấu hình (mặc định 15 ký tự) **và** trang có ảnh raster; trang có đủ text không bị OCR chỉ vì có ảnh. Nếu OCR không trả text, giữ kết quả native.
- `PageText` lưu phương thức trích xuất (`native`/`ocr`) và mean word confidence do Tesseract trả về; thông tin này được giữ qua bước làm sạch và được tổng hợp vào `Chunk`. Snapshot ghi cấu hình OCR, phiên bản engine, ngôn ngữ, DPI, PSM và SHA-256 của traineddata, không ghi đường dẫn máy cụ thể.
- Chưa bóc tách bảng thành hàng/cột để đưa vào retrieval và chưa diễn giải nội dung hình chỉ mang tính thị giác.
- `chunk_document()` dùng whitespace token, mặc định 500 token và overlap 80. Tài liệu nhận diện được cấu trúc Điều thì ưu tiên ranh giới Điều; tài liệu không nhận diện được cấu trúc dùng cửa sổ trượt trên luồng trang. Trang đầu/cuối mỗi chunk được lưu, nhưng hàng bảng chưa được bảo vệ khỏi việc bị tách giữa các chunk.
- OCR chỉ bật khi truyền `--ocr` cho `scripts/build_corpus.py`; nếu không bật, extraction giữ hành vi native-only. Không truyền `--tesseract-cmd` thì code ưu tiên executable nằm trong Python environment hiện tại rồi mới dò `PATH`. Dữ liệu OCR thử được ghi vào `data/processed/g1_ocr/` (Git ignored), không ghi đè snapshot G0.

## 3. Cách xử lý đề xuất

1. **Ưu tiên lớp chữ PDF.** Giữ PyMuPDF native extraction cho trang có chữ có thể chọn được. Việc có ảnh trên trang không tự động kích hoạt OCR, vì trang Sổ tay có ảnh lớn nhưng phần lớn vẫn có lớp chữ.
2. **OCR có điều kiện, chạy hoàn toàn local.** Giữ native text làm mặc định; chỉ chọn OCR text thay cho text native khi trang thiếu text và có ảnh raster. Trường `extraction_method` cho biết nguồn nào được dùng, còn PDF gốc vẫn là nguồn đối chiếu. Ghi lại confidence và cấu hình, nhưng không dùng confidence làm xác suất đúng. OCR chỉ giúp lấy chữ từ ảnh, không tự hiểu bố cục hay quan hệ giữa cột.
3. **Bảng thành dữ liệu có cấu trúc.** Dùng `Page.find_tables()` để tạo ứng viên, kiểm tra số hàng/cột và đối chiếu thủ công trên các trang phù hợp. Khi đưa vào retrieval, giữ tiêu đề bảng, header cột, nhóm hàng cùng đơn vị; nếu phải chia bảng dài thì lặp header và lưu `table_id`, trang nguồn, chỉ số hàng. Bảng không viền hoặc chỉ phân tách bằng màu nền có thể bị bỏ sót; không xem kết quả detector là ground truth.
4. **Hình ảnh và sơ đồ.** Lưu metadata vị trí/loại ảnh và trang nguồn. Với hình có chữ, thử OCR cục bộ; với hình chỉ mang thông tin thị giác, ghi nhận là chưa diễn giải được cho retrieval cho tới khi có caption được kiểm chứng. Không gửi Sổ tay hoặc nội dung phát sinh từ nó tới Gemini/LLM cloud.
5. **Giữ tương thích với baseline.** Mọi trường schema mới nên là optional hoặc có `schema_version`; giữ nguyên cách tạo snapshot/baseline cũ để so sánh trên snapshot mới riêng. Kết quả OCR/table được lưu trong `data/processed/` (đang Git ignore), không commit PDF hay toàn văn.

## 4. Kế hoạch kiểm chứng trong Giai đoạn 1

- Tạo bảng audit theo trang: ký tự native, ảnh phủ trang, trạng thái OCR, số bảng/shape và số trang chưa có nguồn trích xuất usable. Chỉ xuất metadata, không xuất nội dung nhạy cảm.
- Đã chạy thử OCR cục bộ trên cả 26 trang nghi scan của Sổ tay Sinh viên, ở 200 DPI, ngôn ngữ `vie`, page segmentation mode 6. Các trang có trung vị 3 ký tự native; OCR nhận tổng cộng 3.650 từ, median của confidence trung bình theo từng trang là 86,06/100. Đây là chỉ số confidence do engine ước lượng, **không phải** accuracy/CER/WER và chưa chứng minh từng từ được nhận dạng đúng.
- Các trang có confidence trung bình thấp nhất trong lượt khảo sát là trang 1 (61,55), 136 (73,66), 149 (75,80), 137 (77,44) và 109 (79,08). Đây là danh sách ưu tiên rà soát, không phải ngưỡng loại trang. Trước khi đưa OCR text vào corpus cần chọn trang không chứa PII để tạo ground truth ngắn, đối chiếu thủ công và ghi nhận lỗi chữ, dấu tiếng Việt, số hiệu cùng bố cục.
- Đã kiểm tra trực quan một bảng không nhạy cảm ở Quy chế 1727 (PDF page 3). Bảng có cấu trúc phân cấp 14×5; `find_tables()` và `extract()` cùng trả shape 14×5, với 53 ô có text và 17 ô rỗng. Ảnh trang cho thấy có nhóm hàng/ô gộp, nên không thể coi mọi ô rỗng là lỗi detector; cũng chưa đủ để khẳng định mọi giá trị từng ô đều đúng.
- Dựng snapshot OCR mới `cc57c028f3816a3d`: 3 tài liệu, 182 trang, 165 chunks (so với 156 chunk ở baseline), 26 trang OCR và 12 chunks mang provenance OCR (4 OCR-only, 8 trộn native/OCR). Cả 26 trang OCR đều giữ số PDF page; không trang nào nhận diện được printed page, do đó citation hiện phải dùng rõ số trang PDF, không suy đoán số trang in.
- Chạy lại cùng pilot 10 câu (7 câu có gold evidence, 3 câu không trả lời được); mọi gold chunk ID cũ vẫn tồn tại và trỏ đúng document/PDF-page range. Kết quả retrieval:

| Retriever | Baseline Hit@5 | Snapshot OCR Hit@5 | Baseline MRR@10 | Snapshot OCR MRR@10 |
|---|---:|---:|---:|---:|
| BM25 | 3/7 (0,429) | 3/7 (0,429) | 0,371 | 0,351 |
| BGE-M3 dense | 6/7 (0,857) | 6/7 (0,857) | 0,643 | 0,786 |

  Trên bộ nhỏ này, Hit@5 không đổi; BM25 có một câu tăng hạng và một câu giảm hạng, dense có hai câu tăng hạng và không câu nào giảm hạng. Chưa được diễn giải thành kết luận tổng quát hay bằng chứng OCR làm chất lượng tăng: pilot nhỏ, không phải test set độc lập, và OCR confidence chưa được đối chiếu với ground truth.

## 5. Cấu hình OCR đã cài và phạm vi kết quả

OCR local là cần thiết để khảo sát các trang thiếu lớp chữ theo YC4. Cấu hình hiện tại:

- Cài `tesseract=5.5.3` và `pytesseract=0.3.13` bằng Conda-forge trong env `rag-hcmute`. Dry-run dự kiến 34 package link, 2 package thay phiên bản và 217.060.448 byte tải xuống; transaction không thay Python 3.11 hoặc Torch/CUDA. Cài đặt đã hoàn tất và project vẫn qua test suite.
- Tesseract không đi kèm bộ ngôn ngữ trong transaction; model `vie` được tải riêng từ [`tesseract-ocr/tessdata_best`](https://github.com/tesseract-ocr/tessdata_best/blob/main/vie.traineddata), bộ model ưu tiên độ chính xác hơn tốc độ và phát hành theo Apache-2.0 ([README/license](https://github.com/tesseract-ocr/tessdata_best)). File 12.435.550 byte nằm ngoài repo tại `D:\RAG\models\tesseract\tessdata\vie.traineddata`, SHA-256 `b6b49293d95d0b6dbd8780174627e82c75be957b6f4ed9862155540d6b00bb45`.
- Phiên bản kiểm tra: Tesseract 5.5.3, pytesseract 0.3.13, PyMuPDF 1.28.2. OCR dùng trực tiếp trên máy, không gọi API và không gửi văn bản corpus ra ngoài.
- Chỉ số khảo sát nằm ở `artifacts/results/g1_ocr_survey.json`; không chứa OCR text. OCR text của snapshot thử được lưu cục bộ trong `data/processed/g1_ocr/pages/` (Git ignored), không in ra terminal, không commit và không gửi tới cloud. Snapshot/chunks/log cùng nằm trong `data/processed/g1_ocr/`.
- `pytest`: 26 passed; smoke test 2/2 passed; `pip check` không phát hiện dependency hỏng. CUDA vẫn khả dụng. BGE-M3 được chạy bằng snapshot model đã lưu local, không gọi Hugging Face trong lần đánh giá OCR.
- Đã thử gọi OCR trực tiếp trên trang bìa PDF page 1 bằng Python executable của env, không truyền đường dẫn Tesseract riêng: executable được phân giải từ env, OCR trả 232 ký tự với confidence trung bình 61,55. Chỉ ghi số liệu tích hợp, không in nội dung trang ra terminal; đây không phải ground-truth accuracy.

**Giới hạn cần giữ rõ:** confidence 86,06 không được trình bày thành “OCR chính xác 86,06%”. Cần tạo ground truth ngắn trên trang không nhạy cảm, rà soát trang confidence thấp và dùng số PDF page khi printed page chưa nhận diện được. Các trang có ảnh nhưng đã có text native không nên OCR tự động vì có thể lặp nội dung. Bảng phân cấp và hình chỉ mang thông tin thị giác vẫn chưa được tích hợp thành dữ liệu retrieval.

### Tài liệu kỹ thuật đã đối chiếu

- [PyMuPDF — table extraction và giới hạn của find_tables](https://pymupdf.readthedocs.io/en/latest/faq/index.html)
- [Tesseract — bản phát hành upstream](https://github.com/tesseract-ocr/tesseract/releases)
- [Conda-forge — Tesseract 5.5.3, Windows-64, giấy phép Apache-2.0](https://anaconda.org/conda-forge/tesseract)
- [pytesseract — cài wrapper và cấu hình đường dẫn executable](https://github.com/madmaze/pytesseract)
- [Tesseract — so sánh tessdata, tessdata_fast và tessdata_best](https://github.com/tesseract-ocr/tessdoc/blob/main/Data-Files.md)
- [tessdata_best — Vietnamese traineddata và giấy phép Apache-2.0](https://github.com/tesseract-ocr/tessdata_best)
- [ADR-002 — nguồn dữ liệu, tái phân phối và PII](decisions/ADR-002-corpus-sourcing-and-redistribution.md)
- [ADR-003 — quyết định OCR fallback có điều kiện](decisions/ADR-003-conditional-local-ocr.md)

**Checkpoint hiện tại:** OCR fallback đã tích hợp và được chạy trên snapshot riêng; baseline G0 không bị thay đổi. Đã kiểm tra trực quan một bảng mẫu nhưng chưa có bộ chuyển đổi bảng thành chunk giữ nhóm hàng/header. Kế tiếp là kiểm chứng OCR bằng ground truth không nhạy cảm và xây prototype serialize bảng theo title/header/group/row cùng page provenance; sau đó mới quyết định có đưa hai loại dữ liệu này vào benchmark chính hay không.
