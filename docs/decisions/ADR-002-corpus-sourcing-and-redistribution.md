# ADR-002: Khảo sát corpus, chính sách tái phân phối dữ liệu và tài liệu bị loại

## Trạng thái

Đã áp dụng cho snapshot corpus đầu tiên (`5da3bd4d5de54492`).

## Bối cảnh

Môi trường thực thi phiên làm việc này chặn egress mạng theo whitelist tổ chức; ban đầu chỉ PyPI/npm/
GitHub được phép, `hcmute.edu.vn` (và mọi tên miền khác) bị proxy trả 403. Người dùng đã tự mở rộng
quyền mạng cho đúng tên miền `hcmute.edu.vn` (không bao gồm các subdomain như `fit.hcmute.edu.vn`,
`aao.hcmute.edu.vn`, và không bao gồm `huggingface.co`). Việc tải PDF gốc thực hiện qua đường dẫn
`hcmute.edu.vn/Resources/Docs/SubDomain/<don-vi>/...` (một pattern lưu trữ file dùng chung, hoạt động
được qua domain gốc dù URL công bố ban đầu dùng subdomain).

## Quyết định 1 - Tên trường

Đã xác minh qua nhiều nguồn độc lập (Cổng thông tin Chính phủ vanban.chinhphu.vn, ThuVienPhapLuat,
Báo Chính phủ, Người Lao Động): Quyết định số 2809/QĐ-TTg ngày 26/12/2025 của Thủ tướng Chính phủ đổi
tên "Trường Đại học Sư phạm Kỹ thuật Thành phố Hồ Chí Minh" thành **"Trường Đại học Công nghệ Kỹ thuật
Thành phố Hồ Chí Minh"**, hiệu lực từ ngày ký, giữ nguyên bản sắc/logo "HCMUTE". Báo cáo tiến độ dùng
tên MỚI này xuyên suốt phần nội dung do người viết soạn; các văn bản nguồn ban hành TRƯỚC 26/12/2025
vẫn giữ nguyên tên cơ quan ban hành như trên bản gốc khi trích dẫn (ghi chú rõ trong manifest).

## Quyết định 2 - Corpus được chọn (3 văn bản)

| document_id | Loại | Lý do chọn |
|---|---|---|
| `HCMUTE_QCDT_1727_2021` | Quyết định 1727/QĐ-ĐHSPKT (06/09/2021) | Văn bản gốc, có số hiệu, có Điều/Khoản rõ ràng, bao phủ hầu hết chủ đề pilot (xét tốt nghiệp, rút học phần, cảnh báo học tập, học lại, nghỉ học tạm thời, buộc thôi học) |
| `HCMUTE_FIT_TTTN_2022` | Hướng dẫn nội bộ Khoa CNTT | Tài liệu duy nhất tìm được bao phủ đúng chủ đề "thực tập tốt nghiệp" ở mức học phần |
| `HCMUTE_SOTAYSV_2024` | Sổ tay Sinh viên 2024 | Nguồn chính thức, mới nhất (11/2024), có nội dung kỷ luật/cảnh báo để đối chiếu chéo với văn bản quy chế |

## Quyết định 3 - Tài liệu đã khảo sát nhưng LOẠI khỏi corpus

Hai tài liệu sau được tải và kiểm tra nhưng **không đưa vào `corpus_manifest.csv`** (vẫn lưu cục bộ
tại `data/raw/_evaluated_not_used/`, không commit do đã gitignore `data/raw/`):

1. **"Hướng dẫn thực hiện qui chế đào tạo" (Số 125/QC-ĐHSPKT-ĐT, 22/12/2008)** - văn bản hướng dẫn
   thực hiện Quyết định 43/2007/QĐ-BGDĐT. Khung pháp lý quốc gia này đã bị thay thế bởi Thông tư
   08/2021/TT-BGDĐT (chính văn bản `HCMUTE_QCDT_1727_2021` cũng căn cứ trên Thông tư 08/2021). Vì vậy
   văn bản 2008 gần như chắc chắn đã hết hiệu lực áp dụng thực tế, dùng làm nguồn trả lời sẽ rủi ro
   đưa thông tin lỗi thời. Loại khỏi corpus thay vì đưa vào với nhãn "hết hiệu lực" để tránh rủi ro bị
   retrieval baseline vô tình lấy làm bằng chứng.
