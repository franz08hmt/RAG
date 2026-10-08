# So sánh FAISS và Qdrant local trên snapshot HCMUTE

Ngày chạy: 08/10/2026
Snapshot: `5da3bd4d5de54492`; 156 chunks; BGE-M3, vector 1.024 chiều.
Phân hoạch: development, 10 câu (7 answerable), 10 exact-evidence span.
Raw metrics-only JSON (Git-ignored): `artifacts/results/vector_store_ablation/vector_store_5da3bd4d5de54492_20261008T125329Z.json`.

## Thiết kế

Cùng các vector FP32 đã chuẩn hóa L2, cùng phép inner product, cùng Top-10 và cùng truy vấn được nạp vào FAISS `IndexFlatIP` và Qdrant local persistent exact-search. Độ đúng của danh sách Top-10 được so trực tiếp với FAISS. Độ trễ được đo ở tầng tìm kiếm store trên CPU, sau khi embedding truy vấn đã có; không bao gồm model inference. Mỗi trong 7 câu development được chạy 50 lần.

| Store | Build index (ms) | Kích thước artifact (byte) | Query p50 (ms) | Query p95 (ms) | Top-10 khớp FAISS | Evidence-span Recall@5 | Complete-evidence Hit@5 | MRR@10 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| FAISS IndexFlatIP (in-memory exact) | 0,595 | 639.021 | 0,041 | 0,068 | 100% | 9/10 | 6/7 | 0,762 |
| Qdrant local persistent, exact | 885,305 | 1.610.281 | 3,088 | 4,082 | 100% | 9/10 | 6/7 | 0,762 |

Run ID: `vector_store_5da3bd4d5de54492_20261008T125329Z`
Qdrant client: 1.19.1. Chỉ số chất lượng bằng nhau vì cả hai trả về cùng thứ tự Top-10 theo phép đối chiếu này.

## Diễn giải và giới hạn

Phép thử trả lời một câu hỏi hẹp: hai lựa chọn có cho kết quả exact search giống nhau khi nhận đúng cùng vector và khoảng cách hay không? Trong thiết lập nhỏ này, câu trả lời là có. Nó không chứng minh hai hệ thống tương đương ở quy mô lớn, khi có metadata filter, cập nhật/xóa, tải đồng thời hay cấu hình ANN.

Build time và artifact size không phải phép so sánh hoàn toàn đồng dạng: FAISS là index in-memory, còn Qdrant local ghi cả cấu trúc lưu trữ/payload ra đĩa. Query latency ở mức microsecond–millisecond trên 156 vector còn chịu nhiễu môi trường; không nên suy ra thông lượng sản phẩm. Qdrant trong phép thử dùng exact search, không phải HNSW benchmark. Nếu yêu cầu hiện tại chỉ là PoC nhỏ chạy offline, FAISS ít thành phần vận hành hơn; nếu cần metadata payload/persistence thì Qdrant có đặc tính hệ thống thuận tiện hơn. Lựa chọn này là cân bằng vận hành, không phải tuyên bố chất lượng retrieval vượt trội.

## Tái lập và nguồn

`scripts/run_vector_store_ablation.py` tái lập phép thử bằng vector cache được tạo cục bộ; cần Qdrant client và FAISS đã cài. Nội dung nguồn, embeddings và Qdrant storage không được đưa vào Git.

- [FAISS wiki — index và trade-off exact/approximate](https://github.com/facebookresearch/faiss/wiki).
- [Qdrant — local mode](https://qdrant.tech/documentation/frameworks/langchain/) và [hybrid search](https://qdrant.tech/documentation/search/hybrid-search/).
