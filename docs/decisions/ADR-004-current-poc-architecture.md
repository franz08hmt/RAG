# ADR-004: Cấu hình kiến trúc làm việc cho PoC RAG HCMUTE

## Trạng thái

**Đề xuất làm cấu hình tham chiếu cho các bước triển khai Mốc 2.** ADR này không khẳng định cấu hình tối ưu, không thay đổi default/code hiện tại và không thay thế quyết định của giảng viên. Mọi kết luận định lượng bên dưới giới hạn trong snapshot G0 và development pilot nhỏ.

## Bối cảnh

Đề tài cần một PoC có thể chạy tại máy cá nhân, truy ngược câu trả lời về tài liệu học vụ HCMUTE và kiểm soát được chi phí. Corpus G0 hiện có 3 tài liệu, 182 trang, 156 chunks; PDF và toàn văn không đưa vào repository public. Bộ câu hỏi chính gồm 10 câu development (7 answerable, 3 unanswerable), 10 exact-evidence span; chưa có holdout.

Những thử nghiệm đã có không cho thấy một lựa chọn thắng mọi tiêu chí. Vì vậy kiến trúc cần ghi riêng baseline dùng để so sánh với cấu hình tích hợp generation, cùng lý do giữ lại các phương án chưa thắng trong pilot.

## Cấu hình được đề xuất

| Tầng | Cấu hình làm việc | Cơ sở thực nghiệm hiện có | Giới hạn cần giữ nguyên khi báo cáo |
|---|---|---|---|
| Corpus và ingestion | Manifest có nguồn/hash; PyMuPDF cho PDF có text; OCR chỉ bật tường minh trên bản thử riêng | Pipeline G0 đã dựng 3 tài liệu; audit scan và OCR được ghi riêng | QĐ 3116 và snapshot OCR không nằm trong G0. Chưa chứng minh xử lý tổng quát hình, bảng hoặc mọi dạng scan; chưa xác nhận corpus là bộ quy định mới nhất |
| Chunking | Chunk theo Điều khi nhận diện được; fallback sliding window 500/80 | Exact-span ablation: Dense BGE-M3 đạt 9/10 ở 500/80, 10/10 ở 250/40, 9/10 ở 750/120; BM25 lần lượt 4/10, 5/10, 4/10 | 250/40 tạo 297 chunks thay vì 156; chưa đo đầy đủ chi phí reranker và pilot chỉ 7 câu answerable. Giữ 500/80 làm baseline, không gọi là tối ưu |
| Embedding | BGE-M3 local, snapshot revision đã ghim | Trên cùng G0/development, BGE-M3 đạt Recall@5 9/10; multilingual-E5-small đạt 6/10 | E5-small bị giới hạn 512 token và 125/156 chunks vượt giới hạn, trong khi BGE-M3 cấu hình 1.024 token có 4/156; so sánh bị ảnh hưởng bởi truncation, không chứng minh BGE-M3 luôn tốt hơn cho tiếng Việt |
| Vector store | FAISS `IndexFlatIP` cho baseline local nhỏ | Với cùng 156 vector FP32 đã chuẩn hóa, Top-10 của FAISS và Qdrant local exact khớp 100%; Evidence Recall@5 đều 9/10, Complete Hit@5 đều 6/7, MRR@10 đều 0,762 | FAISS p50 0,041 ms so với Qdrant 3,088 ms trong workload nhỏ; không suy ra throughput quy mô lớn. FAISS ít thành phần vận hành; Qdrant vẫn là lựa chọn cần cân nhắc nếu cần persistence/filter/server |
| Retrieval | Giữ BM25 và Dense làm baseline độc lập; dùng Hybrid RRF như một biến thể, không giả định Hybrid luôn tốt hơn | Trước rerank, exact Evidence Recall@5: BM25 4/10, Dense 9/10, RRF 6/10 | Kết quả trên 7 câu answerable/10 span; RRF cải thiện so với BM25 nhưng thấp hơn Dense trong pilot này |
| Reranking | BGE-Reranker-v2-m3 trên candidate pool Top-20, trả Top-5 cho cấu hình generation thử nghiệm | Trên development, Dense→rerank tăng Evidence Recall@5 9/10→10/10 và Complete Hit@5 6/7→7/7; RRF→rerank tăng 6/10→10/10, 4/7→7/7 | Reranker chỉ sắp hạng lại candidate đã tìm thấy; latency, truncation và mẫu nhỏ vẫn là ràng buộc. Chưa chốt làm mặc định cho mọi truy vấn |
| Generation | Qwen3:4B qua Ollama loopback, không gọi cloud API | Lượt generation pilot có phản hồi cho 7/7 answerable; 1/3 unanswerable bị từ chối; 9/9 output đã sinh có citation ID hợp lệ | Citation ID hợp lệ không phải citation support; một output bị JSON lỗi, refusal còn yếu, chưa có correctness/faithfulness/relevance được chấm |
| Console | CLI/console là giao diện PoC | Đã có truy vấn một lần và tương tác; có thể bật local generation | Không đặt mục tiêu UI production. Cần hiển thị rõ retrieval method, source location và giới hạn dữ liệu |
| Evaluation | Tách retrieval metrics khỏi đánh giá câu trả lời; nhãn answer/claim do người học rà nguồn | Có exact-evidence metrics, generation process metrics và rubric/manual-review tooling | Phiếu manual review hiện còn pending; chưa có holdout, chưa có semantic generation metrics hoặc ngưỡng refusal đã hiệu chỉnh |

