# Kiểm kê loại tài liệu và luồng xử lý đầu vào — 07/10/2026

## Mục tiêu và cách kiểm tra

Tài liệu này ghi lại corpus HCMUTE hiện có và cách snapshot G0 xử lý từng dạng đầu vào, nhằm trả lời cụ thể câu hỏi của giảng viên về Document Class, Document Chunk, PDF scan, bảng và hình. Số liệu được tổng hợp từ manifest, snapshot G0, build log, metadata của page/chunk JSONL và tham chiếu ảnh nhúng trong PDF bằng PyMuPDF. Script tái lập là [`audit_document_input_profile.py`](../../scripts/audit_document_input_profile.py); JSON tổng hợp nằm cục bộ trong `artifacts/results/input_document_profile/` và không chứa nội dung trích xuất.

Các SHA-256 của ba PDF trong `data/raw/` đều khớp `corpus_manifest.csv`. Snapshot được rà soát là `5da3bd4d5de54492`: 3 tài liệu, 182 trang, 156 chunk. Trạng thái hiệu lực của QĐ 1727/2021 vẫn chưa xác định đầy đủ; QĐ 3116/2025 chưa có trong corpus. Vì vậy, phép thử dùng quy chế này chỉ mô tả snapshot nghiên cứu, không khẳng định quy định hiện hành.

## Thành phần corpus và chunk hiện tại

| Loại ghi trong manifest | Nguồn và dạng cấu trúc | Trang / chunk G0 | Đặc điểm trích xuất và chia chunk |
|---|---|---:|---|
| `quyet_dinh` | QĐ 1727/2021; văn bản phân cấp Chương/Điều, có bảng | 32 / 52 | 31 dấu Điều; 1 chunk phần mở đầu, 23 chunk giữ trọn Điều, 28 chunk Điều dài được chia tiếp. 51/52 chunk có `section_path`; token count median 394, max 504. |
| `huong_dan` | Hướng dẫn thực tập tốt nghiệp FIT; văn bản ngắn, không có cấu trúc Điều | 1 / 1 | Dùng `sliding_window_fallback`; chunk có 388 token, không có `section_path`. |
| `so_tay` | Sổ tay Sinh viên 2024; tài liệu tổng hợp nhiều loại nội dung và bố cục | 149 / 103 | Có 2 dấu Điều, dưới ngưỡng 4 để nhận diện tài liệu có cấu trúc; 103 chunk dùng `sliding_window_fallback`, token count median/max 500, không có `section_path`. Snapshot gắn cờ 26 trang nghi scan/ít text. |

Cấu hình G0 dùng 500 token mục tiêu, overlap 80 token và tokenizer whitespace. Chunker hiện không định tuyến theo `document_type`; nó tìm dấu Chương/Điều bằng mẫu văn bản. Khi có ít nhất bốn dấu Điều, chunker giữ ranh giới Điều và chỉ chia nhỏ Điều dài; nếu không đạt ngưỡng thì dùng cửa sổ trượt. Điều này tạo hành vi khác nhau giữa quy chế, hướng dẫn ngắn và sổ tay, nhưng chưa phải chiến lược được lựa chọn riêng theo từng lớp tài liệu sau một benchmark.

Page `char_count` min/median/max lần lượt là 519/2652/3010 cho quy chế, 1709/1709/1709 cho hướng dẫn và 0/1838/3945 cho sổ tay. Trong PDF nguồn, PyMuPDF ghi nhận trang có ít nhất một tham chiếu ảnh raster ở 2 trang của quy chế (6 tham chiếu), 0 trang của hướng dẫn và 149 trang của sổ tay (239 tham chiếu). Số tham chiếu raster không cho biết ảnh đó là scan, logo, watermark, bảng hay sơ đồ; không được diễn giải thành số lượng hình có nội dung ngữ nghĩa.

