# 02. Chunking, Embedding và Retrieval

## 1. Chunking nối dữ liệu với truy vấn

Chunk vừa là đơn vị được lập chỉ mục vừa là evidence được đưa vào context. Kích thước và ranh giới của chunk ảnh hưởng đồng thời đến số vector, khả năng tìm đúng đoạn, giới hạn độ dài model và khả năng trích dẫn. Khi đo một embedding model, cần ghi số chunk bị truncate; nếu chỉ nhìn metric tổng hợp, một model có giới hạn ngắn hơn có thể bị phạt vì đầu vào, không chỉ vì chất lượng biểu diễn.

## 2. BM25 và dense retrieval khác nhau ở tín hiệu

BM25 là mô hình xếp hạng từ vựng thuộc IR. Nó cân nhắc tần suất từ trong tài liệu, độ hiếm của từ trong corpus và độ dài tài liệu. Điều này hữu ích với mã quyết định, số điều, tên biểu mẫu hay cụm từ đặc thù. Nếu câu hỏi dùng từ đồng nghĩa hoặc diễn đạt đời thường, exact overlap có thể thấp.

Dense retrieval dùng encoder để biến query và chunk thành vector; các vector gần nhau theo similarity được xem là liên quan. Nó có thể nối hai cách diễn đạt khác nhau, nhưng vector similarity không hiểu chắc tính pháp lý và có thể bỏ sót số/mã. Chuẩn hóa vector và chọn cosine/inner product phải nhất quán giữa index và query.

Trong hybrid search, hai danh sách BM25 và dense được kết hợp. RRF (Reciprocal Rank Fusion) cộng đóng góp dựa trên thứ hạng `1/(k + rank)`, nên không cần so sánh trực tiếp thang điểm BM25 và cosine. RRF vẫn có thể làm thứ hạng giảm nếu một nhánh yếu đưa nhiều ứng viên; cần so sánh với từng nhánh. Reranker cross-encoder chấm từng cặp query–passage trực tiếp để xếp lại một candidate pool. Nó không thể tạo evidence nếu retriever không đưa evidence vào pool.

## 3. Số đo retrieval trên G0

Pilot dùng 7 câu answerable và 10 exact evidence span. Hai cách đo “đúng” không thể thay thế nhau:

- **Evidence-span Recall@k:** số span gold xuất hiện trong Top-k chia tổng span gold.
- **Complete-evidence Hit@k:** số câu có đủ tất cả span bắt buộc trong Top-k chia số câu answerable.
- **MRR@k:** nghịch đảo thứ hạng đầu tiên có evidence liên quan, lấy trung bình trên truy vấn có liên quan.

| Phương pháp | Evidence-span Recall@5 | Câu đủ evidence trong Top-5 | First-evidence MRR@10 | Candidate Top-20 đủ span |
|---|---:|---:|---:|---:|
| BM25 | 4/10 | 3/7 | 0,371 | 7/10 span; đủ câu 5/7 |
| Dense BGE-M3 | 9/10 | 6/7 | 0,762 | 10/10 span; đủ câu 7/7 |
| Hybrid RRF (k=60) | 6/10 | 4/7 | 0,524 | 10/10 span; đủ câu 7/7 |

Run: `hybrid_retrieval_ablation` trên snapshot `5da3bd4d5de54492`, development; chi tiết tại `docs/evidence/HYBRID_RRF_ABLATION_20261007.md`. Pilot này cho thấy dense xếp span tốt hơn hai phương pháp còn lại trên câu hỏi hiện có; RRF nâng một số ca so với BM25 nhưng cũng kém Dense. Không kết luận “hybrid luôn tốt hơn”.

## 4. Embedding: thông số model không thay cho phép đo

Embedding model khác nhau ở chiều vector, độ dài đầu vào, instruction/prefix và dữ liệu huấn luyện. Model card hữu ích để lập kế hoạch, nhưng quyết định cho domain phải xem truy vấn thực, chunk hiện tại, truncation và gold evidence. Một benchmark tiếng Việt như VN-MTEB mở rộng số tác vụ embedding tiếng Việt; nhóm tác giả cũng ghi nhận phần lớn mẫu được tạo bằng dịch từ benchmark tiếng Anh. Vì vậy điểm benchmark có ích khi chọn ứng viên, không thay thế phép đo trên quy chế HCMUTE.

