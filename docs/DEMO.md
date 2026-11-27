# Kịch bản trình bày console RAG

Chạy tại thư mục dự án trên PowerShell. Dùng Python 3.11 của env rag-hcmute và Ollama với qwen3:4b. Khởi động Ollama trước, kiểm tra bằng ollama list. Snapshot G0 gồm ba tài liệu học vụ đã được trích xuất. Cấu hình được chọn là BM25 + BGE-M3, RRF k=60, 50 ứng viên mỗi nhánh, không reranker; Qwen3 dùng JSON Schema và context 8.192. BM25 đơn lẻ vẫn có thể chọn để đối chứng.

~~~powershell
Set-Location D:\RAG\rag-hcmute-dot2
$ragPython = 'C:\Users\Dell\anaconda3\envs\rag-hcmute\python.exe'
$bgeModel = 'D:\RAG\models\huggingface\hub\models--BAAI--bge-m3\snapshots\5617a9f61b028005a4858fdac845db406aefb181'
& $ragPython -c "import sys; print('Python executable:', sys.executable)"
& $ragPython -m rag_hcmute.console_app --method hybrid --dense-model $bgeModel --answer --prompt-variant scope_schema --context-window 8192
~~~

Nhập từng câu rồi gõ :q để kết thúc. Kiểm văn bản PDF theo các trang dưới đây. Model có thể trả sai ở lần chạy mới, kể cả khi cùng cấu hình.

1. **Thủ tục xin nghỉ học tạm thời được quy định ra sao?** Mở QĐ 1727 trang PDF 23–24, Điều 17. Đối chiếu nơi nhận đơn và hai thời hạn nộp trước khi nghỉ và khi học tiếp.
2. **So sánh thời gian thiết kế và số tín chỉ tối thiểu của cử nhân chính quy và vừa làm vừa học theo Bảng 1.** Mở trang PDF 3, giữ đúng nhãn nhóm hàng. Đáp án theo bảng lần lượt là 4 năm và 5 năm, cùng 120 tín chỉ.
3. **Điều kiện để đăng ký học chương trình thứ hai là gì?** Mở Điều 20, trang PDF 25–26. Đọc cả thời điểm sớm nhất và hai trường hợp điều kiện học lực.
4. **Thư viện công cộng ở Cần Thơ mở cửa sáng Chủ nhật lúc mấy giờ?** Corpus HCMUTE không chứa lịch của thư viện này. Ghi nhận model có thực sự từ chối hay trả lời sai.
5. **Đã học môn A nhưng chưa đạt, điều kiện đăng ký môn B khi A là học trước hoặc tiên quyết là gì?** Mở Điều 3, trang PDF 5. Câu này từng làm model trả lời lạc đề hoặc thiếu một nhánh điều kiện; nếu lần chạy hiện tại đúng, vẫn giải thích lỗi ở log cũ thay vì yêu cầu model tạo ra lỗi.

Có thể chạy từng câu một bằng cách thêm --query "câu hỏi". Để chạy lại cả năm câu và lưu log cục bộ, chọn một thư mục mới ngoài repo:

~~~powershell
.\scripts\demo_v4_rrf.ps1 -OutputDirectory 'D:\RAG\private_eval\demo_rrf_lan_chay_moi'
~~~

Thời gian phụ thuộc vào máy, trạng thái nạp mô hình và độ dài context. Theo các lượt đo trước với BM25 và mô hình đã được nạp, mỗi câu thường mất vài giây; lần nạp đầu có thể lâu hơn. Nếu thiếu VRAM hoặc Ollama không phản hồi, dùng chế độ truy xuất BM25 không sinh câu trả lời để vẫn giải thích được nguồn:

~~~powershell
& $ragPython -m rag_hcmute.console_app --method bm25 --query 'Thủ tục xin nghỉ học tạm thời được quy định ra sao?'
~~~

Không dùng log cũ như câu trả lời vừa chạy. Log chứa câu hỏi, đoạn nguồn và câu trả lời, được giữ ngoài Git. Lệnh BM25 ở trên là cấu hình đối chứng hoặc dự phòng, không phải cấu hình RRF đã chọn.

## Lượt RRF ngày 27/11/2026

Run `console_rrf_20261127T011915Z` có 4/5 lượt thành công về mặt kỹ thuật. Câu ngoài phạm vi gặp `invalid_or_missing_citation`; thông báo không tìm thấy căn cứ không được tính là từ chối hợp lệ. Câu Bảng 1 vẫn dẫn nhầm metadata Điều 15; câu chương trình thứ hai thiếu điều kiện về năm học; câu học trước/tiên quyết gộp hai điều kiện. Nhật ký đầy đủ lưu ngoài repo, tại thư mục `D:\RAG\private_eval\final_20261115\demo_v4_20261127a`. Không xem trạng thái thành công kỹ thuật là kiểm chứng nội dung.

Sau khi ràng buộc hai nhánh schema, lượt `console_rrf_v5_20261127T013434Z` có năm lượt hoàn tất kỹ thuật, trong đó câu ngoài phạm vi được đánh dấu `model_abstained`. Đây là một lần chạy; chưa kết luận câu trả lời hoặc khả năng từ chối chính xác. Log cục bộ nằm tại `D:\RAG\private_eval\final_20261115\demo_v5_20261127a`.
## Lượt chạy ngày 25/11/2026

Năm lượt hoàn tất về mặt vận hành, tổng thời gian từng câu 10,81; 7,45; 8,84; 7,01 và 8,38 giây. Đây là thời gian của một lần chạy trên máy, không phải cam kết độ trễ. Tệp log đầy đủ ở D:\RAG\private_eval\final_20261115\demo_v2_20261125 và thống kê mã hóa ở docs/evidence/v2/demo_console.json.

- Câu 1 trả nội dung hai thời hạn và trỏ trang 23–24.
- Câu 2 trả đúng số trong bảng nhưng metadata section_path gắn nhầm Điều 15; cần chỉ ra lỗi nhận diện đề mục và đối chiếu trực tiếp Bảng 1 ở trang 3.
- Câu 3 nêu hai điều kiện học lực nhưng thiếu yêu cầu đã xếp trình độ năm thứ hai.
- Câu 4 trả trạng thái model_abstained.
- Câu 5 trả điều kiện môn học trước nhưng bỏ điều kiện môn tiên quyết.
