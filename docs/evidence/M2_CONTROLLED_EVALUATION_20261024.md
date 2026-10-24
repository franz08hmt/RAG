# Mốc 2 — phép thử có kiểm soát

## Câu hỏi cần trả lời

Chênh lệch BGE-M3 và multilingual-E5-small ở Mốc 1 chịu ảnh hưởng bao nhiêu bởi việc cắt
đầu vào? Giữ nguyên nội dung cho cả hai, kiểm đủ giới hạn tokenizer rồi so lại thay vì
kết luận từ số 4/156 và 125/156 đoạn quá dài ở thiết lập cũ.

## Giao thức

- Run hoàn chỉnh: `controlled_run_20261024T125011Z`.
- G0 `5da3bd4d5de54492`; 10 câu development, 7 answerable, 10 span nguồn. Không holdout.
- 289 cửa sổ chung, tối đa 250 đơn vị khoảng trắng, overlap 40; thu nhỏ đến khi cả hai
  tokenizer nhận đủ prefix + text + special tokens trong 512 token. Không đọc gold để cắt.
- BGE và E5 đều float32, normalize L2; E5 có query:/passage:, BGE không thêm instruction.
- Số liệu đầy đủ: `m2/runs/controlled_evaluation.json`; mọi bảng DOCX đọc từ artifact.
- Trong cùng phép thử, so BM25, hai dense, hai RRF; rerank Top-20 từ BGE Dense/RRF.
- FAISS Flat/HNSW/IVF nhận cùng vector BGE; CPU 1 luồng; warm-up rồi 50 lượt × 7 query.
- Bootstrap cặp 5.000 lần, seed 22110068. IID chỉ là giả định thăm dò: câu hỏi có chung chủ đề.

## Chỉ số không được lẫn

`evidence_span_recall_at_5` cũ là tỷ lệ span có **một** chunk chứa trọn trong top5. Trong
cửa sổ chung chỉ 6/10 span có một chunk chứa trọn ngay từ đầu; đây là trần của chỉ số này,
không phải toàn bộ nội dung bốn span kia đã biến mất khỏi corpus.

`character_coverage` mới dùng hợp khoảng ký tự trong từng document, cho phép nhiều chunk
cùng phủ một span. Chuẩn hóa bằng `split` rồi nối một khoảng trắng; khoảng trắng ở khe
hai đoạn không trả về vẫn có thể bị tính thiếu một ký tự. Chỉ số giữ riêng macro recall,
precision, IoU, Hit ở ngưỡng .5, MRR và nDCG gain tuyến tính theo độ phủ.

Neighbor Recall@10 của ANN dùng Top-10 Flat làm đối chứng, **không** dùng gold học vụ.
Không so kích thước index FAISS với toàn thư mục DB như cùng một dạng bộ nhớ.

## Kết quả và diễn giải

BGE và E5 có Recall ký tự gần nhau trên bảy câu; MRR khác nhiều hơn. RRF k=60 không tự động
vượt Dense. Reranker tăng độ phủ Top-5 nhưng có thể giảm MRR, nên không thể nói nó tốt hơn
ở mọi mặt. Đọc các giá trị chính xác và từng qid trong JSON đi kèm; không điều chỉnh ngưỡng
để tạo ra kết luận ưu tiên model nào.

Flat là baseline hợp lý ở quy mô nhỏ. HNSW efSearch thấp và IVF nprobe thấp minh họa việc
bỏ sót hàng xóm; các độ trễ rất nhỏ không đại diện cho tải production.

Chưa đạt kế hoạch 6 embedding, 3 reranker, 6 kiểu chunking đầy đủ, budget context bằng
tokenizer LLM, holdout hoặc benchmark Việt ngoài HCMUTE. Không dùng khảo sát lý thuyết thay
cho thí nghiệm còn thiếu. Luồng console G0 chưa đổi sang chunk thực nghiệm.
