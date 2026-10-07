# Ma trận lớp đầu vào và hướng kiểm chứng — 07/10/2026

## Mục đích

Ma trận này chuyển kiểm kê corpus thành một kế hoạch kỹ thuật có thể kiểm tra: với từng dạng nội dung, ghi rõ G0 hiện xử lý thế nào, minh chứng nào đã có, điều gì chưa được chứng minh và phép thử kế tiếp nên trả lời câu hỏi gì. Đây là tài liệu làm việc cho Mốc 1, không phải tuyên bố rằng các nhánh xử lý đã hoàn tất.

Ở đây cần tách hai khái niệm. **Document class** mô tả nguồn ở cấp tài liệu, như quyết định, hướng dẫn hay sổ tay. **Input class/layout** mô tả nội dung ở cấp trang hoặc vùng trang, như văn xuôi có cấu trúc, trang scan, bảng hay sơ đồ. Một tài liệu có thể chứa nhiều input class; vì vậy không nên chọn một cách chunk duy nhất chỉ từ nhãn của cả PDF.

## Ma trận hiện trạng và phần cần kiểm chứng

| Dạng nội dung | Trường hợp đã có trong corpus | Cách đang xử lý và minh chứng | Giới hạn cần nói rõ | Phép thử tiếp theo |
|---|---|---|---|---|
| Văn bản quy chế có cấu trúc Chương/Điều | QĐ 1727/2021: 32 trang, 31 dấu Điều, 52 chunk | PyMuPDF lấy text native; bộ nhận diện dùng dấu Chương/Điều. Tài liệu có ít nhất 4 dấu Điều được chia theo ranh giới Điều; Điều dài mới dùng cửa sổ trượt. G0 có 23 chunk giữ trọn Điều, 28 chunk Điều dài, 1 chunk phần mở đầu; 51/52 chunk có `section_path`. | Đây là quy tắc heuristic trên văn bản trích xuất, không phải hiểu biết ngữ nghĩa đầy đủ về Khoản/Điểm. QĐ 3116/2025 chưa có trong corpus; chưa xác nhận hiệu lực hiện hành của QĐ 1727/2021. | Dùng một nhóm câu hỏi đã được duyệt có bằng chứng ở nhiều Điều và các Điều dài; kiểm tra chunk có giữ tiêu đề, ranh giới và trang nguồn hay không. Đo retrieval theo evidence span/đủ bằng chứng, đồng thời xem lại trường hợp bị cắt hoặc xếp hạng thấp. |
| Hướng dẫn ngắn, không có cấu trúc Điều | Hướng dẫn thực tập FIT: 1 trang, 1 chunk, 388 token | Trích xuất text native, sau đó `sliding_window_fallback`; một chunk chứa toàn văn bản trong snapshot. | Một tài liệu một trang không đủ để kết luận fallback phù hợp cho mọi hướng dẫn. Chưa có so sánh retrieval riêng theo nhiều tài liệu cùng lớp. | Trước mắt kiểm tra truy nguyên câu trả lời về đúng tài liệu/trang trên các câu hỏi phù hợp đã duyệt. Chỉ mở rộng kết luận nếu corpus có thêm tài liệu cùng lớp được phép dùng. |
| Sổ tay văn bản thường và nội dung hỗn hợp | Sổ tay Sinh viên 2024: 149 trang, 103 chunk; chỉ có 2 dấu Điều | G0 không đạt ngưỡng 4 dấu Điều nên toàn bộ chunk dùng `sliding_window_fallback`; không có `section_path`. `char_count` dao động từ 0 đến 3945. | Sổ tay là một nguồn hỗn hợp, không thể gọi toàn bộ là văn bản thường hay toàn bộ là scan. G0 không gắn loại bố cục cho từng trang. | Lập nhãn layout ở cấp trang cho một mẫu nhỏ, rồi xem cửa sổ trượt có làm đứt tiêu đề, mục, danh sách hoặc đoạn dẫn chiếu hay không. Không kết luận thay đổi chunking có lợi nếu chưa chạy cùng bộ câu hỏi và đối chiếu nguồn. |
| Trang scan hoặc có ít text native | Trong sổ tay, 26 trang bị heuristic gắn cờ cần xem xét; không phải nhãn scan đã xác minh. Metadata OCR hiện ủng hộ page 107 là nội dung thị giác hỗn hợp. | Snapshot G0 dùng PyMuPDF `get_text("text")`; log không ghi nhận cấu hình OCR. Riêng một thí nghiệm OCR cấp trang đã thử Tesseract tiếng Việt ở DPI 200 với PSM 3/4/6/11/13 trên bốn trang. | OCR chưa được tích hợp vào snapshot G0. Nhãn page 107 là infographic/nội dung thị giác hỗn hợp với độ tin cậy vừa phải, chưa phải nhãn được xác nhận trực quan. CER/WER không tự bảo đảm các con số hoặc điều kiện quan trọng được nhận dạng đúng. | Chọn trang đại diện theo layout đã ghi nhận. Với mỗi trang, giữ bản chép chuẩn cục bộ và so CER/WER; kiểm tra riêng số, mã, điều kiện quan trọng và khả năng truy về đúng trang. Định trước tiêu chí chấp nhận trước lượt đo tiếp theo. |
| Bảng trong văn bản | Bảng 5, QĐ 1727/2021, PDF page 20 (trang in 19): bảng 2 cột, 5 hàng dữ liệu | Đã thử ba biểu diễn trên cùng 155 chunk nền: B0 giữ biểu diễn gốc, T1 thay bằng một Markdown table, T2 tách hàng có ngữ cảnh. Trên 5 câu đã duyệt, Dense đủ toàn bộ evidence Top-5 đạt 5/5 ở cả ba dạng; BM25 lần lượt 4/5, 1/5, 0/5. | Chỉ một bảng và năm câu, đánh giá retrieval chứ không phải trả lời end-to-end. T1/T2 được dựng từ header/hàng đã rà soát thủ công; đây không phải parser bảng tổng quát và chưa xử lý tự động quan hệ ô gộp. | Bổ sung câu hỏi về truy vấn theo hàng/cột và kiểm tra việc giữ đơn vị, tiêu đề, chú thích, quan hệ nhóm. Nếu có thêm bảng phù hợp trong corpus, thử trên bảng khác với nhãn bằng chứng được người học kiểm tra; giữ kết luận riêng cho từng bảng cho tới khi có đủ mẫu. |
| Sơ đồ, infographic hoặc hình có thông tin | Có ảnh raster trong PDF; riêng OCR pilot trên PDF page 136 là sơ đồ | G0 không tạo caption hay biểu diễn ngữ nghĩa cho hình. Trên page 136, PSM tốt nhất trong lượt bốn trang vẫn có CER 73,62% và WER 80,23%; OCR thuần chưa tạo văn bản đáng tin cậy cho sơ đồ. | Tham chiếu ảnh raster không đồng nghĩa với hình chứa thông tin cần truy xuất. Chưa có đánh giá image-captioning/vision và chưa có pipeline hình riêng. Không gọi dịch vụ API có thể phát sinh phí khi chưa có ước tính được duyệt. | Trước hết phân loại cục bộ hình trang trí, sơ đồ và hình chứa chữ; ghi cấu trúc/nội dung cần truy xuất bằng nhãn do người học kiểm tra. So sánh OCR vùng với mô tả hình chỉ khi có dữ liệu tham chiếu phù hợp và được duyệt chi phí nếu dùng API. Kiểm tra citation phải trỏ về đúng trang/hình. |

