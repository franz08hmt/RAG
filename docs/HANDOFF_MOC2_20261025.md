# Bàn giao tiến độ Mốc 2 ngày 25/10/2026

## Đọc trước khi tiếp tục

Đề tài đúng: **Tìm hiểu Retrieval Augmented Generation (RAG)**. Nhánh
`tim-hieu-rag-dot2`, thư mục `D:\RAG\rag-hcmute-dot2`. Chưa push, merge hoặc thay PR #2.
Các mục trong handoff Mốc 1 là lịch sử; trạng thái ngày 25/10 ở tài liệu này.
Bản DEMO và mọi bản Mốc 1 được giữ nguyên; Mốc 2 là báo cáo riêng phát triển tiếp.

## Đã có trong đợt này

1. Khảo sát trang PDF bằng PageArtifacts: vùng chữ/ảnh/bảng ứng viên, tọa độ và hash,
   không đưa full text/ảnh gốc vào Git. Có ảnh nguồn minh họa trong DOCX sau khi rà PII.
2. So BGE-M3/E5-small trên cùng 289 cửa sổ không truncation; dùng đúng tiền tố E5.
   Recall ký tự Top-5: 0,89436 và 0,89019; mẫu chỉ 7 câu answerable development.
   Có per-query và bootstrap cặp, không tuyên bố model tốt nhất cho tiếng Việt.
3. Flat/HNSW/IVF cùng vector; phân biệt neighbor recall với evidence recall. RRF không
   mặc nhiên vượt Dense; reranker tăng recall nhưng có thể giảm MRR.
4. Cache embedding kiểm fingerprint/checksum; phân loại lỗi generation; console đã
   chạy đầu-cuối P007, có kiểm lại ngày 25/10. Hai prompt × 10 câu chạy đủ, chưa sửa
   được refusal: 0/3 model_abstained mỗi prompt; lỗi JSON/citation không được cộng điểm.
5. BM25 tham chiếu để học công thức, có kiểm thử đối chiếu thư viện. Không thay baseline.
6. Báo cáo và hướng dẫn tái lập, tài liệu hỏi đáp bảo vệ, evidence JSON đã lọc nội dung.

## Đường dẫn chính

- Commit chứa mã, số liệu và DOCX của đợt này: `df73d34` (chỉ ở local).

- Báo cáo đã kiểm tra 15 trang: `reports/22110068_RAG_Bao_Cao_Tien_Do_Moc_2_v3.docx`.
  v1/v2 là bản QA cục bộ, không dùng để nộp; bản v6 Mốc 1 không thay đổi.

- Hướng dẫn chạy: `docs/MOC2_HUONG_DAN.md`; launcher `scripts/demo_m2.ps1`.
- Nội dung báo cáo: `docs/MOC2_REPORT_CONTENT.md`; builder `scripts/build_m2_report.py`.
- Số liệu an toàn để commit: `docs/evidence/m2/runs/manifest.json` và các JSON đi kèm.
- Giao thức và giới hạn: `docs/evidence/M2_CONTROLLED_EVALUATION_20261024.md`,
  `M2_INPUT_PROCESSING_20261024.md`, `M2_CONSOLE_RUNTIME_20261025.md`.
- Học và tự giải thích: `docs/hoc_tap/MOC2_CO_CHE_VA_CAU_HOI.md`.
- Bộ nguồn chính G0: 3 PDF, 182 trang, 156 chunk; không đưa QĐ 3116 vào hỏi đáp.
- Chạy kiểm soát: `controlled_run_20261024T125011Z`; sinh: `m2_console_20261024T130313Z`.
- Nội dung riêng: `D:\RAG\private_eval\m2_console\20261024T130313Z`; không commit.

## Phần vẫn mở không được đánh dấu đã xong

Mốc này là gói tiến độ, không phải hoàn tất mọi yêu cầu YC1–YC13. Còn chấm người,
holdout chưa dùng để tinh chỉnh, mở rộng số câu/model, nhiều reranker, đủ kiểu chunking,
OCR bản chép chuẩn và hiểu hình. Mục tiêu lớn trong prompt (6 embeddings, 3 rerankers,
80–100 câu...) chưa đạt; các hạn chế này được nêu trong report.

Sinh viên cần tự đọc nguồn, duyệt nhãn và chấm mệnh đề. Không tự tạo nhãn human_verified.
Khi có nhãn mới, chạy rubric đang có rồi cập nhật báo cáo bằng file mới. Không dùng
Gemini cho đến khi key đã được thay mới và có duyệt theo quy định; không đọc/in .env.
Không dùng dữ liệu ngoài hoặc phát sinh chi phí mà chưa hỏi.

## Môi trường và lưu tiến độ

Project Python: `C:\Users\Dell\anaconda3\envs\rag-hcmute\python.exe`; in interpreter
mỗi lần chạy. RTX3060 Laptop 6 GB; các model đã có sẵn, không tải thêm trong đợt này.
Máy có thể thiếu RAM khi nhiều app cùng mở; không tự sửa pagefile hay đóng app khác.
Giữ commit author theo cấu hình Git hiện có; không thay lịch sử hoặc thêm coauthor.
Commit chứa gói cuối được xác định bằng `git log -1` sau khi bàn giao; các artifact giữ
revision trước-run và SHA-256 để không giả vờ đã chạy trên một commit chưa tồn tại.

Kiểm tra ngày 25/10: 138 tests passed; ảnh của cả 15 trang DOCX được xem lại sau render
Word. Không có bảng vỡ dòng/tràn lề hoặc hình bị cắt mất nhãn ở bản v3. Kiểm định số
liệu và cấu trúc: `scripts/verify_m2_delivery.py`; đây không phải chấm đúng ngữ nghĩa.

Biên bản QA và SHA-256 báo cáo: `docs/evidence/M2_DELIVERY_CHECK_20261025.md`.
