# Phiếu chuẩn bị đánh giá truy xuất thông tin trong bảng

## Mục đích

Thử nghiệm này kiểm tra liệu cách biểu diễn bảng có giúp retriever tìm đúng dòng dữ liệu hơn so với cách lập chỉ mục hiện tại hay không. Phạm vi chỉ là truy xuất bằng chứng từ corpus HCMUTE; chưa đánh giá câu trả lời do LLM sinh ra và chưa thay đổi pipeline mặc định.

## Các cấu hình cần đối chiếu

- **B0 — Baseline hiện tại:** dùng snapshot/chunk hiện có, không bổ sung biểu diễn bảng.
- **T1 — Bảng Markdown:** mỗi bảng được lưu thành một khối có tiêu đề, tên cột và nội dung bảng.
- **T2 — Bản ghi theo dòng có ngữ cảnh:** mỗi dòng được chuyển thành một bản ghi văn bản, kèm tên tài liệu, trang, tiêu đề bảng, nhóm hàng và tên cột cần thiết.

T1 và T2 chỉ là hai cách biểu diễn ứng viên, chưa phải quyết định thiết kế. Cần kiểm tra bảng nguồn trước khi đưa vào index; ô gộp, hàng tiêu đề nhiều tầng, đơn vị và ghi chú phải được giữ đúng. Không suy diễn giá trị cho ô trống nếu tài liệu không thể hiện rõ quan hệ đó.

Prototype serializer hiện nằm ở `src/rag_hcmute/ingestion/tables.py`: `table_as_markdown()`/`table_as_markdown_chunk()` tạo T1 và `table_as_row_records()`/`table_as_row_chunks()` tạo T2 từ header/hàng đã được rà soát. Lệnh `scripts/prepare_table_variants.py` đọc một PDF được chỉ định trong manifest, kiểm SHA-256, yêu cầu chọn trang/bảng/hàng header bằng tay và ghi sidecar dưới `artifacts/results/table_variants/` (Git-ignored). Prototype giữ ô trống, yêu cầu nhãn cột tường minh và không tự điền tiếp ô gộp; ngữ cảnh nhóm chỉ được thêm khi truyền vào bằng chứng đã đối chiếu. Các adapter trả về `Chunk` tương thích retriever hiện tại, nhưng chưa được gọi từ pipeline mặc định và chưa tạo benchmark.

Ví dụ tái lập cho bảng đã kiểm tra (lệnh in executable Python đang chạy trước khi xử lý):

```powershell
conda run -n rag-hcmute python scripts/prepare_table_variants.py `
  --document-id HCMUTE_QCDT_1727_2021 `
  --pdf-page 20 --table-index 2 --header-row-index 1 `
  --title "Bảng 5: Xếp hạng năm đào tạo sinh viên"
