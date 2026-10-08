# 00. RAG giải quyết việc gì và vận hành ra sao?

## 1. Hiểu RAG bằng một bài toán cụ thể

Phạm vi đồ án là tra cứu quy chế và tài liệu học vụ HCMUTE. Người hỏi có thể dùng cách nói tự nhiên như “em muốn rút một môn thì cần làm gì?”, còn tài liệu lại diễn đạt theo điều khoản, thời hạn và tên thủ tục. Hệ thống cần tìm được đúng đoạn quy định rồi trình bày câu trả lời ngắn, có thể lần ngược về văn bản và vị trí trang/điều. Nếu kho tài liệu không chứa câu trả lời, kết quả đúng không phải là một câu đoán nghe hợp lý mà là thông báo chưa có căn cứ.

RAG (Retrieval-Augmented Generation) là cách nối một bước truy xuất thông tin với một mô hình sinh ngôn ngữ. Tài liệu bên ngoài mô hình được chia thành đơn vị tra cứu, lập chỉ mục; lúc có câu hỏi, hệ thống chọn các đoạn liên quan và đưa chúng làm ngữ cảnh cho LLM. LLM diễn đạt câu trả lời từ ngữ cảnh đó. RAG vì thế là kiến trúc/pipeline, không phải một mô hình duy nhất và cũng không phải chỉ là lưu PDF vào vector database.

Paper nền tảng của Lewis và cộng sự mô tả một mô hình RAG được huấn luyện cho các tác vụ NLP tri thức: bộ nhớ tham số là seq2seq model, bộ nhớ phi tham số là chỉ mục tài liệu và retriever; retriever cùng generator được fine-tune trong các thiết lập của bài báo. Cách triển khai đồ án này khác ở một điểm quan trọng: các mô hình embedding/LLM được dùng sẵn, không fine-tune end-to-end. Ở đây RAG là kiến trúc ứng dụng bao quanh các thành phần có sẵn, với dữ liệu được lập chỉ mục riêng và truy xuất khi chạy [1].

## 2. Vì sao thêm retrieval thay vì chỉ hỏi LLM?

LLM có tri thức được mã hóa trong tham số, nhưng kiến thức đó có thể thiếu, lỗi thời, không khớp với một văn bản nội bộ cụ thể hoặc không thể chỉ ra đúng điều khoản. Fine-tuning không phải cách cập nhật nhanh từng văn bản: cần chuẩn bị dữ liệu huấn luyện, thời gian, chi phí và quy trình phát hành model mới, trong khi vẫn cần một cơ chế kiểm chứng nguồn.

RAG cho phép giữ tài liệu bên ngoài mô hình: cập nhật corpus và index khi nguồn thay đổi; giới hạn câu trả lời vào nguồn đã chọn; trả lại định danh tài liệu, trang và điều khoản để người đọc tự đối chiếu. Nhưng RAG không tự động loại bỏ hallucination. Lỗi vẫn có thể xuất hiện nếu tài liệu trích xuất sai, chunk làm mất ngữ cảnh, retriever lấy nhầm đoạn, prompt không ràng buộc mô hình hoặc mô hình diễn giải sai bằng chứng. Vì thế cần theo dõi lỗi ở từng tầng thay vì chỉ nhìn câu trả lời cuối.

## 3. Luồng dữ liệu

```text
Tài liệu đã xác minh
  → trích xuất theo trang và loại nội dung
  → làm sạch có kiểm soát, giữ số trang/section
  → chia thành chunk có định danh và provenance
  → lập chỉ mục từ khóa và/hoặc vector

Câu hỏi
  → chuẩn hóa / tìm kiếm BM25 và dense
  → hợp nhất hoặc xếp lại ứng viên (nếu cấu hình có)
  → chọn ngữ cảnh kèm metadata nguồn
  → LLM tạo câu trả lời bám bằng chứng
  → kiểm tra citation, chất lượng và khả năng từ chối
```

Hai nhánh thường được gọi là offline và online. Ingestion/indexing chạy khi thêm hoặc cập nhật tài liệu. Query-time chạy theo từng câu hỏi. Nếu trộn hai nhánh trong thiết kế, khó biết một lỗi đến từ việc ingest sai hay tìm kiếm sai.

## 4. Search, Information Retrieval và RAG

