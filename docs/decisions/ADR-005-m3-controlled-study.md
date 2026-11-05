# ADR 005 So sánh chunking và kiểm tra đầu ra trước khi mở rộng Mốc 3

Ngày 04/11/2026. YC3, YC5, YC10, YC11, YC13. Trạng thái: triển khai thực nghiệm trên development; chưa đổi cấu hình console mặc định.

## Vấn đề và quyết định

Mốc 2 có so sánh embedding đã loại truncation, nhưng chưa có sáu chính sách chia đoạn dùng cùng giới hạn encoder và ngân sách context. Việc đưa nhiều văn bản hơn vào Top-5 có thể làm tăng recall mà không phản ánh hiệu quả khi LLM bị giới hạn đầu vào.

Đợt này tạo module thực nghiệm riêng, giữ nguyên G0 và splitter vận hành. Sáu chính sách: giới hạn ký tự làm tròn theo đơn vị khoảng trắng, token thật, ưu tiên phân cấp dấu ngắt, câu theo heuristic dấu câu, cấu trúc Điều và semantic theo tương đồng của các đơn vị liên tiếp. Tất cả dùng giới hạn BGE 384 token kể cả special tokens, overlap bằng 0; character có thêm trần 1.200 ký tự. Recursive là cài đặt phục vụ học cơ chế ưu tiên ranh giới, không khẳng định tương đương thuật toán LangChain.

Semantic dùng các đơn vị câu đã cắt để vừa encoder, nhúng BGE-M3, chọn ranh giới có cosine thuộc 25% thấp nhất trong từng tài liệu. Đây là một cấu hình khảo sát, không phải ngưỡng tối ưu đã được chứng minh. Nhúng để tìm ranh giới có chi phí riêng; dùng cùng BGE cho chia semantic và retrieval có thể tạo thiên lệch, cần nói rõ.

Mỗi chính sách được đánh giá bằng BM25 và BGE-M3, cùng bảy câu answerable dev. Đo Top-5 và chọn các chunk nguyên vẹn từ Top-50 theo ngân sách 1.000/2.000 token Qwen3. Cách xếp context đi theo thứ hạng, bỏ qua đoạn không vừa; không đọc gold khi chia hoặc chọn context. Token count đo chuỗi ghép có dấu phân cách, chưa tính câu hỏi, system prompt, nhãn nguồn hoặc chat template. Không gọi đây là toàn bộ chi phí prompt.

## Generation và nhãn đánh giá

Thử ba hợp đồng đầu ra trên cùng các nguồn truy xuất đã lưu ở Mốc 2: JSON thông thường, cùng prompt nhưng ép schema, và evidence_first yêu cầu liệt kê yêu cầu của câu hỏi rồi trích quote cho từng claim. Evidence_first kiểm quote có tồn tại sau chuẩn hóa NFC/khoảng trắng và tự dựng citation từ source ID hợp lệ. Không kiểm được entailment chỉ bằng substring.

Chỉ `model_abstained` được tính vào tỷ lệ model từ chối. Trạng thái lỗi JSON, thiếu citation hoặc quote không có trong nguồn được tính riêng là chặn đầu ra. Phiếu chấm người cũ không có nguyên nhân từ chối nên hai chỉ số tổng hợp được đổi tên thành output_withheld_rate, tránh diễn giải sai; schema CSV cũ được giữ tương thích.

Chưa đưa evidence_first thành mặc định console. Chỉ nâng cấu hình sau kết quả dev và chấm ngữ nghĩa đủ căn cứ. Không chọn theo tỷ lệ JSON hợp lệ đơn thuần.

## Dữ liệu và người chấm

Chuẩn bị gói review riêng ngoài repository: 10 câu pilot, 12 đề xuất nội dung và 5 đề xuất bảng, 10 trang để chép chuẩn, cùng output generation mới. Mọi phiếu mới pending, không đổi nhãn pilot lịch sử. Bộ mới chưa đủ mục tiêu 80–100 câu; chưa tạo test. Validator kiểm trùng, snapshot, nhóm rò rỉ, evidence quote, trường người duyệt và độ phủ nhóm; không xác nhận thay người chấm.

## Nguồn đã mở đọc ngày 04/11/2026

- [Ollama Structured outputs](https://docs.ollama.com/capabilities/structured-outputs): schema truyền qua trường format; vẫn cần kiểm tra ứng dụng.
- [BGE-M3 model card](https://huggingface.co/BAAI/bge-m3): cơ chế và cách dùng model; 384 là giới hạn thử nghiệm của dự án, không phải chiều dài tối đa công bố của model.
- [Qwen3-4B model card](https://huggingface.co/Qwen/Qwen3-4B): tokenizer và model nền. Đợt này chỉ tải file tokenizer/config, không tải trọng số Qwen mới; inference dùng model Ollama đã có.
- [LangChain recursive splitter](https://docs.langchain.com/oss/python/integrations/splitters/recursive_text_splitter): tham khảo cách ưu tiên dấu phân cách; không dùng thư viện này trong cài đặt thử nghiệm mới.

## Giới hạn và điều kiện tiếp theo

Ngày 05/11 đã đo sáu embedding trên 1.175 đoạn chung và ba reranker ở ba độ sâu trên G0. Tách hai phép thử vì chúng dùng cách chia đoạn khác nhau. BGE-M3 đứng đầu về độ phủ Top-5 trên bảy câu ở phép so embedding. Với fusion 75% dense, BGE v2-m3 độ sâu 20 tăng độ phủ từ 0,913 lên 1,000. Giữ các cấu hình này làm ứng viên để kiểm lại trên test. [Số liệu và quy trình tái lập](../MOC3_HUONG_DAN.md)

Một mức kích thước/overlap và bảy câu dev chưa đủ để kết luận cho câu hỏi độc lập. Còn cần bản chép chuẩn OCR, đánh giá nội dung hình, phiếu chấm câu sinh và test đã khóa. Dữ liệu nguồn, bản chép và câu trả lời giữ ở máy dự án.
