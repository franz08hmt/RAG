# Đề xuất tài nguyên và thiết kế thử nghiệm reranker — 07/10/2026

## Trạng thái

Đây là phương án chuẩn bị, chưa tải model, chưa cài thêm package và chưa chạy phép đo reranking. Mốc 1 vẫn mở. Mọi bước tải model sẽ chờ phê duyệt riêng.

## Căn cứ từ kết quả hiện có

Trên pilot G0 hiện tại (7 câu answerable, 10 exact-evidence span), candidate Top-20 của Dense BGE-M3 và Hybrid RRF chứa đủ 10/10 span ở cả 7/7 câu; BM25 chứa 7/10 span và đủ toàn bộ span ở 5/7 câu. Vì reranker chỉ sắp xếp lại candidate đầu vào, BM25 có ba span không thể được “khôi phục” bằng reranking ở phép thử này. Dense và RRF là hai candidate source có cơ sở để đưa vào so sánh tiếp; kết quả coverage mới chỉ là pilot, không chứng minh chất lượng sau rerank.

## Model ứng viên

Ứng viên đầu tiên được đề xuất là `BAAI/bge-reranker-v2-m3`. Tài liệu của nhà phát triển mô tả đây là cross-encoder đa ngôn ngữ: query và passage được đưa vào cùng lượt chấm điểm, sau đó các passage được xếp theo độ liên quan; đây là cách chấm khác với embedding rồi tìm kiếm vector. Model card hiện ghi giấy phép Apache-2.0, tổng repo khoảng 2,29 GB và file trọng số `model.safetensors` khoảng 2,27 GB. Tài liệu công bố nhãn “multilingual”, nhưng không cung cấp trong trang model card một kết luận đủ để đảm bảo chất lượng riêng cho tiếng Việt hoặc corpus học vụ HCMUTE; điều đó phải được đo trên bộ câu hỏi đã kiểm tra của project.

Phương án nạp dự kiến dùng `AutoTokenizer` và `AutoModelForSequenceClassification` từ `transformers`, là cách được hướng dẫn trong model card. Không cần cài `FlagEmbedding` chỉ để thử đường này; môi trường hiện có `transformers 5.17.0`, `sentence-transformers 6.1.0` và CUDA PyTorch `2.14.0+cu126`. Khi chạy thật, phải khóa revision model, lưu hash/config, bật chế độ offline sau khi tải và không cho phép tự tải ngầm trong app.

## Tài nguyên máy và tính khả thi

- Dung lượng trống ổ D tại thời điểm kiểm tra: khoảng 22,33 GiB. Model repo khoảng 2,29 GB, nên có đủ khoảng trống cho một bản cache model và phần dư để hệ thống hoạt động; vẫn cần kiểm tra lại ngay trước khi tải vì dung lượng có thể đổi.
- GPU hiện thấy trong env project: NVIDIA GeForce RTX 3060 Laptop GPU, VRAM 6,0 GiB; `torch.cuda.is_available()` trả về `True`.
- Đánh giá sơ bộ: cấu hình có cơ sở để thử inference local với batch nhỏ và precision phù hợp, nhưng chưa xác nhận model có vừa VRAM hay chạy đủ nhanh. Số GB của file trọng số không tương đương với tổng VRAM lúc inference; activation, batch size và độ dài cặp query–passage cũng chiếm bộ nhớ.
- Tài liệu Transformers của model dùng ví dụ ghép query/passage với `truncation=True` và `max_length=512`. Chunk của project có thể dài, vì vậy trước khi benchmark cần thống kê độ dài token của cặp query–chunk và tỷ lệ bị cắt; không được coi điểm số là công bằng nếu evidence thường nằm ở phần bị truncation.
- Chi phí API dự kiến: 0 USD vì thiết kế chạy local. Chi phí thực tế là thời gian tải, dung lượng đĩa, điện năng và thời gian GPU; không có API trả phí trong bước này.

## Thiết kế benchmark đề xuất

1. Trước khi chọn tham số, tách câu hỏi phát triển khỏi holdout và xác minh thủ công từng gold evidence theo tài liệu/page/section. Bộ 7 câu hiện tại chỉ dùng để smoke test tích hợp, không dùng để tuyên bố hiệu quả tổng quát hoặc tinh chỉnh model.
2. Giữ cố định G0, chunking, câu hỏi, gold span và candidate depth 20. Lập hai cặp so sánh độc lập: Dense Top-20 trước/sau rerank và RRF Top-20 trước/sau rerank. Không trộn candidate set giữa các cặp; như vậy thay đổi thứ hạng trong mỗi cặp mới có thể quy cho reranker.
3. Chấm điểm từng cặp `(query, candidate chunk)` bằng model local, sắp xếp giảm dần theo score, giữ chunk ID và metadata nguồn gốc. Không thay văn bản chunk, corpus hay query giữa baseline và reranked run.
4. Dùng cùng các metric đã có để so sánh: exact-evidence Recall@5, Complete-evidence Hit@5 và First-evidence MRR@10; giữ candidate coverage@20 như kiểm tra rằng tập đầu vào không đổi. Ghi thêm thời gian nạp model, thời gian chấm theo query, median/p95 latency và peak VRAM. Tách thời gian khởi tạo khỏi thời gian inference.
5. Lưu kết quả theo mã câu/span, thứ hạng, config và hash; không ghi câu hỏi, excerpt, nội dung PDF hoặc thông tin cá nhân vào log. Phân tích cả trường hợp cải thiện và suy giảm; chưa đặt reranker làm mặc định nếu chưa có holdout đủ tin cậy.
6. Kiểm tra truncation trước khi kết luận. Nếu tỷ lệ cao, điều tra lựa chọn `max_length`/chunk length và báo cáo ảnh hưởng; không âm thầm cắt evidence hoặc thay chunking trong cùng phép so sánh.

## Điểm cần duyệt trước khi triển khai

- Chỉ tải `BAAI/bge-reranker-v2-m3` sau khi người học xác nhận riêng; dung lượng hiện tại theo model page khoảng 2,29 GB.
- Không tải model reranker thứ hai, không benchmark ngoài corpus HCMUTE, không gọi Gemini hay API khác trong bước thử này.
- Không mở rộng câu hỏi bằng Gemini: khóa Gemini từng được dán trong hội thoại phải được thu hồi/đổi và cấu hình an toàn lại trước; câu hỏi đưa vào holdout cần do người học kiểm tra nguồn và gold evidence.
- Khi được duyệt tải, bước đầu chỉ là tải một revision cố định, xác minh file/hash và chạy kiểm tra nạp model + một smoke batch nhỏ. Chỉ sau khi smoke test đạt mới chạy benchmark trên development set; holdout giữ lại tới khi cấu hình được khóa.

## Nguồn chính thức

- [Model card BAAI/bge-reranker-v2-m3](https://huggingface.co/BAAI/bge-reranker-v2-m3) — model type, hướng dẫn Transformers, license và dung lượng file/repository; truy cập 07/10/2026.
- [FlagEmbedding — hướng dẫn inference reranker](https://github.com/FlagOpen/FlagEmbedding/blob/master/examples/inference/reranker/README.md) — mô tả reranker là mô hình chấm query–passage, lựa chọn model đa ngôn ngữ và cách diễn giải score; truy cập 07/10/2026.
