# Giai đoạn 1 — Khảo sát xử lý tài liệu đầu vào

**Trạng thái:** Đã khảo sát corpus, triển khai OCR fallback dạng tùy chọn qua CLI và dựng snapshot thử riêng; baseline Giai đoạn 0 vẫn native-only, được giữ nguyên.
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

Ở lượt audit cấu trúc tiếp theo, chỉ lưu trang và số hàng/cột, đồng thời bỏ qua trang PDF 140–147 của Sổ tay để tránh xử lý phần danh bạ. Kết quả còn 20 ứng viên bảng trên 17 trang của Sổ tay; Quy chế có 11 ứng viên trên 8 trang; tài liệu hướng dẫn thực tập không có ứng viên. Chênh lệch 28 xuống 20 ứng viên của Sổ tay là do loại các trang 140–147 khỏi lượt sau, không phải kết quả xác nhận thủ công. Ứng viên lớn nhất trong phần đã khảo sát là 36 hàng × 4 cột. Đây vẫn là kết quả heuristic của `find_tables()`, chưa xác nhận bằng mắt hay chứng minh mọi ô được trích đúng. Metadata nằm ở `artifacts/results/g1_table_audit.json` và file này bị Git ignore.

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
- Các trang có confidence trung bình thấp nhất trong lượt khảo sát là trang 1 (61,55), 136 (73,66), 149 (75,80), 137 (77,44) và 109 (79,08). Đây là danh sách ưu tiên rà soát, không phải ngưỡng loại trang.
- Bộ ground truth bắt đầu với ba trang không chứa dữ liệu cá nhân: PDF page 107 (infographic), 109 (đoạn văn kèm minh họa) và 136 (sơ đồ hướng dẫn); sau đó bổ sung page 116 để thành mẫu bốn trang dùng trong sweep hiện tại. Reference JSON bị Git ignore; script `scripts/evaluate_ocr_sample.py` chỉ xuất số liệu, không in OCR text. Chuẩn hóa metric: Unicode NFC, không phân biệt hoa/thường, gộp whitespace; CER giữ dấu câu, WER coi dấu câu là ranh giới token, dấu tiếng Việt được giữ nguyên.
- So sánh thử trên ba trang cho thấy cấu hình OCR ảnh hưởng đáng kể và khác nhau theo kiểu bố cục:

| PDF page / kiểu nội dung | DPI / PSM | CER | WER | Mean confidence |
|---|---:|---:|---:|---:|
| 107 — infographic | 200 / 6 | 19,5% | 32,2% | 88,31 |
| 107 — infographic | 300 / 6 | 20,3% | 34,4% | 87,64 |
| 107 — infographic | 200 / 11 | 9,9% | 16,7% | 90,36 |
| 109 — văn bản và minh họa | 200 / 6 | 23,0% | 24,0% | 79,08 |
| 109 — văn bản và minh họa | 200 / 11 | 17,6% | 29,3% | 87,23 |
| 136 — sơ đồ có nhiều nhãn nhỏ | 200 / 6 | 78,8% | 87,2% | 73,66 |
| 136 — sơ đồ có nhiều nhãn nhỏ | 200 / 11 | 73,6% | 80,2% | 78,00 |

  PSM 11 giảm CER trên cả ba trang nhưng WER tăng ở page 109; tăng DPI từ 200 lên 300 không cải thiện page 107. Page 136 vẫn có lỗi lớn vì nhãn nhỏ nằm trong sơ đồ. Đây là mẫu khảo sát ba trang, ground truth được một người chép và chưa có đánh giá chéo; chưa đủ để đổi mặc định OCR cho toàn corpus. Kết quả cũng cho thấy confidence cao không thể thay CER/WER.
