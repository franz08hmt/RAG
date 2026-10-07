# Độ nhạy OCR theo độ phân giải — 07/10/2026

## Mục tiêu

Kiểm tra liệu tăng DPI từ 200 lên 300 có cải thiện OCR tiếng Việt trên các mẫu đã có reference hay không, đồng thời giữ cố định Tesseract, traineddata và PSM. Đây là phép thử độ nhạy cục bộ, không phải benchmark OCR tổng quát và không thay đổi cấu hình mặc định.

## Thiết kế và khả năng tái lập

- PDF: `HCMUTE_SOTAYSV_2024.pdf`, SHA-256 `99940caca9799b5de43b9e6386304261a80f42b11fbd76acc13904786d738e47` (khớp manifest).
- Tesseract 5.5.3, ngôn ngữ `vie`, traineddata SHA-256 `b6b49293d95d0b6dbd8780174627e82c75be957b6f4ed9862155540d6b00bb45`.
- Bốn trang có reference cục bộ: PDF pages 107, 109, 116, 136. Thử hai mức DPI (200, 300) và hai PSM (4, 11), tổng cộng 16 lượt.
- Cùng hàm CER/WER và cách chuẩn hóa như các lượt OCR trước; giữ dấu tiếng Việt. Không lưu ảnh, reference text hay OCR hypothesis vào output.
- Script tái lập: [`run_ocr_dpi_sensitivity.py`](../../scripts/run_ocr_dpi_sensitivity.py). Kết quả JSON chỉ gồm cấu hình, hash, confidence và metric, nằm trong Git-ignored `artifacts/results/ocr_dpi_sensitivity/ocr_dpi_sensitivity_20261007T074033Z.json`.
- Revision chạy thí nghiệm: `409d168ee42cbebbc650fb8630d475b09b5fd770`; SHA-256 của script: `88174ef756f04fa70ece57741e68c0f3e9e01b8c277bc05ffba453d3f5be9b45`.

Chạy bằng Python 3.11 của env dự án:

```powershell
$py = 'C:\Users\Dell\anaconda3\envs\rag-hcmute\python.exe'
& $py scripts/run_ocr_dpi_sensitivity.py `
  --tessdata-dir 'D:\RAG\models\tesseract\tessdata' `
  --tesseract-cmd 'C:\Users\Dell\anaconda3\envs\rag-hcmute\Library\bin\tesseract.exe'
```

## Kết quả theo trang

Các ô ghi CER / WER theo phần trăm.

| PDF page | Nhãn layout dùng trong phân tích | PSM | DPI 200 | DPI 300 |
|---:|---|---:|---:|---:|
| 107 | Infographic/nội dung thị giác hỗn hợp, nhãn làm việc độ tin cậy vừa phải | 4 | 11,14 / 23,33 | 12,15 / 27,78 |
| 107 | Như trên | 11 | 9,87 / 16,67 | 12,41 / 25,56 |
| 109 | Văn bản kèm minh họa | 4 | 10,06 / 12,67 | 11,86 / 18,00 |
| 109 | Như trên | 11 | 17,57 / 29,33 | 24,02 / 40,00 |
| 116 | Nhiều khối chữ và danh sách | 4 | 23,36 / 27,41 | 30,22 / 38,52 |
| 116 | Như trên | 11 | 36,08 / 35,93 | 53,97 / 59,63 |
| 136 | Sơ đồ | 4 | 77,91 / 90,70 | 77,30 / 89,53 |
| 136 | Như trên | 11 | 73,62 / 80,23 | 80,37 / 86,05 |

## Kết quả gộp có trọng số

| DPI | PSM | CER | WER | Lỗi ký tự / reference | Lỗi từ / reference |
|---:|---:|---:|---:|---:|---:|
| 200 | 4 | 24,89% | 32,21% | 668 / 2.684 | 192 / 596 |
| 200 | 11 | 32,19% | 37,75% | 864 / 2.684 | 225 / 596 |
| 300 | 4 | 28,73% | 39,09% | 771 / 2.684 | 233 / 596 |
| 300 | 11 | 43,63% | 53,36% | 1.171 / 2.684 | 318 / 596 |

