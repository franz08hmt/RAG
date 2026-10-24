# BÁO CÁO TIẾN ĐỘ MỐC 2

## Phạm vi của đợt thực hiện

Đợt này tiếp tục tìm hiểu từng thành phần của RAG trên kho tài liệu học vụ HCMUTE. Bản demo ban đầu được giữ làm tài liệu định hướng; báo cáo này trình bày phần thực nghiệm bổ sung sau Mốc 1. Trọng tâm là giải thích dữ liệu được xử lý ra sao, vì sao một lựa chọn kỹ thuật có thể làm thay đổi kết quả và cách kiểm tra lại các nhận xét bằng mã nguồn.

Ba phần được bổ sung rõ nhất là kiểm tra cấu trúc trang PDF, so sánh embedding khi không bị cắt đầu vào và vận hành console từ câu hỏi đến câu trả lời có nguồn. Các phép thử vẫn dùng tập development nhỏ. Vì vậy, số liệu phục vụ phân tích cơ chế và tìm lỗi; chưa phải kết quả đánh giá độc lập của một hệ thống tư vấn học vụ.

{{summary}}

## 1 Quy trình RAG và bài toán thực nghiệm

RAG kết hợp truy xuất thông tin với sinh câu trả lời. Tài liệu được lập chỉ mục bên ngoài mô hình; khi có câu hỏi, hệ thống tìm các đoạn liên quan rồi chuyển chúng vào ngữ cảnh cho mô hình sinh. Chỉ mục giúp tìm nguồn, còn mô hình sinh diễn đạt nội dung từ nguồn. Việc tìm thấy một đoạn gần nghĩa chưa bảo đảm đoạn đó chứa đủ điều kiện để trả lời.

Trong bài toán thực nghiệm, đầu vào là câu hỏi tiếng Việt về nội dung có trong các văn bản đã thu thập. Đầu ra cần có câu trả lời hoặc trạng thái chưa đủ căn cứ, cùng thông tin để mở lại văn bản và trang PDF. Ví dụ, câu hỏi về nghỉ học tạm thời cần dẫn tới điều khoản quy định trường hợp được nghỉ. Nếu câu hỏi yêu cầu lịch thi của một lớp vào tuần tới, kho quy chế tĩnh không cung cấp dữ liệu đó.

{{pipeline}}

Pha chuẩn bị chạy khi thay đổi tài liệu hoặc cấu hình lập chỉ mục. Pha hỏi đáp chạy theo từng truy vấn. Phân biệt hai pha giúp xác định chỗ cần sửa: lỗi nhận dạng chữ thuộc xử lý đầu vào; bỏ sót đoạn đúng thuộc truy xuất; bổ sung điều kiện không có trong nguồn thuộc sinh câu trả lời. Thêm reranker không thể sửa chữ OCR sai hoặc tìm lại một đoạn chưa có trong tập ứng viên.

Search là cách gọi chung của tìm kiếm. Information Retrieval nghiên cứu biểu diễn và xếp hạng thông tin; BM25 là truy xuất dựa trên từ vựng, còn dense retrieval dùng vector. RAG sử dụng kết quả truy xuất để sinh câu trả lời. Nghiên cứu của Lewis và cộng sự kết hợp bộ nhớ tham số với bộ nhớ tài liệu và huấn luyện các thành phần trong thiết lập của bài báo. PoC này sử dụng mô hình có sẵn, không fine-tune [1].

Các cải tiến như viết lại câu hỏi, truy vấn nhiều lần hoặc nén ngữ cảnh có thể bổ sung sau. Chúng cũng tạo thêm nguồn sai số và chi phí. Đợt này ưu tiên giữ câu hỏi gốc, kiểm tra truy xuất và reranking trước khi thêm một mô hình viết lại truy vấn. Điều đó giúp giải thích kết quả thay vì thay đồng thời nhiều thành phần.

## 2 Dữ liệu và cách tổ chức phép thử

Snapshot G0 được giữ cố định để đối chiếu với Mốc 1. Mỗi tài liệu có mã định danh, đường dẫn nguồn và SHA-256. Hàm kiểm tra dừng nếu mã băm của PDF khác manifest; không tự thay tệp mới vào một phép so sánh cũ. Số trang PDF được đếm từ 1 và được phân biệt với số trang in trên tài liệu.

{{corpus}}

