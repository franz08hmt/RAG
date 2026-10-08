# Thử nghiệm embedding trên corpus HCMUTE

Ngày chạy: 08/10/2026
Snapshot: `5da3bd4d5de54492`
Phân hoạch: development; 10 câu hỏi (7 answerable), 10 exact-evidence span, 156 chunks.
Runner: `scripts/run_embedding_model_ablation.py`
Raw metrics-only JSON (Git-ignored): `artifacts/results/embedding_model_ablation/embedding_5da3bd4d5de54492_20261008T125238Z.json`.

## Câu hỏi phép thử

Với cùng corpus, chunk, gold span và câu hỏi, hai embedding model có đưa đúng đoạn bằng chứng lên đầu danh sách hay không? Phép thử này chỉ khảo sát dense retrieval trên tập development hiện có; nó không phải đánh giá đại diện cho toàn bộ tiếng Việt hoặc dữ liệu học vụ HCMUTE.

## Thiết lập và kết quả

| Model | Vector | Giới hạn sequence của cấu hình | Chunk vượt giới hạn | Evidence-span Recall@5 | Complete-evidence Hit@5 | First-evidence MRR@10 |
|---|---:|---:|---:|---:|---:|---:|
| BAAI/bge-m3 | 1.024 | 1.024 token | 4/156 | 9/10 | 6/7 | 0,762 |
| intfloat/multilingual-e5-small | 384 | 512 token | 125/156 | 6/10 | 5/7 | 0,651 |

Run ID: `embedding_5da3bd4d5de54492_20261008T125238Z`
Hai model được ghim revision riêng; E5 dùng tiền tố `query:` và `passage:` theo model card. Vector được tạo lại riêng cho từng model, không trộn giữa các index. Cả hai chạy trên CUDA. Thời gian mã hóa một lượt không warm-up được lưu trong JSON nhưng không dùng để kết luận tốc độ.

## Cách đọc kết quả

Trong pilot này, BGE-M3 xếp được nhiều exact span vào Top-5 hơn E5-small. Một điểm kỹ thuật đáng chú ý là tập chunk hiện tại được thiết kế quanh cấu hình dài hơn: 125/156 chunk vượt giới hạn 512 token của E5-small, so với 4/156 khi dùng giới hạn 1.024 token cho cấu hình BGE-M3 của project. Vì vậy, chênh lệch quan sát được gắn với cả model **và** tương tác giữa giới hạn đầu vào với chunking hiện tại; đây chưa phải phép so sánh thuần kiến trúc embedding.

Kết quả không chứng minh BGE-M3 luôn tốt hơn cho tiếng Việt. Muốn kết luận phù hợp hơn cần thêm các model, kiểm soát truncation bằng một thiết kế chunk chung khả dụng cho mọi model, bộ câu hỏi độc lập và phép đo nhiều nhóm truy vấn. Không đổi chunk size chỉ để nâng điểm của riêng một model trong lần so sánh này.

## Tái lập

Chạy `scripts/run_embedding_model_ablation.py` trong env `rag-hcmute`, truyền snapshot G0, model paths local và output dưới `artifacts/results/`. Raw output không chứa câu hỏi, câu trả lời hay nội dung PDF; model weights và PDF vẫn ở ngoài Git.

## Nguồn tham khảo

- [BGE-M3, model card](https://huggingface.co/BAAI/bge-m3), [bài báo](https://arxiv.org/abs/2402.03216).
- [Multilingual E5-small, model card](https://huggingface.co/intfloat/multilingual-e5-small), [E5 technical report](https://arxiv.org/abs/2402.05672).
- [VN-MTEB, Findings of EACL 2026](https://aclanthology.org/2026.findings-eacl.86/). Benchmark này giúp tham chiếu cách đánh giá embedding tiếng Việt; không thay cho câu hỏi và tài liệu học vụ của project.
