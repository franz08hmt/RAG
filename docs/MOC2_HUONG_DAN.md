# Chạy và kiểm tra gói Mốc 2

## Mục tiêu

Chạy console có nguồn và đọc được dấu vết của từng thành phần. Đây là PoC thực nghiệm
trên snapshot lịch sử G0, không phải nguồn xác nhận quy định học vụ hiện hành.
Không cần API key, không gọi Gemini, không tải model trong các lệnh bên dưới.

## Chạy trên máy hiện tại

Mở PowerShell tại `D:\RAG\rag-hcmute-dot2`. Mở Ollama nếu muốn sinh câu trả lời.

```powershell
.\scripts\demo_m2.ps1
.\scripts\demo_m2.ps1 -Question 'Thủ tục xin nghỉ học tạm thời được quy định ra sao?'
.\scripts\demo_m2.ps1 -Method bm25 -NoAnswer -Question 'Quy định về đăng ký học lại'
```

Không có `-Question`: nhập câu hỏi trực tiếp, gõ `:q` để thoát.
Mặc định sinh bằng Qwen3:4B, không dùng 8B. Tải model lần đầu có thể mất hàng chục giây;
console hiện báo đang tải model, kiểm cache hay đang sinh. Cache chỉ chứa vector, không
phát lại câu trả lời. GPU dùng tuần tự cho truy xuất rồi LLM.

Lượt console Hybrid + reranker 1024 + Qwen3:4B ngày 25/10 đã chạy P007 thành công,
tổng 45,03 giây với cache sẵn. Đây là một lượt, không bảo đảm độ trễ mọi máy.
Nếu gặp WinError 1455 do thiếu RAM/bộ nhớ ảo, dừng lần chạy và dùng `-Method bm25`
để quan sát luồng nhẹ; không tự thay đổi pagefile. Batch tải model tuần tự nhưng
console tương tác vẫn cần đủ RAM để giữ cả hai model truy xuất.

## Năm tình huống để trình bày

1. P007 — nghỉ học tạm thời: mở lại QĐ 1727 trang PDF 23–24, kiểm đúng Điều 17.
2. P002 — rút học phần: phân biệt số ngày/điều kiện trong nguồn với diễn giải của model.
3. P003 — cảnh báo học tập: hỏi cần bao nhiêu đoạn bằng chứng, có bỏ sót điều kiện không.
4. P009 — lịch thi cụ thể: nguồn tĩnh không đủ. Nếu model vẫn trả lời, ghi đó là lỗi.
5. Câu về bảng: dùng năm đào tạo theo tín chỉ của Bảng 5, PDF 20. Giải thích metadata
   bảng bổ sung chưa tự nhập vào chỉ mục; không giả vờ console đã hiểu mọi hình/bảng.

Không đọc một câu trả lời mượt rồi kết luận đúng. Kiểm từng ý theo trang nguồn.
Trích log trong báo cáo được ghi đúng là trích log, không giả làm ảnh chụp màn hình.

## Tái lập thí nghiệm

```powershell
$ragPython='C:\Users\Dell\anaconda3\envs\rag-hcmute\python.exe'
& $ragPython -u scripts/run_m2_controlled_evaluation.py --reranker-model 'D:\RAG\models\huggingface\hub\models--BAAI--bge-reranker-v2-m3\snapshots\953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e'
& $ragPython -u scripts/run_m2_console_demo.py
```

Chạy lần lượt, không chạy hai phép GPU đồng thời. Lệnh đầu dùng 289 cửa sổ cùng ngân sách
token để so embedding/ANN/rerank. Lệnh sau dùng 156 chunk G0 và 10 câu development để so
hai prompt; **hai phép thử có chính sách chunk khác nhau**, không so chéo như chỉ đổi model.
Mỗi lệnh in interpreter. Không dùng env base, không đặt KMP_DUPLICATE_LIB_OK.

Raw số liệu ở `artifacts/results/m2_eval` và `artifacts/results/m2_console`.
Nội dung câu trả lời + toàn bộ context ở `D:\RAG\private_eval\m2_console`, không đưa vào Git.
Bản JSON đã lọc nội dung được bàn giao trong `docs/evidence/m2/runs`.

## Việc không thể thay bằng tự động hóa

Người học cần duyệt nhãn nguồn, tự viết một phần câu hỏi mới và chấm câu trả lời trước khi
đóng băng test. Không chuyển câu AI đề xuất thành `human_verified`, không lấy tập dev đã
điều chỉnh nhiều lần làm test. Phiếu chấm cũ vẫn được giữ nguyên, không điền thay tên người.

Các mục 6 embedding, 3 reranker, 80–100 câu được duyệt, OCR đủ bản chép chuẩn và đo trên
holdout là mục tiêu còn lại của kế hoạch, không được đánh dấu hoàn thành nhờ có DOCX mới.
Mốc 2 hiện là gói tiến độ có thêm kết quả kiểm soát và app chạy được.

## Git và báo cáo

Giữ bản DEMO và Mốc 1 nguyên trạng. DOCX Mốc 2 là file mới. Commit cục bộ sử dụng identity
đang có, thông điệp mô tả công việc; chưa push, merge hay thay đổi PR #2. Toàn văn nguồn,
trọng số, cache và nội dung chấm riêng không được đưa lên repository công khai.
