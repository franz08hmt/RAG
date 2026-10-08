# Kiểm tra PDF scan QĐ 3116/2025 và nhánh OCR có kiểm soát

Ngày kiểm tra: 08/10/2026. Phép thử này kiểm tra một lỗi đầu vào đã lộ ra khi đối chiếu quy chế học vụ mới hơn; không thay snapshot G0 và không dùng kết quả OCR làm gold evidence.

## Nguồn và phạm vi

Trang Phòng Đào tạo HCMUTE đăng Quyết định 3116/QĐ-ĐHSPKT ngày 22/08/2025, ghi áp dụng từ khóa tuyển sinh 2021; Điều 3 nêu hiệu lực từ ngày ký và thay thế Quyết định 3811/QĐ-ĐHSPKT ngày 31/12/2024. Danh mục văn bản của Phòng Đào tạo cho biết QĐ 3811 thay QĐ 1727. Vì phạm vi khóa tuyển sinh có thể khác nhau, tài liệu này không kết luận QĐ 3116 áp dụng cho mọi khóa hoặc mọi câu hỏi lịch sử. [Trang Quyết định 3116](https://aao.hcmute.edu.vn/?ArticleId=fb49599f-d6e6-402e-806f-94cbc153e9e1), [danh mục quy chế đào tạo](https://aao.hcmute.edu.vn/?ArticleId=77a6cdba-af53-461b-866d-d7a9c643f878).

Toàn văn PDF được liên kết từ trang Phòng Đào tạo, lưu ngoài repository tại `D:\RAG\nguon_bo_sung\3116_QD_Dao_Tao_2025.pdf`. Tệp có 32 trang A4; SHA-256 `604ca10460ab92f3b329e3cc3572cff6c148fad4a40b243ff50e095eee34d8a9`. Không commit tệp PDF, text trang hoặc chunk của nguồn này.

## Vấn đề được phát hiện

Trang bìa và các trang nội dung là ảnh raster lớn, đồng thời PDF có một lớp text OCR sẵn nhưng nhiễu. Bộ trích xuất native trước đây lấy lớp chữ này như văn bản thông thường: snapshot riêng native-only tạo 42 chunk nhưng không gắn cờ trang nghi scan nào và không chạy OCR (32 trang; probable-scan=0; OCR=0). Chỉ kiểm tra `len(native_text)` vì vậy không đủ để phát hiện mọi PDF scan.

Đã bổ sung kiểm tra ảnh phủ ít nhất 70% diện tích trang. Một trang như vậy được gắn cờ cần xem xét dù đã có text layer. OCR toàn trang chỉ chạy khi người vận hành bật rõ cả `--ocr` và `--ocr-full-page-images`; mặc định dựng G0 vẫn không đổi. CLI từ chối `--ocr-full-page-images` nếu không bật `--ocr`.

## Kết quả nhánh OCR thử nghiệm

Chạy Tesseract 5.5.3, tiếng Việt (`vie`), 200 DPI, PSM 6 trên bản PDF ngoài repo, trong thư mục snapshot riêng:

| Cấu hình | Trang PDF | Chunk | Trang bị gắn cờ scan | Trang OCR | Dấu Điều nhận diện |
|---|---:|---:|---:|---:|---:|
| Native-only, trước khi sửa | 32 | 42 | 0 | 0 | chưa dùng làm kết luận |
| OCR toàn trang, opt-in | 32 | 52 | 32 | 32 | 28 |

Snapshot thử nghiệm có ID `444e283ee11b64e6`; kết quả nằm trong Git-ignored `data/processed/moc1_3116_source_audit/ocr_full_page/`. OCR đã phục hồi được phần văn bản cấu trúc ở nhiều trang, nhưng chưa có bản chép vàng đầy đủ để tính CER/WER trên cả 32 trang. Confidence của Tesseract (trung bình khoảng 92,6 trong lượt thử) chỉ phản ánh độ tự tin nội bộ, không phải độ chính xác; số hiệu viết tay trên bìa không được nhận diện tin cậy và một ngày tháng ở trang thay thế bị lẫn ký tự. Các trường pháp lý quan trọng phải được đối chiếu trực tiếp với PDF.

Phép thử không thêm QĐ 3116 vào snapshot G0, không sửa câu hỏi/gold evidence và không đưa nội dung OCR vào index thực nghiệm chính. Mục đích là xác định lỗi parser, bổ sung nhánh tùy chọn và ghi rõ điều kiện cần có trước khi dùng tài liệu scan để trả lời.

## Kiểm thử và cách tái lập

- Thêm unit test tạo PDF có ảnh phủ toàn trang và một lớp text OCR; test xác nhận trang được gắn cờ nhưng không OCR mặc định, và chỉ OCR khi bật opt-in.
- `tests/test_extract.py`: 10/10 passed sau khi thêm test.
- Toàn repo sau các cập nhật Mốc 1: 104/104 passed (`pytest -q -p no:cacheprovider --basetemp=...`).
- Chạy lại với manifest riêng (không dùng manifest công khai hay ghi đè G0):

```powershell
python scripts/build_corpus.py `
  --manifest data/processed/moc1_3116_source_audit/corpus_manifest.csv `
  --pages-output-dir data/processed/moc1_3116_source_audit/ocr_full_page/pages `
  --chunks-output-dir data/processed/moc1_3116_source_audit/ocr_full_page/chunks `
  --snapshot-manifest data/processed/moc1_3116_source_audit/ocr_full_page/snapshot.json `
  --build-log data/processed/moc1_3116_source_audit/ocr_full_page/build.log `
  --ocr --ocr-full-page-images --ocr-language vie --ocr-dpi 200 `
  --tessdata-dir <thu-muc-tessdata> --tesseract-cmd <duong-dan-tesseract.exe>
```

Kết luận cho YC4: đã tìm được và sửa một lỗi cụ thể trong phát hiện scan; đã kiểm tra được nhánh OCR trên một PDF học vụ thật. Chưa chứng minh chất lượng OCR tổng quát, chưa xử lý tự động mọi layout/bảng/hình và chưa đủ căn cứ dùng QĐ 3116 làm corpus trả lời. Đây là kết quả khảo sát có giới hạn, không phải bộ đọc PDF hoàn chỉnh.
