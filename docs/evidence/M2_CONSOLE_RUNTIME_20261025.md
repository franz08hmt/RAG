# Console và generation Mốc 2

## Các lượt chạy thực tế

- Cold console: `artifacts/results/m2_console/cold.json`, Hybrid + reranker 512,
  P007, 156 chunks G0, Qwen3:4B local; exit thành công. Khởi tạo 57,61 s,
  retrieval/rerank 1,14 s, sinh 76,62 s. S1 chỉ được kiểm tra ID.
- Batch hai prompt: `m2_console_20261024T130313Z`, 10 câu development × 2 prompt,
  cùng kết quả hybrid/rerank 1024. Tải embedding và reranker lần lượt để giảm RAM;
  giải phóng chúng trước khi Qwen3 sinh. Hoàn thành đủ 20 lượt, không gọi cloud.
- Kiểm tra console trực tiếp ngày 25/10: `warm_interactive_20261025.json`, cùng P007,
  reranker 1024, cache hit, exit 0. Khởi tạo 30,407 s; truy xuất/rerank 1,367 s;
  sinh 12,400 s; tổng 45,032 s. Không truncation trên 20 cặp. Hạng đầu là
  `HCMUTE_QCDT_1727_2021__c0038`, PDF 23–24, Điều 17. S1 hợp lệ về ID.

Cold/warm không phải một benchmark tăng tốc: khác thời điểm, tải máy và giới hạn
reranker, mỗi cấu hình chỉ một lượt. Cache vector thực sự đã tránh nhúng lại corpus;
không dùng cache câu trả lời để thay suy luận.

## Kết quả hai prompt

Cả standard và scope_check: 7/7 câu answerable có output mang citation ID hợp lệ,
0/3 câu unanswerable có `model_abstained`. P006 thiếu căn cứ nhưng vẫn sinh;
P009 lỗi citation, P010 lỗi JSON. Hai lỗi định dạng không tính như từ chối đúng.
Không có chấm người, nên không báo accuracy/faithfulness hoặc citation entailment.
Không chọn scope_check làm mặc định vì lượt thử này chưa cho thấy lợi ích rõ.

## Lỗi tài nguyên được giữ trong nhật ký

Một thử nghiệm batch trước đó thất bại với WinError 1455 khi nạp đồng thời hai model
truy xuất trong lúc máy thiếu bộ nhớ ảo. Không đổi pagefile, không đóng ứng dụng của
người dùng. Batch được đổi sang tải tuần tự và đã chạy xong. Ngày 25/10 bộ nhớ rảnh
nhiều hơn; console trực tiếp đã chạy được cả embedding, reranker và Qwen3 theo cơ chế
chuyển GPU về CPU. Không khẳng định cấu hình này chạy ổn định ở mọi trạng thái RAM.

## Dữ liệu riêng và tái lập

JSON metrics-only: `docs/evidence/m2/runs/console_generation.json`, `console_cold.json`,
`console_warm.json`. Toàn văn câu trả lời và context lưu cục bộ ngoài repo tại
`D:\RAG\private_eval\m2_console\20261024T130313Z`. Log console trong artifacts bị bỏ qua
bởi Git; không công bố preview nguồn khi chưa rà PII.

Chạy theo `docs/MOC2_HUONG_DAN.md`. Nếu thiếu tài nguyên, dùng `-Method bm25` cho luồng
nhẹ hoặc chạy batch riêng; không âm thầm đổi phương pháp rồi báo là hybrid-rerank.