- Đã kiểm tra trực quan một bảng không nhạy cảm ở Quy chế 1727 (PDF page 3). Bảng có cấu trúc phân cấp 14×5; `find_tables()` và `extract()` cùng trả shape 14×5, với 53 ô có text và 17 ô rỗng. Ảnh trang cho thấy có nhóm hàng/ô gộp, nên không thể coi mọi ô rỗng là lỗi detector; cũng chưa đủ để khẳng định mọi giá trị từng ô đều đúng.
- Prototype cục bộ trên bảng này nhận diện hai hàng nhóm rồi biểu diễn thành 11 bản ghi chi tiết (6 + 5 hàng), mỗi bản ghi lặp metadata tài liệu/trang/bảng, nhóm đào tạo, tên cột và giá trị hàng. Dạng này giữ được ngữ cảnh khi một hàng trở thành retrieval unit; hiện mới thử trên một bảng có đường kẻ và text layer, chưa tích hợp vào pipeline hay đánh giá retrieval.
- Ba cách biểu diễn cần so sánh trước khi chốt: (1) Markdown cho toàn bảng — gọn, PyMuPDF hỗ trợ xuất, nhưng ô gộp/nhóm hàng có thể vẫn để trống; (2) mỗi hàng thành đoạn văn có lặp caption, nhóm và header — truy vấn hàng cụ thể rõ hơn nhưng tăng token và cần quy tắc phát hiện dòng nhóm; (3) lưu bảng cha có cấu trúc cùng row-child chunks — truy xuất chính xác và có thể ghép ngữ cảnh, đổi lại cần schema/retriever xử lý bảng. Hướng thử tiếp theo là so sánh (1) và (2) trên tập câu hỏi riêng cho bảng; chưa thay indexing chính.
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
- `pytest`: 29 passed; smoke test 2/2 passed; `pip check` không phát hiện dependency hỏng. CUDA vẫn khả dụng. BGE-M3 được chạy bằng snapshot model đã lưu local, không gọi Hugging Face trong lần đánh giá OCR.
- Đã thử gọi OCR trực tiếp trên trang bìa PDF page 1 bằng Python executable của env, không truyền đường dẫn Tesseract riêng: executable được phân giải từ env, OCR trả 232 ký tự với confidence trung bình 61,55. Chỉ ghi số liệu tích hợp, không in nội dung trang ra terminal; đây không phải ground-truth accuracy.

**Giới hạn cần giữ rõ:** confidence 86,06 không được trình bày thành “OCR chính xác 86,06%”. Ground truth hiện có bốn trang mẫu, vẫn chưa đại diện cho toàn bộ tài liệu; cần mở rộng tập đối chiếu và rà soát thủ công lỗi dấu/số liệu. Dùng số PDF page khi printed page chưa nhận diện được. Các trang có ảnh nhưng đã có text native không nên OCR tự động vì có thể lặp nội dung. Bảng phân cấp và hình chỉ mang thông tin thị giác vẫn chưa được tích hợp thành dữ liệu retrieval.

### Tài liệu kỹ thuật đã đối chiếu

