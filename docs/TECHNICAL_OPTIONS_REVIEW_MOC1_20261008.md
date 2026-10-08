# Khảo sát lựa chọn công nghệ cho Mốc 1

Ngày rà soát: 08/10/2026
Phạm vi: mô hình embedding, vector store, retrieval và reranker cho PoC hỏi đáp tài liệu học vụ HCMUTE.

## Kết luận dùng cho đồ án

Ở snapshot hiện tại, chưa có cơ sở để kết luận một embedding model hay vector store là tốt nhất cho bài toán. Corpus G0 có 3 tài liệu và 156 chunk; phép đo đang có chủ yếu dùng BGE-M3 cùng FAISS trên 7 câu answerable và 10 exact-evidence span thuộc development. Các kết quả này hữu ích để giải thích pipeline và nhận diện lỗi, nhưng chưa đại diện cho truy vấn thực tế rộng hơn.

Vì vậy, cấu hình hiện tại được giữ làm baseline: BM25 cho tìm kiếm từ khóa, Dense BGE-M3 với FAISS cho tìm kiếm ngữ nghĩa, RRF để khảo sát kết hợp, và BGE-Reranker-v2-m3 để xếp lại candidate. Không cài thêm vector store, không tải thêm embedding model, không gửi corpus lên dịch vụ cloud trong lần rà soát này. Đây là quyết định bảo toàn baseline, không phải khẳng định FAISS hay BGE-M3 luôn tốt hơn lựa chọn khác.

Các ghi chú bên dưới tách ba loại bằng chứng: thông số/capability do nhà phát triển công bố, số đo trên corpus HCMUTE của project, và phép thử còn cần thực hiện. Không so sánh trực tiếp latency hay độ chính xác công bố từ benchmark khác với số đo nội bộ vì corpus, phần cứng, split và metric khác nhau.

## Embedding model

| Model | Thông tin từ nguồn của nhà phát triển | Vai trò hợp lý trong nghiên cứu này | Trạng thái trên corpus HCMUTE |
|---|---|---|---|
| BAAI/bge-m3 | Đầu ra dense 1024 chiều, context tối đa 8192 token; model hỗ trợ dense, sparse và multi-vector, trên 100 ngôn ngữ. Model card nói cách dùng dense không cần thêm query instruction. | Baseline phù hợp để khảo sát tài liệu tiếng Việt dài và nhiều kiểu truy xuất. Tuy nhiên, project hiện chỉ dùng dense vector; chưa dùng các đầu ra sparse/ColBERT của model. | Đã chạy local với FAISS. Trên development pilot, dense đạt exact-evidence Recall@5 9/10 span, Complete-evidence Hit@5 6/7 câu, First-evidence MRR@10 0,762. Đây không phải holdout. |
| intfloat/multilingual-e5-large | Model card nêu embedding 1024 chiều, context tối đa 512 token và hỗ trợ multilingual; phải thêm tiền tố `query:` và `passage:` tương ứng. Card cũng cảnh báo chất lượng có thể giảm với ngôn ngữ ít tài nguyên. | Ứng viên so sánh với BGE-M3 để xem model có tiền tố truy vấn/văn bản và giới hạn context ngắn hơn ảnh hưởng ra sao. Các chunk dài cần được kiểm tra truncation. | Chưa tải, chưa đo trên G0. Chưa thể khẳng định model này tốt hơn hay kém hơn cho tiếng Việt học vụ. |
| sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2 | Model card công bố vector 384 chiều, `max_seq_length` 128 và quy mô khoảng 0,1 tỷ tham số; dùng được cho semantic search. | Ứng viên nhỏ hơn để làm đối chứng tài nguyên thấp. Giới hạn 128 token có thể cắt mất phần quan trọng nếu áp dụng trực tiếp lên chunk hiện tại, vì vậy phải log độ dài/truncation và giữ nguyên chunking trong phép so sánh. | Chưa tải, chưa đo trên G0. Không có kết luận hiệu năng tiếng Việt từ thông số kích thước đơn thuần. |

VN-MTEB là benchmark embedding tiếng Việt được công bố trong Findings of EACL 2026. Bài báo mô tả 41 bộ dữ liệu thuộc 6 nhóm tác vụ, trong đó có retrieval và reranking; phần lớn dữ liệu được tạo bằng cách dịch các mẫu từ MTEB tiếng Anh. Bài báo hữu ích để biết những model và tác vụ nào đã được khảo sát, nhưng điểm benchmark không thay thế phép đo trên quy chế và hướng dẫn học vụ HCMUTE. Trước khi lấy bất kỳ tập con nào về, cần rà giấy phép và nguồn gốc riêng của chính tập con đó; một giấy phép chung ở trang benchmark không tự động giải quyết quyền của mọi dữ liệu thành phần.

### Cách so sánh embedding nếu được duyệt tải model

Giữ nguyên snapshot G0, chunks, câu hỏi, gold evidence, top-k và chính sách chuẩn hóa vector. Mỗi model phải embed lại toàn bộ corpus và câu hỏi theo hướng dẫn model card; không trộn vector từ hai model trong cùng index. Trước khi chạy, ghi revision, SHA-256, kích thước tải, chiều vector, độ dài đầu vào và trường hợp bị cắt.

