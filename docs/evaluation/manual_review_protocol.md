# Quy trình chấm thủ công câu trả lời và trích dẫn

**Mục đích.** Bổ sung đánh giá ngữ nghĩa còn thiếu sau generation pilot. Quy trình này tách ba câu hỏi: hệ thống trả lời đúng không, nội dung có được nguồn hỗ trợ không, và citation có trỏ đúng vị trí nguồn không. Không gộp chúng thành một “điểm RAG” duy nhất.

## Phạm vi và nguyên tắc

- Trước mắt chỉ dùng partition `development` đã được duyệt; 10 câu hiện có là pilot nhỏ, không phải test độc lập. Không dùng kết quả này để tuyên bố tổng quát hóa hoặc hiệu chỉnh ngưỡng cuối.
- Chấm cùng một `run_id`, corpus snapshot, partition và cấu hình. Không trộn output giữa các lần chạy hoặc đổi câu hỏi sau khi đã chạy.
- Người chấm cần xem câu hỏi, câu trả lời và toàn bộ đoạn nguồn đã cấp cho generator trên máy cục bộ. Nếu đối chiếu với PDF gốc, dùng đúng snapshot/hash đã ghi nhận và phân biệt số trang PDF với số trang in.
- Gold answerability/evidence phải do sinh viên đối chiếu tài liệu. Nhãn do mô hình tự sinh không thay thế xác minh thủ công. Gemini/LLM-as-a-judge không nằm trong quy trình này.
- Bundle có nội dung câu hỏi, câu trả lời và văn bản nguồn là dữ liệu đánh giá cục bộ; không gửi vào Git, email hay dịch vụ bên ngoài. CSV nộp cho bộ tổng hợp chỉ có ID và nhãn; không thêm cột ghi chú/tự do.

## Đơn vị đánh giá

1. **Một dòng answer review cho mỗi câu hỏi trong một lần chạy.** Mã định danh là cặp `run_id` + `question_id`.
2. **Một dòng claim review cho mỗi mệnh đề thực tế có thể kiểm chứng trong câu trả lời.** Mã định danh là `run_id` + `question_id` + `claim_id`. Chia câu trả lời thành các claim ngắn, đánh số C01, C02…; không cần chép nội dung claim vào CSV.
3. Nếu hệ thống từ chối, không tạo claim; các trường chất lượng câu trả lời để `not_applicable`. Không coi câu từ chối là câu trả lời sai nếu câu hỏi thực sự không có căn cứ, và ngược lại.

## Rubric cấp câu trả lời

| Trường | Nhãn | Quy tắc chấm |
|---|---|---|
| `answer_correctness` | `correct` | Đáp ứng đúng trọng tâm và các điều kiện quan trọng của gold; không có sai lệch đáng kể. |
|  | `partially_correct` | Có phần đúng nhưng thiếu điều kiện/ngoại lệ quan trọng hoặc chỉ trả lời một phần câu hỏi. |
|  | `incorrect` | Sai nội dung, sai điều kiện, mâu thuẫn với nguồn hoặc bịa thông tin có ảnh hưởng. |
| `faithfulness` | `fully_supported` | Mọi claim thực tế đều được một hay nhiều đoạn nguồn được cấp hỗ trợ. |
|  | `partially_supported` | Có claim được hỗ trợ nhưng còn claim thiếu căn cứ hoặc diễn giải vượt nguồn. |
|  | `unsupported` | Không claim trọng yếu nào được nguồn được cấp hỗ trợ. |
| `answer_relevance` | `direct` | Trả lời trực tiếp câu hỏi, không lạc đề. |
|  | `partial` | Có liên quan nhưng bỏ sót phần đáng kể hoặc thêm nội dung gây nhiễu. |
|  | `irrelevant` | Không giải quyết câu hỏi hoặc trả lời sang vấn đề khác. |
| `citation_location_correctness` | `correct` | Với tất cả citation được nêu, tài liệu và vị trí PDF/mục dẫn tới đúng nơi có thể kiểm tra. |
|  | `incorrect` | Có ít nhất một citation sai tài liệu, sai vị trí hoặc không thể truy ngược như đã ghi. |
|  | `not_applicable` | Không có citation hoặc hệ thống từ chối. |

Các nhãn này không đồng nhất: citation có thể trỏ đúng trang nhưng đoạn đó không hỗ trợ claim; câu trả lời có thể đúng tình cờ nhưng không faithful với context. Cần ghi nhận riêng.

## Rubric cấp claim

Tạo một dòng cho mỗi mệnh đề thực tế trong câu trả lời đã sinh.

- `supported`: nguồn được trích dẫn trực tiếp nâng đỡ claim, bao gồm điều kiện/ngoại lệ cần thiết.
- `partially_supported`: nguồn chỉ hỗ trợ một phần, hoặc claim khái quát hơn mức văn bản cho phép.
- `unsupported`: citation không chứa căn cứ cho claim, mâu thuẫn với claim hoặc claim là suy diễn không được nguồn cho phép.
- `uncited`: claim không có citation gắn với nó; không mặc nhiên kết luận claim sai.
- `citation_location_correctness`: `correct` khi vị trí được trích dẫn có thể mở lại và xác định đúng; `incorrect` khi sai; `not_applicable` chỉ dùng cho claim `uncited`.

