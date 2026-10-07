# Danh sách mẫu đại diện cho kiểm chứng input class — 07/10/2026

## Mục đích

Tài liệu này chuyển ma trận đầu vào thành một danh sách trang có thể dùng cho các lượt kiểm tra extraction, chunking và retrieval tiếp theo. Đây là **sampling plan**, không phải bộ test đã đóng băng và không phải kết quả benchmark. Tất cả mẫu hiện tại thuộc corpus HCMUTE; chưa bổ sung nguồn ngoài.

Việc chọn mẫu cần đại diện cho layout nhưng cũng phải giữ được provenance, bảo vệ dữ liệu cá nhân và tách nhãn đã xác minh khỏi nhãn suy đoán. Một trang có thể mang nhiều nhãn, chẳng hạn văn bản scan kèm hình.

## Mẫu đề xuất

| Vai trò trong phép thử | Nguồn / trang PDF | Vì sao được chọn | Trạng thái nhãn và cách dùng |
|---|---|---|---|
| Văn bản quy chế có cấu trúc | QĐ 1727/2021, PDF page 12 | Trang đã xuất hiện trong quá trình rà soát bằng chứng cho pilot; dùng làm ví dụ văn bản có cấu trúc Điều và citation trang. | Nguồn/đoạn bằng chứng đã được rà soát trong nghiên cứu trước; không suy rộng từ một trang. Kiểm tra `section_path`, ranh giới chunk và trang nguồn. |
| Điều khoản kéo qua trang | QĐ 1727/2021, PDF pages 23–24 | Câu P007 cần bằng chứng ở cả hai trang; đây là trường hợp kiểm tra khả năng giữ đủ evidence và truy nguyên nhiều trang. | Có nhãn exact-evidence trong sidecar pilot. Dùng như ca kiểm thử nhiều trang, không gộp thành một trang giả lập. |
| Bảng | QĐ 1727/2021, PDF page 20 (trang in 19), Bảng 5 | Đã kiểm tra trực quan; có ablation B0/T1/T2 với năm câu hỏi đã duyệt. | Nhãn bảng đã xác minh. Dùng làm bảng đối chứng hiện có; không coi là đại diện cho bảng nhiều tầng/ô gộp. |
| Tài liệu hướng dẫn ngắn | Hướng dẫn FIT, PDF page 1 | Tài liệu chỉ có một trang và một chunk G0; hữu ích để kiểm tra baseline khi toàn tài liệu nằm trong một chunk. | Loại nguồn đã xác định; kiểm tra citation/tính đầy đủ trên nội dung phù hợp đã duyệt. Không dùng một tài liệu để khái quát mọi hướng dẫn. |
| Văn bản thường trong Sổ tay, ứng viên theo metadata | Sổ tay 2024, PDF page 10 | Được chọn tự động trong nhóm trang không bị G0 gắn cờ probable-scan, có ít nhất 1.000 ký tự native; `char_count=1.995`, gần median nhóm này `1.983,5` nhất (108 trang). | **Chưa xác nhận layout bằng mắt và chưa sàng lọc riêng tư tại trang.** Chỉ dùng sau khi người học kiểm tra cục bộ rằng trang phù hợp làm văn bản thường và không đưa thông tin cá nhân vào tập chia sẻ. Nếu không phù hợp, chọn trang kế tiếp theo cùng quy tắc. |
| Trang chữ kèm hình minh họa | Sổ tay 2024, PDF page 109 | Đã có reference cục bộ và kết quả OCR trong sweep ban đầu; đại diện cho trang chữ không thuần, có yếu tố hình ảnh. | Nhãn làm việc theo ghi chú OCR; dùng phân tích lỗi OCR/layout, không gọi đây là trang chữ thuần. Reference không đưa vào Git/hội thoại. |
| Nhiều khối chữ/danh sách | Sổ tay 2024, PDF page 116 (trang in 109) | Đã có phép thử OCR bổ sung và reference cục bộ; bố cục có nhiều vùng chữ và danh sách. | Nhãn layout đã mô tả trong ghi chú OCR; dùng so sánh PSM và kiểm tra thứ tự đọc. Không lưu hypothesis OCR trong repo. |
| Infographic / nội dung thị giác hỗn hợp | Sổ tay 2024, PDF page 107 | Có OCR text nhưng bố cục phân mảnh; thống kê PSM 4 gần mẫu sơ đồ hơn trang chữ dày. | Nhãn làm việc độ tin cậy vừa phải. Chỉ dùng như ca exploratory; không tính là nhãn vàng cho phân loại layout nếu chưa được xác nhận trực quan trên máy. |
| Sơ đồ | Sổ tay 2024, PDF page 136 | Đã có thí nghiệm OCR; ngay PSM tốt nhất trong mẫu vẫn có CER 73,62% và WER 80,23%. | Nhãn sơ đồ đã có trong ghi chú OCR. Dùng làm ca lỗi/giới hạn của OCR thuần; không coi OCR là bản mô tả đúng sơ đồ. |

