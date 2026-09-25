# Ghi chú chỉnh sửa báo cáo — bản v2

Áp dụng cho `reports/22110068_RAG_Bao_Cao_Tien_Do_Dot_1_v2.docx` (file mới, không ghi đè
`reports/22110068_RAG_Bao_Cao_Tien_Do_Dot_1.docx` — bản v1 vẫn giữ nguyên trong repo để đối chiếu).

## 0. Xác minh tệp/commit trước khi sửa

- Tên file thật trong repo chỉ có một dạng: `22110068_RAG_Bao_Cao_Tien_Do_Dot_1.docx` (có gạch dưới
  trước số 1). Không có file `Dot1.docx` (không gạch dưới) nào từng tồn tại trong lịch sử git.
- Đối chiếu số bảng/hình bằng cách đếm trực tiếp thẻ XML (`<w:tbl>`, `<a:blip>`), không suy đoán:
  - Commit `4b3b7d7` (trước khi gộp Phần A): **4 bảng, 3 hình** — khớp đúng với lần kiểm tra trên máy
    người yêu cầu, nên khả năng cao máy đó đang xem bản trước khi commit `4f0031a` được đồng bộ.
  - Commit `4f0031a` (bản v1 đã gộp Phần A + Phần B): **7 bảng, 7 hình** — trước đó tôi báo nhầm là
    "6/6" vì quên đếm bảng thông tin và logo ở trang bìa.
  - Bản v2 (file này áp dụng): vẫn 7 bảng nội dung + hình, nhưng đã sửa toàn bộ bảng tràn trang và vẽ
    lại toàn bộ hình cho đọc được ở kích thước in.

## 1. Định nghĩa Search / IR / RAG và trích dẫn Lewis

- Sửa ở **2 vị trí** (không chỉ một): Phần A.3 (bảng so sánh) và Phần B Mục 2 (đoạn phân biệt 3 khái
  niệm) — cả hai trước đó đều định nghĩa IR là "đánh giá mức độ liên quan **ngữ nghĩa**" rồi lại gọi
  BM25 (từ vựng) là IR, mâu thuẫn với chính định nghĩa vừa nêu.
- Định nghĩa mới: IR là tập hợp phương pháp chọn/xếp hạng đoạn văn bản liên quan, gồm cả phương pháp
  từ vựng (BM25) lẫn ngữ nghĩa (dense) — theo cách trình bày chuẩn trong giáo trình IR (Manning,
  Raghavan & Schütze, Stanford, chương Probabilistic Information Retrieval, nơi giới thiệu BM25).
- Sửa trích dẫn Lewis và cộng sự (2020): không còn quy cho công trình gốc ý "chỉ đưa ngữ cảnh lúc suy
  luận, không huấn luyện" — nêu rõ công trình gốc có fine-tune query encoder + generator (BART), và
  tách bạch với PoC của đồ án này (không huấn luyện lại/fine-tune bất kỳ mô hình nào).

## 2. Dòng repo/branch/PR/commit ở đầu nội dung

- Thêm ngay sau trang bìa (trước cả Phần A): tên repo, nhánh, link PR, và commit `4f0031a` (commit
  chứa toàn bộ script/log/snapshot được trích dẫn — bản DOCX v2 này được thêm vào ở một commit kế
  tiếp trên cùng nhánh/PR, xem lịch sử commit của PR để lấy đúng mã tại thời điểm đọc).

## 3. Bảng tràn trang

Tính lại theo đúng bề rộng khả dụng của trang nội dung (A4, lề trái 1417 / phải 1134 twips =
**9356 dxa**), xác nhận lại bằng cách đọc trực tiếp `w:tblW` trong XML của file v2 (không chỉ tính tay):

| Bảng | v1 (dxa) | v2 (dxa) | Thay đổi |
|---|---|---|---|
| Danh mục corpus (Mục 3.2) | 12000 (tràn 2644) | 9200 | Bỏ cột SHA-256 (chuyển ghi chú trỏ về manifest), rút gọn 2 cột còn lại |
| Search/IR/RAG (Phần A.3) | 10300 (tràn 944) | 9300 | Rút ngắn nội dung ô, giảm bề rộng cột |
| Kế hoạch giai đoạn (Phần A.6) | 10200 (tràn 844) | 9100 | Giảm bề rộng cột |
| BM25 vs Dense — cấu hình (Mục 5.2) | 9600 (tràn 244) | 9200 | Rút ngắn nội dung ô cấu hình |
| Câu hỏi pilot, per-question rank | đã hợp lệ | không đổi | — |
| Bảng thông tin bìa | đã hợp lệ | không đổi | — |

## 4. Vẽ lại hình

