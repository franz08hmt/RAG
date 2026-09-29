# Rà soát ngân hàng câu hỏi ứng viên

**Ngày rà soát:** 2026-09-29  
**Phạm vi:** đối chiếu 12 câu trong `data/question_sets/question_candidates_for_student_review.csv` với văn bản đã trích xuất trong snapshot G0.  
**Thay đổi dữ liệu:** không sửa CSV, không sửa pilot, không gán nhãn và không chạy metric.

## Kết quả rà từng câu

| ID | Nhận xét | Vị trí nguồn nên gắn nhãn | Việc cần làm trước khi duyệt |
|---|---|---|---|
| C001 | Nội dung câu hỏi khớp với khoản 1 Điều 2; không trùng câu hỏi tốt nghiệp P001. | QĐ 1727, PDF tr. 2, Điều 2 khoản 1. | Thu hẹp `source_reference` từ tr. 2-3 về tr. 2. Khi gắn nhãn, lấy đủ các nhóm thông tin được liệt kê, không kéo nội dung thời gian học ở khoản 8 sang. |
| C002 | Câu hỏi định lượng, có nhiều đơn vị khác nhau; phù hợp để kiểm tra việc truy hồi đủ các vế thay vì chỉ tìm một con số. | QĐ 1727, PDF tr. 6, Điều 3 khoản 4(a). | Giữ; kiểm tra đủ đơn vị và khoảng giá trị. Có thể cần nhiều đoạn evidence trong cùng trang. |
| C003 | Câu hỏi rõ điều kiện và hai giới hạn; chi tiết 15 giờ/tuần và 4 giờ/ngày nằm ở trang 10. | QĐ 1727, PDF tr. 10, Điều 8 khoản 4. | Thu hẹp `source_reference` từ tr. 9-10 về tr. 10; giữ cụm “khi cần xếp lịch học tập trung” để không biến ngoại lệ thành quy tắc chung. |
| C004 | Phù hợp với khoản 1 Điều 11; khác câu P001-P010. Câu hiện hỏi đồng thời danh sách hình thức và nguyên tắc kết hợp điểm. | QĐ 1727, PDF tr. 14, Điều 11 khoản 1(a-b). | Thu hẹp `source_reference` từ tr. 14-15 về tr. 14. Khi duyệt, xác nhận đây là một câu hai phần và gold evidence phải trả lời cả hai phần. |
| C005 | Ý tưởng có căn cứ nhưng cách hỏi hiện tại có thể gộp hai trường hợp: giới hạn trực tuyến nói chung/ngoại lệ do thiên tai, dịch bệnh và trường hợp riêng về bảo vệ đồ án/khóa luận trực tuyến với các điều kiện cụ thể. | QĐ 1727, PDF tr. 15, Điều 11 khoản 2. | Chỉnh trước khi duyệt: hoặc hỏi riêng giới hạn và ngoại lệ chung, hoặc hỏi riêng ba điều kiện của buổi bảo vệ trực tuyến. Không gán một nhãn đơn nếu chưa quyết định phạm vi câu hỏi. |
| C006 | Định nghĩa ĐTBTL nằm trên trang 19; câu hỏi đang giới hạn đúng vào nhóm học phần được tính. | QĐ 1727, PDF tr. 19, Điều 12 khoản 1(d). | Giữ; nếu muốn câu hỏi đơn nghĩa hơn, thêm “theo đào tạo tín chỉ” và kiểm tra ý loại trừ học phần không đạt. |
| C007 | Câu hỏi số liệu rõ, câu trả lời trực tiếp ở khoản 5 Điều 15. | QĐ 1727, PDF tr. 22, Điều 15 khoản 5. | Giữ; khi diễn đạt đáp án phải nêu rõ mẫu số là khối lượng học tập tối thiểu của chương trình, không chỉ ghi tỷ lệ. |
| C008 | Điều kiện chuyển chương trình/ngành được nêu ở khoản 1 Điều 18. Cần phân biệt với các khoản sau về chuyển trường và thủ tục. | QĐ 1727, PDF tr. 24, Điều 18 khoản 1. | Thu hẹp `source_reference` từ tr. 24-25 về tr. 24; câu hỏi hiện tại không hỏi điều kiện chuyển trường. |
| C009 | Có ích để kiểm tra truy hồi điều kiện thay thế: sinh viên phải đạt mốc trình độ năm học và một trong hai nhánh học lực, kèm điều kiện khác của Trường. | QĐ 1727, PDF tr. 25-26, Điều 20 khoản 2. | Giữ; annotation cần ghi cả hai nhánh “khá” và “trung bình”, không chỉ một ví dụ. Khoản 3 về trường hợp phải dừng học không thuộc câu hỏi hiện tại, không đưa vào gold evidence. |
| C010 | Có căn cứ rõ ở khoản 2 Điều 22. Dù cùng có kết quả “buộc thôi học” như P008, nguyên nhân và điều khoản khác nhau: thi hộ so với tiến độ học tập. | QĐ 1727, PDF tr. 26, Điều 22 khoản 2. | Giữ; giữ cụm “thi hộ/nhờ thi hộ” để câu không lẫn với P008. |
| C011 | Khác P005: P005 hỏi thời điểm đăng ký học phần; C011 hỏi hồ sơ/minh chứng cuối đợt thực tập. Nguồn nêu báo cáo có nhật ký theo tuần và nhận xét, điểm của người hướng dẫn tại công ty. | Hướng dẫn TTTN của FIT, PDF tr. 1, mục II.2. | Giữ; người duyệt nên xác nhận muốn hỏi các tài liệu nộp cho GVHD hay toàn bộ quy trình thực tập. Không suy diễn thêm biểu mẫu chưa có trong tài liệu. |
| C012 | Truy hồi được từ Sổ tay Sinh viên 2024, nhưng đây là phần trích Quyết định 409/QĐ-ĐHSPKT (2024), không phải xác nhận rằng quy định vẫn hiện hành. Ngưỡng tín chỉ và điểm trung bình được nêu ở trang 38. | Sổ tay Sinh viên 2024, PDF tr. 38, mục học bổng khuyến khích học tập 1-2. | Chỉ giữ nếu mục tiêu là hỏi “theo Sổ tay Sinh viên 2024”. Thu hẹp `source_reference` từ tr. 38-39 về tr. 38; trước khi dùng làm hướng dẫn chính sách hiện tại, cần đối chiếu văn bản gốc và trạng thái áp dụng. |

