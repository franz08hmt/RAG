# Câu hỏi chuẩn bị bảo vệ đồ án RAG

Các câu hỏi bám theo báo cáo và hồ sơ kết quả. Khi trình bày, mở đúng bảng, trang PDF hoặc lượt console được nhắc tới. Các kết luận dưới đây áp dụng cho snapshot G0 và cấu hình đã chạy.

## Bài toán và dữ liệu

1. **Ứng dụng giải quyết việc gì?** Tìm đoạn học vụ liên quan trong kho PDF HCMUTE rồi trả lời bằng tiếng Việt, kèm đường dẫn về văn bản và trang.
2. **Tìm kiếm và RAG khác nhau ở đầu ra nào?** Tìm kiếm trả danh sách tài liệu hoặc đoạn. RAG dùng các đoạn đã truy xuất làm ngữ cảnh để tổng hợp câu trả lời.
3. **RAG gốc của Lewis khác PoC ở đâu?** Công trình gốc huấn luyện bộ mã hóa truy vấn và mô hình sinh, giữ chỉ mục tài liệu cố định trong giai đoạn đó. PoC ghép các mô hình có sẵn khi suy luận.
4. **Tại sao chia quy trình thành hai pha?** Đọc PDF và tạo chỉ mục có thể chạy một lần cho mỗi snapshot. Mã hóa truy vấn, xếp hạng và sinh câu trả lời chạy cho từng câu.
5. **G0 gồm những gì?** Ba tài liệu, 182 trang, 156 đoạn ở cấu hình baseline. Manifest ghi nguồn, phiên bản và SHA-256 để chạy lại.
6. **Nếu có quyết định học vụ mới thì xử lý ra sao?** Xác minh nguồn và quan hệ hiệu lực, tạo snapshot mới rồi chạy lại các phép đo chịu ảnh hưởng. Thí nghiệm G0 dùng văn bản lịch sử đã khóa.
7. **Document, PageText và Chunk khác nhau thế nào?** Manifest mô tả toàn văn bản. PageText giữ văn bản và vị trí trang. Chunk lưu đoạn dùng cho truy xuất cùng khóa tài liệu, trang và khoảng nguồn.
8. **Truy từ citation về PDF thế nào?** Từ mã S1 tra GroundingSource, từ đó lấy Chunk và document_id rồi mở dải trang PDF. Số trang PDF có thể khác số in trên tài liệu.
9. **Nhận diện scan ra sao?** Xem lượng chữ, cấu trúc lớp chữ và vùng ảnh. Trang có ảnh có thể vẫn có lớp chữ dùng được. Kiểm lại các trường hợp không rõ trên ảnh trang.
10. **CER và WER đo điều gì?** Số thao tác sửa ký tự hoặc từ cần thiết để khớp bản chép tham chiếu, chia cho độ dài tham chiếu. Lỗi một chữ số có thể đổi nghĩa dù CER thấp.
11. **Sổ tay trang 116 minh họa điều gì?** OCR tạo lớp chữ dài hơn lớp chữ native. Cần bản tham chiếu để quyết định phần nào đọc đúng. Kết quả bốn trang OCR trước đó cho thấy DPI cao hơn có khi làm sai nhiều hơn.
12. **Tại sao bảng cần cấu trúc hàng và cột?** Một giá trị đứng riêng có thể gắn nhầm hệ đào tạo hoặc cột đơn vị. Bảng 1 có hai hàng cử nhân dễ nhầm nếu mất nhãn nhóm.
13. **Nếu câu hỏi cần hiểu hình?** Cần cơ chế lưu vùng ảnh và diễn giải quan hệ, rồi kiểm trên câu hỏi gắn với vùng đó. OCR chỉ cung cấp chữ trong ảnh.

## Truy xuất và xếp hạng