QĐ 3116/2025 đã có tệp cục bộ và được khảo sát cấu trúc trang riêng. Tệp này chưa được đưa vào G0, chưa dùng làm nguồn cho câu trả lời trong các phép thử chính. Việc có một văn bản mới hơn không tự xác định được quan hệ thay thế hay đối tượng áp dụng của văn bản cũ. PoC hiện chưa được dùng để khẳng định quy định đang có hiệu lực cho một sinh viên cụ thể.

Bộ development chính có 10 câu, gồm 7 câu có bằng chứng và 3 câu ngoài phạm vi hoặc thiếu căn cứ. Các câu có đáp án được gắn với 10 khoảng văn bản nguồn, xác định bằng vị trí trên trang và mã băm nội dung. Năm câu về bảng thuộc phép thử riêng, không cộng vào mẫu số của bộ chính. Chưa có tập test độc lập đã được người học duyệt và đóng băng.

Khi so sánh embedding, hai mô hình nhận cùng nội dung đoạn; khi so sánh chỉ mục, các chỉ mục nhận cùng vector; khi so sánh prompt, mô hình sinh nhận cùng câu hỏi và cùng các nguồn. Máy thực nghiệm dùng Python 3.11 trong môi trường riêng, GPU RTX 3060 Laptop 6 GB và FAISS CPU. Thời gian nhúng, tìm kiếm, reranking và sinh được tách riêng. Không dùng API tính phí hoặc gửi tài liệu học vụ ra dịch vụ đám mây trong đợt này.

## 3 Document Chunk và đường dẫn tới nguồn

Về thiết kế, Document đại diện cho một phiên bản tài liệu, không chỉ một tên tệp. Trong mã hiện tại, thông tin này nằm trong các record của manifest, chưa có một class tên Document. PageText giữ số trang và kết quả trích xuất. Chunk giữ nội dung, mã tài liệu, khoảng trang, đường dẫn Chương–Điều nếu có, phương thức trích xuất và khoảng vị trí tính theo đơn vị khoảng trắng. RetrievalHit bổ sung hạng và điểm của thuật toán. Khi tạo câu trả lời, S1, S2 là nhãn ngắn trỏ tới các chunk đã đưa vào ngữ cảnh; chúng không phải mã nguồn độc lập do LLM tự tạo.

Có thể tổ chức dữ liệu bằng chunk phẳng mang metadata, bằng cây Chương–Điều rồi để chunk tham chiếu nút cây, hoặc bằng các block gốc cùng tọa độ trên trang. Cách phẳng dễ kiểm tra và phù hợp corpus nhỏ nhưng dễ lặp metadata. Cây cấu trúc giữ quan hệ điều khoản tốt hơn nhưng phụ thuộc chất lượng nhận diện tiêu đề. Block có tọa độ thuận lợi để đối chiếu bảng và hình, đổi lại phải quản lý hệ tọa độ và thứ tự đọc.

PoC đang dùng chunk phẳng cho luồng truy xuất. Mốc này bổ sung PageArtifacts để lưu vùng chữ, vùng ảnh và bảng ứng viên theo tọa độ PDF. Hai cấu trúc được giữ tách biệt: bản khảo sát bố cục chưa tự thay thế toàn bộ mô hình Document hoặc tự đưa nội dung OCR mới vào chỉ mục.

{{data_contract}}

Mã băm phát hiện tệp hoặc nội dung thay đổi; tọa độ giúp chỉ lại vùng nguồn; cả hai đều không chứng minh nội dung đúng. Tương tự, section_path là kết quả nhận diện, không phải nhãn luôn đúng. Trường hợp một dòng dẫn chiếu bắt đầu bằng “Điều 12” có thể bị nhầm thành tiêu đề. Vì vậy cần kiểm tra vị trí, thứ tự Điều và bố cục trước khi dùng metadata đó làm căn cứ trích dẫn.

## 4 PDF có chữ trang scan bảng và hình

### 4.1 Phân loại để chọn cách xử lý

Trang có lớp chữ có thể trích xuất trực tiếp bằng PyMuPDF. Trang chủ yếu là ảnh cần kiểm tra OCR. Trang có chữ lẫn hình vẫn cần xem vùng hình chứa thông tin gì. Bộ kiểm tra mới dùng diện tích hợp của các ảnh trên trang, lượng chữ trích xuất và các vùng bảng do thư viện phát hiện. Ảnh chồng lên nhau chỉ được tính diện tích một lần.

{{input_audit}}