- Nguyên nhân gốc: hình được thiết kế ở độ phân giải 1500px nhưng in ra cố định ở bề rộng trang
  (~6,46 inch) → DPI hiệu dụng ~232, chữ trong hình chỉ còn ~5-7pt khi in, dù xem file ảnh gốc phóng to
  thì đọc được bình thường. Đã tăng toàn bộ cỡ chữ trong hình lên ~2 lần (font "px" tuyệt đối) để cỡ
  chữ khi in rơi vào khoảng 10-15pt, gần bằng thân bài.
- Hình BM25 (Hình 2, Mục 5.2) làm lại hoàn toàn: bỏ 3 kết quả xếp chồng + đoạn giới thiệu dài + chú
  thích dài lặp ý; thay bằng đúng 1 trường hợp cụ thể — P002 → chunk hạng #1 (gold) → trang/Điều →
  lý do được xem là đúng, có so sánh ngắn với hạng 2. Đổi tên gọi từ "chụp lại nguyên văn output" /
  ngụ ý ảnh chụp màn hình thành đúng bản chất: "sơ đồ hóa kết quả chạy thật" (dựng lại từ JSON gốc).
- 5 hình còn lại (Hình 1, Hình 3, Hình A1, A2, A3) giữ nguyên nội dung, vẽ lại với cỡ chữ mới; đã kiểm
  tra từng hình bằng mắt sau khi vẽ (không chỉ tin số liệu DPI tính tay) — phát hiện và sửa thêm 2 lỗi
  bố cục lộ ra khi phóng cỡ chữ (dòng tiêu đề rỗng lặp ở Hình 2, chú thích lệch/tràn mép ở Hình 3).
- Mỗi hình có đúng 1 chú thích ngắn, đặt thống nhất ngay dưới hình.

## 5. Trang bìa

- Logo phóng to từ 110×140 lên 150×191 (đúng tỉ lệ logo trong DEMO, ~1,57×2,01 inch).
- Tên trường rút gọn "TP. Hồ Chí Minh" thay vì "Thành phố Hồ Chí Minh" — khớp cách DEMO tự viết trên
  bìa, tránh xuống dòng giữa chừng ở cỡ 14pt in đậm (đã xác nhận không xuống dòng trong bản render).
- Bỏ phụ đề "ĐỢT 1 — 4 TUẦN ĐẦU (TRÊN TỔNG SỐ ~15 TUẦN HỌC KỲ)", thay bằng "Báo cáo tiến độ Đợt 1".
- Không đổi: khung chỉ ở bìa, Times New Roman, nền trắng, đen/trắng, không số trang — đã xác nhận lại
  bằng cách đọc XML (2 `sectPr`, `pgBorders` chỉ xuất hiện ở section 0; không có field PAGE; không có
  header/footer).

## 6. Giọng văn

- Viết lại Mục 1 (Tóm tắt) theo 3 phần: đã hoàn thành / kết quả kiểm tra ban đầu / việc còn dang dở —
  bỏ khung liệt kê kỹ thuật dày đặc, bỏ câu "không phải báo cáo cuối kỳ".
- Bỏ phần lớn chữ CHƯA/KHÔNG viết hoa giữa câu dùng để nhấn mạnh giới hạn (giữ nguyên các chỗ dùng
  KHÔNG/không để mô tả một quyết định kỹ thuật cụ thể, ví dụ "cố tình không ghép từ ngắt dòng" — đây là
  mô tả thiết kế, không phải biện hộ).
- Bỏ câu giải thích quy trình tạo tài liệu ("vì môi trường không có màn hình đồ họa...").
- **Chưa làm** (đúng như đã thống nhất): gom toàn bộ đường dẫn/log vào một mục "Minh chứng thực hiện"
  riêng — việc này cần tái cấu trúc gần như cả bài, để lại cho một đợt chỉnh sửa riêng nếu cần.

## 7. Tài liệu tham khảo

- Sửa mục [C] (Sổ tay Sinh viên 2024): trước đó hiển thị đường dẫn rút gọn có dấu "…" ở giữa khiến bản
  in không gõ lại được URL. Nay hiển thị tên nguồn ngắn dễ đọc + in kèm URL đầy đủ (không mã hóa %XX,
  giữ tiếng Việt có dấu) ngay trong văn bản để bản in vẫn tra cứu lại được.
- Các mục còn lại ([1]-[7], [A], [B], [D]) đã kiểm tra: không có dấu "…" nào khác, đường dẫn hiển thị
  khớp với đường dẫn thật hoặc là tên gọi rõ ràng (không gây hiểu lầm là URL rút gọn).