2. **"Thông báo Hội đồng bảo vệ Khóa luận tốt nghiệp HK1 2019-2020" (Khoa CNTT, 30/12/2019)** - đây là
   thông báo lịch/thủ tục cho MỘT học kỳ cụ thể đã qua từ lâu, không phải văn bản quy định thường trực;
   nội dung chính (deadline nộp báo cáo của HK1 2019-2020) không còn áp dụng. Link duy nhất trỏ tới quy
   định gốc về điều kiện làm khóa luận tốt nghiệp lại nằm ở `fit.hcmute.edu.vn/ArticleId/...` - một
   subdomain bị chặn trong phiên làm việc này, nên chưa thể xác minh nội dung gốc (xem ghi chú câu hỏi
   P006 trong `pilot_questions.csv`).

## Quyết định 4 - Không commit PDF gốc / full-text chunk lên repo public

Repo là public. Theo yêu cầu của đề bài, KHÔNG commit PDF gốc và KHÔNG tái tạo toàn văn tài liệu lên
GitHub khi quyền phát hành lại chưa được xác nhận rõ ràng (các văn bản này là văn bản hành chính công
khai trên website trường, nhưng chưa có tuyên bố giấy phép tái phân phối tường minh):

- `data/raw/*.pdf` (PDF gốc) - đã có trong `.gitignore`, không commit.
- `data/processed/pages/*.jsonl` và `data/processed/chunks/*.jsonl` (text đầy đủ theo trang/chunk) -
  đã có trong `.gitignore`, không commit; có thể tái tạo 100% bằng `python scripts/build_corpus.py`
  một khi có lại đúng các file PDF theo SHA-256 trong `corpus_manifest.csv`.
- Kết quả retrieval thô commit ở `docs/evidence/runs/*.json` CHỈ chứa `text_preview` (cắt ngắn ~220 ký
  tự, xem `rag_hcmute/retrieval/common.py::make_preview`), không phải toàn văn chunk.
- Ngoại lệ duy nhất: đoạn bằng chứng ngắn (1 đến vài câu) cho mỗi câu hỏi pilot trong
  `pilot_questions.csv` và trong `docs/evidence/case_studies.md`, tương tự cách trích dẫn học thuật
  thông thường, không phải tái tạo nguyên văn cả Điều/cả văn bản.

## Bổ sung sau khi rà soát bảo mật trước khi commit

Khi quét file trước khi push, phát hiện `HCMUTE_SOTAYSV_2024` (Sổ tay Sinh viên 2024) có một mục lục
tư vấn viên (trang ~137-146 PDF) chứa **họ tên, email cá nhân/công vụ và số điện thoại di động thật**
của nhiều giảng viên/sinh viên. Đây là một lý do BỔ SUNG (ngoài lý do bản quyền/tái phân phối ở trên)
khẳng định quyết định không commit `data/processed/pages/` và `data/processed/chunks/` (chứa toàn văn
trích xuất, bao gồm cả các trang này) lên GitHub public là đúng đắn. Đã quét toàn bộ file dự định
commit (`docs/evidence/runs/*.json`, `docs/evidence/case_studies.md`, `pilot_questions.csv`,
`corpus_manifest.csv`, `corpus_snapshot.json`, và cả `reports/*.docx`) bằng regex tìm email/số điện
thoại — không có rò rỉ (không câu hỏi pilot nào truy xuất trúng các chunk chứa mục lục này).

## Hệ quả

- Một máy khác muốn tái lập đầy đủ corpus phải tự tải lại 3 PDF theo `source_url` trong manifest, kiểm
  tra khớp SHA-256, rồi chạy `scripts/build_corpus.py` - không thể chạy retrieval ngay từ repo mà
  không có bước này, đây là đánh đổi có chủ đích giữa khả năng tái lập và an toàn bản quyền/tái phân
  phối.
- `HCMUTE_QCDT_1727_2021` có trạng thái hiệu lực ghi là `chua_xac_dinh_day_du` (không phải `hieu_luc`)
  vì phát hiện dấu hiệu có Quyết định 3116/QĐ-ĐHSPKT (22/08/2025) cùng tên nhưng chưa truy cập được
  toàn văn (thư viện số HCMUTE yêu cầu đăng nhập). Đây là việc cần làm ưu tiên ở mốc kế tiếp.