Kết quả này là thống kê cấu trúc, không phải độ chính xác phân loại. Chẳng hạn, ảnh nền phủ cả trang khiến một trang có lớp chữ vẫn được chuyển sang nhóm cần kiểm tra. Ngược lại, không tìm thấy bảng bằng đường kẻ không có nghĩa trang không có bảng. Muốn đo precision và recall của bộ phát hiện phải có danh sách vùng bảng do người kiểm tra đánh dấu [5].

### 4.2 Bảng cần giữ quan hệ giữa cột và hàng

{{table_crop}}

Hình trên lấy từ trang PDF 20 của QĐ 1727, không phải hình minh họa sinh bằng AI. Tên cột quyết định ý nghĩa của các con số. Nếu trích riêng “36–71” mà mất nhãn cột và hàng, đoạn đó gần như không đủ để trả lời câu hỏi về năm đào tạo. Với ô gộp, giá trị null từ bộ trích xuất có thể biểu thị vùng gộp, không nhất thiết là dữ liệu trống.

Cách xử lý phù hợp cho mẫu này là giữ tên bảng, lặp nhãn cột khi tách nhóm hàng, lưu trang và vùng bảng gốc. Phép thử bảng ở Mốc 1 đã có bộ câu hỏi riêng; bộ dò bảng bổ sung trong Mốc 2 mới giúp tìm và lưu vùng cần kiểm tra, chưa thay thế việc xác minh từng ô. Không lấy số bảng ứng viên làm bằng chứng rằng bảng đã được hiểu chính xác.

### 4.3 OCR và nội dung hình

OCR chuyển ảnh chữ thành chuỗi ký tự. Nó có thể làm sai dấu, số, ngắt dòng hoặc thứ tự cột. CER tính số phép chèn, xóa và thay thế ký tự chia cho độ dài bản chép chuẩn; WER áp dụng cùng cách tính trên đơn vị từ đã quy ước. Kết quả phụ thuộc bản chép chuẩn và cách chuẩn hóa, nên điểm confidence của Tesseract không thể thay cho CER/WER.

Các phép thử OCR trước đã so sánh DPI và chế độ phân đoạn trang trên một mẫu nhỏ. Tesseract cung cấp nhiều chế độ bố cục; lựa chọn cho một khối văn xuôi không nhất thiết phù hợp trang sơ đồ [6]. Ở đợt này, QĐ 3116 tiếp tục được tách khỏi corpus hỏi đáp vì lớp chữ cần rà lại. Chưa có đủ bản chép chuẩn để công bố độ chính xác OCR trên toàn văn bản.

{{figure_crop}}

Với sơ đồ, nhận được các nhãn chữ chưa đồng nghĩa hiểu đúng mũi tên và quan hệ giữa các vùng. Phương án nhẹ là lưu ảnh cùng trang, OCR phần chữ và yêu cầu người đọc kiểm tra hình gốc. Mô hình đa phương thức có thể mô tả quan hệ nhưng cũng có thể suy đoán; mô tả phải được đánh dấu là nội dung suy ra, không trộn với trích dẫn nguyên văn. Mốc này đã lưu được vị trí và ảnh nguồn, chưa thực nghiệm mô hình hiểu hình.

## 5 Chunking và vấn đề mất bằng chứng ở ranh giới

Chia cố định theo độ dài dễ tái lập nhưng có thể cắt giữa một điều kiện. Chia theo đoạn hoặc câu giữ đơn vị diễn đạt tốt hơn, song câu dài vẫn cần giới hạn. Chia theo Chương–Điều phù hợp quy chế khi nhận diện tiêu đề đáng tin cậy. Semantic chunking dựa vào thay đổi ngữ nghĩa giữa câu, cần thêm mô hình và một ngưỡng khác để hiệu chỉnh. Parent–child tìm đoạn nhỏ rồi mở rộng về đoạn cha; cách này giữ được chi tiết truy xuất nhưng phải kiểm soát lượng ngữ cảnh đưa vào LLM.

Baseline đang dùng 500 đơn vị tách bằng khoảng trắng và overlap 80; đây không phải 500 token của encoder. Phép thử mới tạo cửa sổ tối đa 250 đơn vị khoảng trắng, overlap 40, rồi thu ngắn đến khi cả tokenizer BGE-M3 và E5 đều nhận đủ đoạn trong 512 token, kể cả tiền tố và token đặc biệt. Việc chọn ranh giới không đọc câu hỏi hoặc nhãn đáp án.