Các trang sổ tay bị gắn cờ nghi scan trong snapshot là PDF pages 1, 107, 109–112, 116–117, 121, 123–127, 129–139 và 149. Đây là cờ heuristic dựa trên lượng text native thấp kết hợp ảnh/trang rỗng, không phải nhãn scan đã được xác minh bằng mắt cho cả 26 trang.

## Luồng xử lý đã hiện thực và minh chứng hiện có

1. **Xác minh nguồn:** manifest lưu document ID, loại văn bản, URL, đường dẫn, số trang và SHA-256. Script kiểm kê dừng nếu hash nguồn lệch manifest.
2. **Trích xuất trang:** G0 dùng PyMuPDF `page.get_text("text")`, tách văn bản theo trang và tìm số trang in bằng heuristic ở header/footer. Build log G0 chỉ ghi cấu hình PyMuPDF, không ghi cấu hình OCR; page records G0 cũng không có trường `extraction_method`. Vì vậy, snapshot G0 không chứng minh OCR đã được áp dụng cho các trang nghi scan.
3. **OCR thử nghiệm:** OCR đã được đo riêng trên bốn trang (PDF pages 107, 109, 116, 136), với Tesseract tiếng Việt, DPI 200, các PSM 3/4/6/11/13. Đây là thí nghiệm CER/WER cấp trang, chưa phải kết quả OCR đã tích hợp vào corpus G0. Trên page 136 có sơ đồ, PSM tốt nhất trong lượt bốn trang vẫn có CER 73,62% và WER 80,23%, nên OCR thuần không đủ để coi sơ đồ là văn bản đáng tin cậy.
4. **Làm sạch và nhận diện cấu trúc:** pipeline loại dòng boilerplate lặp theo trang, rồi phát hiện dấu Chương/Điều. Đây là xử lý văn bản; chưa có bước nhận biết ngữ nghĩa hình, sơ đồ hoặc bố cục bảng tự động.
5. **Chunking văn bản:** nội dung trang được nối thành token stream theo whitespace; mỗi chunk ghi document ID, title, trang PDF/trang in, section path nếu có, phương thức chunk, token count và hash nội dung. Trong JSONL G0 đang dùng, các trường `extraction_methods`, OCR confidence và token offsets chưa có; không nên khẳng định các metadata này đã lưu trong snapshot lịch sử.
6. **Bảng:** Bảng 5 ở PDF page 20 (trang in 19) của QĐ 1727 đã được kiểm tra trực quan; đó là bảng hai cột với năm hàng dữ liệu. Thử nghiệm B0/T1/T2 so văn bản baseline, Markdown table và bản ghi theo hàng có ngữ cảnh. Serializer hiện yêu cầu header/hàng được rà soát rõ ràng và không tự điền ô gộp; dữ liệu bảng của ablation được đối chiếu thủ công. Đây chưa phải bộ phát hiện/trích xuất tự động cho mọi bảng trong corpus.
7. **Hình:** pipeline G0 hiện lấy text layer, không tạo caption/alt-text hoặc biểu diễn ngữ nghĩa cho hình. Tham chiếu ảnh raster được dùng trong phát hiện trang có thể cần OCR, không đồng nghĩa hình đã được xử lý như một modality riêng.

## Điểm cần sửa trước khi mô tả đây là pipeline hoàn chỉnh