- [PyMuPDF — API table extraction, `find_tables`, `Table.extract()` và `Table.to_markdown()`](https://pymupdf.readthedocs.io/en/latest/page.html)
- [PyMuPDF — giới hạn phát hiện bảng không viền / chỉ tô nền và phương án `strategy="text"`](https://pymupdf.readthedocs.io/en/latest/faq/index.html)
- [Tesseract — bản phát hành upstream](https://github.com/tesseract-ocr/tesseract/releases)
- [Conda-forge — Tesseract 5.5.3, Windows-64, giấy phép Apache-2.0](https://anaconda.org/conda-forge/tesseract)
- [pytesseract — cài wrapper và cấu hình đường dẫn executable](https://github.com/madmaze/pytesseract)
- [Tesseract — so sánh tessdata, tessdata_fast và tessdata_best](https://github.com/tesseract-ocr/tessdoc/blob/main/Data-Files.md)
- [tessdata_best — Vietnamese traineddata và giấy phép Apache-2.0](https://github.com/tesseract-ocr/tessdata_best)
- [ADR-002 — nguồn dữ liệu, tái phân phối và PII](decisions/ADR-002-corpus-sourcing-and-redistribution.md)
- [ADR-003 — quyết định OCR fallback có điều kiện](decisions/ADR-003-conditional-local-ocr.md)

**Checkpoint hiện tại:** OCR fallback được triển khai như tùy chọn và chạy trên snapshot riêng; baseline G0 vẫn native-only. CER/WER và token trọng yếu đã được đối chiếu trên bốn trang; PSM 4 có CER/WER gộp thấp nhất, còn PSM 6 có recall token số cao nhất trong mẫu nhỏ. Hai tiêu chí cho thứ hạng khác nhau, vì vậy chưa chọn cấu hình OCR tối ưu và chưa đổi mặc định; một trang sơ đồ vẫn có lỗi rất cao. Xem [phép đo OCR và giới hạn](evidence/OCR_DPI_SENSITIVITY_20261007.md). Serializer và sidecar T1/T2 đã được thử trên một bảng hai cột có cấu trúc đơn giản; bảng phân cấp 14×5 ở PDF page 3 vẫn chưa giải quyết ô gộp và chưa đưa vào retrieval. Đã chạy khảo sát kích thước chunk 250/40, 500/80, 750/120 bằng BM25 và BGE-M3; chỉ số dùng nhãn section/page proxy vì chunk ID thay đổi theo cấu hình, do đó chưa đủ để chốt cấu hình. Xem [kết quả và giới hạn](evidence/CHUNK_SIZE_ABLATION_20260929.md). Ngày 07/10 đã so sánh chính sách theo cấu trúc Điều với cửa sổ cố định 500/80 trên cùng G0, dùng 7 câu answerable và 10 exact evidence span; chính sách theo Điều bao phủ 10/10 span, cửa sổ cố định bao phủ 9/10. Kết quả BM25 và BGE-M3 không cùng xu hướng nên chưa đổi default; chi tiết ở [phép thử chính sách chunk](evidence/CHUNK_STRATEGY_ABLATION_20261007.md). Các bước còn lại là mở rộng đánh giá có kiểm soát trên lớp tài liệu/câu hỏi phù hợp và xử lý bảng, scan, hình theo giới hạn quyền riêng tư; kết quả hiện tại chưa khép kín YC4 hoặc YC13.

**Cập nhật 2026-09-28:** Lượt đầu sweep PSM 3/4/6/11/13 ở DPI 200 dùng ba trang reference 107, 109, 136; kết quả lượt này được giữ trong [bảng ban đầu](evidence/OCR_PSM_SWEEP_20260928.md). Sau đó bổ sung PDF page 116 (trang in 109; khối chữ và danh sách), chạy lại đủ bốn trang. [Bổ sung PSM page 116 và số gộp bốn trang](evidence/OCR_PSM_PAGE116_20260928.md) cho thấy PSM 4 thấp nhất theo cả CER/WER gộp, nhưng kết quả còn bị ảnh hưởng bởi độ dài reference page 116 và mẫu nhỏ; mặc định PSM 6 chưa đổi.

**Cập nhật 2026-09-29:** Đã thêm runner [run_chunking_ablation.py](../scripts/run_chunking_ablation.py) để so sánh 250/40, 500/80, 750/120 trên snapshot native-only G0. Metric được gắn rõ là section/page-location proxy, không gọi là exact chunk recall; Dense có 0, 4, 20 chunk vượt giới hạn 1.024 subword tương ứng. Kết quả chi tiết, profile theo loại tài liệu và giới hạn suy luận nằm trong [chunk-size ablation](evidence/CHUNK_SIZE_ABLATION_20260929.md); chưa đổi cấu hình mặc định.

**Cập nhật 2026-10-07:** Sweep trên cùng bốn trang đã có reference được mở rộng thành 24 lượt (DPI 200/300 × PSM 4/6/11). PSM 4 có CER/WER gộp thấp nhất; PSM 6 có recall token số cao nhất trong mẫu nhỏ, nhưng CER/WER gộp cao hơn PSM 4. Nhóm cue điều kiện chỉ có bốn occurrence, nên chưa đủ để đánh giá khả năng nhận dạng điều kiện/phủ định. Không chọn cấu hình OCR tối ưu và không đổi default; kết quả, phương pháp và giới hạn nằm trong [báo cáo độ nhạy OCR](evidence/OCR_DPI_SENSITIVITY_20261007.md). Đây là minh chứng cho việc đã khảo sát sâu hơn một phần xử lý tài liệu đầu vào, không đồng nghĩa YC4 hoặc YC13 đã hoàn thành.

**Cập nhật 2026-10-07 — chiến lược chunk:** Trên G0 native-only, thử BM25 và Dense BGE-M3 local giữa policy theo Điều hiện tại và cửa sổ cố định 500/80 trên tài liệu có cấu trúc. Bộ pilot có 7 câu answerable/10 span, trong đó 6 câu thuộc Quy chế 1727 và 1 câu thuộc Hướng dẫn thực tập; Sổ tay không có câu answerable. Policy hiện tại bao phủ 10/10 span; cửa sổ cố định 9/10. Exact evidence Recall@5 lần lượt là BM25 4/10 so với 6/10, Dense 9/10 so với 8/10; đây là các kết quả trên pilot nhỏ, không phải test độc lập. Vì hai retriever cho xu hướng khác nhau và cửa sổ cố định làm mất độ phủ một span, giữ nguyên default. Xem [báo cáo ablation](evidence/CHUNK_STRATEGY_ABLATION_20261007.md); raw JSON metrics-only được Git-ignore.

**Cập nhật 2026-10-07 — Hybrid Retrieval:** Đã hợp nhất BM25 và Dense BGE-M3 bằng RRF (`k=60`, Top-20 mỗi nhánh, Top-10 đầu ra) trên đúng G0 và bộ pilot 7 câu/10 span. Exact evidence Recall@5: BM25 4/10, Dense 9/10, RRF 6/10; Complete-evidence Hit@5 tương ứng 3/7, 6/7, 4/7. RRF cao hơn BM25 nhưng chưa vượt Dense trong mẫu này, nên chưa đưa Hybrid thành mặc định; cần thêm câu hỏi độc lập trước khi kết luận hoặc chỉnh tham số. Xem [báo cáo Hybrid RRF](evidence/HYBRID_RRF_ABLATION_20261007.md). Phép thử chỉ đánh giá retrieval, không đánh giá generation, citation hay refusal.