{{chunk_control}}

Việc hết truncation không đồng nghĩa mọi điều kiện đều nằm trọn trong một chunk. Trong bộ cửa sổ mới, một số span vàng đi qua ranh giới. Nếu bộ chấm chỉ công nhận một chunk chứa trọn span, nó sẽ ghi miss ngay cả khi hai chunk được trả về ghép lại có đủ nội dung. Vì vậy báo cáo giữ chỉ số chứa trọn để đối chiếu lịch sử và bổ sung độ phủ ký tự của hợp các chunk. Không gọi hai cách đo này bằng cùng một tên.

Trường hợp P004 về đăng ký học lại là ví dụ cần quan sát ranh giới thay vì chỉ nhìn điểm vector. Với câu nhiều điều kiện như P003 và P008, tìm được một đoạn đúng vẫn có thể thiếu đoạn còn lại. Kết quả chunking cần đọc cùng độ phủ nguồn, độ dài context và khả năng trích dẫn, không chọn cấu hình chỉ vì có nhiều chunk hơn.

## 6 Embedding cho tiếng Việt

Bi-encoder mã hóa câu hỏi và đoạn văn thành các vector riêng. Các vector tài liệu có thể tính trước; khi hỏi chỉ cần nhúng câu hỏi rồi tìm vector gần nó. Đổi model đồng nghĩa đổi không gian biểu diễn, nên không được dùng vector câu hỏi của model mới với chỉ mục của model cũ. Trong phép thử, vector được chuẩn hóa L2 và so bằng tích vô hướng.

Hai model đã chạy là BGE-M3 và multilingual-E5-small. BGE-M3 hỗ trợ nhiều ngôn ngữ, vector 1024 chiều, context tối đa theo model card là 8192; ứng dụng cũ chủ động giới hạn ở 1024. E5-small tạo vector 384 chiều và sử dụng tiền tố query: cho câu hỏi, passage: cho tài liệu, kể cả tiếng Việt. Bản kiểm soát giới hạn cả hai ở 512 để đoạn không bị cắt [2, 3].

{{embedding}}

{{embedding_interpretation}}

Kết luận phù hợp hiện tại là hai model đều cần được dùng đúng giao thức đầu vào. Kích thước model, pooling, dữ liệu huấn luyện và tiền tố vẫn khác nhau dù độ dài đã được kiểm soát. Chưa có cơ sở kết luận model tốt nhất cho tiếng Việt nói chung từ bảy câu học vụ. Mục tiêu khảo sát ít nhất sáu model, trong đó có model chuyên tiếng Việt, vẫn chưa hoàn thành; không dùng bảng giới thiệu model để thay cho số đo thực nghiệm.

## 7 Chỉ mục vector và vector database

Flat so sánh truy vấn với toàn bộ vector và là đối chứng tìm kiếm chính xác. HNSW tổ chức một đồ thị láng giềng nhiều tầng; tăng efSearch thường mở rộng vùng tìm kiếm nhưng tốn thời gian hơn. IVF phân cụm vector thành các danh sách; nprobe quyết định số danh sách được duyệt. Nếu nprobe quá nhỏ, một láng giềng gần có thể nằm trong danh sách chưa được tìm [4].

FAISS là thư viện chỉ mục. Vector database như Qdrant còn quản lý dữ liệu lưu bền, payload và thao tác với metadata. Phép so sánh FAISS–Qdrant local exact ở Mốc 1 trả cùng Top-10 trên corpus nhỏ; điều đó chưa nói lên khả năng mở rộng hoặc chất lượng bộ lọc. Đợt này tách riêng bài toán ANN bằng cách cho Flat, HNSW và IVF nhận cùng vector BGE-M3.

{{vector_indexes}}

Neighbor Recall@10 ở bảng này đo số ID hàng xóm trùng với Top-10 của Flat, chia cho 10, rồi lấy trung bình theo truy vấn. Nó không phải Recall của bằng chứng học vụ. Thời gian chỉ bao gồm tìm trong chỉ mục CPU, sau warm-up, không gồm nhúng câu hỏi hoặc sinh câu trả lời. Corpus nhỏ và truy vấn lặp lại có lợi cho cache; không suy rộng số mili giây này thành tải phục vụ thực tế.

