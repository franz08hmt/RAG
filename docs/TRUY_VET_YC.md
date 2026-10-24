# Truy vết yêu cầu của giảng viên YC1–YC13

Cập nhật: 25/10/2026. “Có minh chứng” nghĩa là có nội dung/code/kết quả cụ thể trong repository; không đồng nghĩa yêu cầu đã được đáp ứng đầy đủ nếu mẫu còn nhỏ hoặc phần kiểm chứng chưa chạy. Các YC dùng nguyên số hiệu do giảng viên cung cấp. Phần Mốc 2 bên dưới bổ sung và thay các số liệu vận hành cũ; hàng Mốc 1 giữ để truy vết lịch sử, không dùng làm trạng thái mới nhất.

| YC | Nội dung yêu cầu | Bằng chứng hiện có | Trạng thái trung thực | Phần còn thiếu / tiêu chí để khép |
|---|---|---|---|---|
| YC1 | Đúng tên “Tìm hiểu Retrieval Augmented Generation (RAG)” | Report v6 dùng đúng tên; README cập nhật theo tên này | Đạt về tên | — |
| YC2 | Tìm hiểu kỹ quy trình RAG hiện đại | `docs/tim_hieu/00_quy_trinh_rag.md`, `03_generation_va_danh_gia.md` | Một phần | Bổ sung ví dụ/lỗi theo từng giai đoạn và đối chiếu thêm các hướng nâng cao; không chỉ mô tả kiến trúc |
| YC3 | Input/output, Document Class, Chunk và citation | `docs/tim_hieu/01_du_lieu_document_chunk.md`, manifest, snapshot, chunk metadata | Một phần | Xây dựng và rà soát nhiều lớp tài liệu, version/validity, truy ngược citation đến nguồn thật |
| YC4 | PDF có text, scan, bảng, hình; cách xử lý | OCR audit, input-class audit, table ablation, optional OCR branch | Một phần | OCR scan chưa được vàng hóa đầy đủ; chưa có parser bảng tổng quát hoặc xử lý ngữ nghĩa hình; QĐ 3116 chưa vào corpus |
| YC5 | Chunking: vấn đề, thuật toán, ưu/nhược, thời điểm dùng và so sánh | Size ablation 250/40, 500/80, 750/120; section-aware vs fixed-window; bảng riêng | Một phần | Mẫu nhỏ; cần thử trên nhiều lớp tài liệu và câu hỏi độc lập; xác định trade-off theo context/citation/latency |
| YC6 | Nhiều embedding, đánh giá và phù hợp tiếng Việt bằng số liệu | BGE-M3 và multilingual-E5-small đo trên cùng G0/development | Một phần | Hai model thay vì ít nhất sáu mục tiêu; E5 bị truncation nhiều; chưa có holdout/benchmark Việt độc lập đã duyệt |
| YC7 | Vector store và so sánh thực nghiệm | FAISS IndexFlatIP vs Qdrant local exact, 156 vectors | Một phần | Chỉ hai lựa chọn; cần phân biệt Flat/IVF/HNSW và ít nhất một DB ở quy mô/metadata workload phù hợp |
| YC8 | Retrieval và đánh giá định lượng | BM25, dense BGE-M3, RRF; candidate coverage; exact-span recall, complete Hit, MRR | Một phần | Development pilot 7 câu answerable; chưa có holdout và phân tích độ bất định |
| YC9 | Reranker và đánh giá | BGE-Reranker-v2-m3 trước/sau trên Dense và RRF | Một phần | Chỉ một reranker, bảy câu; cần so sánh thêm, audit truncation và kiểm lại độc lập |
| YC10 | Xử lý query, sinh câu trả lời, citation và từ chối | Console nối Ollama/Qwen3:4B; citation ID structure; refusal pilot | Một phần; có lỗi an toàn | Từ chối 1/3 câu unanswerable, gồm output abstain/không hợp lệ; hai câu thiếu căn cứ vẫn được trả lời; chưa kiểm chứng citation semantics |
| YC11 | Đánh giá hệ thống RAG | Retrieval metrics; generation process metrics; đã bổ sung rubric/bundle private và bộ tổng hợp nhãn chấm thủ công | Một phần; chưa đánh giá end-to-end về ngữ nghĩa | Phiếu 10 câu đang ở trạng thái pending; chưa chấm answer correctness, faithfulness, answer relevance hay entailment citation; context metrics/Ragas/TruLens/judge chưa chạy; development pilot không phải holdout |
| YC12 | Ứng dụng console | `src/rag_hcmute/console_app.py`; smoke test BM25 ngày 12/10 trên 156 chunks: P007 trả Điều 17, trang PDF 23–24 ở hạng 1 và hiển thị provenance; query thử về tốt nghiệp chỉ đưa Điều 16 lên hạng 3 | Một phần | Đã xác nhận luồng console và metadata nguồn; chất lượng xếp hạng vẫn cần đánh giá trên bộ câu hỏi/gold được duyệt. Generation, refusal và citation semantics không được suy ra từ smoke test này; không cần UI bóng bẩy |
| YC13 | Tìm hiểu sâu, không lướt qua | Các audit, ablation, mã nguồn, raw metrics-only artifacts, giới hạn được ghi nhận | Đang thực hiện | Nhiều điểm vẫn chỉ là pilot; cần thêm số liệu/đọc nguồn và giải thích lỗi ở từng lớp trước khi đánh dấu hoàn tất |

