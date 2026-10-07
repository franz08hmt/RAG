# Đề xuất tài nguyên và thiết kế thử nghiệm reranker — 07/10/2026

## Trạng thái

Model đã được người học duyệt tải ngày 07/10/2026 và đã được tải, ghim revision, xác minh trọng số; smoke test offline và phép so sánh reranking đầu tiên trên development pilot G0 đã chạy. Không cài thêm package. Kết quả chỉ có tính thăm dò trên mẫu nhỏ, chưa có holdout hoặc kết luận khái quát. Mốc 1 vẫn mở.

- Revision cố định: `953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e`.
- Snapshot local: `D:\RAG\models\huggingface\hub\models--BAAI--bge-reranker-v2-m3\snapshots\953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e` (ngoài Git).
- `model.safetensors`: 2,271,071,852 bytes; SHA-256 `d9e3e081faff1eefb84019509b2f5558fd74c1a05a2c7db22f74174fcedb5286`, khớp metadata Hub.
- Smoke test dùng Python env `rag-hcmute`, PyTorch `2.14.0+cu126`, CUDA 12.6, RTX 3060 Laptop GPU; nạp FP16 và chấm hai cặp văn bản tổng hợp, `max_length=128`. Cặp khớp ngữ nghĩa được xếp trên cặp không liên quan; peak CUDA allocation 1.067 GiB.
- Đây là kiểm tra kỹ thuật nhỏ, không dùng câu hỏi/tài liệu HCMUTE, không phải benchmark, không chứng minh chất lượng tiếng Việt hoặc hiệu quả trên corpus.

## Căn cứ từ kết quả hiện có

Trên pilot G0 hiện tại (7 câu answerable, 10 exact-evidence span), candidate Top-20 của Dense BGE-M3 và Hybrid RRF chứa đủ 10/10 span ở cả 7/7 câu; BM25 chứa 7/10 span và đủ toàn bộ span ở 5/7 câu. Vì reranker chỉ sắp xếp lại candidate đầu vào, BM25 có ba span không thể được “khôi phục” bằng reranking ở phép thử này. Dense và RRF là hai candidate source có cơ sở để đưa vào so sánh tiếp; kết quả coverage mới chỉ là pilot, không chứng minh chất lượng sau rerank.

## Model ứng viên

Ứng viên đầu tiên được đề xuất là `BAAI/bge-reranker-v2-m3`. Tài liệu của nhà phát triển mô tả đây là cross-encoder đa ngôn ngữ: query và passage được đưa vào cùng lượt chấm điểm, sau đó các passage được xếp theo độ liên quan; đây là cách chấm khác với embedding rồi tìm kiếm vector. Model card hiện ghi giấy phép Apache-2.0, tổng repo khoảng 2,29 GB và file trọng số `model.safetensors` khoảng 2,27 GB. Tài liệu công bố nhãn “multilingual”, nhưng không cung cấp trong trang model card một kết luận đủ để đảm bảo chất lượng riêng cho tiếng Việt hoặc corpus học vụ HCMUTE; điều đó phải được đo trên bộ câu hỏi đã kiểm tra của project.

Đường chạy thực tế dùng `AutoTokenizer` và `AutoModelForSequenceClassification` trong `transformers`, ghim revision và xác minh hash trước khi nạp với `local_files_only=True`. Không cài `FlagEmbedding` hay package mới. Môi trường dùng `transformers 5.17.0`, `sentence-transformers 6.1.0` và CUDA PyTorch `2.14.0+cu126`. Runner giữ model local/offline, không tự tải ngầm trong app.

## Tài nguyên máy và tính khả thi

- Dung lượng trống ổ D trước khi tải khoảng 22,33 GiB; sau khi tải, lần kiểm tra gần nhất còn khoảng 20,19 GiB. Model đã nằm ngoài Git tại cache local; dung lượng có thể thay đổi khi tiếp tục chạy project.
- GPU hiện thấy trong env project: NVIDIA GeForce RTX 3060 Laptop GPU, VRAM 6,0 GiB; `torch.cuda.is_available()` trả về `True`.
- Inference local đã chạy thành công với FP16. Trong lượt pilot, peak CUDA allocated là 1,110 GiB và peak reserved là 2,135 GiB sau khi model được nạp. Đây là phép đo trên batch nhỏ của project, không phải mức tối đa cho mọi batch/chiều dài đầu vào.
- Dùng `max_length=512` với `truncation="only_second"` để giữ query và chỉ cắt phần cuối passage. Trong 140 cặp mỗi nhánh, 99 cặp Dense và 110 cặp RRF dài hơn giới hạn; kiểm tra offset cho thấy 0/10 occurrence exact gold evidence bị cắt ở mỗi nhánh. Nhiều phần ngữ cảnh không phải gold vẫn bị cắt, nên giới hạn này cần được giữ trong diễn giải.
- Chi phí API dự kiến: 0 USD vì thiết kế chạy local. Chi phí thực tế là thời gian tải, dung lượng đĩa, điện năng và thời gian GPU; không có API trả phí trong bước này.

