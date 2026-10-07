# Thử nghiệm Hybrid Retrieval bằng Reciprocal Rank Fusion — 07/10/2026

## Mục tiêu

Đối chiếu ba cách xếp hạng trên cùng một corpus: BM25, Dense BGE-M3 và kết hợp hai danh sách bằng Reciprocal Rank Fusion (RRF). Đây là thử nghiệm retrieval, chưa phải đánh giá end-to-end RAG.

RRF cộng đóng góp thứ hạng của mỗi nhánh theo công thức:

\[
\operatorname{RRF}(d)=\sum_i \frac{1}{k + \operatorname{rank}_i(d)}
\]

Với chunk không nằm trong danh sách ứng viên của một nhánh, nhánh đó không cộng điểm cho chunk. Thử nghiệm giữ `k=60` theo thiết lập kinh điển trong bài báo gốc; đây là điểm khởi đầu cố định, không phải kết luận rằng 60 tối ưu cho dữ liệu HCMUTE. [Cormack, Clarke và Buettcher, SIGIR 2009](https://doi.org/10.1145/1571941.1572114) giới thiệu RRF như một cách hợp nhất thứ hạng không phụ thuộc việc chuẩn hóa điểm giữa các hệ thống; kết quả của bài báo không bảo đảm RRF sẽ tốt hơn trong corpus này.

## Thiết kế

- Dữ liệu: snapshot G0 native-only `5da3bd4d5de54492`, 3 tài liệu, 182 trang, 156 chunk; SHA-256 được đối chiếu với manifest trước khi chạy.
- Câu hỏi: 7 câu answerable/10 evidence span đã xác minh theo offset và hash; 3 câu unanswerable được thống kê nhưng không tính retrieval metric vì không có gold evidence.
- BM25 dùng `rank_bm25.BM25Okapi`; Dense dùng BGE-M3 local với FAISS `IndexFlatIP`, chuẩn hóa vector L2, chạy trên CUDA. Không tải model và không gọi API.
- RRF nhận Top-20 của BM25 và Top-20 của Dense, sau đó trả Top-10 fused; đánh giá evidence Recall@5, Complete-evidence Hit@5 và First-evidence MRR@10.
- G0 được tạo trước khi lưu token offsets. Runner tái tạo chunk trong bộ nhớ từ các trang nguồn rồi kiểm tra ID, hash văn bản, số token, section path, phương pháp chia và trang đầu/cuối khớp G0. Chỉ sau khi chữ ký nội dung khớp mới dùng offsets để đánh giá; không ghi đè snapshot.

## Kết quả

| Phương pháp | Evidence Recall@5 | Complete-evidence Hit@5 | First-evidence MRR@10 |
|---|---:|---:|---:|
| BM25 | 4/10 (0,400) | 3/7 (0,429) | 0,371 |
| Dense BGE-M3 | 9/10 (0,900) | 6/7 (0,857) | 0,762 |
| Hybrid RRF (k=60) | 6/10 (0,600) | 4/7 (0,571) | 0,524 |

Trong sáu câu về Quy chế 1727 (9 span), BM25 tìm được 4/9 span, Dense 8/9 và RRF 6/9. Với câu duy nhất về Hướng dẫn thực tập, Dense tìm được 1/1 span; BM25 và RRF đều 0/1. Bộ pilot không có câu answerable về Sổ tay Sinh viên.

Để xem điểm tổng hợp che khuất trường hợp nào, mỗi câu được phân loại theo vị trí các span bắt buộc; bảng dưới chỉ dùng mã câu/span và hạng, không chép câu hỏi hoặc nguồn:

| Lớp kết quả | BM25 | Dense | RRF |
|---|---:|---:|---:|
| Đủ tất cả span trong Top-5 | 3/7 | 6/7 | 4/7 |
| Có một phần span trong Top-5 | 0/7 | 1/7 | 1/7 |
| Không có span ở Top-5, nhưng có span hạng 6–10 | 1/7 | 0/7 | 1/7 |
| Không có span chính xác trong Top-10 | 3/7 | 0/7 | 1/7 |

Hạng evidence theo câu (danh sách hạng lần lượt ứng với các span S1, S2; `—` là không tìm thấy trong Top-10):

| Mã câu | BM25 | Dense | RRF | Phân loại RRF |
|---|---|---|---|---|
| P001 | [2] | [1] | [1] | Đủ trong Top-5 |
| P002 | [1] | [3] | [1] | Đủ trong Top-5 |
| P003 | [—, —] | [2, 3] | [4, 6] | Một phần trong Top-5 |
| P004 | [—] | [1] | [4] | Đủ trong Top-5 |
| P005 | [—] | [1] | [—] | Không có trong Top-10 |
| P007 | [1, 1] | [1, 1] | [1, 1] | Đủ trong Top-5 |
| P008 | [—, 10] | [2, 7] | [6, 8] | Chỉ có ở hạng 6–10 |

Ở các ca cụ thể, RRF đưa P004 từ ngoài Top-10 của BM25 vào hạng 4, nhưng làm evidence của P003 kém đầy đủ hơn Dense (một span ở hạng 6) và không giữ được evidence P005 mà Dense xếp hạng 1. Với P008, Dense có một span ở hạng 2 còn RRF đẩy cả hai xuống hạng 6 và 8. P007 không phân biệt được ba phương pháp trong danh sách hạng quan sát được. Các ca này giải thích vì sao điểm RRF nằm giữa BM25 và Dense, nhưng không cho phép kết luận phương pháp nào tốt hơn nói chung.

## Độ phủ candidate trước khi áp dụng reranker

Reranker chỉ sắp xếp lại các chunk được đưa vào candidate pool; nó không thể thêm lại evidence đã bị bước retrieval loại khỏi pool. Vì vậy, ngoài điểm Top-5, runner đo xem exact evidence có xuất hiện trong Top-20 đầu vào của từng phương pháp hay không. Với Hybrid, candidate list là Top-20 sau RRF từ hai nhánh BM25/Dense, mỗi nhánh lấy tối đa 20 ứng viên.

| Candidate list | Exact span có mặt trong Top-20 | Câu có đủ mọi span trong Top-20 |
|---|---:|---:|
| BM25 | 7/10 (0,700) | 5/7 (0,714) |
| Dense BGE-M3 | 10/10 (1,000) | 7/7 (1,000) |
| Hybrid RRF | 10/10 (1,000) | 7/7 (1,000) |

Trong pilot này, cả Dense và Hybrid đều đưa toàn bộ evidence đã gán nhãn vào Top-20; do đó candidate pool của chúng có đủ dữ liệu để một reranker thử đưa evidence lên cao hơn. Đây chỉ là **độ phủ đầu vào**: không chứng minh reranker sẽ xếp đúng, và không thay cho việc so sánh reranker bằng metric sau xếp hạng. RRF hiện còn khoảng cách giữa Recall@5 (6/10) và candidate coverage@20 (10/10), nhưng bộ pilot phát triển nhỏ, chưa độc lập; không dùng kết quả này để chốt hiệu quả hoặc chọn model reranker.

## Diễn giải

Trong mẫu này, RRF cải thiện so với BM25 nhưng không vượt Dense BGE-M3: Recall@5 tăng từ 4/10 lên 6/10 khi hợp nhất, trong khi Dense riêng đạt 9/10. RRF cũng giảm Complete-evidence Hit@5 so với Dense (4/7 so với 6/7). Kết quả nhắc rằng việc kết hợp lexical và dense không tự động tốt hơn nhánh mạnh nhất; thứ hạng có thể đổi theo câu hỏi và lớp tài liệu.

Chưa chọn RRF làm mặc định. Kết quả chỉ hỗ trợ kết luận cục bộ trên bộ pilot nhỏ; chưa có holdout độc lập, chưa đo tác động của các cutoff khác, chưa so sánh vector store, chưa chạy reranker và chưa đánh giá answer generation/citation/refusal. Nếu tiếp tục, cần mở rộng câu hỏi đã được kiểm tra và tách dev/test trước khi điều chỉnh `candidate_k` hoặc `k`; không dùng lại cùng bộ để vừa chọn tham số vừa tuyên bố hiệu quả.

## Tái lập và bảo vệ dữ liệu

Runner: [`run_hybrid_retrieval_ablation.py`](../../scripts/run_hybrid_retrieval_ablation.py); triển khai RRF: [`hybrid.py`](../../src/rag_hcmute/retrieval/hybrid.py). JSON kết quả Git-ignore tại `artifacts/results/hybrid_retrieval_ablation/hybrid_5da3bd4d5de54492_20261007T091540Z.json` ghi cấu hình/hash, metric gộp, coverage@20 và chẩn đoán bằng mã câu/span, loại tài liệu, thứ hạng; không ghi câu hỏi, đáp án, trích đoạn nguồn, preview hay vector.

```powershell
& 'C:\Users\Dell\anaconda3\envs\rag-hcmute\python.exe' scripts/run_hybrid_retrieval_ablation.py --dense-model 'D:\RAG\models\huggingface\hub\models--BAAI--bge-m3\snapshots\5617a9f61b028005a4858fdac845db406aefb181'
```
