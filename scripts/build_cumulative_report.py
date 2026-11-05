"""Consolidate the three reviewed progress reports by RAG stage."""
from copy import deepcopy
from io import BytesIO
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

from docx import Document
from docx.oxml.ns import qn
from docx.opc.constants import RELATIONSHIP_TYPE as RT
from docx.text.paragraph import Paragraph
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt
from build_m1_report_v3 import add_p, add_heading, add_data_table, set_run_font

ROOT = Path(__file__).resolve().parents[1]
SOURCES = {
    "m1": ROOT / "reports/22110068_RAG_Bao_Cao_Tien_Do_Dot_1_v6.docx",
    "m2": ROOT / "reports/22110068_RAG_Bao_Cao_Tien_Do_Moc_2_v3.docx",
    "m3": ROOT / "reports/22110068_RAG_Bao_Cao_Tien_Do_Moc_3_v1.docx",
}


def main():
    print(f"Python executable: {sys.executable}")
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    inputs = {name: Document(path) for name, path in SOURCES.items()}
    bodies = {name: list(doc.element.body) for name, doc in inputs.items()}
    doc = Document(SOURCES["m3"])
    for child in list(doc.element.body)[9:]:
        if child.tag != qn("w:sectPr"):
            doc.element.body.remove(child)
    ledger = []
    reference_paragraphs = []
    counters = {"Bảng": 0, "Hình": 0}
    chapter = 0
    subsection = 0
    def p(text, **kwargs):
        return add_p(doc, text, **kwargs)
    def h(text):
        nonlocal subsection
        subsection += 1
        return add_heading(doc, f"{chapter}.{subsection} {text}", 2)
    def ch(text):
        nonlocal chapter, subsection
        chapter += 1
        subsection = 0
        heading = add_heading(doc, f"CHƯƠNG {chapter} {text}")
        heading.paragraph_format.page_break_before = True
    def rename_caption(text):
        match = re.match(r"^(Bảng|Hình)\s+\d+(?:\.\d+)?\.?\s+(.*)", text, re.S)
        if match:
            kind, rest = match.groups()
            counters[kind] += 1
            return f"{kind} {counters[kind]}  {rest}"
        return text
    def cp(name, *indices):
        source = inputs[name]
        for index in indices:
            element = deepcopy(bodies[name][index])
            if element.tag == qn("w:sectPr"):
                raise ValueError("Cannot import section properties")
            for pp in element.xpath(".//w:pPr"):
                for b in list(pp):
                    if b.tag in (qn("w:pageBreakBefore"), qn("w:sectPr")):
                        pp.remove(b)
            for br in element.xpath(".//w:br"):
                if br.get(qn("w:type")) == "page":
                    br.getparent().remove(br)
            # Source image IDs belong to their original packages.
            for blip in element.xpath(".//a:blip"):
                old = blip.get(qn("r:embed"))
                if old:
                    image = source.part.related_parts[old]
                    rid, _ = doc.part.get_or_add_image(BytesIO(image.blob))
                    blip.set(qn("r:embed"), rid)
            if element.tag == qn("w:p"):
                para = Paragraph(element, doc._body)
                old = para.text
                new = rename_caption(old)
                if name == "m1":
                    new = new.replace("[2, 6, 7]", "[10, 11, 12]").replace("[3, 4]", "[13, 14]")
                new = new.replace("định nghĩa đầy đủ ở Mục 11", "định nghĩa đầy đủ ở Mục 5.1")
                if name == "m2":
                    new = new.replace("Mốc này bổ sung", "Mốc 2 bổ sung").replace("Mốc này đã", "Tại Mốc 2 đã")
                    new = new.replace("Đợt này bổ sung", "Ở Mốc 2 đã bổ sung")
                    if index == 97:
                        new = new.replace("của ứng dụng.", "của ứng dụng [9].")
                if new != old:
                    first = deepcopy(para.runs[0]._r.rPr) if para.runs and para.runs[0]._r.rPr is not None else None
                    para.clear()
                    run = para.add_run(new)
                    if first is not None:
                        run._r.insert(0, first)
                para.paragraph_format.page_break_before = False
                if element.xpath(".//w:drawing"):
                    para.paragraph_format.keep_with_next = True
            doc.element.body.insert(-1, element)
            if name == "m2" and 146 <= index <= 154:
                reference_paragraphs.append(Paragraph(element, doc._body))
            ledger.append({"source": name, "body_element": index})
    def span(name, start, end):
        cp(name, *range(start, end + 1))
    def table(label, headers, rows, widths, note):
        counters["Bảng"] += 1
        return add_data_table(doc, f'Bảng {counters["Bảng"]}  {label}', headers, rows, widths, note)

    opening = add_heading(doc, "BÁO CÁO TIẾN ĐỘ TỔNG HỢP")
    opening.style = doc.styles["Title"]
    for run in opening.runs:
        set_run_font(run, 14, bold=True)
    p("Tài liệu tổng hợp nội dung tìm hiểu và thực nghiệm từ Mốc 1 đến Mốc 3 của đề tài được giao. Dữ liệu học vụ HCMUTE được dùng để quan sát từng công đoạn của RAG, từ đọc trang tài liệu, chia đoạn và tạo chỉ mục đến tìm bằng chứng, sinh câu trả lời và mở lại nguồn dẫn.")
    p("Qua các phép thử, chất lượng truy xuất thay đổi theo lượng nội dung mà mô hình thực sự nhận được. Một đoạn có thể bị cắt trước khi tạo embedding, bị bỏ khi đóng gói ngữ cảnh hoặc bị đẩy xuống sau khi hợp kết quả. Ở khâu sinh, trích dẫn đúng mã nguồn vẫn có thể đi kèm cách diễn giải sai. Báo cáo trình bày các trường hợp này cùng cấu hình và số liệu để có thể đối chiếu lại.")
    p("Kết quả chính dùng ba tài liệu, 182 trang, trên một tập phát triển gồm 10 câu hỏi. Bảy câu có đáp án được gắn với 10 khoảng bằng chứng, ba câu còn lại dùng để kiểm tra phản hồi khi thiếu căn cứ. Các thí nghiệm lần lượt bổ sung qua ba mốc nhưng phần kết luận được cập nhật đến ngày 05/11/2026. Tập test độc lập và nhãn chấm ngữ nghĩa đang trong quá trình chuẩn bị.")
    p("Nội dung được tổ chức thành năm chương. Chương 1 giải thích cách hiểu về RAG và bài toán ứng dụng. Chương 2 trình bày dữ liệu và cấu trúc truy nguyên. Chương 3 khảo sát chia đoạn, embedding và chỉ mục. Chương 4 theo dõi truy xuất, xếp hạng lại và sinh câu trả lời. Chương 5 trình bày đánh giá, ứng dụng console và công việc tiếp theo.")
    table("Các cấu hình nguồn cần phân biệt khi đọc kết quả", ["Phép thử", "Tập đoạn", "Điều được kiểm tra"], [
        ["Baseline Mốc 1", "G0 gồm 156 đoạn, cửa sổ 500/80 đơn vị khoảng trắng", "Truy xuất ban đầu và lưu trữ vector"],
        ["Kiểm soát Mốc 2", "289 đoạn vừa 512 token của BGE và E5", "Ảnh hưởng của cắt đầu vào"],
        ["Chunking Mốc 3", "Sáu cách chia, cùng trần 384 token BGE", "Ranh giới và ngân sách ngữ cảnh"],
        ["Embedding Mốc 3", "1.175 đoạn vừa 128 token của cả sáu model", "So bộ mã hóa trên cùng nội dung"],
        ["Reranker Mốc 3", "Trở về 156 đoạn G0, cặp hỏi–đoạn tối đa 512 token", "Cách hợp điểm và xếp lại ứng viên"],
    ], [1.35, 2.55, 2.4], "Các bảng ghi cấu hình và mẫu số riêng. So sánh model trong cùng phép thử để tránh lẫn tác động của việc chia đoạn.")

    ch("BÀI TOÁN VÀ CƠ SỞ VỀ RAG")
    h("Bài toán hỏi đáp trên tài liệu học vụ")
    cp("m1", 17)
    h("Đầu vào đầu ra và phạm vi sử dụng")
    cp("m2", 16)
    cp("m1", 23)
    p("Kho thực nghiệm lưu các phiên bản tài liệu đã thu thập. Khi câu hỏi phụ thuộc học kỳ, chương trình đào tạo hoặc văn bản mới ban hành, cần kiểm tra nguồn và đối tượng áp dụng trước khi trả lời. Thông tin lịch thi theo lớp, học phí học kỳ tới và dữ liệu cá nhân nằm ngoài phạm vi kho hiện tại.")
    h("Nguyên lý và hai pha xử lý")
    cp("m2", 15, 21)
    span("m2", 17, 20)
    h("Các hướng tổ chức hệ thống RAG")
    cp("m1", 37, 38)
    p("Trong PoC, các module được tổ chức để đổi bộ chia đoạn, embedding hoặc reranker mà vẫn dùng cùng nguồn và cách chấm. Các phép thử ở chương sau lần lượt kiểm tra tác động của những thay đổi này. Câu hỏi gốc được giữ trong các lượt đối chiếu chính để hạn chế thêm một nguồn biến thiên do viết lại truy vấn.")

    ch("DỮ LIỆU VÀ XỬ LÝ TÀI LIỆU ĐẦU VÀO")
    h("Corpus và thiết kế đối chiếu")
    span("m2", 24, 30)
    p("G0 ban đầu có 156 chunk với cửa sổ 500 đơn vị tách bằng khoảng trắng và phần chồng lấn 80 đơn vị. Các phép thử sau dùng lại PDF nguồn nhưng tạo những tập đoạn khác. Vì vậy, khi đọc bảng phải xem cả cách chia và cách tính chỉ số. Độ phủ ký tự đo tỷ lệ nội dung bằng chứng nằm trong hợp các đoạn truy xuất. Chỉ số theo span ở Mốc 1 yêu cầu một đoạn chứa trọn khoảng bằng chứng.")
    h("Document Page Chunk và truy nguyên")
    span("m2", 32, 38)
    h("Phân loại trang có chữ ảnh và bảng")
    span("m2", 41, 45)
    h("OCR và giới hạn của bản trích chữ")
    cp("m2", 52)
    p("Ở Mốc 1, phép thử DPI và chế độ phân đoạn dùng bốn trang sổ tay có bản tham chiếu cục bộ, gồm trang PDF 107, 109, 116 và 136. Cấu hình PSM 4, 200 dpi có CER gộp 24,89% và WER 32,21%. Riêng trang sơ đồ 136 có CER 77,91%. Những giá trị này phản ánh bốn trang của phép thử lịch sử và cách chuẩn hóa đã ghi trong hồ sơ M1-OCR. Chúng cho thấy kết quả gộp có thể che lỗi lớn ở một kiểu bố cục.")
    p("Ở Mốc 3, phạm vi kiểm tra được mở thành mười trang G0. Các bản chép chuẩn của gói mới đang chờ duyệt, nên lượt chạy hiện ghi số ký tự và thời gian xử lý. Bản tham chiếu của phép thử bốn trang và phiếu duyệt mới được lưu theo từng lần để tránh nhầm mức độ kiểm chứng.")
    cp("m3", 17)
    p("CER và WER cần được đọc cùng lỗi làm đổi ý nghĩa, như sai số tín chỉ, thời hạn, từ phủ định hoặc điều kiện ngoại lệ. Với trang có nhiều cột, thứ tự đọc cũng ảnh hưởng mạnh đến số phép sửa khi chấm. Cần chọn chế độ OCR sau khi xem bố cục và đối chiếu bản trích với ảnh gốc [6].")
    h("Giữ quan hệ giữa các ô trong bảng")
    span("m2", 47, 50)
    h("Nội dung hình và quan hệ không gian")
    span("m2", 54, 56)

    ch("CHIA ĐOẠN EMBEDDING VÀ CHỈ MỤC")
    h("Kích thước đoạn và phần chồng lấn")
    cp("m2", 58)
    p("Phép thử đầu ở Mốc 1 thay cửa sổ và phần chồng lấn theo ba cặp 250/40, 500/80 và 750/120. Đơn vị trong các cặp này là phần tử tách bằng khoảng trắng. Bảng giữ cách đo bằng chứng theo span của lần thử đó. Evidence Recall@5 đếm số span được chứa trọn trong ít nhất một chunk Top-5, còn cột đủ bằng chứng đếm câu có đủ mọi span trong Top-5.")
    span("m1", 58, 59)
    p("Nguồn M1-CH. Cùng bảy câu có đáp án và mười span của G0. Với dense, cửa sổ 250/40 đạt 10/10 span trong mẫu nhưng tạo 297 đoạn. Cửa sổ 750/120 giảm còn 111 đoạn và có những đoạn vượt giới hạn đầu vào. Thử nghiệm này giúp chọn cấu hình để kiểm tiếp, còn kết luận về kích thước phù hợp cần xét cả ngữ cảnh và chi phí xếp hạng.")
    h("Kiểm soát độ dài mà encoder nhận được")
    cp("m2", 59)
    span("m2", 60, 64)
    h("So sánh sáu cách chia và ngân sách ngữ cảnh")
    span("m3", 21, 26)
    p("Nguồn M3-CH. Các đoạn giữ vị trí trên tài liệu gốc để so độ phủ khi ranh giới thay đổi.", italic=True, first_line=False)
    cp("m3", 28)
    span("m3", 29, 33)
    p("Ngân sách 1.000 hoặc 2.000 token của phép thử này chỉ tính chuỗi đoạn nguồn và dấu phân cách bằng tokenizer Qwen3. Phần câu hỏi, nhãn nguồn và khung chat được tính thêm khi gọi mô hình. Bộ chọn duyệt theo thứ hạng, bỏ qua đoạn không còn vừa ngân sách và tiếp tục xét các đoạn sau. Quy tắc này không sử dụng đáp án chuẩn.")
    h("Embedding và đối chiếu trên cùng đầu vào")
    cp("m2", 66)
    p("Phép thử Mốc 1 dùng BGE-M3 ở trần 1.024 token và E5-small ở trần 512 token. Có 4/156 đoạn vượt trần BGE và 125/156 đoạn vượt trần E5. Chênh lệch truy xuất lúc đó chịu ảnh hưởng của cả model lẫn phần tài liệu bị cắt. Mốc 2 tạo lại tập 289 đoạn vừa 512 token của cả hai model để kiểm tra ảnh hưởng này.")
    cp("m2", 67)
    span("m2", 68, 71)
    p("Kết quả giúp thu hẹp cách diễn giải. Trên cùng đoạn vừa đầu vào, độ phủ của hai model gần nhau, dù thứ hạng và thời gian mã hóa vẫn khác. Các thuộc tính như pooling, tiền tố và dữ liệu huấn luyện tiếp tục ảnh hưởng kết quả. Bảy câu học vụ chỉ cung cấp quan sát cho mẫu đang xét.")
    h("Mở rộng so sánh sang sáu embedding")
    span("m3", 35, 40)
    p("Nguồn M3-EM. Tập 1.175 đoạn ở trần 128 token được dùng riêng để cả sáu bộ mã hóa nhận cùng nội dung. Vì tập đoạn khác với 289 đoạn ở Mốc 2, mức 0,771 của BGE-M3 trong bảng này không được dùng để kết luận model suy giảm so với 0,894 ở bảng trước. Kết quả có ý nghĩa so sánh các model trong cùng một bảng [2, 3, 15–18].")
    h("Vector store và tìm kiếm gần đúng")
    cp("m2", 74)
    p("Ở Mốc 1, FAISS IndexFlatIP và Qdrant local exact nhận cùng vector của 156 chunk G0. Hai cách lưu và tìm kiếm trả cùng Top-10 trong lượt đối chiếu, nên chất lượng retrieval bằng nhau. FAISS có p50 tìm kiếm 0,041 ms, Qdrant local 3,088 ms, với 50 lượt cho mỗi câu. Thời gian chỉ gồm tìm kiếm CPU. Phạm vi lưu trữ của hai hệ khác nhau, nên kích thước artifact cần đọc cùng phần payload và cơ chế lưu bền. Hồ sơ M1-VS lưu phép thử này.")
    p("Mốc 2 tiếp tục khảo sát tính gần đúng của thuật toán bằng Flat, HNSW và IVF trên cùng vector của 289 đoạn BGE-M3. Neighbor Recall so các ID hàng xóm với kết quả Flat, qua đó tách lỗi chỉ mục khỏi khả năng biểu diễn của embedding.")
    span("m2", 76, 79)
    p("Flat được giữ cho console vì corpus nhỏ và kết quả dễ đối chiếu. HNSW và IVF cho thấy cách tham số làm đổi số hàng xóm tìm lại. Việc chọn một database cho kho lớn còn cần đo lọc metadata, cập nhật, bộ nhớ và độ trễ với quy mô tương ứng. Phạm vi hiện có mới cung cấp số liệu trên máy cá nhân.")

    ch("TRUY XUẤT XẾP HẠNG VÀ SINH CÂU TRẢ LỜI")
    h("BM25 dense và kết hợp kết quả")
    span("m2", 82, 88)
    p("Sau phép thử RRF trên cửa sổ chung, Mốc 3 quay lại 156 đoạn G0 để so cách hợp điểm và reranker trên một tập ứng viên cố định.")
    cp("m3", 42, 43)
    h("Reranker và độ sâu ứng viên")
    span("m2", 90, 94)
    p("Phép thử Mốc 2 dùng một cross-encoder với đầu vào tối đa 1.024 token. Mốc 3 mở rộng sang ba model và ba độ sâu 10, 20, 50, giữ giới hạn 512 token mỗi cặp. Do cả tập đoạn và giới hạn khác nhau, các bảng được dùng để giải thích từng phép thử, không lấy chênh lệch giữa hai bảng làm mức cải thiện qua thời gian.")
    span("m3", 44, 48)
    p("Nguồn M3-RK. BGE v2-m3 đạt độ phủ 1,000 trong cả ba độ sâu đã thử trên bảy câu. Bảng trình bày độ sâu 20 để đối chiếu cùng số ứng viên. Hai độ sâu còn lại được lưu trong minh chứng. Chọn cấu hình dựa trên các câu này rồi đánh giá lại cũng trên chúng chỉ cho kết quả phát triển, nên cần tập test đã khóa để kiểm chứng lựa chọn [8, 19, 20].")
    h("Sinh câu trả lời có nguồn")
    span("m2", 97, 105)
    p("Qua trường hợp P006, có thể thấy kiểm tra ID giúp phát hiện nguồn nằm ngoài danh sách cho phép, còn đánh giá một phát biểu cần xem nội dung nguồn thực sự hỗ trợ ý nào. Các biến thể đầu ra ở phần tiếp theo được thử để kiểm tra thêm trích đoạn trước khi xuất câu trả lời.")
    h("Kiểm trích đoạn và xử lý câu thiếu căn cứ")
    span("m3", 50, 55)
    p("Nguồn M3-G. Ba biến thể chạy nối tiếp, mỗi biến thể mười câu, dùng lại cùng nguồn truy xuất đã lưu ở Mốc 2. Schema ràng buộc cấu trúc đầu ra qua Ollama [21]. Chỉ số ở bảng là hành vi xuất câu trả lời, từ chối và chặn lỗi. Các nhãn đúng nội dung, đầy đủ điều kiện và mức hỗ trợ của từng trích dẫn cần được chấm trên nguồn gốc.")

    ch("ĐÁNH GIÁ ỨNG DỤNG CONSOLE VÀ HƯỚNG TIẾP TỤC")
    h("Định nghĩa chỉ số và đơn vị so sánh")
    cp("m2", 108, 109)
    p("Trong thí nghiệm Mốc 1, bộ chấm theo span yêu cầu một chunk chứa trọn bằng chứng. Phép đo độ phủ ký tự ở Mốc 2 và 3 tính trên hợp các đoạn nên ghi nhận được cả trường hợp bằng chứng nằm ở hai chunk. Khi so số liệu cần dùng cùng định nghĩa, cùng snapshot, câu hỏi và giới hạn đầu vào. Neighbor Recall của chỉ mục được đọc riêng vì nó so hàng xóm vector với Flat.")
    span("m2", 110, 114)
    p("Với phần sinh, correctness đo mức đúng so với đáp án và nguồn, relevance xét mức trả lời đúng câu hỏi, còn faithfulness xét các phát biểu có được ngữ cảnh hỗ trợ hay không. RAGAs và ARES là các tài liệu tham khảo về đánh giá tự động. Khi sử dụng judge, cần lưu model, prompt, tiêu chí và đối chiếu một phần nhãn với người đọc nguồn [13, 14].")
    h("Ứng dụng console và quản lý tài nguyên")
    span("m2", 116, 123)
    cp("m3", 19)
    p("Lượt kiểm lại BM25 ngày 05/11/2026 xác nhận truy xuất và metadata nguồn vẫn hoạt động. Bộ kiểm thử phần mềm hiện có 163 trường hợp đạt. Kết quả này kiểm tra các hợp đồng và lỗi đã mô hình hóa trong mã, còn khả năng trả lời câu hỏi học vụ mới cần tập đánh giá riêng.")
    h("Chuẩn bị dữ liệu cho đánh giá độc lập")
    cp("m3", 57, 58)
    p("Mục tiêu bộ câu hỏi gồm ít nhất 15 câu thiếu căn cứ, 10 câu dùng bảng hoặc hình, 10 câu cần nhiều đoạn và 20 câu khác từ vựng nguồn. Các nhóm có thể giao nhau. Ít nhất 30% số câu cần do sinh viên tự viết và mọi câu dùng để chấm cần kiểm lại đáp án cùng vị trí bằng chứng. Những câu có cùng nội dung hoặc cùng điều khoản được nhóm trước khi chia dev và test để giảm rò rỉ.")
    p("Công cụ kiểm tra phiếu rà ID trùng, snapshot, trích đoạn, trạng thái người duyệt và nhóm dùng chung giữa hai tập. Câu pilot đã dùng để chọn cấu hình tiếp tục thuộc dev. Khi dữ liệu đủ điều kiện, khóa danh sách và mã băm, chọn cấu hình bằng dev rồi chạy đánh giá một lần trên test. Các mục gắn nhãn nhiều bằng chứng phải có các vị trí riêng biệt trong nguồn.")
    h("Kết luận từ các kết quả hiện có")
    p("Chuỗi thực nghiệm đã giúp làm rõ những quan hệ dễ bị bỏ qua khi chỉ xem sơ đồ RAG. Cách chia đoạn quyết định phần tài liệu mà embedding có thể đọc. Ngân sách ngữ cảnh quyết định phần bằng chứng thực sự đến được mô hình sinh. Chỉ mục gần đúng và reranker có thể thay đổi thứ hạng ở những vị trí khác nhau. Vì vậy mỗi phép so sánh cần giữ lại đầu vào và kết quả trung gian để giải thích nguyên nhân.")
    p("Trên tập học vụ nhỏ, dense tìm lại bằng chứng tốt hơn BM25 trong nhiều cấu hình, nhưng RRF chưa vượt nhánh dense. BGE v2-m3 đưa thêm bằng chứng vào Top-5, còn việc kiểm quote làm giảm số câu trả lời được xuất ra và vẫn chưa giải quyết P006. Các quan sát này dẫn đến ưu tiên tiếp theo là kiểm chất lượng đáp án và nguồn theo từng ý, cùng với mở rộng câu hỏi có người duyệt.")
    p("Phần còn cần hoàn thiện gồm bản chép chuẩn OCR, đánh giá cấu trúc bảng và nội dung hình, kiểm độ nhạy của kích thước và overlap trên mẫu rộng hơn, và phép thử độc lập cho cấu hình được chọn. Console hiện tạo được đường đi có thể quan sát từ câu hỏi đến nguồn và câu trả lời. Khi có bộ nhãn đầy đủ, báo cáo cuối sẽ có cơ sở đánh giá cả khả năng tìm bằng chứng, diễn giải điều kiện, dẫn nguồn và từ chối.")

    ah = add_heading(doc, "PHỤ LỤC A MINH CHỨNG VÀ CÁCH CHẠY")
    ah.paragraph_format.page_break_before = True
    p("Mã nguồn và số liệu đã tích lũy tới Mốc 3 được lưu tại commit e22282f trên nhánh cục bộ tim-hieu-rag-dot2 của repository https://github.com/franz08hmt/RAG. Commit này là mốc đối chiếu kỹ thuật cho bản tổng hợp. Liên kết GitHub cần được cập nhật sau khi nhánh được công bố.")
    table("Danh mục minh chứng theo phép thử", ["Mã", "Nội dung", "Vị trí trong docs/evidence"], [
        ["M1-OCR", "OCR bốn trang và DPI", "OCR_DPI_SENSITIVITY_20261007.md"],
        ["M1-CH", "Cửa sổ và overlap", "CHUNK_SIZE_EXACT_EVIDENCE_20260929.md"],
        ["M1-VS", "FAISS và Qdrant", "VECTOR_STORE_ABLATION_20261008.md"],
        ["M2-D0", "Snapshot G0", "m2/runs/corpus_snapshot.json"],
        ["M2-D1", "Vùng trang ảnh bảng", "m2/runs/input_artifacts_summary.json"],
        ["M2-E1", "Embedding và chỉ mục", "m2/runs/controlled_evaluation.json"],
        ["M2-G1", "Hai prompt sinh", "m2/runs/console_generation.json"],
        ["M2-C0/C1", "Console cold và warm", "m2/runs/console_cold.json và console_warm.json"],
        ["M3-CH", "Sáu cách chia đoạn", "m3/runs/chunking.json"],
        ["M3-EM", "Sáu embedding", "m3/runs/embeddings.json"],
        ["M3-RK", "Fusion và ba reranker", "m3/runs/ranking.json"],
        ["M3-G", "Ba cách sinh", "m3/runs/generation.json"],
        ["M3-OCR", "OCR mười trang", "m3/runs/ocr.json"],
        ["M3-Q", "Kiểm phiếu duyệt", "m3/runs/review.json"],
    ], [.85, 1.65, 3.8], "Mỗi hồ sơ giữ cấu hình, thời điểm hoặc run ID. Manifest Mốc 3 lưu SHA-256 của bản ghi gốc và bản xuất số liệu.")
    p("Mở PowerShell tại D:\\RAG\\rag-hcmute-dot2. Các lệnh sau dùng môi trường Python dự án và model đã có trên máy. Khi sinh câu trả lời, cần mở Ollama với qwen3:4b.")
    p('.\\scripts\\demo_m2.ps1 -Method bm25 -NoAnswer -Question "Thủ tục xin nghỉ học tạm thời được quy định ra sao?"', first_line=False)
    p('.\\scripts\\demo_m2.ps1 -Question "Thủ tục xin nghỉ học tạm thời được quy định ra sao?"', first_line=False)
    p("Hướng dẫn tái lập từng thí nghiệm nằm trong docs/MOC2_HUONG_DAN.md và docs/MOC3_HUONG_DAN.md. Tài liệu nguồn, bản chép, câu trả lời đầy đủ và phiếu có tên người duyệt được lưu cục bộ. Bản số liệu chia sẻ chỉ giữ các mã, cấu hình và thống kê cần đối chiếu.")

    ah = add_heading(doc, "PHỤ LỤC B ĐỐI CHIẾU YÊU CẦU CỦA GIẢNG VIÊN")
    ah.paragraph_format.page_break_before = True
    table("Nội dung đã khảo sát và phần cần kiểm tiếp", ["YC", "Minh chứng hiện có và giới hạn", "Mục"], [
        ["YC1", "Tên đề tài theo yêu cầu", "Bìa"],
        ["YC2", "Quy trình hai pha và các hướng tổ chức RAG", "1.3–1.4"],
        ["YC3", "Manifest PageText Chunk và nguồn dẫn", "2.1–2.2"],
        ["YC4", "Trang có chữ ảnh bảng và OCR, chờ bản chép mới và chấm nội dung hình", "2.3–2.6"],
        ["YC5", "Kích thước overlap sáu cách chia và ngân sách, cần mẫu độc lập", "3.1–3.3"],
        ["YC6", "Sáu embedding, có model tiếng Việt, trên cùng tập đoạn", "3.4–3.5"],
        ["YC7", "FAISS Qdrant exact và Flat HNSW IVF, quy mô còn nhỏ", "3.6"],
        ["YC8", "BM25 dense RRF và hợp điểm có trọng số", "4.1"],
        ["YC9", "Ba reranker ở ba độ sâu, có thống kê cắt đầu vào", "4.2"],
        ["YC10", "Câu hỏi nguồn JSON trích đoạn và từ chối, còn lỗi P006", "4.3–4.4"],
        ["YC11", "Chỉ số theo nguồn và câu, đang chuẩn bị test và nhãn chấm sinh", "5.1, 5.3"],
        ["YC12", "Console có nguồn và generator cục bộ", "5.2"],
        ["YC13", "Giải thích cơ chế qua thí nghiệm và trường hợp sai", "Toàn bài"],
    ], [.7, 4.6, 1.0], "Trạng thái cập nhật tới ngày 05/11/2026. Các mục còn chờ kiểm chứng được trình bày trong phần kết luận.")
    add_heading(doc, "Công cụ hỗ trợ", 2)
    cp("m3", 65)

    ah = add_heading(doc, "TÀI LIỆU THAM KHẢO")
    ah.paragraph_format.page_break_before = True
    span("m2", 146, 154)
    refs = [
        "[10] Y. Gao và cộng sự (2024). Retrieval-Augmented Generation for Large Language Models: A Survey. https://arxiv.org/abs/2312.10997",
        "[11] A. Asai và cộng sự (2024). Self-RAG: Learning to Retrieve, Generate, and Critique through Self-Reflection. https://arxiv.org/abs/2310.11511",
        "[12] Shi-Qi Yan và cộng sự (2024). Corrective Retrieval Augmented Generation. https://arxiv.org/abs/2401.15884",
        "[13] S. Es và cộng sự (2024). RAGAs: Automated Evaluation of Retrieval Augmented Generation. https://aclanthology.org/2024.eacl-demo.16/",
        "[14] J. Saad-Falcon và cộng sự (2024). ARES: An Automated Evaluation Framework for Retrieval-Augmented Generation Systems. https://aclanthology.org/2024.naacl-long.20/",
        "[15] BKAI. Vietnamese bi-encoder model card. https://huggingface.co/bkai-foundation-models/vietnamese-bi-encoder",
        "[16] Dang Van Tuan. Vietnamese Embedding model card. https://huggingface.co/dangvantuan/vietnamese-embedding",
        "[17] Intfloat. Multilingual E5 base model card. https://huggingface.co/intfloat/multilingual-e5-base",
        "[18] Sentence Transformers. Paraphrase multilingual MiniLM L12 v2 model card. https://huggingface.co/sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        "[19] Cross Encoder. mMARCO mMiniLMv2 L12 H384 v1 model card. https://huggingface.co/cross-encoder/mmarco-mMiniLMv2-L12-H384-v1",
        "[20] BAAI. BGE reranker base model card. https://huggingface.co/BAAI/bge-reranker-base",
        "[21] Ollama. Structured outputs. https://docs.ollama.com/capabilities/structured-outputs",
    ]
    for ref in refs:
        reference_paragraphs.append(p(ref, first_line=False))
    p("Phiên bản model thực chạy được ghi trong từng artifact. Nguồn PDF học vụ, URL gốc và mã băm nằm trong manifest của corpus.")
    # Keep paragraphs and short comparison tables readable across page breaks.
    for paragraph in doc.paragraphs[9:]:
        paragraph.paragraph_format.keep_together = True
    for t in doc.tables[1:]:
        for row in t.rows[:-1]:
            for cell in row.cells:
                for paragraph in cell.paragraphs:
                    paragraph.paragraph_format.keep_with_next = True
        for cell in t.rows[-1].cells:
            for paragraph in cell.paragraphs:
                paragraph.paragraph_format.keep_with_next = False
    for paragraph in reference_paragraphs:
        paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT
        paragraph.paragraph_format.line_spacing = 1
        paragraph.paragraph_format.space_after = Pt(3)
        paragraph.paragraph_format.keep_with_next = False
    # Make drawing IDs unique after importing different documents.
    for index, element in enumerate(doc.element.xpath("//wp:docPr"), 1):
        element.set("id", str(index))
    embedded = set(doc.element.xpath("//@r:embed | //@r:id | //@r:link"))
    for rid, relation in list(doc.part.rels.items()):
        if relation.reltype == RT.IMAGE and rid not in embedded:
            doc.part.drop_rel(rid)
    doc.core_properties.title = "Tìm hiểu Retrieval Augmented Generation (RAG)"
    doc.core_properties.subject = "Báo cáo tiến độ tổng hợp từ Mốc 1 đến Mốc 3"
    doc.save(args.output)
    audit = {
        "sources": {name: {"file": str(path.relative_to(ROOT)), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()} for name, path in SOURCES.items()},
        "output": str(args.output),
        "sha256": hashlib.sha256(args.output.read_bytes()).hexdigest(),
        "imported_elements": ledger,
        "tables": counters["Bảng"], "figures": counters["Hình"],
    }
    (ROOT / "artifacts/results/merged_docqa/merge_manifest.json").write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf8")
    print(args.output)
    print(f'Tables {counters["Bảng"]}, figures {counters["Hình"]}')


if __name__ == "__main__":
    main()