Đánh giá retrieval bằng exact-evidence Recall@5, Complete-evidence Hit@5 và First-evidence MRR@10; ghi thêm thời gian mã hóa câu hỏi, thời gian dựng index, VRAM đỉnh và độ trễ truy vấn. Chỉ dùng development để phân tích lỗi. Kết quả không được gọi là đánh giá độc lập cho tới khi có holdout do người học tự viết hoặc kiểm tra, rồi đăng ký vào manifest mà không dùng để tune.

## Vector store

| Công nghệ | Cách triển khai và năng lực được tài liệu mô tả | Nhận xét trong phạm vi PoC | Trạng thái |
|---|---|---|---|
| FAISS | Thư viện C++/Python cho similarity search; có các index chính xác và approximate, hỗ trợ nhiều metric, một số index GPU và lưu index ra đĩa. FAISS không tự đóng vai trò một dịch vụ database quản lý toàn bộ metadata, API và vòng đời tài liệu. | Hợp với PoC một máy, corpus nhỏ, chạy offline. Ứng dụng hiện quản lý chunk/provenance ngoài index và dùng `IndexFlatIP`, nên phép tìm kiếm dense hiện tại là baseline exact. | Đã dùng; không cần thêm dịch vụ. |
| Chroma | Có thể chạy local, lưu persistence trên đĩa hoặc nối tới server; tài liệu hiện hành mô tả dense, sparse, hybrid, full-text/regex search và metadata filter. | Dễ thử cho ứng dụng local cần giữ document/metadata cùng vector. Cần kiểm tra rõ persistence và cấu hình khi đóng/mở ứng dụng; tính năng công bố không chứng minh hiệu năng trên G0. | Chưa cài/chưa benchmark. Cần duyệt package trước khi thêm. |
| Qdrant | Có local mode trong bộ client (memory hoặc disk), server tự host và dịch vụ cloud; hỗ trợ dense/sparse/hybrid retrieval, payload và filter. | Ứng viên hợp lý nếu muốn chứng minh cùng một collection lưu vector và metadata, hoặc khảo sát hybrid trong một store. Local mode có thể đủ cho PoC nhưng cần đo phần lưu trữ và khởi tạo thực tế. | Chưa cài/chưa benchmark. Cần duyệt package trước khi thêm. |
| Milvus | Hỗ trợ các trường vector dense và sparse cùng hybrid search với ranker; có các kiểu triển khai phục vụ quy mô lớn hơn. | Có thể dùng khi bài toán cần triển khai nhiều collection hoặc quy mô lớn, nhưng vận hành phức tạp hơn nhu cầu 156 chunk hiện tại. Chưa có số đo nội bộ để kết luận về tốc độ. | Chưa cài/chưa benchmark. Không phải lựa chọn đầu tiên cho PoC hiện tại. |
| Pinecone | Dịch vụ managed/serverless nhận dense, sparse và trường full-text, triển khai theo cloud/region; tài liệu nêu lưu trữ và truy vấn thuộc cách tính sử dụng dịch vụ. | Không phù hợp với ràng buộc hiện tại: không phát sinh chi phí, không gửi corpus học vụ lên cloud và ưu tiên chạy local. Chỉ xem xét nếu có duyệt riêng về chi phí, quyền dữ liệu và cấu hình triển khai. | Không sử dụng trong project hiện tại. |

So sánh giữa FAISS và một vector database cần nói rõ mục tiêu. Nếu mục tiêu chỉ là chất lượng dense ranking, so với cùng embeddings và metric sẽ là phép đo retrieval/index; nếu mục tiêu là năng lực hệ thống, cần đo thêm metadata filter, persistence, cập nhật/xóa, khởi động lại, kích thước lưu trữ và độ trễ. Một con số QPS từ benchmark của nhà cung cấp không thể thay cho phép thử này.

### Cách so sánh vector store nếu được duyệt cài package

Ứng viên thực tế là FAISS baseline, Chroma local persistence và Qdrant local. Dùng cùng 156 chunk, cùng một bộ vector BGE-M3, cùng chunk IDs, cùng cosine/inner-product semantics, cùng top-k và cùng query list. Lưu build time, query p50/p95, memory/disk, độ chính xác so với exact reference, filter/provenance, persistence sau restart và thao tác cập nhật. Cấu hình ANN phải được ghi lại; không so tốc độ của index approximate với exact search mà bỏ qua chênh lệch chất lượng.

Corpus này nhỏ nên latency có thể quá thấp để phân biệt các hệ thống. Không nhân bản cùng tài liệu để tạo cảm giác benchmark quy mô lớn. Nếu cần đánh giá ở quy mô lớn hơn, trước hết phải đề xuất nguồn dữ liệu, giấy phép, dung lượng và cách tránh đưa dữ liệu không được phép lên repo; chỉ tải sau khi người học duyệt.

## Retrieval và reranking

