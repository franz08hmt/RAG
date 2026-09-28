# Môi trường thực nghiệm

Cập nhật: 2026-09-28. Các trạng thái bên dưới phân biệt rõ môi trường đã xác minh và các bước còn chờ.

## Máy và công cụ đã kiểm tra

- Hệ điều hành: Windows 11 Pro (theo thông tin trong prompt bàn giao).
- GPU: NVIDIA GeForce RTX 3060 Laptop GPU, VRAM 6144 MiB; driver 610.60.
- RAM: khoảng 23 GB (theo thông tin đã cung cấp; phép đọc WMI trong sandbox bị từ chối nên chưa xác minh độc lập).
- Python hệ thống mặc định: 3.13.9; không dùng cho project vì project yêu cầu Python `>=3.11,<3.13` và môi trường base có cảnh báo OpenMP.
- Môi trường riêng: Conda `rag-hcmute`, Python 3.11.16 tại `C:\Users\Dell\anaconda3\envs\rag-hcmute\python.exe`.
- Dung lượng trống lúc bắt đầu: ổ C khoảng 77.3 GiB, ổ D khoảng 24.9 GiB.
- Ollama chưa được cài; dự kiến dùng ở Giai đoạn 7. Tesseract được cài riêng trong env project khi bắt đầu Giai đoạn 1; không thêm vào PATH toàn hệ thống.
- Kiểm tra HTTPS HEAD tới PyPI, Hugging Face, HCMUTE và GitHub đều nhận HTTP 200. Đã xác minh tải BGE-M3 pinned revision thành công; việc tải model/dataset khác vẫn phải kiểm tra dung lượng và nguồn riêng trước khi thực hiện.

## Trạng thái PyTorch và khóa API