14. **Overlap có tác dụng gì?** Lặp phần ranh giới giúp giảm nguy cơ một ý bị cắt đôi. Giá phải trả là nhiều đoạn và nội dung lặp trong Top-5.
15. **Vì sao so sáu thuật toán với cùng trần token?** Để quan sát ảnh hưởng của điểm cắt khi hạn đầu vào được giữ cố định. Phép quét kích thước và overlap là thí nghiệm riêng.
16. **Token của chunk có giống token của embedding không?** Baseline dùng đơn vị tách theo khoảng trắng. Encoder và generator có tokenizer riêng. Cần đo độ dài thực sự trước khi so sánh.
17. **Sáu embedding được so công bằng ra sao?** Dùng cùng 1.175 đoạn vừa giới hạn 128 token ở cả sáu tokenizer, giữ tiền tố hoặc tách từ theo từng model. Điều kiện này khác phép thử 289 đoạn ở Mốc 2.
18. **Vì sao cần đúng query/passage prefix?** Một số model được huấn luyện với hai tiền tố để diễn đạt vai trò đầu vào. Phép bỏ tiền tố là đối chứng và cần đọc cả Recall lẫn thứ hạng.
19. **Kết luận gì về embedding tiếng Việt?** BGE-M3 dẫn đầu mẫu học vụ theo giao thức sáu model đã chạy. Các câu và tài liệu chuyên ngành khác cần thí nghiệm riêng.
20. **FAISS và Qdrant khác gì trong demo?** FAISS cung cấp chỉ mục vector. Qdrant lưu vector cùng payload và áp điều kiện tìm kiếm theo metadata. Bài thử lọc tài liệu đối chiếu cùng một tập vector.
21. **Vì sao lọc sau lấy Top-5 có thể trả thiếu?** Các đoạn thuộc tài liệu mục tiêu có thể đứng ngoài Top-5 toàn kho. Phép lọc trước xếp hạng chỉ xét tập đủ điều kiện.
22. **Flat, HNSW và IVF có trade-off nào?** Flat tính với mọi vector. HNSW đi qua đồ thị láng giềng. IVF tìm trong một số cụm. So hàng xóm, tốc độ, khâu xây chỉ mục và RAM trên cùng vector.
23. **BM25 và dense mạnh ở đâu?** BM25 khai thác từ khóa, tên và mã. Dense có thể bắt gặp cách diễn đạt khác từ vựng. Với hồ sơ thực tế, kiểm từng ví dụ trên danh sách xếp hạng.
24. **RRF và Weighted75 hợp kết quả ra sao?** RRF cộng điểm từ thứ hạng. Weighted75 chuẩn hóa điểm theo từng nhánh trong danh sách ứng viên rồi gán trọng số dense 0,75 và BM25 0,25.
25. **Reranker làm gì khi ứng viên bỏ sót bằng chứng?** Chỉ có thể sắp lại các đoạn đã nhận. Cần kiểm cả độ phủ của danh sách ứng viên và độ dài cặp mà cross-encoder đọc.
26. **Vì sao độ phủ tăng mà MRR có thể giảm?** Các đoạn đầu có thể phủ tổng cộng nhiều ký tự bằng chứng hơn trong khi đoạn liên quan đầu tiên lại tụt hạng. Bảng chạy mở rộng có cả hai chỉ số.

## Sinh câu trả lời và kiểm chứng

27. **Citation hợp lệ về ID có đủ không?** Cần đối chiếu cả phát biểu, đúng văn bản, đúng trang và điều kiện. F07 với BM25 lấy đoạn nói về chương trình thứ hai trong khi câu hỏi hỏi về tiên quyết.
28. **Tại sao đo cả câu thiếu căn cứ?** Hệ thống cần biết khi nào nên trả lời. Với U01 và U13, quy chế chung không xác nhận bảng điểm cá nhân hoặc quy định của trường khác.
29. **Khi nào tính là model chủ động từ chối?** Khi đầu ra hợp lệ và yêu cầu từ chối. JSON hỏng, citation sai hoặc lỗi kết nối được ghi riêng.
30. **JSON Schema cải thiện được gì?** Hạn chế dạng khóa và kiểu dữ liệu đầu ra. Mức đúng, đủ ý và hỗ trợ của nguồn phải chấm riêng.
31. **Đánh giá truy xuất khác đánh giá sinh ở đâu?** Chỉ số ký tự so vùng nguồn được lấy với vùng tham chiếu. Chấm sinh kiểm đáp án, từng ý và trích dẫn, cả khi dữ liệu truy xuất đã đủ.
32. **Tại sao chưa gọi số liệu mới là test độc lập?** Câu hỏi do AI soạn từ một tài liệu của G0 và đã được dùng quan sát lỗi. Bộ test độc lập cần câu chưa dùng để chọn cấu hình và nhãn đối chiếu nguồn.
33. **Có thể trình bày kết quả console nào?** Chạy câu về nghỉ học tạm thời, mở Điều 17 và gạch ra thời hạn, nơi nộp. Sau đó chạy một câu thiếu hồ sơ cá nhân để giải thích trạng thái thực tế.
34. **Điều gì cần giữ khi chạy lại?** Snapshot và SHA-256, file câu hỏi, thứ tự các đoạn ngữ cảnh, revision embedding và reranker, digest Ollama, prompt, cửa sổ ngữ cảnh và định nghĩa chỉ số.