| Model | Đặc điểm cấu hình | Evidence Recall@5 | Complete Hit@5 | MRR@10 | Chunk bị cắt |
|---|---|---:|---:|---:|---:|
| BAAI/bge-m3 | 1.024 chiều; cấu hình project 1.024 token; không prefix | 9/10 | 6/7 | 0,762 | 4/156 |
| multilingual-e5-small | 384 chiều; tối đa 512 token; cần `query:` / `passage:` | 6/10 | 5/7 | 0,651 | 125/156 |

Đây là so sánh hai model trên cùng chunk, không phải khảo sát đủ yêu cầu nhiều ứng viên. Phần lớn chunk vượt giới hạn E5-small; cần kiểm soát truncation/chunk length và mở rộng model set trước khi trả lời câu hỏi “model nào tốt cho tiếng Việt” một cách rộng hơn. BGE-M3 được giữ làm baseline hiện tại, không được coi là đã chứng minh tối ưu.

## 5. Vector store là lựa chọn về tìm kiếm và vận hành

FAISS là thư viện index vector; có index exact và approximate. `IndexFlatIP` là baseline exact gọn cho corpus nhỏ, nhưng ứng dụng tự giữ metadata/provenance. Qdrant local là một vector store có persistence và payload metadata. Thử nghiệm so exact search trên cùng 156 vector: Top-10 khớp FAISS 100% ở cả hai; metric evidence giống nhau. FAISS query p50 0,041 ms, Qdrant 3,088 ms; đây là tìm kiếm CPU, đã loại thời gian embedding, và chưa đại diện cho tải đồng thời.

Không nên so kết quả này với thông lượng do nhà cung cấp công bố: index size, hardware, cấu hình ANN, filter, persistence và workload khác nhau. Kích thước artifact cũng không “công bằng” trực tiếp vì một bên in-memory, một bên lưu cả store. Với corpus nhỏ, FAISS đơn giản; nếu cần payload/filter/persistence, Qdrant là ứng viên phù hợp để cân nhắc. Milvus và Pinecone chưa sử dụng; Chroma chưa benchmark. Không dùng dịch vụ cloud trong PoC hiện tại do ràng buộc chi phí và dữ liệu.

## 6. Reranking và giới hạn candidate

Trên Top-20 Dense, reranker BGE-v2-m3 đưa exact Recall@5 từ 9/10 lên 10/10 và câu đủ evidence từ 6/7 lên 7/7; trên Top-20 RRF, từ 6/10 và 4/7 lên 10/10 và 7/7. Một lần chạy 7 câu có thể tăng metric do thay đổi thứ hạng, nhưng không đủ chứng minh mức cải thiện sẽ lặp lại. Nếu candidate pool thiếu span, reranker không khôi phục được span; vì vậy cần đo candidate recall riêng.

Ở max length 512 có nhiều cặp query–passage bị cắt; sensitivity max length 1.024 hết truncation trên cặp quan sát nhưng chậm hơn và metric không đổi. Chưa so sánh ba reranker, nên chưa đáp ứng mục tiêu khảo sát rộng. Reranker hiện là phương án được thử, không phải default đã chọn.

## 7. Map phép đo vào code

- Ingestion / chunking: `src/rag_hcmute/ingestion/` và `scripts/build_corpus.py`.
- BM25 / dense / RRF: `src/rag_hcmute/retrieval/`; runner ở `scripts/run_hybrid_retrieval_ablation.py`.
- Embedding ablation: `scripts/run_embedding_model_ablation.py`.
- Vector-store test: `scripts/run_vector_store_ablation.py`.
- Reranker ablation: `scripts/run_reranker_ablation.py`.
- Console: `python -m rag_hcmute.console_app`; dùng model local theo đường dẫn rõ ràng, không auto-download.

### Nguồn đọc

1. Robertson & Zaragoza (2009), [The Probabilistic Relevance Framework: BM25 and Beyond](https://doi.org/10.1561/1500000019).
2. Cormack et al. (2009), [Reciprocal Rank Fusion outperforms Condorcet and individual Rank Learning Methods](https://doi.org/10.1145/1571941.1572114).
3. Chen et al. (2024), [BGE-M3](https://arxiv.org/abs/2402.03216).
4. Wang et al. (2024), [Multilingual E5](https://arxiv.org/abs/2402.05672).
5. Pham et al. (2026), [VN-MTEB](https://aclanthology.org/2026.findings-eacl.86/).
6. [FAISS documentation](https://github.com/facebookresearch/faiss/wiki); [Qdrant documentation](https://qdrant.tech/documentation/).