## Minh chứng bổ sung Mốc 2 ngày 25/10/2026

| YC | Bổ sung và giới hạn hiện tại |
|---|---|
| YC1 | DOCX Mốc 2 dùng đúng tên đề tài, không sửa bản đã nộp. |
| YC2 | Báo cáo trình bày từng khâu, nguyên lý, quyết định, phép thử và giới hạn; không chỉ kiến trúc. |
| YC3 | Phân biệt manifest tài liệu, PageText, Chunk, RetrievalHit, GroundingSource; thêm PageArtifacts có bbox/hash. Chưa có class riêng tên Document. |
| YC4 | Audit 4 PDF (3 G0 và QĐ3116 riêng); kiểm ảnh/bảng thực. Bảng ứng viên không phải bảng đã xác minh; hiểu hình và CER/WER toàn văn chưa xong. |
| YC5 | 289 cửa sổ chung không đọc gold; 0 truncation cả hai model; phân biệt span chứa trọn với hợp khoảng ký tự. Chưa đủ mọi kiểu chunking trong kế hoạch. |
| YC6 | BGE/E5 đúng prefix, cùng đầu vào ≤512; Recall ký tự 0,894/0,890 trên 7 câu dev. Cải thiện tính công bằng, không đủ để kết luận model tốt nhất tiếng Việt. |
| YC7 | Flat/HNSW/IVF trên cùng 289 vector; recall hàng xóm, p50/p95 và kích thước; Qdrant giữ kết quả Mốc 1. Corpus quá nhỏ để kết luận khả năng mở rộng. |
| YC8 | BM25/dense/RRF, union character coverage, per-query; BM25 tham chiếu khớp công thức thư viện trong unit test. Chưa có holdout. |
| YC9 | Rerank 1024 Top20 tăng recall nhưng có thể giảm MRR; chỉ một cross-encoder. |
| YC10 | 2 prompt × 10 câu chạy đủ. Mỗi prompt 0/3 model_abstained; P006 vẫn sinh, P009 lỗi citation, P010 lỗi JSON. Không gộp lỗi định dạng vào từ chối đúng. |
| YC11 | Bootstrap cặp và chỉ số retrieval định nghĩa rõ; 20 lượt sinh chỉ kiểm vận hành. Nhãn người vẫn pending; không có điểm correctness/faithfulness đã xác minh. |
| YC12 | Cold console và cache-hit console chạy đầu–cuối; lượt kiểm lại 25/10 P007 tổng 45,03 s, S1 hợp lệ về ID. Chưa bảo đảm mọi câu đúng hoặc mọi trạng thái RAM chạy ổn định. |
| YC13 | Có phân tích lỗi P006, ranh giới chunk, truncation, ANN, trade-off reranker. Phải tiếp tục tự đọc nguồn và giải thích; không đánh dấu toàn bộ nghiên cứu hoàn tất. |

Số liệu: `docs/evidence/m2/runs/manifest.json`. Chi tiết: `docs/HANDOFF_MOC2_20261025.md`.

## Giới hạn vẫn giữ

- G0 là snapshot lịch sử gồm 3 tài liệu, 182 trang, 156 chunks; không dùng để khẳng định hiệu lực hiện tại của mọi quy định.
- Tập chính hiện có 10 câu development: 7 answerable, 3 unanswerable; 10 exact evidence span. Năm câu bảng thuộc `ablation_only`; chưa có holdout.
- Không có corpus ngoài HCMUTE. Benchmark tiếng Việt chỉ được đề xuất sau khi kiểm giấy phép và duyệt nguồn; chưa tải dữ liệu ngoài.
- Gemini chưa được gọi. Các tác vụ có thể phát sinh chi phí bị dừng ở mức 0 USD cho đến khi có ước tính và phê duyệt.
- QĐ 3116/2025 lưu ngoài repo; scan/OCR chưa đủ kiểm chứng để dùng trong retrieval/generation.

## Quy tắc cập nhật

Không chuyển trạng thái “một phần” thành “đạt” chỉ vì đã viết phần mô tả. Cập nhật YC cùng đường dẫn evidence, run ID, split và giới hạn. Khi một phép đo cần câu hỏi/gold mới, người học phải tự rà soát nguồn trước khi dữ liệu vào benchmark.
