# 03. Generation, citation, refusal và đánh giá RAG

## 1. Generation không phải bước “viết lại câu trả lời” đơn thuần

Sau retrieval, context là một tập các chunk có định danh nguồn. Prompt cần nêu rõ nhiệm vụ, giới hạn bằng chứng, cách xử lý khi context mâu thuẫn hoặc thiếu, định dạng citation và cách từ chối. Cần truyền dữ liệu cấu trúc thay vì ghép citation sau khi LLM trả lời.

Một prompt có thể yêu cầu: chỉ dùng thông tin trong context; không tự bổ sung thời hạn/điều kiện; với mỗi kết luận nêu citation chunk; nếu không có đoạn hỗ trợ thì nói rõ chưa tìm thấy căn cứ trong kho hiện tại. Nhưng system prompt không phải bộ xác minh chân lý. Model vẫn có thể suy luận quá mức, chọn citation không liên quan, hoặc không tuân thủ khi định dạng đầu ra sai.

Citation có ít nhất ba mức kiểm tra: (1) ID trích dẫn thuộc danh sách chunk đã truy xuất; (2) metadata resolve đúng văn bản/trang/điều; (3) nội dung chunk thực sự hỗ trợ mệnh đề được dẫn. Pilot hiện chỉ kiểm ID và tỷ lệ có document ID mong đợi; chưa đánh giá entailment. Vì vậy “citation hợp lệ về cấu trúc” không đồng nghĩa “citation chứng minh câu trả lời”.

Refusal cũng cần đánh giá độc lập. “Không tìm thấy kết quả trong Top-k” không luôn có nghĩa corpus không có câu trả lời; ngược lại, có một chunk có vẻ gần nghĩa chưa chắc đủ căn cứ để trả lời. Một refusal guard cần tập answerable/unanswerable đủ đa dạng, ngưỡng được chọn trên development và kiểm lại trên holdout; phải xem cả false refusal lẫn unsupported answer.

## 2. Kết quả generation pilot hiện có

Thử nghiệm local bằng Ollama/Qwen3:4B, temperature 0, Hybrid RRF + reranker, Top-5, trên cùng 10 câu development (7 answerable, 3 unanswerable). Kết quả: hệ thống sinh phản hồi cho 7/7 answerable; từ chối 1/3 câu unanswerable; document ID kỳ vọng xuất hiện ở 7/7 câu answerable; citation ID hợp lệ cấu trúc 9/9 citation đã sinh. Hai câu unanswerable còn lại nhận câu trả lời không có căn cứ; một lần output không hợp lệ JSON được đánh dấu abstain bởi bộ xử lý.

Run ID: `generation_hybrid-rerank_5da3bd4d5de54492_20261008T124010Z`; raw metrics-only JSON nằm dưới `artifacts/results/generation_pilot/` và bị Git-ignore. Trung vị retrieval+rerank khoảng 2,255 ms; generation khoảng 8,720 ms trong run này. Đây là số thời gian của một máy và một lần chạy, không bao gồm phân phối độ trễ hoặc tải đồng thời.

Pilot không chấm câu trả lời đúng/sai, faithfulness, answer relevance hay quan hệ hỗ trợ giữa từng citation và mệnh đề. Không được dùng các tỷ lệ document/citation ID để gọi generation là chính xác. Kết quả refusal thấp là cảnh báo cần xử lý, không phải căn cứ đặt threshold tự động.

## 3. Đánh giá phải tách tầng

### Retrieval

Khi đã có gold evidence, đo evidence-span Recall@k, Complete-evidence Hit@k và MRR/nDCG. Nêu đơn vị/mẫu số rõ: span hay câu hỏi. Hit@k cho biết truy vấn có ít nhất một relevant item trong top-k; Recall@k theo span cho biết phần nào của toàn bộ bằng chứng được lấy. Với câu cần hai điều kiện từ hai khoản, chỉ kiểm tra “có một chunk tốt” sẽ phóng đại chất lượng.

### Generation và grounding

Đối chiếu câu trả lời với gold answer và context. Faithfulness hỏi liệu các khẳng định có được context hỗ trợ; answer relevance hỏi câu trả lời có đáp đúng query; context precision/recall đo độ liên quan và độ phủ của context được lấy. RAGAS đề xuất các metric tham chiếu tự động, trong đó một số dùng LLM/judge; điểm số phụ thuộc model judge, prompt và dữ liệu, nên cần kiểm tra thủ công mẫu lỗi [3]. ARES là một khung tự động khác, cũng nhấn mạnh context relevance, faithfulness và answer relevance [4]. Không dùng metric do LLM chấm như ground truth tuyệt đối.

### Citation và refusal

Tách validity của ID, source/page resolution và semantic support. Với refusal, báo precision/recall hoặc confusion matrix cho answerable/unanswerable, nêu ngưỡng và loại lỗi. Đo cả trường hợp không biết, có nhiều nguồn xung đột, dữ liệu lỗi OCR, và truy vấn về lịch/hiệu lực thời gian nằm ngoài corpus.

### Vận hành

Ghi latency retrieval/rerank/generation riêng, context size/token, model/version, cấu hình, lỗi parse và chi phí nếu có. Trong project hiện tại mọi generation đều local; Gemini chưa được gọi. Nếu tương lai đề xuất LLM judge bằng Gemini, phải xin duyệt estimate lượt gọi/token và giữ chi phí 0 USD cho tới khi được chấp thuận; tuyệt đối không sử dụng API tính phí khác.

## 4. Cách tổ chức bộ câu hỏi

Mỗi câu cần loại answerable, gold answer, evidence span, document hash, page PDF, trang in nếu xác minh, section path và trạng thái người học duyệt. Bộ câu hỏi nên gồm exact terminology, diễn đạt cách khác, câu nhiều span, câu hỏi bảng/scan và câu ngoài corpus. Các paraphrase của cùng một yêu cầu phải nằm chung một partition để tránh rò rỉ.

Hiện chỉ có 10 câu development và 5 câu bảng dành riêng cho ablation; chưa có holdout độc lập hoặc `questions_v2.jsonl` được duyệt. Vì chủ sở hữu bài tập cần tự rà câu hỏi/gold, không tự sinh thêm data rồi ghi là đã xác minh. Cấu trúc và quy tắc tạo bộ mới ở `data/eval/README.md`.

## 5. Console PoC và giới hạn hiện tại

Console cho phép chạy retrieval, xem rank, metadata trang/section và excerpt; có lựa chọn local generator cho demo kỹ thuật. Câu trả lời không nên dùng để đưa quyết định học vụ. Hướng hoàn thiện cần: kiểm soát corpus/version, citation resolve ra vị trí nguồn, hiển thị đủ bằng chứng, xử lý lỗi model/JSON, refuse an toàn và test end-to-end trên test set. Giao diện được giữ ở mức console theo yêu cầu giảng viên; UI bóng bẩy không phải mục tiêu.

### Tài liệu đọc

1. Es et al. (2024), [RAGAs: Automated Evaluation of Retrieval Augmented Generation](https://aclanthology.org/2024.eacl-demo.16/).
2. Saad-Falcon et al. (2024), [ARES](https://aclanthology.org/2024.naacl-long.20/).
3. Lewis et al. (2020), [RAG for Knowledge-Intensive NLP](https://arxiv.org/abs/2005.11401).
4. Gao et al. (2024), [RAG survey](https://arxiv.org/abs/2312.10997).