## Cách chia mẫu theo câu hỏi nghiên cứu

Không cần chạy tất cả các trang trong một thí nghiệm. Mỗi lượt nên giữ câu hỏi và đầu ra phù hợp với tầng đang kiểm tra:

1. **Trích xuất và OCR:** lấy page 109, 116, 107 và 136 làm nhóm layout đa dạng; page 109/116 là ca có chữ, 107 là nội dung thị giác hỗn hợp, 136 là sơ đồ. So CER/WER cùng kiểm tra các trường thông tin trọng yếu; riêng page 107 giữ nhãn có độ tin cậy vừa phải.
2. **Chunking và provenance:** dùng QĐ pages 12 và 23–24 để kiểm tra cấu trúc/ranh giới Điều, FIT page 1 làm đối chứng tài liệu ngắn, và QĐ page 20 để quan sát cách biểu diễn bảng. Chỉ thay đổi chiến lược chunking hoặc cách biểu diễn, không đồng thời đổi retrieval model.
3. **Kiểm tra văn bản thường trong Sổ tay:** page 10 là ứng viên theo metadata, chưa đưa vào tập chia sẻ cho tới khi được kiểm tra layout và quyền riêng tư cục bộ. Giữ như một ca bổ sung, không bắt buộc để tái lập các phép thử OCR cũ.

## Tiêu chí tối thiểu trước khi coi mẫu là hợp lệ

- **Nhãn và provenance:** ghi document ID, PDF page, hash nguồn và trạng thái nhãn; phân biệt `confirmed`, `probable` và `candidate`.
- **OCR:** dùng cùng ảnh nguồn, DPI, ngôn ngữ, model và PSM; báo CER/WER theo trang, không chỉ số gộp. Đối chiếu riêng mã số, con số, điều kiện và tiêu đề vì một vài ký tự sai có thể đổi nghĩa.
- **Chunking:** kiểm tra ranh giới Điều/đoạn/bảng, metadata trang và việc giữ đủ các span bằng chứng; ghi lại trường hợp bị chia cắt.
- **Retrieval:** sử dụng câu hỏi và gold evidence được người học duyệt; báo evidence-span coverage/complete-evidence Hit@k và đọc các lỗi cụ thể. Các trang mẫu đơn lẻ chỉ hỗ trợ phân tích ca, không tạo tuyên bố tổng quát.
- **Hình và dữ liệu cá nhân:** không gửi ảnh/text của Sổ tay hoặc derived sensitive text lên dịch vụ bên ngoài. Chưa dùng Gemini/vision API; mọi lượt có thể phát sinh phí cần estimate và phê duyệt trước.

## Việc cần hoàn tất trước lượt thực nghiệm mới

1. Người học kiểm tra cục bộ ứng viên Sổ tay page 10 về loại bố cục và thông tin cá nhân; nếu không đạt, chọn trang gần median tiếp theo trong nhóm metadata tương tự.
2. Nếu muốn dùng page 107 làm nhãn chính thức, xác nhận trực quan cục bộ; nếu chưa xác nhận, giữ nhãn `probable_visual_mixed` và chỉ phân tích exploratory.
3. Chốt câu hỏi/gold riêng cho thí nghiệm tiếp theo, không sửa pilot hiện tại hoặc gộp câu hỏi bảng vào benchmark chung khi chưa có phê duyệt.
4. Tạo snapshot và log mới nếu thay đổi extractor, OCR hay chunker; không ghi đè G0 hoặc raw results cũ.

## Trạng thái

Danh sách này là kế hoạch chọn mẫu cho YC4/YC13, chưa chạy một benchmark mới và chưa thay đổi pipeline mặc định. Mốc 1 vẫn đang được hoàn thiện; DOCX nộp giảng viên chưa được cập nhật ở bước này.

## Tài liệu liên quan

- [`INPUT_CLASS_PROCESSING_MATRIX_20261007.md`](INPUT_CLASS_PROCESSING_MATRIX_20261007.md)
- [`INPUT_DOCUMENT_CLASS_AUDIT_20261007.md`](INPUT_DOCUMENT_CLASS_AUDIT_20261007.md)
- [`OCR_LAYOUT_LABEL_RECHECK_20261007.md`](OCR_LAYOUT_LABEL_RECHECK_20261007.md)
- [`OCR_PSM_SWEEP_20260928.md`](OCR_PSM_SWEEP_20260928.md), [`OCR_PSM_PAGE116_20260928.md`](OCR_PSM_PAGE116_20260928.md)
- [`CHUNK_SIZE_EXACT_EVIDENCE_20260929.md`](CHUNK_SIZE_EXACT_EVIDENCE_20260929.md), [`TABLE_RETRIEVAL_APPROVED_ABLATION_20261005.md`](TABLE_RETRIEVAL_APPROVED_ABLATION_20261005.md)
