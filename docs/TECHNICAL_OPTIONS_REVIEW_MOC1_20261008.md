# Rà soát phương án kỹ thuật — Mốc 1

Cập nhật: 08/10/2026. Mục đích là phân biệt năng lực do tài liệu công bố, phép đo đã chạy trên HCMUTE và khoảng trống cần tiếp tục nghiên cứu. Kết quả dưới đây dùng snapshot G0 `5da3bd4d5de54492`, 3 tài liệu/182 trang/156 chunks, câu hỏi development; không đại diện cho hệ thống vận hành hoặc quy định hiện hành.

## Kết luận hiện tại

Baseline có thể tái lập cho retrieval là BM25 và dense BGE-M3 + FAISS; RRF và BGE-Reranker-v2-m3 đã được đo như các biến thể. Hai model embedding (BGE-M3, multilingual-E5-small) và hai store (FAISS, Qdrant local) đã có phép thử nội bộ. Đây là một bước tiến từ khảo sát tính năng, nhưng chưa đủ số ứng viên hay dữ liệu độc lập để kết luận model/store tốt nhất. Mốc 1 vẫn mở theo YC1–YC13.

## Embedding

| Model | Thông số cần lưu ý | Bằng chứng HCMUTE hiện có | Giới hạn |
|---|---|---|---|
| BAAI/bge-m3 | 1.024 chiều; model card mô tả multi-functionality/multi-lingual; project dùng dense output và giới hạn encode 1.024 token | Evidence Recall@5 9/10; complete Hit@5 6/7; MRR@10 0,762 | Development pilot; 4/156 chunks vượt cấu hình 1.024; không dùng sparse/ColBERT outputs |
| intfloat/multilingual-e5-small | 384 chiều; 512 token; query/passage prefix theo model card | Evidence Recall@5 6/10; complete Hit@5 5/7; MRR@10 0,651 | 125/156 chunks vượt 512 token; chênh lệch chịu ảnh hưởng của truncation và chunk hiện tại |
| multilingual MiniLM-L12-v2 | Model nhỏ hơn, chiều thấp hơn; giới hạn đầu vào ngắn theo model card | Chưa đo trên corpus này | Chưa được coi là đối chứng thực nghiệm |
| multilingual-e5-large | Đối chứng model lớn hơn; cần kiểm tra đúng giới hạn/prefix theo revision | Chưa tải/chưa đo | Không có kết luận nội bộ |
| Vietnamese-specific candidates | Ứng viên từ VN-MTEB/model cards, sau khi xem nguồn và license | Chưa tải/chưa đo | Benchmark ngoài không thay corpus học vụ; license từng data/model cần xét riêng |

Raw run: `artifacts/results/embedding_model_ablation/embedding_5da3bd4d5de54492_20261008T125238Z.json` (Git-ignored); diễn giải tại `docs/evidence/EMBEDDING_MODEL_ABLATION_20261008.md`. Hai model hiện có không đáp ứng mục tiêu so sánh tối thiểu sáu model. Muốn so sánh công bằng hơn cần xử lý khác biệt input length, cố định policy, thêm model candidates, rồi đánh giá trên holdout do người học duyệt.

VN-MTEB (Findings EACL 2026) là benchmark tiếng Việt hữu ích khi chọn candidate, nhưng không khẳng định hiệu năng trên quy chế HCMUTE. Nhiều tập con được xây dựng từ việc dịch benchmark tiếng Anh; phải xem riêng tác vụ, nguồn và license trước khi tải. Không có dữ liệu benchmark ngoài trong corpus PoC hiện tại.

## Vector store và index

| Lựa chọn | Bản chất / ưu thế | Trạng thái project |
|---|---|---|
| FAISS IndexFlatIP | Thư viện index; exact search đơn giản, gọn, phù hợp baseline cục bộ | Đã benchmark trên 156 vector |
| Qdrant local | Vector store có persistence/payload metadata và local mode | Đã benchmark exact search; không bật ANN |
| Chroma | Local persistence và API tiện cho prototype; cần đo lifecycle/metadata workload | Chưa benchmark |
| Milvus | DB vector có triển khai nhiều mức quy mô; vận hành nặng hơn PoC nhỏ | Chưa cài/benchmark |
| Pinecone | Dịch vụ managed cloud; dễ triển khai dịch vụ nhưng có giới hạn dữ liệu/chi phí/region | Không dùng trong project, không gửi corpus cloud |

