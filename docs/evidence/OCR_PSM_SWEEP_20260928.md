# Khảo sát PSM cho OCR tiếng Việt trên ba trang mẫu

## Mục tiêu và phạm vi

Khảo sát độ nhạy của OCR theo Page Segmentation Mode (PSM), giữ nguyên các yếu tố khác. Mẫu gồm hai trang scan văn bản (PDF page 107, 109) và một trang có sơ đồ (PDF page 136) trong Sổ tay Sinh viên 2024. Ba trang đều có reference chép thủ công ở local artifacts; reference chưa được đưa vào Git. Đây là pilot nhỏ, không đại diện cho toàn bộ corpus.

## Cấu hình và cách tính

- Nguồn: `HCMUTE_SOTAYSV_2024.pdf`, SHA-256 `99940caca9799b5de43b9e6386304261a80f42b11fbd76acc13904786d738e47` (khớp manifest).
- Tesseract 5.5.3, pytesseract 0.3.13, model `vie` trong `tessdata_best` (SHA-256 được ghi tại `docs/G1_KHAO_SAT_DU_LIEU_DAU_VAO.md`).
- Cố định DPI = 200; thử PSM 3, 4, 6, 11, 13 trên cùng ba trang bằng `scripts/evaluate_ocr_sample.py`.
- CER giữ dấu câu và khoảng trắng sau chuẩn hóa Unicode NFC/case-fold; WER dùng dấu câu/ký hiệu làm ranh giới token. Số gộp là tổng edit distance chia tổng ký tự/từ reference, không phải trung bình đều của ba tỷ lệ trang.
- Chỉ lưu số liệu metric trong tài liệu này; không lưu hypothesis OCR hay chép lại nội dung Sổ tay.

## Kết quả

| PSM | Page 107 CER/WER | Page 109 CER/WER | Page 136 CER/WER | CER/WER gộp có trọng số |
|---:|---:|---:|---:|---:|
| 3 | 0,1114 / 0,2333 | 0,0916 / 0,1133 | 0,7945 / 0,9186 | **0,2624 / 0,3589** |
| 4 | 0,1114 / 0,2333 | 0,1006 / 0,1267 | 0,7791 / 0,9070 | 0,2632 / 0,3620 |
| 6 | 0,1949 / 0,3222 | 0,2297 / 0,2400 | 0,7883 / 0,8721 | 0,3511 / 0,4294 |
| 11 | **0,0987 / 0,1667** | 0,1757 / 0,2933 | **0,7362 / 0,8023** | 0,2855 / 0,3926 |
| 13 | 1,0000 / 1,0000 | 0,9970 / 1,0000 | 1,0000 / 1,0000 | 0,9986 / 1,0000 |

Trên hai trang văn bản, PSM 3 đạt CER/WER tốt nhất ở page 109 và gần page 107; trên page 136 có sơ đồ, PSM 11 tốt nhất nhưng vẫn còn CER 73,62% và WER 80,23%, quá cao để dùng kết quả OCR làm văn bản đáng tin cậy. PSM 13 gần như không nhận dạng được nội dung ở cả ba trang. PSM 3 và 4 gần như ngang nhau về metric gộp; chênh lệch này không đủ căn cứ để khẳng định một chế độ tốt hơn trên dữ liệu tổng quát.

## Diễn giải và quyết định tạm thời

PSM 3 có metric gộp thấp nhất ở mẫu này, nhưng kết quả tổng bị chi phối bởi hai trang văn bản dài hơn; riêng trang sơ đồ lại phù hợp hơn với PSM 11. Vì chỉ có ba trang và một trang sơ đồ, **giữ PSM 6 làm mặc định hiện tại**, không chọn PSM theo kết quả của mẫu nhỏ. Có thể đưa PSM 3 vào lượt kiểm chứng kế tiếp trên tập trang scan văn bản lớn hơn; sơ đồ cần một nhánh xử lý layout/ảnh riêng thay vì dựa vào OCR thuần.

Đây là đánh giá độ giống ký tự/từ trên reference thủ công, không phải đánh giá chất lượng retrieval hay câu trả lời RAG. CER/WER thấp hơn cũng chưa bảo đảm các con số/điều kiện quan trọng được nhận dạng chính xác; nội dung dùng làm bằng chứng vẫn cần kiểm tra ngược trang nguồn.

## Tái lập

Trong PowerShell, lần lượt chạy từng reference với cùng DPI và các PSM trên:

```powershell
$py = 'C:\Users\Dell\anaconda3\envs\rag-hcmute\python.exe'
$pages = @(107, 109, 136)
$psms = @(3, 4, 6, 11, 13)
foreach ($page in $pages) {
  $reference = "artifacts/results/g1_ocr_reference_page$page.json"
  foreach ($psm in $psms) {
    & $py scripts/evaluate_ocr_sample.py `
      --pdf data/raw/HCMUTE_SOTAYSV_2024.pdf `
      --page $page --reference $reference `
      --tessdata-dir 'D:\RAG\models\tesseract\tessdata' `
      --dpi 200 --psm $psm
  }
}
```

`evaluate_ocr_sample.py` in lần chạy này tự in `sys.executable`. Reference nằm trong `artifacts/results/` và bị Git ignore; không đưa văn bản reference lên repo.
