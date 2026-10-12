# Chuẩn bị đánh giá thủ công cho generation pilot

Ngày: 12/10/2026. Đây là bước chuẩn bị phương pháp và dữ liệu xem xét cho YC11, chưa phải kết quả đánh giá semantic.

## Thiết lập

- Corpus snapshot `5da3bd4d5de54492`, partition `development`: 10 câu (7 answerable, 3 unanswerable), cùng bộ câu hỏi đã dùng trong generation pilot trước.
- Hybrid RRF + BGE reranker, trả Top-5 cho generator; Qwen3:4B qua Ollama local loopback. Không dùng model 8B, Gemini hoặc cloud API.
- Mục tiêu bổ sung bundle cục bộ để người học có thể kiểm tra câu hỏi, output và các đoạn nguồn thực sự đã đưa cho generator; đồng thời chỉ xuất phiếu đánh giá gồm ID/nhãn.

## Kết quả chạy và giới hạn

Lượt chạy ngày 12/10 là tái lập cùng snapshot/query/config, không phải tập mới: 7/7 câu answerable có phản hồi; 1/3 câu unanswerable bị từ chối; 7/7 câu answerable có citation về đúng document ID kỳ vọng; 9/9 output đã sinh có citation ID thuộc nguồn đã truy xuất. Một output còn lại bị từ chối do JSON không hợp lệ. Đây là metric vận hành/định tuyến nguồn, không cho biết câu trả lời đúng, faithful hay citation có nâng đỡ claim.

Metadata bundle đã được kiểm tra cục bộ: 10 record với 10 question ID duy nhất, cùng run/snapshot/partition, retrieved sources có ở cả 10 record. Không sao chép nội dung câu hỏi/đáp án/nguồn vào Git. Bundle và phiếu review nằm ngoài repo trong `D:\RAG\private_eval\`.

## Phần đã hiện thực

- `src/rag_hcmute/evaluation/manual_review.py`: kiểm tra schema nghiêm, nhãn hợp lệ, ID trùng/mã lạ, quan hệ answer–claim, một run/snapshot/partition mỗi lần tổng hợp và phân phối nhãn kèm mẫu số.
- `scripts/run_generation_pilot.py --review-bundle-dir`: lưu nội dung review chỉ khi bật rõ ràng; từ chối đường dẫn nằm trong repository; chế độ mặc định metrics-only không đổi.
- `scripts/prepare_manual_review.py`: tạo answer sheet 10 dòng `pending` và claim sheet trống, chỉ chứa ID/metadata/nhãn.
- `scripts/summarize_manual_reviews.py`: sau khi người học chấm, tổng hợp answer correctness, faithfulness, relevance, độ đúng vị trí citation, mức hỗ trợ claim, refusal trên câu unanswerable và false refusal trên câu answerable. Không tạo điểm tổng hợp.
- `docs/evaluation/manual_review_protocol.md` cùng hai template header-only nêu rubric và cách điền.

## Trạng thái

Chưa có nhãn thủ công nào được điền; answer sheet còn 10 dòng `pending`, claim sheet chỉ có header. Do đó chưa được báo cáo bất kỳ kết quả correctness/faithfulness/answer relevance/semantic citation nào. Development pilot không phải holdout, không dùng để hiệu chỉnh ngưỡng cuối. YC11 còn một phần; Mốc 1 không được xem là đóng bởi lượt tái lập này.

Toàn bộ test suite sau thay đổi: **113 passed**; `compileall src scripts tests` và `git diff --check` đạt. Không cài dependency, không gọi API, không push/merge/PR, không sửa DOCX.