Nếu một claim có nhiều citation, chỉ đánh `supported` khi tập citation thực sự cung cấp đủ căn cứ. Một citation hợp lệ về ID không tự động là citation được hỗ trợ.

## Cách điền và xử lý trường hợp khó

1. Chọn run cục bộ và mở bundle được tạo có chủ đích cho chấm thủ công; xác nhận `snapshot_id`, `partition` và cấu hình trước khi chấm.
2. Đọc gold answerability và evidence đã được người học xác minh; sau đó đọc câu hỏi, output và từng nguồn được cấp. Không chỉ nhìn citation label hoặc tên tài liệu.
3. Điền một answer row và các claim row theo rubric. Nếu không thể xác nhận do PDF scan/OCR, trang mờ, nguồn mâu thuẫn hoặc thiếu tài liệu, để `review_status=pending`; không đoán nhãn. Mẫu pilot hiện không có cơ chế adjudication độc lập, nên `adjudicated` chỉ dùng nếu thực sự có lượt phân xử thứ hai được ghi nhận.
4. Mỗi dòng phải giữ mã của đúng lần chạy và câu hỏi. Không gộp hai cấu hình vào một lần chấm.
5. Chạy bộ tổng hợp sau khi rà các dòng; đầu ra chỉ chứa phân phối nhãn và mẫu số. Giữ bundle, CSV đã điền và mọi ghi chú cục bộ ngoài repo.

## Diễn giải số liệu

Bộ tổng hợp báo riêng phân phối correctness, faithfulness, relevance, độ đúng vị trí citation và mức hỗ trợ từng claim; đồng thời tính tỷ lệ từ chối trên nhóm unanswerable và tỷ lệ từ chối nhầm trên nhóm answerable. Mẫu số luôn đi cùng tử số. Không tính trung bình các chiều thành một điểm tổng hợp, không gọi development là holdout, và không kết luận chất lượng chung từ 10 câu.

Với số lượng nhỏ, nên báo cả số đếm (ví dụ `x/n`) và mô tả một vài lỗi đại diện đã được kiểm tra. Nếu cần so sánh cấu hình, dùng cùng câu hỏi/snapshot, công bố số cặp câu trả lời bất đồng và giữ kết quả từng câu để truy nguyên; chỉ tổng hợp nhãn/mã, không công bố nội dung nguồn thuộc phạm vi hạn chế.

## File biểu mẫu và lệnh tổng hợp

- `answer_review_template.csv`: một dòng cho mỗi câu hỏi/run; template chỉ có header.
- `claim_review_template.csv`: một dòng cho mỗi claim/run; template chỉ có header.
- Có thể copy hai template ra vị trí cục bộ ngoài repo rồi điền nhãn; giữ nguyên header và không thêm cột văn bản tự do. Hoặc dùng script chuẩn bị bên dưới để tạo sẵn 10 answer rows `pending` từ một private bundle; script không sao chép câu hỏi/đáp án/nguồn vào CSV.

```powershell
& 'C:\Users\Dell\anaconda3\envs\rag-hcmute\python.exe' scripts/prepare_manual_review.py `
  --bundle 'D:\RAG\private_eval\m2_generation_reviews\<run_id>.jsonl' `
  --output-root 'D:\RAG\private_eval\manual_review'
```
- Khi chạy generation pilot để chấm, chỉ bật tùy chọn bundle nếu thực sự cần lưu nội dung. Chọn thư mục ngoài repository, ví dụ `D:\RAG\private_eval\generation_review`; mặc định runner chỉ lưu số liệu metrics-only như trước.

```powershell
& 'C:\Users\Dell\anaconda3\envs\rag-hcmute\python.exe' scripts/run_generation_pilot.py `
  --method hybrid-rerank --partition development --top-k 5 `
  --dense-model 'D:\RAG\models\huggingface\hub\models--BAAI--bge-m3\snapshots\5617a9f61b028005a4858fdac845db406aefb181' `
  --reranker-model 'D:\RAG\models\huggingface\hub\models--BAAI--bge-reranker-v2-m3\snapshots\953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e' `
  --review-bundle-dir 'D:\RAG\private_eval\generation_review'
```

Runner refuses to put this bundle inside the project repository. Bundle files include question text, generated answer and retrieved-source text; protect them as local evaluation data. The metrics-only JSON and review bundle are two separate outputs.

```powershell
& 'C:\Users\Dell\anaconda3\envs\rag-hcmute\python.exe' scripts/summarize_manual_reviews.py `
  --answers 'D:\RAG\private_eval\answer_review.csv' `
  --claims 'D:\RAG\private_eval\claim_review.csv'
```

Script từ chối schema lạ/ID trùng/nhãn mâu thuẫn, chỉ tổng hợp một run/snapshot/partition mỗi lượt, không ghi đè file đã có và không in/serialize câu hỏi, câu trả lời, trích đoạn nguồn hay ghi chú.