## Trùng lặp và độ phủ

- Không phát hiện câu trùng trực tiếp với P001-P010. C011 cùng tài liệu một trang với P005 nhưng kiểm tra một thông tin khác; C010 có kết quả kỷ luật gần với P008 nhưng kiểm tra căn cứ vi phạm khác.
- Nên sửa tham chiếu trang cho C001, C003, C004, C008 và C012; các tham chiếu này hiện rộng hơn phần bằng chứng tối thiểu cần thiết. C005 cần chỉnh phạm vi câu hỏi trước khi tạo gold evidence.
- 12 ứng viên hiện chủ yếu kiểm tra truy hồi nội dung văn bản. Chúng chưa tạo bằng chứng riêng cho câu hỏi phụ thuộc bảng, PDF scan/OCR hoặc nội dung nằm trong hình. Đây vẫn là khoảng trống cần xử lý ở bước khảo sát các trang OCR/bảng/hình; không nên tuyên bố bộ câu hỏi này đã kiểm tra đầy đủ YC4.
- QĐ 1727 có tình trạng thay thế/chỉnh sửa chưa được xác minh trong hồ sơ dự án. Khi đánh giá retrieval trên snapshot, có thể hỏi nội dung “theo QĐ 1727”; không dùng kết quả này để khẳng định chính sách hiện hành.

## Quyết định chờ người học

Tất cả 12 câu vẫn ở trạng thái `draft_not_in_pilot`. Cần người học đối chiếu nguồn, tự sửa hoặc xác nhận cách diễn đạt, và quyết định C005 có tách phạm vi hay không. Chỉ sau bước đó mới tạo annotation exact-span và đưa câu được duyệt vào một lần chạy evaluation riêng.