Ở quy mô hiện có, Flat vẫn là lựa chọn dễ giải thích cho console. Các cấu hình ANN được giữ làm phép thử để thấy trường hợp bỏ sót và tác động của tham số. Chưa có nhu cầu chuyển sang một dịch vụ vector cloud chỉ để tạo thêm thành phần cho kiến trúc.

## 8 Truy xuất từ vựng dense và hybrid

BM25 cộng đóng góp của các từ trong câu hỏi dựa trên tần suất trong đoạn, độ hiếm trong corpus và hiệu chỉnh độ dài. Tần suất tăng có hiệu ứng bão hòa; một đoạn dài không được cộng điểm chỉ vì chứa nhiều từ hơn. Với tiếng Việt, tách theo âm tiết và tách từ ghép có thể tạo các thống kê khác nhau, vì vậy phải giữ tokenizer giống nhau khi đối chiếu thuật toán.

Đợt này bổ sung một bản BM25 tham chiếu ngắn để đọc cơ chế và đối chiếu điểm với rank_bm25 trên cùng token, gồm cả quy tắc xử lý IDF âm của BM25Okapi. Bản này chưa thay baseline đang dùng thư viện. Kiểm thử khớp điểm trên dữ liệu kiểm thử xác nhận cách cài công thức, không chứng minh chất lượng truy xuất trên dữ liệu mới.

Dense hỗ trợ câu hỏi khác cách diễn đạt của văn bản, nhưng cũng có thể đưa lên các đoạn cùng chủ đề mà thiếu điều kiện được hỏi. RRF cộng nghịch đảo thứ hạng từ từng bộ tìm kiếm, dùng hằng số 60 trong cấu hình này. RRF không cần ép điểm BM25 và cosine về cùng thang; tuy nhiên một nhánh yếu vẫn có thể làm tụt thứ hạng kết quả tốt của nhánh còn lại [7].

{{retrieval}}

Ở đây hybrid không mặc nhiên vượt dense. Đó là lý do cần giữ cả kết quả từng nhánh và danh sách ứng viên trước khi hợp nhất. Một điểm cosine cao chỉ thể hiện quan hệ trong không gian vector; nó không phải xác suất câu hỏi có đáp án trong corpus. Đặt ngưỡng từ chối từ vài điểm cao thấp có thể làm mất câu có đáp án và vẫn giữ câu ngoài phạm vi.

## 9 Reranker và giới hạn của tập ứng viên

Cross-encoder đọc câu hỏi cùng một đoạn trong một lần suy luận rồi cho điểm cặp. Nó xét tương tác trực tiếp tốt hơn cách so hai vector độc lập, nhưng phải chạy lại theo câu hỏi và theo số ứng viên. BGE-Reranker-v2-m3 được dùng ở bước này; điểm logit dùng xếp hạng, không được diễn giải như xác suất đúng đã hiệu chỉnh [8].

{{reranking}}

{{reranking_interpretation}}

Reranker không thể lấy lại một đoạn không nằm trong Top-20 ban đầu. Tăng số ứng viên có thể giảm rủi ro đó nhưng tăng thời gian suy luận. Thí nghiệm này mới dùng một model và một độ sâu ứng viên; chưa đạt mục tiêu đối chiếu nhiều reranker. Console dùng giới hạn 1024 token cho cặp để hạn chế cắt đoạn, còn số cặp thực tế bị cắt vẫn được ghi trong từng lượt chạy.

## 10 Sinh câu trả lời trích dẫn và từ chối

Các đoạn được chọn được gắn nhãn S1, S2 rồi đưa vào prompt cùng vị trí nguồn. Qwen3:4B chạy cục bộ qua Ollama, tắt thinking và đặt temperature bằng 0. JSON đầu ra phân biệt câu trả lời, danh sách nguồn và trạng thái từ chối. Văn bản tài liệu được đặt trong vùng dữ liệu tham khảo; chỉ dẫn xuất hiện trong nguồn không được xem như mệnh lệnh của ứng dụng.

Phép thử giữ cùng kết quả truy xuất và so hai prompt. Prompt chuẩn yêu cầu bám nguồn và từ chối khi thiếu thông tin. Prompt scope_check yêu cầu đối chiếu thêm đối tượng, thời điểm, điều kiện và số liệu, tránh dùng một quy định chung để trả lời một thông tin cụ thể không có trong nguồn. Không cài quy tắc nhận biết mã câu hỏi hoặc chép đáp án chuẩn vào prompt.

{{generation}}

{{generation_interpretation}}

