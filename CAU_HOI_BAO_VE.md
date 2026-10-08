# Câu hỏi tự kiểm tra khi trình bày Mốc 1

Các câu trả lời dưới đây là khung ngắn để luyện giải thích; khi bảo vệ cần chỉ ra code, file evidence hoặc một kết quả cụ thể. Không trình bày kết quả pilot như kết luận phổ quát.

1. **RAG là gì?** — Một kiến trúc kết hợp truy xuất bằng chứng bên ngoài với bước sinh câu trả lời có điều kiện theo bằng chứng đó.
2. **RAG có phải một LLM không?** — Không. RAG là pipeline; retriever, vector index và generator là các thành phần có thể thay thế.
3. **RAG khác fine-tuning thế nào?** — RAG lấy tri thức từ kho lúc truy vấn; fine-tuning cập nhật tham số model. Hai cách giải quyết nhu cầu khác nhau và có thể kết hợp.
4. **RAG có loại bỏ hallucination không?** — Không. Lỗi extraction, retrieval, context hoặc generation vẫn dẫn đến câu trả lời không có căn cứ.
5. **Search, IR và RAG khác nhau ra sao?** — Search là từ rộng; IR là phương pháp biểu diễn/truy vấn/xếp hạng thông tin; RAG dùng retrieval rồi đưa kết quả vào generation.
6. **BM25 có phải semantic search không?** — Không. BM25 là lexical retrieval nhưng vẫn là một kỹ thuật IR.
7. **Document và chunk khác nhau thế nào?** — Document đại diện nguồn/phiên bản; chunk là đơn vị nhỏ được index và trả về làm evidence.
8. **Vì sao phải giữ metadata trong chunk?** — Để xác định tài liệu, phiên bản, trang, section và truy ngược citation.
9. **SHA-256 dùng để làm gì?** — Nhận diện chính xác tệp nguồn và phát hiện tài liệu thay đổi giữa các lần build.
10. **PDF text layer và PDF scan khác nhau ở đâu?** — Text PDF có ký tự máy đọc được; scan chủ yếu là ảnh nên cần OCR và kiểm tra lại với trang gốc.
11. **OCR confidence có chứng minh chính xác không?** — Không. Nó là tín hiệu chất lượng của engine, không thay cho đối chiếu văn bản vàng.
12. **Vì sao bảng cần xử lý riêng?** — Quan hệ hàng/cột, tiêu đề và ô gộp có thể mất khi flatten thành chuỗi; chunk cần giữ ngữ cảnh cột/hàng.
13. **Vì sao giữ ranh giới Điều/Khoản?** — Tên Điều và điều kiện có thể bị tách, làm đoạn retrieval mất chủ thể/ngữ cảnh pháp lý.
14. **Chunk quá nhỏ gây vấn đề gì?** — Có thể thiếu định nghĩa, ngoại lệ hoặc tiền đề cần để hiểu mệnh đề.
15. **Chunk quá lớn gây vấn đề gì?** — Context có nhiễu, tốn token, có thể bị cắt và làm giảm độ chính xác evidence.
16. **Overlap có tác dụng và chi phí gì?** — Giữ thông tin sát ranh giới nhưng làm tăng số chunk và trùng lặp kết quả.
17. **Evidence-span Recall@k đo gì?** — Tỷ lệ span bằng chứng vàng xuất hiện trong top-k trên tổng số span vàng.
18. **Complete-evidence Hit@k khác gì?** — Đếm câu hỏi có đủ tất cả span cần thiết trong top-k; hữu ích cho câu hỏi nhiều căn cứ.
19. **MRR đo gì?** — Trung bình nghịch đảo thứ hạng của evidence liên quan đầu tiên.
20. **Embedding biến đổi gì?** — Văn bản thành vector số để so sánh gần nghĩa trong không gian biểu diễn.
21. **BM25 phù hợp với truy vấn nào?** — Truy vấn chứa từ/cụm, mã quyết định, số điều hoặc tên gọi giống nguyên văn.
22. **Dense retrieval mạnh ở đâu và yếu ở đâu?** — Có thể tìm paraphrase nhưng có thể trượt ở mã/số chính xác và không bảo đảm đủ evidence.
23. **RRF làm gì?** — Hợp nhất thứ hạng nhiều danh sách bằng reciprocal-rank score, không cộng thẳng các thang điểm khác nhau.
24. **Reranker có thể cứu evidence không được truy xuất không?** — Không. Nó chỉ xếp lại các candidate đã nhận.
25. **Vì sao không gọi BGE-M3 là model tốt nhất?** — Chỉ so hai model trên pilot development; E5 còn bị truncation nhiều và chưa có holdout.
26. **FAISS và Qdrant khác gì trong project?** — FAISS là thư viện index gọn; Qdrant local thêm persistence/payload; phép exact search nhỏ cho top-10 giống nhau nhưng vận hành khác.
27. **Vì sao không kết luận từ latency hiện tại?** — Chỉ 156 vector, 7 query, chạy local trên một máy; không đại diện tải thực tế.
28. **Citation hợp lệ nghĩa là gì?** — Ít nhất ID phải resolve tới nguồn đúng; để chứng minh cần kiểm nội dung nguồn có hỗ trợ mệnh đề hay không.
29. **Khi nào hệ thống nên từ chối?** — Khi corpus/context không chứa đủ căn cứ; quyết định cần được đánh giá bằng answerable và unanswerable đã rà soát.
30. **Refusal pilot hiện nói gì?** — Chỉ 1/3 câu unanswerable được ghi nhận là non-answer; hai câu khác vẫn sinh nội dung không căn cứ, nên không thể gọi guard đạt.
31. **Vì sao test set phải tách khỏi dev?** — Dev dùng chọn cấu hình; dùng cùng câu để tune rồi báo điểm sẽ làm kết quả lạc quan.
32. **RAGAS có thay đánh giá thủ công không?** — Không. Đây là framework metric tự động, một số cần LLM judge; cần audit mẫu và kiểm tra độ tin cậy.
33. **Tại sao chưa tạo 100 câu hỏi ngay?** — Mỗi câu cần gold evidence và trang được xác minh; không tự sinh đáp án chuẩn bằng LLM.
34. **QĐ 3116 vì sao chưa vào corpus?** — Bản tải được là PDF scan với text layer nhiễu; OCR chưa được kiểm chứng đủ, nên đưa vào sẽ làm sai benchmark.
35. **PoC hiện đã làm được gì?** — Có ingestion/snapshot, BM25/dense/hybrid/rerank, console, local generation thử nghiệm và các phép đo retrieval/process.
36. **PoC chưa làm được gì?** — Chưa có holdout, đánh giá semantic correctness/citation, refusal đáng tin, số model theo rubric hoặc parser tổng quát cho hình/bảng.
37. **Vì sao không dùng UI bóng bẩy?** — Giảng viên yêu cầu tập trung vào hiểu từng tầng; console đủ để kiểm tra luồng và chứng minh lựa chọn kỹ thuật.
38. **Nếu retriever lấy sai thì LLM có thể bù không?** — Không đáng tin cậy; generator thường bị ràng buộc bởi context sai, nên cần phân tích retrieval trước generation.
39. **Làm sao tái lập một kết quả?** — Ghim snapshot/hash, split, model revision, tham số, script, run ID và lưu metric raw không chứa text nhạy cảm.
40. **Điều gì quyết định khi nào Mốc 1 đóng?** — Có giải thích/so sánh từng YC với bằng chứng đủ, câu hỏi đã rà, giới hạn được xử lý và giảng viên đánh giá; không phải chỉ vì đã viết DOCX.
