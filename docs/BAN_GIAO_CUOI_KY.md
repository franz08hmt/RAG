# Bàn giao cuối kỳ IT Project

Báo cáo chính là [Tìm hiểu Retrieval Augmented Generation (RAG)](../reports/22110068_RAG_Bao_Cao_Cuoi_Ky_v1.docx). Báo cáo trình bày cơ chế từng công đoạn và thực nghiệm trên tài liệu học vụ HCMUTE. Phiên bản DEMO và các mốc là tài liệu quá trình.

Mã và số liệu dùng trong bản Word nằm trên nhánh cục bộ `tim-hieu-rag-dot2` của [franz08hmt/RAG](https://github.com/franz08hmt/RAG). Commit minh chứng là `01e2025ff000bdbaa47cfaff8e3b63c37cdee11e`. [Manifest kết quả](evidence/final/manifest.json) giữ mã băm của 11 tệp số liệu. Commit mới hiện có trong repo cục bộ.

## Chạy console

Mở PowerShell tại thư mục dự án. Python 3.11 dùng env `rag-hcmute`. Bản cài hiện tại đã có snapshot G0 với 156 đoạn và Ollama phục vụ `qwen3:4b` cục bộ.

~~~powershell
Set-Location -LiteralPath 'D:\RAG\rag-hcmute-dot2'
$ragPython = 'C:\Users\Dell\anaconda3\envs\rag-hcmute\python.exe'
& $ragPython -m rag_hcmute.console_app --method bm25 --query 'Thủ tục xin nghỉ học tạm thời được quy định ra sao?'
& $ragPython -m rag_hcmute.console_app --method bm25 --answer --prompt-variant scope_schema --context-window 8192
~~~

Lệnh đầu chỉ truy xuất. Lệnh sau mở chế độ hỏi đáp có sinh câu trả lời. Gõ `:q` để thoát. Kiểm model bằng `ollama list`. Khi đổi máy, dùng đúng đường dẫn Python 3.11 và các PDF khớp [manifest](../data/manifests/corpus_manifest.csv). [README](../README.md) mô tả cài môi trường, kiểm SHA-256 và dựng lại corpus. Runner cuối kỳ dùng corpus gốc ở `data/processed/g0_reproduction`. Cách dựng lại bản lịch sử nằm ở đoạn tiếp theo. Kiểm lại ID G0 `5da3bd4d5de54492` trước khi đọc kết quả.

| Tình huống | Câu hỏi và điều cần chỉ ra |
|---|---|
| Quy trình | Thủ tục xin nghỉ học tạm thời. Lượt thực tế dẫn Điều 17, PDF trang 23–24. Mở trang 24 để kiểm hai thời hạn. |
| Đoạn đúng nằm sau hạng 1 | Kỳ hè kéo dài bao lâu. Lượt thực tế dẫn S3, Điều 8, PDF trang 9. Kiểm 5 tuần học và ít nhất 1 tuần đánh giá. |
| Đọc bảng | So hai dòng cử nhân chính quy và vừa làm vừa học về thời gian thiết kế và tín chỉ. Mở Bảng 1 PDF trang 3 để kiểm tên nhóm và số. |
| Câu khó | Học phần A đã học nhưng chưa đạt. So điều kiện của môn B khi A là học trước và khi A là tiên quyết. So Điều 3 với kết quả model và xác định ý bị bỏ. |
| Thiếu căn cứ | Hỏi giờ mở cửa thư viện công cộng ở Cần Thơ. Console BM25 đã ghi nhận `model_abstained` ở lượt lưu. Những câu ngoài phạm vi khác có thể trả sai. |

Lệnh trong [hướng dẫn Mốc 2](MOC2_HUONG_DAN.md) dùng để trình bày Hybrid RRF và reranker. Cấu hình này dùng cửa sổ reranker khác với Weighted75 trong phép thử cuối kỳ.

## Dựng lại G0 từ PDF

Phép tái lập dùng mã trích xuất ở commit 47b3665 và PyMuPDF 1.28.2. Bản build hiện tại thêm metadata OCR nên sinh ID 364ba3c398de1ffb dù 156 đoạn có cùng nội dung. Để tái lập chính xác ID và mã băm lịch sử, lấy ba PDF đúng hash từ manifest, đặt sẵn trong data/raw rồi dùng đoạn lệnh dưới. Chỉ chép vào g0_reproduction khi thư mục đích chưa có.

~~~powershell
$ragPython = 'C:\Users\Dell\anaconda3\envs\rag-hcmute\python.exe'
$scratchRoot = Join-Path 'artifacts/results' ('g0_archive_' + (Get-Date -Format 'yyyyMMdd_HHmmss'))
New-Item -ItemType Directory -Path $scratchRoot | Out-Null
git archive --format=zip --output="$scratchRoot/source.zip" 47b3665 -- scripts/build_corpus.py src data/manifests
if ($LASTEXITCODE) { throw 'git archive không thành công.' }
Expand-Archive -LiteralPath "$scratchRoot/source.zip" -DestinationPath "$scratchRoot/source"
$scratch = (Resolve-Path "$scratchRoot/source").Path
New-Item -ItemType Directory -Path "$scratch/data/raw" | Out-Null
foreach ($record in Import-Csv data/manifests/corpus_manifest.csv) {
    if ((Get-FileHash -LiteralPath $record.local_path -Algorithm SHA256).Hash -ne $record.file_sha256) {
        throw "Sai SHA-256 của $($record.document_id)"
    }
    Copy-Item -LiteralPath $record.local_path -Destination "$scratch/data/raw/"
}
Push-Location $scratch
try {
    & $ragPython -c 'import sys,runpy; print(sys.executable,flush=True); sys.argv[0]="scripts/build_corpus.py"; runpy.run_path(sys.argv[0],run_name="__main__")' --snapshot-manifest data/processed/snapshot.json --build-log data/processed/build.log
    if ($LASTEXITCODE) { throw 'Dựng corpus không thành công.' }
} finally { Pop-Location }
$chunkHash = (Get-FileHash -LiteralPath "$scratch/data/processed/chunks/chunks.jsonl" -Algorithm SHA256).Hash
if ($chunkHash -ne '7D71D353220A63E2E8058242FB671FE5B41B98D78F07A0330482BDEBBC73E54E') {
    throw 'File đoạn khác bản G0 lịch sử.'
}
if (-not (Test-Path -LiteralPath 'data/processed/g0_reproduction')) {
    Copy-Item -LiteralPath "$scratch/data/processed" -Destination 'data/processed/g0_reproduction' -Recurse
}
~~~

Lượt kiểm lại dựng đúng G0, 182 trang và 156 đoạn. SHA-256 của tệp đoạn trùng bản lịch sử theo từng byte. Console BM25 chạy từ tệp vừa dựng trả Điều 17 ở hạng 1.
## Đối chiếu và chạy lại số liệu

Các mô hình chạy trên máy cá nhân. Tệp để chạy lại nằm ngoài Git ở `D:\RAG\private_eval\final_20261115`. Dùng một thư mục kết quả mới mỗi lần chạy.

~~~powershell
$ragPython = 'C:\Users\Dell\anaconda3\envs\rag-hcmute\python.exe'
$inputs = 'D:\RAG\private_eval\final_20261115'
$output = Join-Path $inputs ('replay_' + (Get-Date -Format 'yyyyMMdd_HHmmss'))
New-Item -ItemType Directory -Path $output | Out-Null

& $ragPython scripts/run_final_extended_eval.py --cases "$inputs/cases.tsv" --private-dir "$output/extended" --metrics "$output/extended_a.json"
& $ragPython scripts/run_final_scope_schema.py --before "$output/extended_a.json" --private-before "$output/extended" --private-out "$output/schema4096" --metrics "$output/scope_schema.json" --context-window 4096
& $ragPython scripts/run_final_scope_schema.py --before "$output/extended_a.json" --private-before "$output/extended" --private-out "$output/schema8192" --metrics "$output/scope_8192.json" --context-window 8192
& $ragPython scripts/audit_final_vector_filter.py --metrics "$output/vector_filter.json"
& $ragPython scripts/audit_final_pdf_tables.py --reference "$inputs/table_reference.json" --metrics "$output/pdf_tables.json"
~~~

Kết quả gốc dùng mặc định Ollama 4.096 token cho hai lượt đầu và đặt rõ 8.192 cho lượt cuối. Xác nhận context hoạt động bằng `ollama ps` khi tái lập. Chấm lại nội dung trên đầu ra của lần tái lập vì nhãn cũ gắn với lần chạy cũ. Khởi động model hoặc đổi phần cứng có thể làm thay đổi thời gian.

- [Truy xuất và chunking](evidence/final/extended_a.json) dùng 43 câu và 57 khoảng bằng chứng. Trong 15 câu thiếu căn cứ, 6 câu tham gia đánh giá đầu-cuối.
- [Kết quả chấm thử đầu-cuối](evidence/final/review_summary.json) tập hợp 72 lượt và đối chiếu nội dung do trợ lý AI thực hiện. Câu F39 thiếu thang điểm trong đề nên chỉ tính trạng thái vận hành.
- [Thử lọc vector](evidence/final/vector_filter.json) đối chiếu cùng vector G0. [Kiểm tra cấu trúc bảng](evidence/final/pdf_tables.json) dùng 12 hàng được đối chiếu qua ảnh PDF.
- [Bộ câu hỏi bảo vệ](CAU_HOI_BAO_VE_RAG.md) gồm 34 câu từ bài toán đến đánh giá và giới hạn.

## Đánh giá cần người học xác nhận

Gói `D:\RAG\private_eval\final_20261115\question_review\START_HERE.html` có 85 mục chờ đối chiếu. Bộ đủ tiêu chí cần câu hỏi mới do sinh viên tự viết, đáp án và nguồn thực sự được duyệt, cùng một tập giữ lại theo nhóm bằng chứng. Câu pilot và các câu F/U của lượt này đã dành cho phát triển hoặc kiểm tra mở rộng. Khi tạo test mới, loại các câu tương đương và nhóm bằng chứng đã dùng để chỉnh tham số. Giao thức và validator nằm trong [hướng dẫn duyệt](evaluation/MOC3_GIAO_THUC_DUYET.md).

Phiếu chấm thử và từng đầu ra nằm dưới `private_eval\final_20261115`. Bản chép từ ảnh trang OCR còn ở gói Mốc 3. Kết quả OCR định lượng trong báo cáo là trên bốn trang có tham chiếu của thí nghiệm trước. Mười trang bổ sung dùng để kiểm lượng chữ phục hồi và trường hợp bảng/hình.
