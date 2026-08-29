# HCMUTE Academic Documents RAG PoC

Đây là mã nguồn thực nghiệm cho đề tài **Nghiên cứu, thiết kế và hiện thực hóa hệ thống Retrieval-Augmented Generation (RAG)**. PoC được giới hạn ở bài toán hỏi đáp trên tài liệu học vụ chính thức của HCMUTE.

## Phạm vi phiên bản đầu

- Đầu vào: câu hỏi tiếng Việt về quy chế đào tạo và thủ tục học vụ.
- Đầu ra: câu trả lời ngắn, đoạn bằng chứng, tên văn bản và vị trí trang/điều khoản.
- Ngoài phạm vi: chatbot hội thoại mở, dữ liệu cá nhân, lịch học hoặc lịch thi thay đổi theo thời gian nếu corpus không chứa dữ liệu đó.
- Quy tắc an toàn: khi không có bằng chứng phù hợp, hệ thống trả về trạng thái chưa đủ căn cứ.

## Nguyên tắc triển khai

1. Mọi tài liệu phải có nguồn, phiên bản, ngày hiệu lực và mã băm trước khi được đưa vào corpus.
2. Mỗi chunk phải truy ngược được về tài liệu và số trang gốc.
3. Retrieval và generation được đánh giá riêng.
4. Cấu hình thí nghiệm, log và kết quả thô phải được lưu lại để đối chiếu trong báo cáo.

## Cấu trúc dự án

```text
rag-hcmute-poc/
├── configs/                 Cấu hình dự án và thí nghiệm
├── data/
│   ├── raw/                 PDF gốc, không chỉnh sửa
│   ├── manifests/           Danh mục và phiên bản corpus
│   ├── processed/           Text và chunks đã xử lý
│   └── question_sets/       Câu hỏi development/test
├── docs/
│   ├── decisions/           Nhật ký quyết định kỹ thuật
│   └── evidence/            Minh chứng dùng cho report
├── src/rag_hcmute/          Mã nguồn chính
├── tests/                   Kiểm thử tự động
└── artifacts/               Index, log và kết quả thực nghiệm
```

## Bước 1 - Chuẩn bị corpus

1. Đặt các PDF chính thức vào `data/raw/`.
2. Điền một dòng cho mỗi tài liệu trong `data/manifests/corpus_manifest.csv`.
3. Chạy kiểm tra:

```powershell
python scripts/audit_corpus.py `
  --manifest data/manifests/corpus_manifest.csv `
  --project-root .
```

Kết quả hợp lệ phải xác nhận được file tồn tại, định dạng PDF, không trùng `document_id`, không trùng SHA-256 và đủ metadata bắt buộc.

## Trạng thái hiện tại

Khung dự án và bộ kiểm tra manifest đã được tạo. Chưa thực hiện chunking, embedding hoặc gọi LLM cho đến khi corpus đầu tiên được kiểm tra và đóng snapshot.

Kiểm tra nhanh mã nguồn hiện tại bằng lệnh:

```powershell
python tests/run_smoke_tests.py
```