```

Lệnh tạo một chunk T1 và năm chunk T2 tại `artifacts/results/table_variants/HCMUTE_QCDT_1727_2021_p020_t02/`. Đây là đầu ra local bị Git ignore; script không ghi đè thư mục đã tồn tại.

## Cách giữ phép so sánh công bằng

1. Dùng cùng một bản corpus đầu vào và cùng danh sách câu hỏi đã được người học rà soát.
2. Ghim cấu hình retrieval (BM25 hoặc dense), `top_k`, tokenizer/model embedding và các tham số còn lại trong từng lượt chạy; không thay nhiều yếu tố cùng lúc.
3. Đối chiếu gold evidence theo vị trí ổn định trong tài liệu gốc — mã tài liệu, số trang PDF, mã bảng nếu có, hàng/nhóm hàng và ô liên quan. Sau khi tạo từng snapshot, ánh xạ vị trí này sang `chunk_id` riêng của B0, T1 và T2.
4. Chạy retrieval trước, chưa đưa generation vào phép so sánh. Ghi lại thứ hạng và nội dung bằng chứng để có thể kiểm tra thủ công.
5. Chọn metric theo cấu trúc nhãn và ghi đúng tên. Với câu cần nhiều bằng chứng, tách `Complete Evidence Hit@k` khỏi `Evidence Coverage@k`; MRR của chunk bằng chứng đầu tiên không có nghĩa mọi bằng chứng đã được tìm thấy. Không gọi tỷ lệ câu có ít nhất một chunk liên quan là `Recall@k` chuẩn.
6. Nếu một bảng không thể xác định chắc cấu trúc hàng/cột bằng trích xuất tự động, đánh dấu cần kiểm tra thủ công hoặc loại khỏi lượt đo; không biến đầu ra heuristic thành ground truth.

## Bộ câu hỏi đã duyệt cho ablation Bảng 5

Ngày 05/10/2026, năm câu TB001–TB005 được duyệt cho phép ablation retrieval riêng trên Bảng 5 của QĐ 1727/2021. Câu hỏi, đáp án chấp nhận và phạm vi nguồn được đóng băng tại [`table_questions_reviewed_ablation_20261005.csv`](../../data/question_sets/table_questions_reviewed_ablation_20261005.csv). Trạng thái này chỉ cho phép dùng trong ablation bảng; không đồng nghĩa với việc nhập câu hỏi vào pilot hay xác nhận QĐ 1727 là quy định hiện hành.

Ánh xạ evidence theo biến thể nằm trong [`table_question_variant_evidence_20261005.csv`](../../data/question_sets/table_question_variant_evidence_20261005.csv). TB001 cần hàng 3; TB002 hàng 2; TB003 hàng 4; TB004 hàng 5; TB005 cần đồng thời hàng 2 và 3 ở T2. Tất cả vị trí đều được đối chiếu với PDF page 20 (số in 19), Bảng 5.

Các file [`table_question_candidates_for_student_review.csv`](../../data/question_sets/table_question_candidates_for_student_review.csv), [`table_candidate_chunk_mapping.csv`](../../data/question_sets/table_candidate_chunk_mapping.csv) và [`table_question_review_proposals_20261003.csv`](../../data/question_sets/table_question_review_proposals_20261003.csv) được giữ nguyên làm lịch sử nháp. Chúng không phải input của ablation đã duyệt.

Kết quả ablation retrieval đã chạy được ghi tại [`TABLE_RETRIEVAL_APPROVED_ABLATION_20261005.md`](TABLE_RETRIEVAL_APPROVED_ABLATION_20261005.md). BM25 và Dense được so trên corpus nền tương đương, không đưa generation vào và không thay đổi retrieval mặc định.

Mẫu dưới đây chỉ dành cho câu hỏi mới ở các lượt mở rộng; năm câu TB001–TB005 hiện tại đã được lưu riêng và đã chạy ablation.

```text
question_id:
question:                         [Do người học tự viết]
answerability:                    answerable | unanswerable
expected_document:
pdf_page:                         [Số trang PDF, không phải số trang in nếu khác]
table_title_or_identifier:
row_or_group:
column_or_cell:
expected_evidence:                [Trích ngắn đúng phần cần đối chiếu]
expected_answer_or_acceptance:    [Những dữ kiện tối thiểu cần có trong kết quả]
review_status:                    draft | verified
notes:
```

Với một câu hỏi mới, nếu đáp án cần nhiều hàng hoặc nhiều bảng thì ghi đủ các đơn vị bằng chứng. Ánh xạ cho phép thử hiện tại đã được ghi theo từng biến thể trong [`table_question_variant_evidence_20261005.csv`](../../data/question_sets/table_question_variant_evidence_20261005.csv); không dùng mẫu trống phía trên để thay nhãn đã duyệt.

## Kết quả ablation retrieval hiện tại

Ngày 05/10, phép thử B0/T1/T2 chạy với BM25 và Dense top-5 trên năm câu đã duyệt. Kết quả đầy đủ, định nghĩa metric và giới hạn diễn giải nằm trong [`TABLE_RETRIEVAL_APPROVED_ABLATION_20261005.md`](TABLE_RETRIEVAL_APPROVED_ABLATION_20261005.md). Đây là ablation giới hạn theo một bảng, không phải lựa chọn cấu hình mặc định.

Hai lượt table-only ngày 03/10 và 05/10 không cân đối kích thước corpus nên chỉ giữ làm đầu mối lịch sử. Lượt matched-background ngày 05/10 có 156/157/161 chunk tương ứng B0/T1/T2. Kết quả đầu tiên trên câu nháp vẫn lưu riêng tại [`TABLE_RETRIEVAL_MATCHED_CONTEXT_SMOKE_20261005.md`](TABLE_RETRIEVAL_MATCHED_CONTEXT_SMOKE_20261005.md).

## Giới hạn hiện tại

- Bộ câu hỏi Bảng 5 đã được duyệt cho ablation riêng, nhưng chưa được nhập vào pilot chung; chưa đánh giá generation, citation correctness hoặc refusal.
- Sidecar T1/T2 hiện chỉ dùng trong ablation retrieval; chưa tham gia retrieval mặc định.
- Một bảng phân cấp khác ở Quy chế 1727 (PDF page 3, 14×5 theo PyMuPDF) còn ô nhóm/ô gộp chưa giải quyết; không dùng bảng đó cho phép thử hiện tại.
- Chỉ dùng tài liệu thuộc corpus HCMUTE đã cho phép. Bỏ qua vùng chứa dữ liệu cá nhân; không gửi PDF, trích đoạn nhạy cảm hoặc câu hỏi có PII lên dịch vụ cloud.