Các số liệu OCR gộp và theo PSM được ghi tại [`OCR_PSM_PAGE116_20260928.md`](OCR_PSM_PAGE116_20260928.md). Dù nhãn làm việc của page 107 đã được cập nhật, không dùng kết quả gộp bốn trang để kết luận PSM nào phù hợp cho một layout cụ thể vì mẫu ít và gồm nhiều loại bố cục. Kết quả Bảng 5 được mô tả đầy đủ tại [`TABLE_RETRIEVAL_APPROVED_ABLATION_20261005.md`](TABLE_RETRIEVAL_APPROVED_ABLATION_20261005.md).

## Luồng quyết định nên dùng khi mở rộng xử lý

```text
Nguồn PDF
  └─ xác minh hash và nhận diện document class
      └─ tách trang, ghi text native và metadata trang
          └─ phân loại layout/modality ở cấp trang hoặc vùng
              ├─ văn bản có cấu trúc → chia theo Chương/Điều, rồi xử lý Điều dài
              ├─ văn bản không cấu trúc → sliding window làm baseline
              ├─ bảng → giữ header, hàng, đơn vị và ngữ cảnh nhóm đã xác minh
              ├─ trang scan → OCR thử nghiệm, kiểm tra lỗi và đối chiếu trang gốc
              └─ sơ đồ/hình → chưa coi OCR là đủ; cần nhãn/mô tả có kiểm chứng
                  └─ tạo chunk có provenance → kiểm tra truy xuất và citation
```

Đây là **luồng đề xuất để phân tích**, không phải mô tả pipeline G0 hiện tại. Các nhánh bảng và hình không nên bị nhập chung với chunk văn bản thường vì cách tạo bằng chứng và lỗi có thể khác nhau.

