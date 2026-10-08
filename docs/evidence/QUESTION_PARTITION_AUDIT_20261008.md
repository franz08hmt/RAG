# Kiểm tra phân hoạch tập câu hỏi — 08/10/2026

## Mục đích

Tách rõ câu hỏi dùng để phát triển cấu hình khỏi các bộ câu hỏi có mục đích khác. Việc phân hoạch nằm ở
sidecar manifest để không cần sửa nội dung câu hỏi/gold chỉ để thêm metadata. Validator chỉ đọc ID,
trạng thái duyệt và mã snapshot; không in câu hỏi, đáp án hoặc văn bản nguồn.

## Trạng thái manifest

`data/question_sets/question_partition_manifest.csv` ghi nhận:

- 10 câu P001–P010 trong `pilot_questions.csv`: `development`.
- 5 câu TB001–TB005 về Bảng 5: `ablation_only`, không gộp vào benchmark pilot tổng quát.
- Snapshot tham chiếu: `5da3bd4d5de54492`.
- Câu hỏi holdout độc lập: hiện chưa có.

Đây là ghi nhận mục đích của các bộ hiện có, không phải kết quả benchmark mới và không chứng minh chất
lượng tổng quát hóa. Các metric đã có vẫn là development evidence.

## Cơ chế kiểm soát

`load_pilot_questions()` kiểm tra manifest trước khi nạp câu hỏi và chỉ trả về ID thuộc partition được
yêu cầu; mặc định là `development`. CLI `scripts/run_pilot_eval.py` cho phép chọn `development` hoặc
`holdout`. Các runner ablation đang gọi loader mặc định nên tiếp tục chỉ dùng development.

Exact-evidence loader nhận chính các ID đã chọn, kiểm tra gold span trong phạm vi đó và không đưa
annotation của partition khác vào kết quả. Nếu CSV, manifest, trạng thái duyệt hoặc snapshot không khớp,
quy trình dừng thay vì tự suy đoán cách phân nhóm.

Hai script đọc trực tiếp bộ câu hỏi Bảng 5 (`evaluate_table_ablation.py` và
`diagnose_bm25_query_sensitivity.py`) cũng đối chiếu ID với partition `ablation_only` trước khi chạy.

Tái lập kiểm tra manifest:

```powershell
python scripts/audit_question_partitions.py
```

## Điều kiện trước khi có holdout

Holdout cần được người học tự tạo/đối chiếu với tài liệu, có nhãn answerability và exact evidence được
duyệt, rồi mới đăng ký ID và snapshot. Không dùng holdout để chọn chunking, embedding, retrieval, reranker
hoặc prompt. Nếu corpus snapshot thay đổi, evidence annotation cần được kiểm tra lại trước khi so sánh.