## Phép đo bổ sung: nhận dạng token số và dấu hiệu điều kiện

CER/WER gộp có thể che khuất lỗi ở các phần tử mà chỉ sai một ký tự cũng có thể đổi nghĩa, chẳng hạn mã số, mốc thời gian, tỷ lệ hoặc dấu hiệu phủ định/điều kiện. Vì vậy, cùng 16 output OCR được đo thêm bằng exact occurrence precision/recall sau chuẩn hóa NFC và không phân biệt hoa thường. Token số được tính nếu token có ít nhất một chữ số; nhóm dấu hiệu điều kiện/phủ định dùng một danh sách cố định trong mã. Kết quả chỉ lưu tổng số lần xuất hiện và số lần khớp, không lưu từ, token, giá trị hay đoạn văn được trích ra.

| DPI | PSM | Token số khớp / reference | Precision | Recall | Cue khớp / reference |
|---:|---:|---:|---:|---:|---:|
| 200 | 4 | 10 / 32 | 71,43% | 31,25% | 4 / 4 |
| 200 | 11 | 15 / 32 | 62,50% | 46,88% | 4 / 4 |
| 300 | 4 | 13 / 32 | 72,22% | 40,63% | 4 / 4 |
| 300 | 11 | 15 / 32 | 60,00% | 46,88% | 4 / 4 |

> **Giới hạn diễn giải:** 32 token số và 4 cue là tổng của đúng bốn trang mẫu, không phải tập kiểm thử đại diện. Mức cue 4/4 không chứng minh OCR xử lý tốt phủ định/điều kiện nói chung; recall token số 31,25–46,88% cho thấy không nên dùng bản OCR này làm căn cứ duy nhất để trả lời các câu hỏi có mã, số liệu hoặc điều kiện. Các trường hợp trọng yếu vẫn cần đối chiếu trực tiếp với trang nguồn.

## Diễn giải

- Trên mẫu này, tăng lên 300 DPI không cải thiện kết quả tổng: với PSM 4, CER/WER tăng 3,84/6,88 điểm phần trăm; với PSM 11 tăng 11,44/15,61 điểm phần trăm.
- Ở ba trang 107, 109 và 116, cả hai PSM đều có CER/WER cao hơn tại 300 DPI. Trên page 136, PSM 4 giảm nhẹ CER từ 77,91% xuống 77,30% và WER từ 90,70% xuống 89,53%, nhưng mức lỗi vẫn quá cao để coi OCR là bản chép đáng tin; PSM 11 còn xấu hơn ở 300 DPI.
- Kết quả không chứng minh 200 DPI luôn tốt hơn. Mẫu chỉ có bốn trang; page 116 chiếm tỷ trọng lớn trong số ký tự tham chiếu, còn page 107 là nhãn layout có độ tin cậy vừa phải. Kết quả gộp vì vậy chỉ mô tả đúng mẫu này.
- Không có cơ sở để đổi PSM mặc định 6: PSM 6 không nằm trong phép so sánh độ phân giải lần này. Giữ nguyên cấu hình pipeline; có thể dùng 200 DPI làm điểm xuất phát cho lần kiểm chứng mở rộng, không gọi đây là tham số tối ưu tổng quát.
- Confidence OCR không được dùng thay cho CER/WER hoặc việc đối chiếu nội dung trọng yếu.

## Trạng thái và giới hạn

Thí nghiệm chạy hoàn toàn cục bộ, không gọi Gemini hay API khác. PDF/reference không thay đổi; JSON chỉ lưu metric/cấu hình và bị Git ignore. Chưa đánh giá chunking, retrieval, citation hoặc câu trả lời RAG. Các số liệu chỉ hỗ trợ tìm hiểu YC4; chưa khép kín YC4/YC13 và chưa cập nhật DOCX Mốc 1.