“Search” là từ rộng để chỉ thao tác tìm. Information Retrieval (IR) là lĩnh vực/mô hình hóa việc biểu diễn truy vấn, tài liệu và xếp hạng kết quả; BM25 và dense retrieval đều là phương pháp IR, nhưng dựa trên tín hiệu khác nhau. RAG dùng một kết quả IR làm ngữ cảnh cho bước generation. Nói “IR là tìm kiếm ngữ nghĩa” là không chính xác vì BM25 cũng thuộc IR mà là retrieval từ vựng.

| Thành phần | Đầu vào chính | Đầu ra | Câu hỏi đánh giá |
|---|---|---|---|
| BM25 | Từ/ngữ trong query và chunk | Danh sách chunk theo điểm lexical | Có tìm đúng thuật ngữ, mã và số hiệu không? |
| Dense retrieval | Vector query và vector chunk | Danh sách lân cận theo độ tương tự | Có tìm được cách diễn đạt gần nghĩa không? |
| RAG generation | Query, context, chỉ dẫn và LLM | Câu trả lời/citation hoặc từ chối | Câu trả lời có được context hỗ trợ không? |

## 5. Các mức kiến trúc

**Naive RAG** chuẩn bị văn bản, chunk, embedding/index; mỗi câu hỏi được embed, lấy Top-k vector rồi đưa context cho LLM. Ưu điểm là dễ hiểu, làm baseline nhanh và có ít thành phần. Hạn chế: query có thể không hợp với cách index; vector gần nghĩa chưa chắc đúng điều khoản; chunks dài/ngắn gây mất hoặc thừa ngữ cảnh; không có bước xác nhận rằng evidence đủ.

**Advanced RAG** cải thiện lỗi cụ thể theo tầng. Trước truy xuất có thể viết lại query hoặc tạo truy vấn giả định (HyDE); retrieval có thể kết hợp BM25 và dense, lọc metadata, hợp nhất thứ hạng (RRF); sau retrieval có thể rerank, lọc trùng và nén context. Không nên thêm mọi kỹ thuật cùng lúc: nếu metric thay đổi sẽ khó biết nguyên nhân. Mỗi thay đổi cần ablation trên cùng data, question và gold evidence.

**Modular RAG** nhìn hệ thống thành các module thay thế được: ingestion, retriever, reranker, context builder, generator, verifier. Cách tổ chức này giúp đổi một thành phần mà vẫn giữ giao diện chung. **Agentic RAG** cho một agent quyết định tìm tiếp, đổi query, gọi tool hoặc dừng; linh hoạt hơn nhưng tốn lượt chạy, khó tái lập và có thêm lỗi điều phối.

Self-RAG đưa cơ chế tự đánh giá việc có cần truy xuất và mức hỗ trợ của bằng chứng vào quá trình sinh. CRAG đánh giá chất lượng tài liệu truy xuất rồi có thể sửa truy vấn hoặc tìm nguồn bổ sung. Đây là hướng nghiên cứu để hiểu, không phải thành phần đã hiện thực trong PoC. Một hệ thống đồ án nhỏ nên chứng minh baseline và các bước kiểm soát trước khi thêm agent.

## 6. Ánh xạ vào PoC

PoC dùng corpus nhỏ gồm văn bản học vụ có nguồn, phiên bản và SHA-256. BM25 và dense BGE-M3 được đo riêng, sau đó so sánh RRF và BGE reranker. Generation được nối bằng Ollama/Qwen3:4B để kiểm tra tích hợp cục bộ; pilot hiện chưa chứng minh độ đúng nội dung hay citation. Không sử dụng app để tư vấn quy định còn hiệu lực nếu chưa cập nhật và kiểm định corpus.

### Tài liệu đọc

1. Lewis et al. (2020), [Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks](https://arxiv.org/abs/2005.11401).
2. Gao et al. (2024), [Retrieval-Augmented Generation for Large Language Models: A Survey](https://arxiv.org/abs/2312.10997).
3. Asai et al. (2024), [Self-RAG](https://arxiv.org/abs/2310.11511).
4. Yan et al. (2024), [Corrective Retrieval Augmented Generation](https://arxiv.org/abs/2401.15884).
5. Es et al. (2024), [RAGAs](https://aclanthology.org/2024.eacl-demo.16/).