- Đã được duyệt tải và cài PyTorch `2.14.0+cu126` (CUDA 12.6) trong Conda env `rag-hcmute`. Wheel Windows/CPython 3.11 từ chỉ mục chính thức có kích thước 2,602,751,531 byte (khoảng 2.42 GiB).
- Đã xác minh: `torch.cuda.is_available() == True`; GPU hiển thị là NVIDIA GeForce RTX 3060 Laptop GPU. Thử phép tính CUDA nhỏ thành công. CUDA Toolkit runtime đi kèm Torch báo phiên bản 12.6.
- Đã cài Torch CUDA trước `pip install -e ".[dev,dense]"`; cài thêm `python-dotenv`. Các import Torch, NumPy, PyMuPDF, FAISS, Sentence Transformers và rank_bm25 đều chạy; `pip check` báo không có dependency bị hỏng. `python-dotenv` là 1.2.3.
- Đã được duyệt tải BGE-M3 và tải các tệp PyTorch/Sentence Transformers cần thiết từ revision `5617a9f61b028005a4858fdac845db406aefb181` vào `D:\RAG\models\huggingface` (ngoài repo). Cache chiếm khoảng 2.136 GiB; chỉ lấy 10 tệp cần dùng, không tải ONNX checkpoint thứ hai. `pytorch_model.bin`: 2,271,145,830 byte; SHA-256 `b5e0ce3470abf5ef3831aa1bd5553b486803e83251590ab7ff35a117cf6aad38`. [Model card và trọng số BAAI/bge-m3](https://huggingface.co/BAAI/bge-m3).
- `GEMINI_API_KEY` chưa có trong tiến trình hiện tại. Một khóa đã bị dán vào cuộc trò chuyện nên cần thu hồi/đổi khóa; giá trị khóa không được lưu trong tài liệu, terminal, log hoặc Git. Chỉ cấu hình khóa mới cục bộ sau khi đã đổi; cho tới khi đó không gọi Gemini.
- Không dùng API trả phí. Mọi tác vụ Gemini chỉ trong ba phạm vi đã duyệt và phải giữ chi phí ở mức 0 USD nếu chưa có ước tính được chấp thuận.

## Các gói và xác minh Giai đoạn 0

- Đã cài extras `dev,dense` của project sau Torch CUDA; những phiên bản đã xác minh gồm `torch 2.14.0+cu126`, `numpy 2.4.6`, `pymupdf 1.28.2`, `faiss-cpu 1.15.1`, `sentence-transformers 6.1.0`, `rank-bm25 0.2.2`, `python-dotenv 1.2.3`.
- `pytest`: 20 bài kiểm thử đạt; smoke tests: 2/2 đạt.
- Kiểm tra corpus: 3 tài liệu, 0 lỗi; SHA-256 của cả ba tệp khớp manifest. PDF và các hiện vật có thể chứa văn bản nguồn vẫn nằm trong vùng bị Git ignore, không đưa vào commit.
- Tái dựng snapshot trong thư mục scratch bị ignore: 3 tài liệu, 182 trang, 156 chunks; snapshot ID `5da3bd4d5de54492`.
- Tái lập BM25 trên pilot set: Hit@5 = 3/7 (0.429), MRR@10 = 0.371; kết quả khớp baseline đã lưu ở mốc trước. Không gọi các chỉ số này là Recall@5 vì phép đo đếm câu hỏi có ít nhất một kết quả liên quan trong Top-5.
- Tái lập Dense từ snapshot scratch bằng model revision nêu trên: Hit@5 = 6/7 (0.857), MRR@10 = 0.643; khớp kết quả Dense lịch sử trong repo. Script hiện in nhãn `Recall@5`, nhưng phép đo trên bộ pilot này đếm câu hỏi có ít nhất một gold chunk trong Top-5, do đó được diễn giải là Hit@5.
- Gemini chưa được gọi; cần khóa mới sau khi khóa đã lộ được thu hồi/đổi. OCR engine đã cài ở Giai đoạn 1 nhưng chưa tích hợp vào ingestion pipeline.

## OCR cục bộ — Giai đoạn 1

- Tesseract 5.5.3 và pytesseract 0.3.13 được cài vào Conda env `rag-hcmute`. Executable: `C:\Users\Dell\anaconda3\envs\rag-hcmute\Library\bin\tesseract.exe`.
- Model tiếng Việt `vie.traineddata` lấy từ [`tesseract-ocr/tessdata_best`](https://github.com/tesseract-ocr/tessdata_best), giấy phép Apache-2.0; file nằm ngoài repo tại `D:\RAG\models\tesseract\tessdata\vie.traineddata`, dung lượng 12.435.550 byte, SHA-256 `b6b49293d95d0b6dbd8780174627e82c75be957b6f4ed9862155540d6b00bb45`.
- Khi gọi Tesseract từ Python, chỉ rõ model bằng `--tessdata-dir D:\RAG\models\tesseract\tessdata`; lệnh kiểm tra: `& 'C:\Users\Dell\anaconda3\envs\rag-hcmute\Library\bin\tesseract.exe' --tessdata-dir 'D:\RAG\models\tesseract\tessdata' --list-langs`.
- Đã khảo sát 26 trang nghi scan ở 200 DPI, `lang=vie`, `psm=6`; các metric tổng hợp nằm ở `artifacts/results/g1_ocr_survey.json` (bị Git ignore, không lưu nội dung OCR). Confidence chưa được xem là độ chính xác; cần ground truth thủ công trước khi dùng OCR text trong corpus.
- Sau cài đặt, xác minh `torch==2.14.0+cu126`, `torch.cuda.is_available() == True`, `pytest` 20 passed, smoke tests 2/2 passed.

## Lệnh chạy thống nhất

Trong PowerShell, dùng executable tuyệt đối hoặc `conda run -n rag-hcmute`. Ví dụ:

```powershell
$py = 'C:\Users\Dell\anaconda3\envs\rag-hcmute\python.exe'
& $py -c 'import sys; print(sys.executable)'
& $py -c 'import torch; print(torch.__version__, torch.version.cuda, torch.cuda.is_available())'
```

Không kích hoạt/đổi sang Python base khi chạy script. Không dùng `KMP_DUPLICATE_LIB_OK` để che lỗi thư viện.