Trong project, BM25 và Dense là hai tín hiệu khác nhau chứ không phải hai database. BM25 xếp hạng dựa trên khớp từ/ngữ; vì vậy mã quyết định, số điều và từ khóa chính xác có thể hữu ích, nhưng cách hỏi hoặc cách gọi cột có thể làm thứ hạng đổi. Dense dùng embedding để so khớp gần nghĩa; nó có thể tìm được cách diễn đạt khác, nhưng không đảm bảo lấy đúng mã/số hiệu hoặc đủ mọi đoạn bằng chứng. Hybrid RRF cộng đóng góp theo thứ hạng, không cộng trực tiếp BM25 score với cosine score; hợp nhất cũng không đảm bảo vượt nhánh mạnh nhất.

Trên G0 và development pilot 7 câu/10 evidence span, exact-evidence Recall@5 lần lượt là BM25 4/10, Dense BGE-M3 9/10 và Hybrid RRF 6/10. Complete-evidence Hit@5 tương ứng 3/7, 6/7 và 4/7; First-evidence MRR@10 là 0,371, 0,762 và 0,524. Đây là số đo trong cùng corpus/split của project, không phải kết luận mọi truy vấn học vụ đều nên dùng Dense.

Reranker nhận query cùng từng passage để chấm độ liên quan, rồi sắp xếp lại một candidate pool đã truy xuất. Nó không thể bổ sung evidence nếu bước retrieval không đưa evidence đó vào pool. Với Top-20 Dense và RRF trong pilot này, cả hai candidate list có đủ 10/10 exact spans; sau rerank, Recall@5 đạt 10/10 và Complete-evidence Hit@5 đạt 7/7 cho mỗi nhánh. Chỉ có 7 câu và một lần chạy trên development, nên kết quả được giữ ở mức pilot; không đặt reranker làm mặc định. Độ trễ, truncation và chi phí GPU được ghi riêng trong [`RERANKER_RESOURCE_AND_EVAL_PLAN_20261007.md`](evidence/RERANKER_RESOURCE_AND_EVAL_PLAN_20261007.md).

## Hướng chốt Mốc 1

1. Giữ nguyên corpus HCMUTE G0 và baseline đã chạy; không dùng benchmark ngoài để thay thế câu hỏi học vụ của project.
2. Nếu cần so sánh embedding, xin duyệt trước model weights; ưu tiên một model nhỏ làm đối chứng tài nguyên, sau đó mới quyết định có cần thêm model lớn hay không.
3. Nếu cần so sánh vector store, xin duyệt cài Chroma và Qdrant; chỉ chạy local, dùng chung BGE vectors và giữ tài liệu nguồn ngoài Git.
4. Người học tiếp tục tự viết/đối chiếu câu hỏi, gold answer và evidence. Audit hiện tại xác nhận 10 câu development (7 answerable, 3 unanswerable), 5 câu bảng thuộc ablation riêng và **0 holdout**. Không tạo holdout thay người học.
5. Quyết định 3116/QĐ-ĐHSPKT năm 2025 chưa có trong `D:\RAG\nguon_bo_sung`; nếu tải được thì giữ ngoài repo, đối chiếu hash/nguồn và cập nhật manifest theo quy trình. Nếu chưa lấy được, báo cáo giới hạn nội dung/hiệu lực của QĐ 1727/2021.
6. YC10 (sinh câu trả lời, citation và refusal) và YC11 (đánh giá RAG end-to-end) chưa được hoàn thành chỉ bằng retrieval console; cần giữ đúng phạm vi ở báo cáo này và đưa phần generation/evaluation sang mốc phát triển tương ứng. Không dùng Gemini nếu chưa có khóa đã xoay mới và chưa duyệt chi phí; không gọi API tính phí.

## Nguồn đã đối chiếu

- [BGE-M3 model card](https://huggingface.co/BAAI/bge-m3) và [bài báo BGE-M3](https://arxiv.org/abs/2402.03216).
- [Multilingual E5 large model card](https://huggingface.co/intfloat/multilingual-e5-large).
- [Multilingual MiniLM model card](https://huggingface.co/sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2).
- [VN-MTEB, Findings of EACL 2026](https://aclanthology.org/2026.findings-eacl.86/).
- [FAISS project wiki](https://github.com/facebookresearch/faiss/wiki) — index, metric, trade-off exact/approximate search.
- [Chroma introduction](https://docs.trychroma.com/docs/overview/introduction) and [Chroma source repository](https://github.com/chroma-core/chroma) — capability and license.
- [Qdrant local framework guide](https://qdrant.tech/documentation/frameworks/langchain/) and [hybrid search documentation](https://qdrant.tech/documentation/search/hybrid-search/).
- [Milvus hybrid search documentation](https://milvus.io/docs/v2.5.x/hybrid_search_with_milvus.md).
- [Pinecone serverless indexes](https://sdk.pinecone.io/python/how-to/indexes/serverless.html).
- [BGE reranker v2 M3 model card](https://huggingface.co/BAAI/bge-reranker-v2-m3).

Đây là khảo sát tính năng/tài liệu công bố và kết quả đã có trong repository; không phải benchmark mới giữa các model hoặc database. Trạng thái tải/cài đặt chưa được thay đổi bởi tài liệu này.