- **Phân loại trang scan:** 26 trang hiện là candidate theo heuristic. Cần kiểm tra mẫu theo loại layout và đưa nhãn đã xác minh vào manifest/annotation; không nên ghi “OCR xử lý 26 trang” khi lượt OCR chỉ đánh giá bốn trang.
- **Nhãn PDF page 107 đã được rà soát ở mức metadata:** hai ghi chú OCR trước đây không thống nhất. Thống kê hộp OCR PSM 4 (86 đơn vị/15 dòng/8 khối) gần page 136 (79/13/7) hơn các trang chữ nhiều hơn trong mẫu; đây là tín hiệu ủng hộ nhãn infographic/nội dung thị giác hỗn hợp. Độ tin cậy vừa phải vì không phải xác nhận trực quan. Ghi chú cũ “hai trang scan văn bản (107, 109)” đã được sửa; CER/WER giữ nguyên. Chi tiết tại [`OCR_LAYOUT_LABEL_RECHECK_20261007.md`](OCR_LAYOUT_LABEL_RECHECK_20261007.md).
- **Document Class chưa gắn với policy xử lý:** manifest hiện có loại văn bản ở mức nguồn (`quyet_dinh`, `huong_dan`, `so_tay`), nhưng chưa phân loại nội dung theo modality/layout như văn xuôi, bảng, scan, biểu đồ. Chunker cũng chưa dùng lớp đó để chọn chiến lược.
- **Metadata của G0 còn thiếu để truy nguyên OCR:** page/chunk JSONL lịch sử không lưu extraction method, confidence OCR hoặc token offsets. Mã hiện tại đã có hỗ trợ một số trường này, nhưng muốn dùng trong kết quả chính thức cần tạo snapshot mới, ghi cấu hình và hash, rồi đánh giá lại trên cùng bộ câu hỏi; không sửa ngược số liệu G0.
- **Độ phủ thí nghiệm còn nhỏ:** OCR có bốn trang mẫu; table ablation có một bảng và năm câu hỏi. Chưa đủ để kết luận về mọi dạng scan, sơ đồ, bảng nhiều tầng/ô gộp hoặc lớp tài liệu khác.

## Kết luận cho báo cáo tiến độ

Hiện có thể trình bày chắc chắn rằng corpus gồm ba lớp nguồn khác nhau; bộ nạp đang trích xuất text theo trang, nhận diện cấu trúc Điều cho một tài liệu, và dùng sliding window cho các nguồn còn lại. Đã có một số đo về chunk size, OCR cấp trang và biểu diễn một bảng cụ thể. Chưa thể mô tả hệ thống là đã xử lý đầy đủ PDF scan, hình và bảng tổng quát: OCR chưa được xác nhận trong G0, hình chưa được diễn giải ngữ nghĩa, và table parser còn phụ thuộc dữ liệu đã rà soát thủ công.

Theo góp ý giảng viên, bước tiếp theo là chọn mẫu đại diện theo ma trận input class/layout → phương thức trích xuất → loại chunk → tiêu chí kiểm tra tại [`INPUT_CLASS_PROCESSING_MATRIX_20261007.md`](INPUT_CLASS_PROCESSING_MATRIX_20261007.md). Bất nhất mô tả page 107 đã được rà soát và sửa ở mức metadata OCR; nhãn infographic/nội dung thị giác hỗn hợp có độ tin cậy vừa phải, không phải xác nhận bằng mắt. Các việc này vẫn thuộc Mốc 1; chưa cập nhật DOCX cho đến khi nội dung và minh chứng mốc được chốt.

## Tài liệu và mã liên quan

- [`corpus_manifest.csv`](../../data/manifests/corpus_manifest.csv), snapshot và build log G0 trong `data/processed/g0_reproduction/`.
- [`extract.py`](../../src/rag_hcmute/ingestion/extract.py), [`chunk.py`](../../src/rag_hcmute/ingestion/chunk.py), [`sectioning.py`](../../src/rag_hcmute/ingestion/sectioning.py), [`tables.py`](../../src/rag_hcmute/ingestion/tables.py).
- [`OCR_PSM_SWEEP_20260928.md`](OCR_PSM_SWEEP_20260928.md), [`OCR_PSM_PAGE116_20260928.md`](OCR_PSM_PAGE116_20260928.md), [`TABLE_RETRIEVAL_APPROVED_ABLATION_20261005.md`](TABLE_RETRIEVAL_APPROVED_ABLATION_20261005.md).