P006 hỏi các điều kiện để thực hiện khóa luận hoặc đồ án tốt nghiệp. Ở prompt chuẩn, mô hình trả lời rằng sinh viên cần tham gia nghiên cứu khoa học theo nhóm hoặc đề tài cùng giảng viên, rồi dẫn S1 và S3. Đối chiếu S1 với trang PDF 32 của QĐ 1727 cho thấy đoạn này liệt kê nhiều hình thức được công nhận tham gia nghiên cứu khoa học. Câu trả lời đã lấy một hình thức trong danh sách để diễn đạt như điều kiện chung, đồng thời chưa cung cấp đủ điều kiện mà câu hỏi yêu cầu. Đây là một trường hợp cần sửa cách sử dụng bằng chứng, không phải lỗi thiếu tên văn bản. Nhận xét này dùng để phân tích lỗi; chưa được tính thành điểm chấm người.

Bộ kiểm tra hiện xác minh citation ID thuộc danh sách nguồn. Chưa xác minh tự động từng mệnh đề được nguồn đó chứng minh; cũng chưa bắt buộc mọi câu phải có trích dẫn nội dòng. Báo cáo giữ hai trạng thái này riêng. Một ID hợp lệ hoặc một câu trả lời có văn phong tự tin đều chưa phải bằng chứng về độ đúng nội dung.

## 11 Đánh giá chất lượng và đọc trường hợp sai

Độ phủ ký tự được tính bằng số ký tự vàng nằm trong hợp các chunk Top-5, chia cho tổng ký tự vàng của câu hỏi, rồi lấy trung bình trên bảy câu có bằng chứng. Các đoạn giao nhau được hợp nhất trong từng tài liệu để không đếm trùng. Precision theo ký tự chia phần giao cho lượng ký tự truy xuất; IoU chia phần giao cho hợp của bằng chứng và phần truy xuất. Các khoảng vị trí được tính trên văn bản đã chuẩn hóa khoảng trắng, không phải số byte của PDF.

Hit@5 chỉ hỏi có ít nhất một chunk đạt ngưỡng liên quan hay không. Trong phép thử mới, ngưỡng là phủ ít nhất 50% một span vàng. MRR@10 lấy nghịch đảo thứ hạng chunk đầu tiên đạt ngưỡng. nDCG@5 dùng độ phủ lớn nhất của một span làm gain tuyến tính và so với thứ tự lý tưởng của các chunk hiện có. Một câu nhiều điều kiện có thể Hit nhưng Recall chưa đủ; nDCG cao cũng không khẳng định câu trả lời đúng.

{{cases}}

So sánh embedding có thêm bootstrap cặp 5.000 lần, seed cố định, trên cùng bảy câu. Khoảng 95% này chỉ mô tả độ nhạy của mẫu development; các câu chung chủ đề hoặc chung điều khoản không hoàn toàn độc lập. Không dùng khoảng tin cậy nhỏ từ việc lặp cùng truy vấn để thay cho một tập câu hỏi lớn hơn.

Đánh giá sinh câu trả lời cần thêm bản đáp án tham chiếu, danh sách mệnh đề và người đối chiếu nguồn. Phiếu chấm đã được chuẩn bị nhưng chưa có nhãn người đầy đủ, nên chưa công bố điểm faithfulness, correctness hoặc độ đồng thuận với judge. Các kết quả tự động trong báo cáo là kiểm tra vận hành, định dạng, vị trí nguồn và hành vi trên các câu đã gán nhãn; chúng không được đổi tên thành “độ chính xác toàn hệ thống”.

## 12 Ứng dụng console và tái lập

Console hỗ trợ các chế độ BM25, dense, hybrid và hai chế độ có reranker. Mỗi lượt in tên phương pháp, danh sách đoạn, điểm, trang và Điều nếu metadata có. Khi bật sinh câu trả lời, console in thêm nội dung từ Qwen3 và nguồn được chọn. Lỗi kết nối hoặc JSON không hợp lệ được trả bằng trạng thái lỗi, không bị tính như một lần từ chối đúng.

Trước đây mỗi lần mở console lại nhúng toàn bộ corpus. Bản mới lưu vector cục bộ và khóa cache theo nội dung model, nội dung chunk, thứ tự chunk và cấu hình mã hóa. Khi dữ liệu thay đổi, khóa đổi và vector được tính lại. Cache được kiểm tra kiểu dữ liệu, kích thước, giá trị hữu hạn, chuẩn L2 và mã băm. Đây là cache vector, không phải cache câu trả lời để trình diễn thay cho chạy thật.