- Không có phát biểu khẳng định hiệu lực pháp lý nào chưa xác minh — trạng thái hiệu lực của
  `HCMUTE_QCDT_1727_2021` vẫn ghi "chưa xác định đầy đủ" như bản v1.

## Bảng đối chiếu số liệu/chứng cứ với commit thực tế

Tất cả các dòng dưới đây đã xác minh trực tiếp trong phiên làm việc này bằng cách đọc file JSON/log
thật hoặc chạy lại lệnh, **không suy đoán từ nội dung báo cáo cũ**.

| Số liệu / claim trong báo cáo | Nguồn xác minh | Kết quả xác minh |
|---|---|---|
| BM25 Recall@5 = 0,429 (3/7), MRR@10 = 0,371 | `docs/evidence/runs/bm25_5da3bd4d5de54492_20260924T112003Z.json` | Khớp đúng |
| Dense Recall@5 = 0,857 (6/7), MRR@10 = 0,643 | `docs/evidence/runs/dense_bge_m3_5da3bd4d5de54492_20260925T040111Z.json`, field `metrics` | Khớp đúng |
| Dense đã tải model thật (không giả lập) | field `config.embedding_dim = 1024` (chỉ có được khi model thật chạy forward pass) | Xác nhận |
| Dense đã xây FAISS index thật | field `config.faiss_index = "IndexFlatIP"`, mỗi `top_k[].score` nằm trong [-1,1] đúng phân bố cosine | Xác nhận |
| Dense đã chạy truy vấn thật (không phải số dựng) | field `latency_ms` mỗi câu ~117-135ms — khớp thời gian suy luận CPU thực tế cho BGE-M3, không phải số tròn/giả | Xác nhận |
| Thời điểm chạy Dense: 2026-09-25T04:01:11 UTC | field `created_at` trong cùng file JSON trên | Xác nhận — sau BM25 (24/09) và sau khi PR #1 mở (24/09), đúng là cập nhật trong Đợt 1, không phải viết lại lịch sử |
| 20 test pytest PASSED | chạy lại `pytest` trong phiên này | 20 passed |
| snapshot_id = 5da3bd4d5de54492, 182 trang, 156 chunk | `data/manifests/corpus_snapshot.json` | Khớp đúng |
| PR #1 tồn tại, chứa đúng commit `4f0031a` | `pull_request_read` (GitHub API) trong phiên này | head sha = `4f0031a7033b4f9f2355ce1591a35c2fa490d20d` |
| Repository công khai (không cần quyền riêng để xem) | `search_repositories` (GitHub API), field `visibility` | `"public"`, `"private": false` |
| 7 bảng trong v1, 0 bảng tràn trang trong v2 | đếm `<w:tbl>` và đọc `w:tblW` trực tiếp từ XML | v1: 4/7 bảng tràn; v2: 0/7 bảng tràn |

## Điểm chưa xác minh được / giới hạn còn lại

- **Chưa xem được bản in Word thật.** Sandbox này không chạy được LibreOffice/soffice (đã thử lại,
  vẫn lỗi "source file could not be loaded" — giới hạn tầng sandbox, không đổi so với trước). Đã dùng
  phương án thay thế: dựng PDF phân trang thật bằng Chromium (Playwright, có sẵn trong môi trường) từ
  bản HTML xuất ra qua pandoc, rồi xem từng trang — cách này xác nhận được bố cục, bảng, hình, ngắt
  dòng ở mức gần đúng, nhưng **engine layout của Chromium không giống hệt Word** (đặc biệt: ranh giới
  giữa trang bìa và trang nội dung — do 2 section riêng trong DOCX — không được pandoc giữ lại thành
  ngắt trang trong HTML, nên trong bản xem thử này đoạn "Ghi chú cấu trúc/Mã nguồn" bị dính vào cuối
  trang bìa; đã xác minh riêng bằng XML rằng DOCX thật có 2 section tách biệt và Word sẽ ngắt trang
  đúng chỗ). Khuyến nghị: người nhận vẫn nên tự mở bằng Word thật trước khi nộp để soát khoảng trắng/
  ngắt trang lần cuối.
- **Chưa push/commit bản v2 này lên nhánh tại thời điểm viết ghi chú này** — sẽ thực hiện ngay sau khi
  gửi các tài liệu bàn giao này, cùng một commit, không tạo PR mới, không đụng `main`.
- Các giới hạn về nội dung đã nêu trong báo cáo (hiệu lực `HCMUTE_QCDT_1727_2021` chưa xác định đầy
  đủ, P006 chưa có gold evidence, Dense không thắng tuyệt đối, mẫu đánh giá nhỏ) không đổi so với v1 —
  đây là giới hạn thật của Đợt 1, không phải điều cần "sửa".