## Thiết kế phép so sánh đã áp dụng

1. Dùng 7 câu answerable hiện có như development pilot với 10 gold evidence span đã được kiểm tra hash theo snapshot. Không dùng holdout, không dùng pilot này để tuyên bố hiệu quả tổng quát hoặc tinh chỉnh tham số/model.
2. Giữ cố định G0, chunking, câu hỏi, gold span và candidate depth 20. Lập hai cặp so sánh độc lập: Dense Top-20 trước/sau rerank và RRF Top-20 trước/sau rerank. Không trộn candidate set giữa các cặp; như vậy thay đổi thứ hạng trong mỗi cặp mới có thể quy cho reranker.
3. Chấm điểm từng cặp `(query, candidate chunk)` bằng model local, sắp xếp giảm dần theo score, giữ chunk ID và metadata nguồn gốc. Không thay văn bản chunk, corpus hay query giữa baseline và reranked run.
4. Dùng cùng các metric đã có để so sánh: exact-evidence Recall@5, Complete-evidence Hit@5 và First-evidence MRR@10; giữ candidate coverage@20 như kiểm tra rằng tập đầu vào không đổi. Ghi thêm thời gian nạp model, thời gian chấm theo query, median/p95 latency và peak VRAM. Tách thời gian khởi tạo khỏi thời gian inference.
5. Lưu kết quả theo mã câu/span, thứ hạng, config và hash; không ghi câu hỏi, excerpt, nội dung PDF hoặc thông tin cá nhân vào log. Phân tích cả trường hợp cải thiện và suy giảm; chưa đặt reranker làm mặc định nếu chưa có holdout đủ tin cậy.
6. Kiểm tra truncation trước khi kết luận. Nếu tỷ lệ cao, điều tra lựa chọn `max_length`/chunk length và báo cáo ảnh hưởng; không âm thầm cắt evidence hoặc thay chunking trong cùng phép so sánh.

## Phạm vi đã giữ khi triển khai

- Không tải model reranker thứ hai, không benchmark ngoài corpus HCMUTE, không gọi Gemini hay API khác trong bước thử này.
- Không mở rộng câu hỏi bằng Gemini: khóa Gemini từng được dán trong hội thoại phải được thu hồi/đổi và cấu hình an toàn lại trước; câu hỏi đưa vào holdout cần do người học kiểm tra nguồn và gold evidence.
- Pilot reranker đã hoàn tất trên candidate Top-20 Dense và RRF; kết quả, truncation, latency và giới hạn được ghi ở phần dưới. Bước sau cần mở rộng/hoàn thiện holdout và kiểm tra thêm input classes trước khi cân nhắc đổi mặc định.

## Nguồn chính thức

