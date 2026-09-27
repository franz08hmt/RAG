# Tóm tắt metric retrieval - đợt 1

Nguồn:
- BM25: `docs/evidence/runs/bm25_5da3bd4d5de54492_20260924T112003Z.json`
- Dense (BGE-M3): `docs/evidence/runs/dense_bge_m3_5da3bd4d5de54492_20260925T040111Z.json`

Lệnh tái tạo: `python scripts/run_pilot_eval.py --method bm25` / `--method dense`
Snapshot corpus: `5da3bd4d5de54492` (xem `data/manifests/corpus_snapshot.json`)

## Định nghĩa

- **Gold chunk**: chunk chứa đoạn bằng chứng đã xác minh thủ công cho câu hỏi (cột `expected_chunk_id`
  trong `pilot_questions.csv`); một số câu có 2 gold chunk.
- **"Truy xuất đúng"**: chunk trả về có `chunk_id` trùng với một gold chunk của câu hỏi đó.
- **Recall@5**: tỉ lệ câu hỏi có ít nhất 1 gold chunk trong Top-5.
- **MRR@10**: trung bình 1/hạng của gold chunk đầu tiên trong Top-10; 0 nếu không xuất hiện.
- **Mẫu số**: 7/10 câu có gold evidence đã xác minh (P001, P002, P003, P004, P005, P007, P008).

## Kết quả

| Phương pháp | Cấu hình | Recall@5 | MRR@10 |
|---|---|---|---|
| BM25 (baseline) | rank_bm25.BM25Okapi, tokenize `\w+` Unicode, hạ chữ thường | 3/7 = **0,429** | **0,371** |
| Dense (BGE-M3) | model `BAAI/bge-m3`, dim 1024, L2-normalize, FAISS `IndexFlatIP` (≈cosine), `max_seq_length=1024`, không cần instruction prefix cho câu hỏi (theo model card) | 6/7 = **0,857** | **0,643** |

Dense Retrieval cải thiện rõ rệt so với BM25 trên đúng corpus và bộ câu hỏi này. Đây là **kết quả thật,
đo lần đầu** trên một mẫu rất nhỏ (7 câu) — chưa đủ để kết luận tổng quát cho mọi loại câu hỏi, chỉ đủ
để xác nhận pipeline Dense Retrieval hoạt động đúng và có tín hiệu tích cực đáng để đầu tư tiếp
(hybrid, reranker) ở mốc sau.

## Chi tiết theo câu hỏi (hạng của gold chunk đầu tiên, Top-10; "-" = không lọt Top-10)

| ID | Câu hỏi (rút gọn) | Hạng BM25 | Điểm BM25 top-1 | Hạng Dense | Điểm Dense top-1 |
|---|---|---|---|---|---|
| P001 | Xét công nhận tốt nghiệp | 2 | 16,81 | **1** | 0,797 |
| P002 | Rút bớt học phần | **1** | 27,26 | 3 | 0,670 |
| P003 | Cảnh báo học tập | - | 14,33 | **2** | 0,685 |
| P004 | Đăng ký học lại | - | 15,87 | 6 | 0,663 |
| P005 | Đăng ký Thực tập tốt nghiệp | - | 18,73 | **1** | 0,721 |
| P007 | Nghỉ học tạm thời | **1** | 23,53 | **1** | 0,750 |
| P008 | Buộc thôi học | 10 | 19,22 | 2 | 0,680 |

Quan sát: Dense sửa đúng 2 trường hợp BM25 thất bại nặng nhất do lệch từ vựng/corpus mất cân bằng
(P003, P005 — xem phân tích nguyên nhân gốc trong `case_studies.md`), nhưng lại **kém hơn BM25** ở
P002 (từ hạng 1 tụt xuống hạng 3) — cho thấy hai phương pháp có điểm mạnh khác nhau như dự đoán trong
tài liệu DEMO, ủng hộ hướng Hybrid (RRF) ở mốc kế tiếp thay vì chỉ chọn một phương pháp.

## Quan sát trên câu hỏi unanswerable (P006, P009, P010)

BM25: điểm Top-1 dao động 13,2-20,1, không tách biệt rõ answerable khó khỏi unanswerable.
Dense: điểm Top-1 (cosine) là 0,691 (P006), 0,561 (P009), 0,632 (P010) — thấp hơn phần lớn câu
answerable (0,66-0,80), tách biệt rõ hơn BM25 một chút, nhưng **P006 vẫn cao hơn cả một số câu
answerable** (ví dụ P004 = 0,663) nên **vẫn chưa thể dùng một ngưỡng điểm đơn giản để tự động từ
chối** — hệ thống CHƯA có refusal guard đã hiệu chỉnh ở mốc này, đúng như phạm vi đã khai báo. Việc
hiệu chỉnh ngưỡng (hoặc dùng tín hiệu sau rerank) vẫn là công việc dự kiến ở mốc kế tiếp.