## Quyết định và phương án chưa chọn

1. **Giữ G0 làm snapshot tái lập lịch sử.** Không đưa tài liệu scan QĐ 3116 vào generation chỉ vì đã thử OCR; cần kiểm transcript, hiệu lực, phạm vi áp dụng và gold evidence trước.
2. **Giữ 500/80 làm baseline hiện tại, song song lưu 250/40 như nhánh ứng viên.** Chỉ xem xét đổi sau khi có câu hỏi/evidence độc lập hơn và đo thêm latency/candidate pool.
3. **Giữ BM25/Dense riêng để phân tích lỗi; không gộp mọi lần chạy thành “Hybrid thắng”.** Với PoC generation, có thể tiếp tục dùng hybrid-rerank làm một cấu hình tích hợp cần đánh giá, vì kết quả reranker phụ thuộc candidate pool và chưa có nhãn answer quality.
4. **Chưa mở rộng vector database hoặc tải thêm embedding/reranker.** FAISS hiện đáp ứng baseline nhỏ; phép thử Qdrant chỉ là local exact trên 156 vector. Chroma, Milvus, Pinecone và HNSW chưa có benchmark công bằng theo workload đã xác định.
5. **Không dùng Gemini hoặc API cloud để chấm/generate trong bước này.** Mức chi tiêu API vẫn là 0 USD cho tới khi có ước tính và được người học duyệt; generation hiện dùng Ollama cục bộ.

## Hệ quả

- Mỗi lần chạy phải ghi snapshot, question partition, model revision, candidate depth, top-k, latency và phương thức chunking. So sánh hai cấu hình cần giữ nguyên các biến khác.
- Không dùng các tỷ lệ của development để tuyên bố độ chính xác triển khai, độ an toàn tư vấn học vụ hay khả năng tổng quát hóa.
- Phần việc tiếp theo có hai cổng khác nhau: (a) người học chấm answer/claim và xác minh gold; (b) sau khi có đủ dữ liệu, thiết kế holdout độc lập. Không thay thế cổng nào bằng một metric proxy.
- Bản demo ban đầu của giảng viên và DOCX Mốc 1 vẫn là các tài liệu riêng; ADR này chỉ làm rõ quyết định kỹ thuật làm việc cho Mốc 2.

## Nguồn evidence trong repository

- `docs/evidence/CHUNK_SIZE_EXACT_EVIDENCE_20260929.md`
- `docs/evidence/EMBEDDING_MODEL_ABLATION_20261008.md`
- `docs/evidence/VECTOR_STORE_ABLATION_20261008.md`
- `docs/evidence/HYBRID_RRF_ABLATION_20261007.md`
- `docs/evidence/RERANKER_RESOURCE_AND_EVAL_PLAN_20261007.md`
- `docs/evidence/GENERATION_PILOT_20261008.md`
- `docs/evidence/MANUAL_REVIEW_SCAFFOLD_20261012.md`
