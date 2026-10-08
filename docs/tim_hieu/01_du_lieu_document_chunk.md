# 01. Tài liệu, Document Class, Chunk và truy nguyên nguồn

## 1. Corpus không chỉ là một thư mục PDF

Một câu trả lời chỉ đáng tin nếu biết nó xuất phát từ tài liệu nào, phiên bản nào, trang nào và đoạn nào. Vì vậy mỗi nguồn cần metadata quản lý vòng đời: `document_id`, tiêu đề, cơ quan ban hành, loại văn bản, ngày ban hành/hiệu lực (nếu xác minh được), URL nguồn, ngày lấy, SHA-256, quyền sử dụng, trạng thái đưa vào corpus và lý do loại bỏ. Manifest trả lời câu “đã ingest đúng tệp nào?”, còn snapshot manifest gắn cấu hình làm sạch/chunking với lần build cụ thể.

G0 của project là snapshot lịch sử cố định, không mặc nhiên là corpus có hiệu lực pháp lý hiện nay. Ba tệp đã xác minh tạo thành 182 trang và 156 chunks. Quyết định 3116/2025 được tải riêng ngoài repository, nhưng là PDF scan có text layer nhiễu; chưa có bản chép OCR được kiểm tra đầy đủ nên không đưa vào G0. Việc nêu rõ ranh giới này quan trọng hơn việc làm corpus trông lớn hơn.

## 2. Document Class và các dạng đầu vào

Document Class mô tả cấu trúc có ý nghĩa nghiệp vụ của cả tài liệu; lớp nội dung ở từng trang có thể khác nhau. Một văn bản có thể có trang văn xuôi, bảng, dấu/ảnh scan và biểu đồ. Nên ghi lớp ở mức tài liệu và page/layout ở mức trang thay vì gán một nhãn duy nhất cho cả PDF.

| Lớp/đặc điểm | Dấu hiệu | Cách xử lý ban đầu | Rủi ro cần kiểm tra |
|---|---|---|---|
| Quy chế có cấu trúc | Chương, Điều, Khoản, Điểm | Trích xuất theo trang; nhận diện section; chunk ưu tiên ranh giới Điều/Khoản | Số điều mất, tiêu đề tách khỏi khoản, tham chiếu chéo |
| Hướng dẫn ngắn | Tiêu đề, bước thực hiện, ít trang | Giữ đoạn/mục hoàn chỉnh, tránh chunk quá nhỏ | Mất quan hệ giữa điều kiện và bước kế tiếp |
| PDF scan | Trang ảnh, lớp text rỗng/nhiễu | Render trang, OCR có cấu hình và lưu provenance | OCR nhầm chữ/số, sai cột, sai thứ tự đọc |
| Bảng | Hàng/cột, ô gộp, tiêu đề lặp | Giữ tiêu đề cột và ngữ cảnh hàng; biểu diễn một hàng hoặc nhóm hàng | Ô gộp/multi-row mất liên hệ; dữ liệu sai cột |
| Hình/sơ đồ | Nội dung nằm trong ảnh | OCR vùng chữ; mô tả hình có kiểm duyệt nếu thật sự cần | OCR không hiểu quan hệ không gian/ý nghĩa hình |

Không phải mọi trang ảnh đều có thể sửa bằng OCR. OCR nhận diện ký tự; nó không khôi phục chắc chắn cấu trúc bảng hoặc suy luận nội dung hình. Trước khi dùng, cần so khớp với ảnh gốc, đặc biệt với số hiệu, điều kiện, dấu phủ định và con số. Tesseract khuyến nghị cân nhắc độ nghiêng, độ phân giải và chế độ phân đoạn trang; chúng là tham số cần ghi lại, không phải thiết lập tối ưu mặc định cho mọi tài liệu [2].

## 3. Hai dạng PDF: text layer và ảnh scan

Với PDF có text layer tốt, native extraction giữ được chữ và tọa độ nhanh hơn OCR; vẫn phải kiểm tra header/footer lặp, thứ tự cột, số trang PDF so với trang in và ký tự tiếng Việt. Với scan, trích xuất native có thể trả văn bản rỗng hoặc nhiễu; OCR tạo văn bản dự đoán, do đó phải lưu `extraction_method`, trang gốc, cấu hình DPI/PSM và confidence nếu có.

