# Hướng dẫn tự học và chạy thử PoC

Các tài liệu học tập được chia theo đúng luồng giải thích: kiến trúc RAG → dữ liệu/Document/Chunk → chunking và retrieval → generation/evaluation. Đọc phần giải thích rồi tự chạy lệnh tương ứng; khi báo cáo, nên mở mã nguồn và một file evidence để chứng minh nhận định.

- Nội dung lý thuyết: `../tim_hieu/`.
- Truy vết YC1–YC13: `../TRUY_VET_YC.md`.
- Bộ câu hỏi tự kiểm tra: `../../CAU_HOI_BAO_VE.md`.
- Quy tắc question/gold/eval data: `../../data/eval/README.md`.

## Lệnh cơ bản trên Windows

```powershell
$py = 'C:\Users\Dell\anaconda3\envs\rag-hcmute\python.exe'
& $py -c 'import sys; print(sys.executable)'
& $py -m rag_hcmute.console_app --help
& $py -m rag_hcmute.console_app --query "Điều kiện để được công nhận tốt nghiệp là gì?" --method bm25
```

Dense/Hybrid/rerank cần model snapshot đã tải local. Chỉ rõ đường dẫn local bằng CLI; không bỏ chế độ offline hoặc để model tự tải. Generation local cần Ollama và `qwen3:4b` cài sẵn. Trước khi nhập câu hỏi, phải kiểm tra tài liệu đang dùng là snapshot G0 lịch sử; không dùng kết quả như lời khuyên cho quy định hiện hành.

## Thực hành đọc kết quả

Khi một answerable query không tìm đủ evidence, kiểm tra lần lượt: nguồn/manifest → text theo trang → chunk boundary → danh sách top-k và thứ hạng → điểm truncation → rerank → prompt/context. Không bắt đầu bằng cách yêu cầu LLM viết lại câu trả lời; đó là tầng cuối, không sửa được evidence bị mất ở các tầng trước.