Thử nghiệm dùng cùng BGE-M3 normalized FP32 vectors, exact dot product, Top-10, 50 lần cho mỗi trong 7 câu development. Top-10 của Qdrant khớp FAISS 100%; cả hai có evidence Recall@5 9/10, complete Hit@5 6/7, MRR@10 0,762. Query p50 là 0,041 ms với FAISS và 3,088 ms với Qdrant; đây chỉ là microbenchmark store trên CPU, không gồm embedding. Kích thước artifact không so sánh ngang vì FAISS in-memory còn Qdrant lưu payload/index. Raw run: `artifacts/results/vector_store_ablation/vector_store_5da3bd4d5de54492_20261008T125329Z.json`; diễn giải `docs/evidence/VECTOR_STORE_ABLATION_20261008.md`.

Nếu PoC ưu tiên số thành phần ít và dữ liệu nhỏ, FAISS là baseline hợp lý. Nếu cần persistence, payload và metadata filter, Qdrant local là ứng viên hệ thống đáng khảo sát. Không có cơ sở nói store nào có chất lượng retrieval tốt hơn trong exact test vì cả hai trả cùng kết quả. Chưa benchmark FAISS IVF/HNSW, Chroma, Milvus hoặc workload tải đồng thời.

## Retrieval và reranking

BM25 là lexical IR; dense embedding là semantic similarity; cả hai đều là retrieval, tín hiệu khác nhau. RRF hợp nhất thứ hạng thay vì cộng điểm thô. Cross-encoder reranker đọc query và từng passage để đổi thứ tự trong candidate pool nhưng không thể bổ sung evidence bị bỏ khỏi pool.

Trên 7 câu answerable/10 spans của development, exact evidence Recall@5 là BM25 4/10, dense 9/10, RRF 6/10; complete-evidence Hit@5 lần lượt 3/7, 6/7, 4/7; MRR@10 lần lượt 0,371, 0,762, 0,524. Top-20 Dense và RRF mỗi nhánh chứa 10/10 spans. RRF giúp một số truy vấn so với BM25, nhưng tổng thể pilot không vượt dense.

Với BGE reranker duy nhất được thử, Dense Recall@5 đổi 9/10 → 10/10; RRF 6/10 → 10/10. Complete-evidence Hit đổi 6/7 → 7/7 và 4/7 → 7/7 tương ứng. Mẫu nhỏ, một reranker, development-only; không tuyên bố hiệu năng chung và chưa chọn làm mặc định. `max_length=512` cắt một phần nhiều query–passage pairs; sensitivity 1.024 giảm truncation nhưng chậm hơn, không đổi thứ hạng trên pilot.

## Các quyết định còn mở

1. Tiếp tục dùng G0 làm snapshot tái lập được, nhưng gắn rõ nhãn dữ liệu lịch sử.
2. Không đưa QĐ 3116/2025 vào corpus trả lời: file scan ngoài repo, OCR chưa có transcript vàng và kiểm tra đầy đủ.
3. Giữ FAISS/BGE-M3 làm baseline kỹ thuật hiện tại, không gọi là lựa chọn tối ưu.
4. Không đặt refusal threshold từ development scores; nhóm answerable/unanswerable đang chồng lấn và pilot chỉ có 3 câu unanswerable.
5. Chưa thêm model/store/data bên ngoài nếu chưa kiểm dung lượng, license, quyền dữ liệu và có duyệt riêng.
6. Thực hiện holdout và câu hỏi/gold do người học kiểm tra trước khi đưa ra tuyên bố chất lượng.

## Tài liệu nguồn

- [BGE-M3 model card](https://huggingface.co/BAAI/bge-m3), [paper](https://arxiv.org/abs/2402.03216).
- [Multilingual E5-small model card](https://huggingface.co/intfloat/multilingual-e5-small), [technical report](https://arxiv.org/abs/2402.05672).
- [VN-MTEB, Findings EACL 2026](https://aclanthology.org/2026.findings-eacl.86/).
- [FAISS wiki](https://github.com/facebookresearch/faiss/wiki); [Qdrant documentation](https://qdrant.tech/documentation/); [Chroma documentation](https://docs.trychroma.com/docs/overview/introduction); [Milvus hybrid search](https://milvus.io/docs/v2.5.x/hybrid_search_with_milvus.md); [Pinecone serverless index documentation](https://sdk.pinecone.io/python/how-to/indexes/serverless.html).
- Robertson & Zaragoza (2009), [BM25 and Beyond](https://doi.org/10.1561/1500000019); Cormack et al. (2009), [Reciprocal Rank Fusion](https://doi.org/10.1145/1571941.1572114).
- [BGE reranker v2 m3 model card](https://huggingface.co/BAAI/bge-reranker-v2-m3).