{{console}}

Máy 6 GB VRAM cần chia sẻ tài nguyên giữa embedding, cross-encoder và LLM. Console chuyển model truy xuất về CPU trước khi gọi Ollama, sau đó khôi phục khi cần truy vấn mới. Cách này giảm tranh chấp VRAM nhưng vẫn cần RAM hệ thống. Một lần khởi tạo đã gặp lỗi thiếu bộ nhớ ảo Windows khi cùng giữ hai model truy xuất. Kịch bản batch sau đó tải embedding và reranker lần lượt, giải phóng chúng trước khi sinh. Không thay đổi cấu hình bộ nhớ của Windows để lấy số đo; thời gian batch cũng không đại diện cho độ trễ phiên tương tác đầy đủ.

Các lệnh tái lập và kết quả được tập hợp trong phụ lục và tài liệu hướng dẫn Mốc 2. Thầy có thể chọn một câu đã thử để đối chiếu nguồn hoặc nhập câu mới trong console. Kịch bản demo không bảo đảm mọi câu đều đúng; câu thất bại được giữ để giải thích giới hạn của phương pháp.

## 13 Kết luận và phạm vi còn tiếp tục

Đợt thực hiện này đã đi sâu hơn vào quan hệ giữa các khâu. Một thay đổi ở chunking làm thay đổi lượng thông tin mà embedding nhìn thấy và cách bộ chấm tính bằng chứng. Một chỉ mục gần đúng có thể nhanh hơn nhưng bỏ sót hàng xóm. Reranking có thể tăng độ phủ ở Top-5 mà không cải thiện thứ hạng đầu tiên. Những kết quả đó giúp xác định đúng điều đang đo thay vì chỉ tìm một điểm tổng hợp cao.

Console đã có đường chạy từ truy xuất đến sinh và trích dẫn, có số liệu thời gian, cache được kiểm tra và lỗi được phân loại. Tài liệu đầu vào đã được khảo sát thêm ở mức vùng chữ, ảnh và bảng. Báo cáo vẫn giữ rõ ranh giới giữa phát hiện bố cục, hiểu nội dung hình, truy xuất bằng chứng và xác minh câu trả lời. Các phần này cần các cách đánh giá khác nhau.

Mốc 2 là báo cáo tiến độ có thực nghiệm, chưa khép toàn bộ kế hoạch tìm hiểu. Những việc còn ảnh hưởng trực tiếp đến kết luận cuối gồm mở rộng và duyệt câu hỏi, đóng băng holdout, bổ sung các model chuyên tiếng Việt và reranker, kiểm tra OCR bằng bản chép chuẩn, cùng đánh giá mệnh đề và trích dẫn bởi người. Chưa có căn cứ để xem PoC là nguồn tư vấn học vụ chính thức. Giá trị của bản hiện tại là cho phép đọc lại từng quyết định, chạy lại phép thử và thấy rõ chỗ cần cải thiện tiếp.

## Phụ lục A Minh chứng và cách chạy

{{evidence_manifest}}

Kho GitHub: https://github.com/franz08hmt/RAG. Nhánh làm việc cục bộ: tim-hieu-rag-dot2. Các thay đổi của đợt này chưa được push; liên kết GitHub hiện không thay thế bộ mã và minh chứng cục bộ được bàn giao. Mã nguồn và số liệu mới chỉ có thể đối chiếu trên GitHub sau khi nhánh này được công bố.

{{code_revision}}

{{reproduction}}

## Phụ lục B Đối chiếu yêu cầu của giảng viên

{{traceability}}

## Công cụ hỗ trợ

Các công cụ AI đã hỗ trợ rà soát mã, thiết lập và chạy thử nghiệm, phân tích lỗi, biên tập nội dung và định dạng báo cáo. Model Qwen3:4B là thành phần sinh câu trả lời được thử nghiệm; không được dùng để tự chấm chất lượng câu trả lời của chính nó. Các bảng định lượng được tạo từ kết quả chương trình. Việc đọc nguồn và phân tích bằng AI không được ghi thành nhãn đã có người xác nhận. Sinh viên cần kiểm tra nội dung, tự chạy các lệnh và chịu trách nhiệm cho bản nộp cuối.

## Tài liệu tham khảo

{{references}}