- [Model card BAAI/bge-reranker-v2-m3](https://huggingface.co/BAAI/bge-reranker-v2-m3) — model type, hướng dẫn Transformers, license và dung lượng file/repository; truy cập 07/10/2026.
- [FlagEmbedding — hướng dẫn inference reranker](https://github.com/FlagOpen/FlagEmbedding/blob/master/examples/inference/reranker/README.md) — mô tả reranker là mô hình chấm query–passage, lựa chọn model đa ngôn ngữ và cách diễn giải score; truy cập 07/10/2026.

## Kết quả pilot reranking đầu tiên — 07/10/2026

Runner `scripts/run_reranker_ablation.py` đánh giá hai candidate source độc lập trên snapshot native-only G0. Mỗi source lấy Top-20, sau đó so sánh thứ hạng ban đầu với thứ hạng do reranker tạo ra trên đúng cùng tập ứng viên; không thay đổi corpus, chunking, câu hỏi hay gold evidence. Trước khi chạy, runner xác minh manifest, snapshot, chunk signature, gold-span hash, revision và SHA-256 của model. Holdout không được dùng.

| Candidate source | Candidate coverage@20 | Trước rerank: Recall@5 / Complete Hit@5 / MRR@10 | Sau rerank: Recall@5 / Complete Hit@5 / MRR@10 |
| --- | --- | --- | --- |
| Dense BGE-M3 | 10/10 span; 7/7 câu đủ evidence | 9/10; 6/7; 0,762 | 10/10; 7/7; 0,857 |
| Hybrid RRF (k=60) | 10/10 span; 7/7 câu đủ evidence | 6/10; 4/7; 0,524 | 10/10; 7/7; 0,857 |

Trong pilot nhỏ này, reranker xếp đủ evidence vào Top-5 ở cả hai nguồn ứng viên. Kết quả chỉ mô tả 7 câu answerable/10 span của development pilot; không phải test độc lập, không chứng minh khái quát cho các lớp tài liệu hoặc câu hỏi khác, và chưa đủ cơ sở để đổi retrieval mặc định. Một lần chạy đơn lẻ cũng không đủ để kết luận về độ ổn định của latency.

### Độ dài đầu vào và độ trễ

- Có 99/140 cặp Dense (70,7%) và 110/140 cặp RRF (78,6%) vượt giới hạn 512 token. Exact gold evidence không bị cắt trong 10/10 occurrence ở từng candidate source; phần ngữ cảnh khác của nhiều candidate passage vẫn bị cắt.
- Trên RTX 3060 Laptop GPU, FP16: thời gian rerank median mỗi câu là 446,1 ms (Dense) và 445,2 ms (RRF); p95 nearest-rank lần lượt 772,2 ms và 461,2 ms. Model load khoảng 6,99 s; peak CUDA allocated 1,110 GiB và peak reserved 2,135 GiB trong lượt chạy này. Các số đo đến từ 7 lượt mỗi nhánh, không phải cam kết hiệu năng production.
- Chi phí API: 0 USD; model, retrieval và reranking đều chạy local/offline. Không cài thêm package.

Raw result metrics-only, Git-ignored: `artifacts/results/reranker_ablation/reranker_5da3bd4d5de54492_20261007T094759Z.json`. File chỉ ghi hash, metric tổng hợp, mã câu/span, thứ hạng, độ dài/cắt token và thời gian; không ghi câu hỏi, câu trả lời, excerpt nguồn hay vector. Kiểm thử cuối toàn repo: 80 passed; compileall và `git diff --check` đạt. Mốc 1 vẫn mở; chưa cập nhật DOCX, chưa đánh giá generation/citation/refusal và chưa chuyển Mốc 2.

### Kiểm tra độ nhạy ở 1.024 token — 07/10/2026

Để xem ngưỡng 512 có làm mất ngữ cảnh ứng viên hay đổi thứ hạng, chạy lại cùng runner với `--max-length 1024 --batch-size 4`. Câu hỏi, corpus G0, candidate Top-20, chunking, gold spans, model revision và các phương pháp còn lại giữ nguyên.

- Độ dài cặp lớn nhất quan sát được là 723 token ở candidate Dense và 812 token ở candidate RRF; ở ngưỡng 1.024, truncation giảm từ 99/140 và 110/140 xuống 0/140 cặp.
- Metric trước/sau reranking và bản đồ thứ hạng evidence theo từng câu không đổi so với lượt 512. Trong cả hai lượt, gold evidence candidate không bị cắt.
- Median rerank mỗi câu ở lượt 1.024 là 560,8 ms (Dense) và 571,4 ms (RRF), cao hơn lượt 512 trong lần đo này. Peak CUDA allocated là 1,137 GiB, peak reserved 2,135 GiB.
- Đây là kiểm tra độ nhạy trên cùng development pilot, không phải cách chọn ngưỡng tối ưu. Kết quả không chứng minh rằng ngưỡng 1.024 sẽ tốt hơn trên corpus hoặc câu hỏi khác; chưa đổi cấu hình mặc định. Cần đánh giá lại sau khi có câu hỏi đã duyệt đa dạng hơn và holdout tách biệt.

Raw result metrics-only, Git-ignored: `artifacts/results/reranker_ablation/reranker_5da3bd4d5de54492_20261007T095831Z.json`.