Trong mẫu OCR 4 trang của Sổ tay, PSM 4 tại 200 DPI có CER/WER gộp tốt nhất trong các cấu hình đã thử, nhưng trang infographic vẫn có CER/WER rất cao; cấu hình tốt nhất theo tổng ký tự không đồng nghĩa phù hợp từng layout. Mẫu còn nhỏ, không đủ để khẳng định cài đặt chung. OCR hiện là nhánh tùy chọn, G0 vẫn native-only.

## 4. Mô hình dữ liệu đề xuất

**Document** đại diện cho nguồn và phiên bản. **Page** giữ text đã trích xuất cùng số trang PDF và thông tin extraction. **Chunk** là đơn vị retrieval; nội dung chunk phải kèm `document_id`, `document_sha256`, `pdf_page_start/end`, `printed_page` nếu kiểm chứng được, `section_path`, `chunk_id`, `chunking_policy`, `extraction_method` và nguồn vị trí. Câu trả lời nên giữ citation tới chunk ID, sau đó resolve chunk ID ra tên văn bản, trang và điều/mục. Nếu thiếu mapping này, citation chỉ là nhãn trang trí.

Metadata không nên nhồi toàn bộ vào embedding. Một context prefix ngắn như tên văn bản/chương/điều có thể giúp embedding hiểu đoạn đang nói về gì; metadata có cấu trúc vẫn lưu riêng để lọc/truy nguyên. Không được lấy tên mới của cơ quan để thay tên cơ quan ban hành trên văn bản lịch sử.

## 5. Chunking: vì sao không có một kích thước luôn đúng?

Chunk quá nhỏ dễ tách điều kiện, ngoại lệ hoặc tên Điều khỏi nội dung; chunk quá dài đưa nhiều nội dung không liên quan, làm tăng context và có thể vượt giới hạn model. Overlap giữ phần tiếp giáp nhưng tạo trùng lặp, index lớn hơn và có thể làm các top-k kết quả gần như lặp lại.

Các phương án chính:

- **Fixed window theo token/ký tự:** dễ tái lập, làm baseline; điểm cắt không hiểu cấu trúc pháp lý.
- **Recursive splitter theo dấu phân đoạn:** ưu tiên đoạn, câu, dòng, rồi mới cắt cứng; cân bằng tổng quát, nhưng không bảo đảm ranh giới Điều.
- **Section-aware/hierarchical:** tách Chương/Điều/Khoản trước, dùng window trong đơn vị quá dài; giữ ngữ cảnh pháp lý tốt hơn nhưng phụ thuộc parser và chất lượng tiêu đề.
- **Semantic chunking:** cắt theo thay đổi ngữ nghĩa; có thể giữ chủ đề, nhưng tốn thêm model/chi phí và ranh giới khó giải thích.
- **Table-aware:** giữ tiêu đề cột/đơn vị và các hàng liên quan cùng nhau; cần quy tắc riêng, không nên coi bảng chỉ là văn bản tuần tự.

Ở phép thử 250/40, 500/80 và 750/120 token theo splitter của project, BM25 tìm được lần lượt 5/10, 4/10, 4/10 exact span ở Top-5; dense BGE-M3 đạt 10/10, 9/10, 9/10. Complete-evidence Hit ở dense là 7/7, 6/7, 6/7. Kích thước corpus thay đổi từ 297 xuống 156 và 111 chunks. Đây chỉ là development pilot; 250/40 có kết quả tốt hơn ở retrieval nhưng làm index lớn hơn, chưa đủ để chọn nếu chi phí, câu trả lời và test độc lập chưa đo.

Thử nghiệm policy theo Điều và fixed windows cũng cho kết quả trái chiều giữa BM25 và dense. Điều đó gợi ý giữ ranh giới Điều làm mặc định cho quy chế có cấu trúc, nhưng phải tiếp tục quan sát tài liệu khác; một pilot không chứng minh một chính sách tối ưu cho mọi Document Class.

### Tài liệu đọc

1. [Tesseract User Manual — improving quality and page segmentation](https://tesseract-ocr.github.io/tessdoc/ImproveQuality.html).
2. [PyMuPDF documentation](https://pymupdf.readthedocs.io/en/latest/).
3. Gao et al. (2024), [RAG survey](https://arxiv.org/abs/2312.10997), phần indexing/chunking.