## Trình tự thực hiện để có kết luận đáng tin

1. **Chốt nhãn input class trước khi chạy thêm:** page 107 hiện được gán nhãn làm việc là infographic/nội dung thị giác hỗn hợp dựa trên metadata OCR, độ tin cậy vừa phải. Tiếp tục lập danh sách trang theo các nhóm văn bản có cấu trúc, văn bản thường, scan văn bản, bảng và sơ đồ/hình; có thể gán nhiều nhãn cho một trang nếu nội dung pha trộn. Không cần chép nội dung Sổ tay hoặc dữ liệu cá nhân vào Git.
2. **Chọn phép thử theo câu hỏi của giảng viên:** mỗi phép thử chỉ thay đổi một thành phần (OCR/layout, chunking hoặc cách biểu diễn bảng), giữ cố định corpus còn lại, câu hỏi, nhãn bằng chứng và retriever khi mục tiêu là đo thành phần đó.
3. **Đánh giá đúng tầng:** OCR đo bằng CER/WER và kiểm tra nội dung trọng yếu; chunking kiểm tra ranh giới/metadata/provenance; retrieval đo bằng evidence span, Hit@k/MRR phù hợp với nhãn; câu trả lời và citation chỉ đánh giá khi đã có generation. Không dùng một điểm tổng để che lấp lỗi ở từng tầng.
4. **Ghi rõ phạm vi kết luận:** kết quả Bảng 5, OCR bốn trang và corpus ba tài liệu hiện tại là các nghiên cứu trường hợp nhỏ. Không suy rộng thành quy luật cho mọi bảng, scan, hình hoặc tiếng Việt.
5. **Chỉ đổi cấu hình mặc định sau khi có bằng chứng lặp lại:** giữ nguyên G0 và raw output; tạo snapshot mới có hash/config rõ ràng nếu tích hợp OCR hoặc thay đổi chunking. Không sửa ngược kết quả lịch sử.

## Trả lời trực tiếp yêu cầu của giảng viên

- **Document Class tổ chức ra sao?** Hiện corpus có ba nhãn ở cấp nguồn (`quyet_dinh`, `huong_dan`, `so_tay`); đây là nhóm tài liệu, chưa phải phân loại đầy đủ mọi layout bên trong.
- **Document Chunk tổ chức thế nào?** G0 dùng cấu trúc Điều khi văn bản có ít nhất bốn dấu Điều; trường hợp khác dùng cửa sổ trượt 500 token, overlap 80 theo whitespace tokenizer. Số liệu từng lớp được ghi trong audit, không đồng nhất cách chia cho mọi nguồn.
- **PDF scan, bảng, hình được xử lý thế nào?** Scan mới có OCR thử nghiệm tách riêng, chưa tích hợp G0; một bảng đã được thử bằng ba cách biểu diễn dựa trên dữ liệu kiểm tra thủ công; hình/sơ đồ chưa được diễn giải ngữ nghĩa trong pipeline.
- **Cần làm gì để chứng minh hiểu từng giai đoạn?** Chọn mẫu trang có nhãn layout đã kiểm tra, giải thích phương án và điểm yếu, chạy phép so sánh cô lập, lưu cấu hình/kết quả, rồi phân tích cả trường hợp thành công lẫn thất bại.

## Trạng thái

Đây là bước lập kế hoạch thực nghiệm dựa trên audit, chưa chạy thêm benchmark và chưa thay đổi code/pipeline mặc định. Mốc 1 vẫn đang được làm sâu theo YC4/YC13; chưa chuyển sang Mốc 2 và chưa cập nhật DOCX nộp giảng viên. Nếu cần nhãn layout chắc chắn bằng mắt, người học có thể xác nhận page 107 trên máy cá nhân; không cần gửi ảnh hoặc chữ trang ra ngoài máy.

## Tài liệu liên quan

- [`INPUT_DOCUMENT_CLASS_AUDIT_20261007.md`](INPUT_DOCUMENT_CLASS_AUDIT_20261007.md) — nguồn số liệu corpus và giới hạn G0.
- [`OCR_PSM_SWEEP_20260928.md`](OCR_PSM_SWEEP_20260928.md) và [`OCR_PSM_PAGE116_20260928.md`](OCR_PSM_PAGE116_20260928.md) — thí nghiệm OCR cấp trang.
- [`TABLE_RETRIEVAL_APPROVED_ABLATION_20261005.md`](TABLE_RETRIEVAL_APPROVED_ABLATION_20261005.md) — ablation retrieval Bảng 5.
- Mã liên quan: `src/rag_hcmute/ingestion/extract.py`, `sectioning.py`, `chunk.py`, `tables.py`.
