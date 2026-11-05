# Duyệt dữ liệu trước thí nghiệm Mốc 3

Gói review mới nằm ngoài repo, đường dẫn được ghi trong handoff Mốc 3. Mở START_HERE.html để xem câu hỏi, trang nguồn và output. CSV UTF-8 là nơi ghi nhãn; các file nguồn và run gốc không bị sửa.

## Câu hỏi

Gói đầu có 27 mục: 10 pilot để kiểm lại bằng chứng, 12 đề xuất nội dung và 5 đề xuất bảng. Không phải 27 câu mới hoặc test đã duyệt. Pilot giữ development. Câu gần trùng hoặc cách diễn đạt khác của cùng yêu cầu cần cùng leakage_group; validator bắt trùng trực tiếp nhưng không thay được rà ngữ nghĩa của người học.

Điền answerability, reference_answer, nguồn và quote trong evidence_json. Với câu không trả lời được, reference_answer ghi phản hồi mong đợi và absence_review_note ghi phạm vi đã kiểm; không kết luận thiếu căn cứ từ một lượt retrieval thất bại. Với câu có đáp án, mỗi quote ghi document_id và pdf_page; dùng đúng nội dung của snapshot. Nếu có nhiều nguồn đúng, ghi đủ các vị trí. Không dùng dấu ba chấm thay cho toàn bộ evidence liên tục.

Trạng thái human_verified chỉ do người học đặt sau khi đọc, cùng verified_by và verified_at. created_by phân biệt human và AI đề xuất; imported_origin_not_reverified có nghĩa chưa xác minh nguồn tạo lịch sử, không tự tính là người viết. Mục tiêu ít nhất 30% câu do người học viết. Các nhãn nhóm phân cách bằng dấu |, gồm requires_table_or_image, multi_span, lexical_gap.

Mục tiêu 100 câu, tối thiểu 80; ít nhất 15 câu thiếu căn cứ, 10 bảng/hình/scan, 10 đa nguồn, 20 khác từ vựng. Nhóm có thể chồng lấp. Dev/test khoảng 30/70 là mục tiêu thiết kế; khi phân nhóm để tránh rò rỉ có thể lệch nhẹ và phải ghi tỷ lệ thật. Validator chưa tự chia hay đóng băng test.

Lệnh audit sau khi điền, gọi đúng Python dự án:

```powershell
& 'C:\Users\Dell\anaconda3\envs\rag-hcmute\python.exe' scripts/audit_m3_review.py --input 'D:\RAG\private_eval\m3_review\<run>\question_review.csv' --output 'artifacts/results/m3/review_audit_new.json'
```

Không ghi đè output audit cũ. ready_for_freeze chỉ xác nhận kiểm tra cấu trúc, độ phủ mục tiêu và quote; cần kiểm lại nhãn/phân tầng và tạo manifest split có hash trước khi dùng test. Không coi nhãn đúng schema là bằng chứng người chấm đã hiểu đúng quy chế.

## Trang OCR

Mười trang G0 được chọn để đối chiếu text layer, bảng và trang nhiều hình. Đây không phải mẫu ngẫu nhiên đại diện toàn corpus và không phải mười trang thuần scan. native_draft.txt là bản trích máy; gold.txt ban đầu để trống. Người học chép/sửa theo ảnh, ghi người duyệt trong ocr_review.csv. Phần scan QĐ3116 riêng chỉ đưa vào phép thử với phạm vi/snapshot riêng, không nhập lẫn G0.

Chỉ tính CER/WER sau khi bản chép đã duyệt, với cùng chuẩn hóa. Bảng cần thêm đối chiếu hàng/cột, không kết luận chất lượng bảng chỉ từ CER. Nếu hình không có chữ, OCR không thể tự tạo mô tả nội dung hình.

## Câu trả lời

generation_review.csv giữ run ID, question ID, variant và generation_status. Các cột nội dung để trống: correctness, faithfulness, relevance, citation support, vị trí citation và lý do từ chối. Các cột người chấm cần tuân theo rubric tại manual_review_protocol.md; bảng gói Mốc 3 là worksheet, chưa phải CSV thay thế trực tiếp cho bộ tổng hợp cũ.

Không tính invalid_model_json hoặc invalid_evidence_quote là model từ chối đúng. Một câu được xuất ra có quote hợp lệ vẫn có thể diễn giải sai điều kiện. Ghi lỗi cụ thể khi duyệt; chưa có review thì báo pending, không tự điền tỷ lệ đúng.
