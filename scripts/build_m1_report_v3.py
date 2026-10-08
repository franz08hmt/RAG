"""Build a new, evidence-linked Mốc 1 DOCX from the approved v2 cover template.

Every numerical result table is assembled from a raw metrics artifact at build time.
The source report is never overwritten; its SHA-256 is checked before authoring.
"""

from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

from docx import Document
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "reports/22110068_RAG_Bao_Cao_Tien_Do_Dot_1_v2.docx"
OUTPUT = ROOT / "reports/22110068_RAG_Bao_Cao_Tien_Do_Dot_1_v6.docx"
EXPECTED_TEMPLATE_SHA256 = "AE41A7D813F8C8A1EF4EA5E01A3528F99757D54B7AAA0AB8EFC898BBECA4D932"
TABLE_WIDTH_IN = 6.30

RAW = {
    "snapshot": ROOT / "data/manifests/corpus_snapshot.json",
    "chunk_bm25": ROOT / "artifacts/results/chunking_ablation/bm25_5da3bd4d5de54492_20260929T045502Z.json",
    "chunk_dense": ROOT / "artifacts/results/chunking_ablation/dense_5da3bd4d5de54492_20260929T045717Z.json",
    "hybrid": ROOT / "artifacts/results/hybrid_retrieval_ablation/hybrid_5da3bd4d5de54492_20261007T091540Z.json",
    "embedding": ROOT / "artifacts/results/embedding_model_ablation/embedding_5da3bd4d5de54492_20261008T125238Z.json",
    "vector_store": ROOT / "artifacts/results/vector_store_ablation/vector_store_5da3bd4d5de54492_20261008T125329Z.json",
    "reranker": ROOT / "artifacts/results/reranker_ablation/reranker_5da3bd4d5de54492_20261007T094759Z.json",
    "generation": ROOT / "artifacts/results/generation_pilot/generation_hybrid-rerank_5da3bd4d5de54492_20261008T124010Z.json",
}


def sha256(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def load_json(path: Path) -> dict:
    if not path.is_file():
        raise FileNotFoundError(f"Required raw evidence is missing: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def fmt_ratio(metric: dict) -> str:
    return f"{metric['hits']}/{metric['denominator']}"


def fmt_count_ratio(metric: dict) -> str:
    return f"{metric['count']}/{metric['denominator']}"


def fmt_decimal(value: float, digits: int = 3) -> str:
    return f"{value:.{digits}f}".replace(".", ",")


def set_run_font(run, size: int = 12, *, bold: bool | None = None, italic: bool | None = None) -> None:
    run.font.name = "Times New Roman"
    run.font.size = Pt(size)
    run.font.color.rgb = RGBColor(0, 0, 0)
    if bold is not None:
        run.bold = bold
    if italic is not None:
        run.italic = italic
    rpr = run._element.get_or_add_rPr()
    fonts = rpr.rFonts
    if fonts is None:
        fonts = OxmlElement("w:rFonts")
        rpr.insert(0, fonts)
    for attr in ("ascii", "hAnsi", "eastAsia", "cs"):
        fonts.set(qn(f"w:{attr}"), "Times New Roman")


def set_cell_margins(cell, top: int = 55, start: int = 65, bottom: int = 55, end: int = 65) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    margins = tc_pr.first_child_found_in("w:tcMar")
    if margins is None:
        margins = OxmlElement("w:tcMar")
        tc_pr.append(margins)
    for edge, value in (("top", top), ("start", start), ("bottom", bottom), ("end", end)):
        node = margins.find(qn(f"w:{edge}"))
        if node is None:
            node = OxmlElement(f"w:{edge}")
            margins.append(node)
        node.set(qn("w:w"), str(value))
        node.set(qn("w:type"), "dxa")


def set_table_borders(table, *, visible: bool = True) -> None:
    tbl_pr = table._tbl.tblPr
    borders = tbl_pr.first_child_found_in("w:tblBorders")
    if borders is None:
        borders = OxmlElement("w:tblBorders")
        tbl_pr.append(borders)
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        node = borders.find(qn(f"w:{edge}"))
        if node is None:
            node = OxmlElement(f"w:{edge}")
            borders.append(node)
        if visible:
            node.set(qn("w:val"), "single")
            node.set(qn("w:sz"), "6")
            node.set(qn("w:space"), "0")
            node.set(qn("w:color"), "000000")
        else:
            node.set(qn("w:val"), "nil")


def set_repeat_table_header(row) -> None:
    tr_pr = row._tr.get_or_add_trPr()
    repeat = OxmlElement("w:tblHeader")
    repeat.set(qn("w:val"), "true")
    tr_pr.append(repeat)


def prevent_row_split(row) -> None:
    tr_pr = row._tr.get_or_add_trPr()
    cant_split = OxmlElement("w:cantSplit")
    tr_pr.append(cant_split)


def add_p(doc, text: str = "", *, size: int = 12, bold: bool = False, italic: bool = False,
          align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line: bool = True, keep_with_next: bool = False):
    text = text.replace("`", "")
    paragraph = doc.add_paragraph()
    paragraph.alignment = align
    paragraph.paragraph_format.space_after = Pt(5)
    paragraph.paragraph_format.line_spacing = 1.12
    paragraph.paragraph_format.keep_with_next = keep_with_next
    if first_line and align == WD_ALIGN_PARAGRAPH.JUSTIFY:
        paragraph.paragraph_format.first_line_indent = Inches(0.28)
    run = paragraph.add_run(text)
    set_run_font(run, size, bold=bold, italic=italic)
    return paragraph


def add_bullet(doc, text: str):
    paragraph = doc.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    paragraph.paragraph_format.left_indent = Inches(0.28)
    paragraph.paragraph_format.first_line_indent = Inches(-0.18)
    paragraph.paragraph_format.space_after = Pt(3)
    paragraph.paragraph_format.line_spacing = 1.08
    run = paragraph.add_run("• " + text)
    set_run_font(run, 12)
    return paragraph


def add_heading(doc, text: str, level: int = 1, *, page_break: bool = False):
    if page_break:
        doc.add_page_break()
    paragraph = doc.add_heading(text, level=level)
    paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT
    paragraph.paragraph_format.keep_with_next = True
    paragraph.paragraph_format.space_before = Pt(8 if level == 1 else 5)
    paragraph.paragraph_format.space_after = Pt(4)
    for run in paragraph.runs:
        set_run_font(run, 14 if level == 1 else 13, bold=True)
    return paragraph


def add_caption(doc, text: str, *, align=WD_ALIGN_PARAGRAPH.CENTER):
    paragraph = doc.add_paragraph()
    paragraph.alignment = align
    paragraph.paragraph_format.space_before = Pt(3)
    paragraph.paragraph_format.space_after = Pt(4)
    paragraph.paragraph_format.keep_with_next = True
    run = paragraph.add_run(text)
    set_run_font(run, 12, bold=True)
    return paragraph


def add_data_table(doc, caption: str, headers: list[str], rows: list[list[str]], widths: list[float],
                   run_note: str, *, font_size: int = 12):
    if abs(sum(widths) - TABLE_WIDTH_IN) > 0.02:
        raise ValueError(f"Table columns must total {TABLE_WIDTH_IN} inches: {widths}")
    add_caption(doc, caption)
    table = doc.add_table(rows=1, cols=len(headers))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    set_table_borders(table)
    for index, width in enumerate(widths):
        table.columns[index].width = Inches(width)
    header = table.rows[0]
    set_repeat_table_header(header)
    prevent_row_split(header)
    for index, value in enumerate(headers):
        cell = header.cells[index]
        cell.width = Inches(widths[index])
        cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
        set_cell_margins(cell)
        cell.text = value
        for paragraph in cell.paragraphs:
            paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            paragraph.paragraph_format.space_after = Pt(0)
            paragraph.paragraph_format.line_spacing = 1.0
            for run in paragraph.runs:
                set_run_font(run, font_size, bold=True)
    for row_values in rows:
        row = table.add_row()
        prevent_row_split(row)
        for index, value in enumerate(row_values):
            cell = row.cells[index]
            cell.width = Inches(widths[index])
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            set_cell_margins(cell)
            cell.text = str(value)
            for paragraph in cell.paragraphs:
                paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT if index == 0 else WD_ALIGN_PARAGRAPH.CENTER
                paragraph.paragraph_format.space_after = Pt(0)
                paragraph.paragraph_format.line_spacing = 1.0
                for run in paragraph.runs:
                    set_run_font(run, font_size)
    note = add_p(doc, run_note, size=12, italic=True, align=WD_ALIGN_PARAGRAPH.LEFT, first_line=False)
    note.paragraph_format.space_after = Pt(8)
    return table


def add_flow_diagram(doc, caption: str, stages: list[tuple[str, str]], note: str):
    add_caption(doc, caption)
    table = doc.add_table(rows=0, cols=1)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    table.columns[0].width = Inches(TABLE_WIDTH_IN)
    set_table_borders(table, visible=False)
    for index, (title, detail) in enumerate(stages):
        row = table.add_row()
        prevent_row_split(row)
        cell = row.cells[0]
        cell.width = Inches(TABLE_WIDTH_IN)
        cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
        set_cell_margins(cell, top=75, bottom=75, start=120, end=120)
        set_table_borders_for_cell(cell)
        paragraph = cell.paragraphs[0]
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        paragraph.paragraph_format.space_after = Pt(0)
        paragraph.paragraph_format.line_spacing = 1.0
        run = paragraph.add_run(title)
        set_run_font(run, 12, bold=True)
        run = paragraph.add_run("\n" + detail)
        set_run_font(run, 12)
        if index < len(stages) - 1:
            arrow = table.add_row()
            prevent_row_split(arrow)
            arrow_cell = arrow.cells[0]
            arrow_cell.width = Inches(TABLE_WIDTH_IN)
            set_cell_margins(arrow_cell, top=0, bottom=0)
            paragraph = arrow_cell.paragraphs[0]
            paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            paragraph.paragraph_format.space_after = Pt(0)
            run = paragraph.add_run("↓")
            set_run_font(run, 12, bold=True)
    add_p(doc, note, size=12, italic=True, align=WD_ALIGN_PARAGRAPH.LEFT, first_line=False)


def set_table_borders_for_cell(cell) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    borders = tc_pr.first_child_found_in("w:tcBorders")
    if borders is None:
        borders = OxmlElement("w:tcBorders")
        tc_pr.append(borders)
    for edge in ("top", "left", "bottom", "right"):
        node = OxmlElement(f"w:{edge}")
        node.set(qn("w:val"), "single")
        node.set(qn("w:sz"), "8")
        node.set(qn("w:space"), "0")
        node.set(qn("w:color"), "000000")
        borders.append(node)


def remove_old_body_and_update_cover(doc) -> None:
    body = doc._element.body
    children = list(body)
    cover_break = None
    for child in children:
        if child.tag == qn("w:p"):
            p_pr = child.find(qn("w:pPr"))
            if p_pr is not None and p_pr.find(qn("w:sectPr")) is not None:
                cover_break = child
                break
    if cover_break is None:
        raise RuntimeError("Cover section break was not found; refusing to modify template structure.")
    after_cover = False
    for child in list(body):
        if child is cover_break:
            after_cover = True
            continue
        if after_cover and child.tag != qn("w:sectPr"):
            body.remove(child)

    paragraphs = list(doc.paragraphs)
    for paragraph in paragraphs:
        text = paragraph.text.strip()
        if text in {
            "BÁO CÁO TIẾN ĐỘ ĐỒ ÁN IT PROJECT",
            "Báo cáo tiến độ Đợt 1",
            "Hướng ứng dụng: Tra cứu và hỏi đáp trên tài liệu học vụ",
        }:
            paragraph._element.getparent().remove(paragraph._element)
        elif text == "NGHIÊN CỨU, THIẾT KẾ VÀ HIỆN THỰC HÓA HỆ THỐNG RETRIEVAL-AUGMENTED GENERATION (RAG)":
            paragraph.text = "Tìm hiểu Retrieval Augmented Generation (RAG)"
            paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            paragraph.paragraph_format.space_before = Pt(8)
            paragraph.paragraph_format.space_after = Pt(8)
            for run in paragraph.runs:
                set_run_font(run, 14, bold=True)
        elif text.startswith("TP. Hồ Chí Minh,"):
            paragraph.text = "Tháng 10 năm 2026"
            paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            for run in paragraph.runs:
                set_run_font(run, 12, italic=True)

    # Preserve the template's six metadata rows and monochrome cover layout.
    if not doc.tables:
        raise RuntimeError("Cover metadata table is missing from the source template.")
    cover_table = doc.tables[0]
    for row in cover_table.rows:
        for cell in row.cells:
            for paragraph in cell.paragraphs:
                for run in paragraph.runs:
                    set_run_font(run, 12, bold=run.bold)


def get_chunk_rows() -> tuple[list[list[str]], list[str]]:
    paths = [RAW["chunk_bm25"], RAW["chunk_dense"]]
    rows: list[list[str]] = []
    for path, label in ((paths[0], "BM25"), (paths[1], "Dense BGE-M3")):
        data = load_json(path)
        for config in data["configs"]:
            exact = config["retrieval"]["exact_evidence"]
            rows.append([
                f"{label}\n{config['chunk_tokens']}/{config['overlap_tokens']}",
                str(config["chunk_count"]),
                fmt_ratio(exact["evidence_span_recall_at_k"]),
                fmt_ratio(exact["complete_evidence_hit_at_k"]),
                fmt_decimal(exact["first_evidence_mrr_at_top_k"]["value"]),
            ])
    return rows, [path.stem for path in paths]


def build_report(doc) -> None:
    snapshot = load_json(RAW["snapshot"])
    hybrid = load_json(RAW["hybrid"])
    embedding = load_json(RAW["embedding"])
    stores = load_json(RAW["vector_store"])
    reranker = load_json(RAW["reranker"])
    generation = load_json(RAW["generation"])

    totals = snapshot["totals"]
    doc.core_properties.title = "Tìm hiểu Retrieval Augmented Generation (RAG) — Báo cáo tiến độ Mốc 1"
    doc.core_properties.subject = "Báo cáo tìm hiểu và tiến độ thực nghiệm RAG cho môn IT Project"
    doc.core_properties.author = "Huỳnh Minh Tài"

    add_heading(doc, "TÓM TẮT PHẠM VI BÁO CÁO", 1)
    add_p(doc, "Tài liệu ghi lại cách hiểu về RAG và những phần đã khảo sát, hiện thực, đo thử trong Mốc 1 của đề tài được giao. Trọng tâm không phải trình bày một sản phẩm hoàn tất, mà là giải thích từng khâu của hệ thống hỏi đáp tài liệu học vụ: dữ liệu đi vào từ đâu, được chuyển thành đơn vị tra cứu như thế nào, các phương án retrieval khác nhau ra sao, kết quả đã đo cho thấy điều gì và phần nào chưa đủ căn cứ để kết luận.")
    add_p(doc, "Để tránh lẫn kế hoạch với kết quả, các bảng số liệu trong báo cáo được dựng trực tiếp từ JSON của từng lượt chạy. Những phép đo hiện tại dùng snapshot G0 lịch sử, 10 câu development (7 câu có đáp án, 3 câu ngoài dữ liệu) và 10 đoạn evidence được gắn nhãn. Đây là tập nhỏ để tìm lỗi và so cấu hình, không phải holdout độc lập hay mẫu đại diện cho toàn bộ câu hỏi sinh viên.")
    add_p(doc, "Mã nguồn công khai nằm tại github.com/franz08hmt/RAG; nhánh đang làm là `tim-hieu-rag-dot2`, phát triển từ commit nền `7a2fb49`. Báo cáo và các thay đổi hiện tại đang ở workspace cục bộ, chưa push và chưa có PR cho nhánh này. Tệp nguồn, text trích xuất và raw artifacts vẫn được giữ ngoài Git theo quy tắc dữ liệu của project.", italic=False)

    add_heading(doc, "CHƯƠNG 1. BÀI TOÁN ỨNG DỤNG VÀ PHẠM VI", 1, page_break=True)
    add_heading(doc, "1.1. Nhu cầu cần xử lý", 2)
    add_p(doc, "Trong tra cứu học vụ, người học thường đặt câu hỏi bằng ngôn ngữ tự nhiên, còn câu trả lời nằm rải rác trong quy chế, hướng dẫn hoặc sổ tay. Người hỏi cần biết không chỉ nội dung mà cả điều khoản/trang để tự kiểm tra. Tìm theo từ khóa có thể giúp mở đúng tài liệu nhưng người dùng vẫn phải đọc và tổng hợp; một LLM không được nối với kho nguồn có thể trả lời trôi chảy mà không chứng minh được căn cứ.")
    add_p(doc, "Bài toán của PoC được giới hạn thành hỏi đáp dựa trên một kho tài liệu học vụ HCMUTE. Ví dụ: truy vấn về điều kiện rút học phần cần tìm được đúng mục quy định, đưa đoạn đó cùng tên văn bản và vị trí nguồn đến bước sinh câu trả lời. Nếu người hỏi xin lịch thi cụ thể của một lớp trong tuần tới mà kho chỉ có quy chế tĩnh, hệ thống phải nhận ra dữ liệu đó không có trong snapshot thay vì dự đoán.")
    add_heading(doc, "1.2. Đầu vào, đầu ra và ranh giới", 2)
    add_bullet(doc, "Đầu vào: PDF/văn bản học vụ đã xác minh nguồn, phiên bản và mã băm; câu hỏi tiếng Việt; metadata trang, chương/điều và phương thức trích xuất.")
    add_bullet(doc, "Đầu ra mong muốn: câu trả lời ngắn; một hoặc nhiều chunk evidence; citation có thể resolve đến văn bản và trang/điều; trạng thái chưa đủ căn cứ khi nguồn không hỗ trợ.")
    add_bullet(doc, "Ngoài phạm vi hiện tại: chatbot hội thoại mở, truy cập dữ liệu cá nhân, tra lịch/học phí động, tư vấn pháp lý/học vụ như nguồn có hiệu lực nếu chưa xác minh phiên bản.")
    add_heading(doc, "1.3. Tiêu chí kỹ thuật của một câu trả lời dùng được", 2)
    add_p(doc, "Một câu trả lời đúng định dạng nhưng dẫn sai trang vẫn không đạt yêu cầu tra cứu. Vì vậy cần phân biệt ba điều: retriever có đưa đúng evidence vào candidate pool không; generator có diễn đạt đúng nội dung evidence không; citation có chỉ đúng nguồn và thực sự hỗ trợ khẳng định không. Với câu cần nhiều điều kiện, phải lấy đủ các span chứ không chỉ một chunk gần nghĩa. Trường hợp ngoài phạm vi cũng phải được đánh giá, vì refusal là một kết quả có chủ đích chứ không phải lỗi giao diện.")

    add_heading(doc, "CHƯƠNG 2. CƠ SỞ VÀ CÁCH HIỂU VỀ RAG", 1, page_break=True)
    add_heading(doc, "2.1. RAG là kiến trúc truy xuất rồi sinh", 2)
    add_p(doc, "Retrieval-Augmented Generation kết hợp một hệ thống truy xuất với một mô hình sinh. Trước khi có câu hỏi, tài liệu được làm sạch, chia thành chunk và lập chỉ mục; khi chạy, câu hỏi được dùng để chọn các đoạn liên quan, rồi LLM nhận câu hỏi cùng ngữ cảnh để tạo câu trả lời. Tên gọi RAG mô tả cách kết nối các bước, không phải một vector database, một model embedding hay một LLM cụ thể.")
    add_p(doc, "Bài báo nền tảng của Lewis và cộng sự nghiên cứu RAG cho tác vụ NLP tri thức và fine-tune retriever cùng generator trong thiết lập của paper; bộ nhớ phi tham số là chỉ mục tài liệu, còn generator là mô hình seq2seq. Cách đó không nên bị giản lược thành “paper chỉ đưa PDF vào prompt”. PoC hiện tại thì không fine-tune model: embedding, reranker và LLM được dùng sẵn, còn corpus được lập chỉ mục ngoài tham số của LLM [1].")
    add_heading(doc, "2.2. Luồng hai pha", 2)
    add_flow_diagram(doc, "Hình 2.1. Luồng offline và query-time của PoC", [
        ("1. Nguồn và manifest", "PDF đã xác minh; version/hash; trạng thái sử dụng."),
        ("2. Trích xuất và phân loại", "Native text; OCR tùy chọn cho trang ảnh; bảng/hình cần kiểm tra riêng."),
        ("3. Chunk và lưu provenance", "Chunk có ID, section, PDF page và phương thức extraction."),
        ("4. Lập chỉ mục", "BM25 cho lexical retrieval; FAISS/Qdrant cho dense vectors."),
        ("5. Truy vấn", "Câu hỏi → BM25/dense → candidate list → RRF/rerank nếu bật."),
        ("6. Context và generation", "Top evidence + metadata vào prompt; LLM local trả lời hoặc abstain."),
        ("7. Kiểm chứng", "Resolve citation, đọc lại nguồn và đánh giá retrieval/generation riêng."),
    ], "Sơ đồ thể hiện các module đang khảo sát; không hàm ý OCR tổng quát, refusal đạt yêu cầu hay citation semantics đã được xác nhận.")
    add_p(doc, "Ingestion chạy khi thêm/cập nhật tài liệu; query-time chạy theo câu hỏi. Phân biệt hai luồng giúp khoanh vùng lỗi: chữ sai trong PDF trích xuất thuộc ingestion, đoạn phù hợp không được tìm thấy thuộc retrieval, còn câu trả lời suy diễn vượt nguồn thuộc generation.")
    add_heading(doc, "2.3. Search, IR và RAG", 2)
    add_p(doc, "Search là tên gọi rộng của thao tác tìm kiếm. Information Retrieval (IR) nghiên cứu cách biểu diễn, truy vấn và xếp hạng thông tin; BM25 là lexical IR, còn dense retrieval dùng vector biểu diễn ngữ nghĩa. RAG sử dụng kết quả IR làm ngữ cảnh cho generation. Vì vậy không chính xác khi đồng nhất IR với tìm kiếm ngữ nghĩa hoặc nói BM25 không thuộc IR.")
    add_heading(doc, "2.4. Naive, Advanced, Modular và Agentic RAG", 2)
    add_p(doc, "Naive RAG dùng một đường đi đơn giản: chia chunk, embedding, lấy Top-k và đưa vào LLM. Nó dễ kiểm chứng nhưng nhạy với cách chunk, chất lượng query và ngữ cảnh thiếu. Advanced RAG thêm cải thiện ở từng đoạn: query rewriting/HyDE trước truy xuất; hybrid BM25+dense và metadata filter khi truy xuất; reranking, loại trùng hoặc context compression sau truy xuất. Mỗi bước mới phải được đo riêng để biết lợi ích đến từ đâu, vì thêm thành phần cũng có thể làm giảm recall, tăng độ trễ hoặc che lỗi.")
    add_p(doc, "Modular RAG tổ chức ingestion, retrieval, reranker, context builder, generator và evaluator thành module có thể thay thế. Agentic RAG cho agent chọn truy vấn lại, gọi tool hoặc tìm tiếp; linh hoạt hơn nhưng khó tái lập và cần kiểm soát vòng lặp. Self-RAG đưa cơ chế tự đánh giá việc retrieve và mức hỗ trợ của evidence vào generation; CRAG đánh giá chất lượng retrieval rồi có thể sửa truy vấn/nguồn. Các hướng này được đưa vào phần tìm hiểu, chưa được hiện thực trong PoC [2, 6, 7].")
    add_heading(doc, "2.5. Ba điểm có thể làm câu trả lời sai", 2)
    add_bullet(doc, "Nguồn/extraction: văn bản mới thay đổi nhưng corpus cũ; số/điều OCR sai; thứ tự cột bị đảo.")
    add_bullet(doc, "Retrieval/context: query không khớp từ khóa; vector gần nghĩa nhưng sai điều khoản; chunk bị cắt hoặc thiếu một span cần thiết.")
    add_bullet(doc, "Generation/citation: LLM thêm điều kiện không có trong context; citation ID hợp lệ nhưng không hỗ trợ câu; mô hình không từ chối khi thiếu nguồn.")

    add_heading(doc, "CHƯƠNG 3. DỮ LIỆU VÀ CẤU TRÚC INGESTION", 1, page_break=True)
    add_heading(doc, "3.1. Corpus, nguồn và phiên bản", 2)
    add_p(doc, "Corpus phải được quản lý như một tập nguồn có thể truy nguyên, không phải tập PDF gom tùy ý. Manifest giữ document_id, tên/loại nguồn, URL/cơ quan ban hành, ngày lấy, SHA-256, trạng thái và ghi chú quyền sử dụng. Snapshot ghim corpus cùng cấu hình chunk/extraction để các phép thử so sánh cùng đầu vào. PDF gốc và toàn văn trích xuất được để ngoài Git.")
    corpus_rows = []
    for item in snapshot["documents"]:
        corpus_rows.append([item["document_id"], str(item["page_count"]), str(item["chunk_count"]), "Có" if item.get("dieu_structured") else "Không"])
    add_data_table(doc, "Bảng 3.1. Quy mô snapshot G0", ["Document ID", "Trang PDF", "Chunks", "Nhận diện Điều"], corpus_rows, [2.75, 0.9, 0.9, 1.75], f"Snapshot `{snapshot['snapshot_id']}`; cấu hình {snapshot['config']['chunk_tokens']}/{snapshot['config']['overlap_tokens']}; nguồn số liệu: `data/manifests/corpus_snapshot.json`.")
    add_p(doc, f"Snapshot có {totals['document_count']} tài liệu, {totals['page_count']} trang và {totals['chunk_count']} chunks. Đây là baseline lịch sử, không được xem là danh mục đầy đủ hay là phiên bản quy định hiện hành.")
    add_heading(doc, "3.2. Document Class và cách xử lý đầu vào", 2)
    add_p(doc, "Một file có thể chứa nhiều layout: văn xuôi có cấu trúc Chương/Điều, hướng dẫn ngắn, bảng, trang scan hoặc sơ đồ. Xử lý theo lớp: native extraction phù hợp khi text layer đọc được; OCR chỉ dành cho trang ảnh và cần so với ảnh gốc; bảng cần giữ liên hệ tiêu đề cột–hàng; hình cần OCR vùng chữ hoặc mô tả được kiểm duyệt, vì OCR đơn thuần không hiểu quan hệ không gian.")
    add_p(doc, "Đã có thử OCR cục bộ trên bốn trang có reference, nhiều DPI/PSM. Trên đúng mẫu này PSM 4 ở 200 DPI có CER/WER gộp 24,89%/32,21%, nhưng trang sơ đồ vẫn có lỗi cao; cấu hình tốt theo tổng không đồng nghĩa đúng cho mọi layout. Tesseract cần được xem là recognizer chứ không phải bộ hiểu hình. G0 vẫn native-only; QĐ 3116/2025 là scan có text layer nhiễu và chưa có transcript vàng, nên chưa được dùng cho retrieval/generation. Chi tiết tại `docs/evidence/OCR_DPI_SENSITIVITY_20261007.md` và `docs/evidence/QD3116_SCAN_TEXT_LAYER_AUDIT_20261008.md` [10].")
    add_heading(doc, "3.3. Document, Page và Chunk", 2)
    add_p(doc, "Document đại diện cho một nguồn/phiên bản; Page lưu văn bản sau extraction cùng số trang PDF; Chunk là đơn vị được tìm kiếm và có thể trở thành evidence. Chunk cần giữ ID, document hash, PDF page start/end, printed page nếu đã xác minh, section_path, policy chia, extraction_method và offset/token span. Citation nên trỏ chunk ID trước, rồi resolve ra tên văn bản, trang và điều. Metadata cấu trúc được lưu riêng; context prefix ngắn có thể đưa tên văn bản/chương/điều vào embedding nhưng không thay cho provenance.")
    add_heading(doc, "3.4. Chunking và lựa chọn ranh giới", 2)
    chunking_paragraph = add_p(doc, "Fixed window dễ triển khai nhưng có thể cắt giữa tiêu đề và điều kiện. Recursive splitting ưu tiên dấu đoạn/câu rồi mới cắt cứng, hữu ích làm baseline tổng quát. Section-aware ưu tiên ranh giới Chương/Điều/Khoản, phù hợp văn bản quy chế nhưng phụ thuộc nhận diện heading. Chunk bảng phải giữ header và nhóm hàng; semantic chunking có thể bám chủ đề nhưng dùng thêm model và ranh giới khó giải thích. Chunk nhỏ tăng số index entries nhưng dễ tìm evidence cụ thể; chunk lớn giữ ngữ cảnh song có thể nhiễu và vượt giới hạn encoder.")
    chunking_paragraph.paragraph_format.keep_together = True
    chunk_rows, chunk_runs = get_chunk_rows()
    add_data_table(doc, "Bảng 3.2. So sánh kích thước chunk bằng exact evidence", ["Retriever / chunk-overlap", "Số chunk", "Evidence Recall@5", "Đủ evidence Hit@5", "MRR@10"], chunk_rows, [1.9, 0.8, 1.15, 1.3, 1.15], f"Run IDs: `{chunk_runs[0]}`; `{chunk_runs[1]}`. Snapshot G0, 7 câu answerable/10 span; raw JSON trong `artifacts/results/chunking_ablation/`.")
    add_p(doc, "Trong mẫu này dense đạt độ phủ evidence cao nhất ở chunk 250/40 nhưng tạo nhiều chunk hơn; với 500/80 và 750/120, một số span không lên Top-5 và một số chunk vượt giới hạn BGE-M3 1.024 token. BM25 có kết quả khá ổn định hơn giữa ba cỡ nhưng thấp hơn dense trên pilot. Vì mẫu nhỏ, chưa đo đủ chi phí reranking và chưa có holdout, 500/80 vẫn được giữ làm cấu hình baseline thay vì tuyên bố 250/40 tối ưu.")

    add_heading(doc, "CHƯƠNG 4. RETRIEVAL, EMBEDDING VÀ ĐÁNH GIÁ PoC", 1, page_break=True)
    add_heading(doc, "4.1. Các metric và quy tắc so sánh", 2)
    add_p(doc, "Evidence-span Recall@k đo phần trăm span gold xuất hiện trong Top-k. Complete-evidence Hit@k đếm câu mà mọi span bắt buộc đều có mặt. MRR@k phản ánh thứ hạng của evidence liên quan đầu tiên; MRR cao không đảm bảo lấy đủ bằng chứng. Chỉ số phải nêu đơn vị và mẫu số. Tập development dùng để phân tích, không dùng để tuyên bố kết quả độc lập.")
    retrieval_rows = []
    for key, label in (("bm25", "BM25"), ("dense", "Dense BGE-M3"), ("hybrid_rrf", "Hybrid RRF (k=60)")):
        m = hybrid["methods"][key]["metrics"]
        retrieval_rows.append([label, fmt_ratio(m["evidence_span_recall_at_5"]), fmt_ratio(m["complete_evidence_hit_at_5"]), fmt_decimal(m["first_evidence_mrr_at_10"]["value"])])
    add_data_table(doc, "Bảng 4.1. So sánh retrieval trên cùng development pilot", ["Phương pháp", "Evidence Recall@5", "Đủ evidence Hit@5", "MRR@10"], retrieval_rows, [2.25, 1.35, 1.45, 1.25], f"Run ID: `{RAW['hybrid'].stem}`; snapshot {hybrid['snapshot_id']}; 7 câu answerable/10 span; đây là retrieval-only.")
    add_p(doc, "Dense dẫn đầu trên bộ pilot, BM25 hữu ích với token/mã nguyên văn, còn RRF không tự động vượt nhánh tốt nhất. Đây là kết quả cụ thể của tập hiện có; không suy rộng đến mọi truy vấn, corpus hay model. Candidate Top-20 của Dense/RRF chứa toàn bộ spans trong mẫu, cho phép đánh giá bước reranking riêng.")
    add_heading(doc, "4.2. Embedding model: đo trên chunk hiện tại", 2)
    embedding_rows = []
    for model in embedding["models"]:
        m = model["metrics"]
        prefix = "query:/passage:" if model["query_prefix"] else "không prefix"
        embedding_rows.append([
            model["model_id"],
            f"{model['embedding_dim']} chiều; {model['max_seq_length']} token; {prefix}",
            f"{fmt_ratio(m['evidence_span_recall_at_5'])}; {fmt_ratio(m['complete_evidence_hit_at_5'])}; {fmt_decimal(m['first_evidence_mrr_at_10']['value'])}",
            f"{model['chunks_over_limit']}/{embedding['chunk_count']}",
        ])
    add_data_table(doc, "Bảng 4.2. Hai embedding đã chạy trên G0", ["Model", "Cấu hình đầu vào", "Recall@5 / Hit@5 / MRR@10", "Chunk vượt limit"], embedding_rows, [1.75, 1.65, 1.85, 1.05], f"Run ID: `{RAW['embedding'].stem}`; 10 câu development (7 answerable), 10 evidence spans.")
    add_p(doc, "BGE-M3 xếp nhiều span vào Top-5 hơn E5-small trong phép thử này. Nhưng E5-small bị giới hạn 512 token nên 125/156 chunk vượt ngưỡng, còn BGE-M3 với cấu hình project 1.024 token có 4/156. Chênh lệch vừa phản ánh embedding vừa phản ánh tương tác giữa max length và chunk policy; không thể gọi đây là kết luận “BGE tốt hơn cho tiếng Việt” nói chung. Mục tiêu khảo sát sáu model chưa đạt. VN-MTEB là benchmark tham khảo hữu ích, song không thay các câu hỏi học vụ do người học xác minh [5, 8].")
    add_heading(doc, "4.3. Vector store: chất lượng truy xuất và vận hành", 2)
    store_rows = []
    for store in stores["stores"]:
        m = store["metrics"]
        store_rows.append([
            store["store"],
            f"{fmt_ratio(m['evidence_span_recall_at_5'])}; {fmt_ratio(m['complete_evidence_hit_at_5'])}; {fmt_decimal(m['first_evidence_mrr_at_10']['value'])}",
            f"{fmt_decimal(store['query_p50_ms'], 3)} / {fmt_decimal(store['query_p95_ms'], 3)} ms",
            f"{fmt_decimal(store['build_ms'], 3)} ms; {store['artifact_bytes']:,} B".replace(",", "."),
        ])
    add_data_table(doc, "Bảng 4.3. FAISS và Qdrant local với cùng vector exact", ["Store", "Recall@5 / Hit@5 / MRR@10", "Query p50 / p95", "Build / artifact"], store_rows, [2.05, 1.55, 1.35, 1.35], f"Run ID: `{RAW['vector_store'].stem}`; 50 lần/query × 7 câu; thời gian search CPU, không gồm embedding.")
    add_p(doc, "Top-10 của Qdrant khớp FAISS trong phép đối chiếu 100% nên các metric retrieval bằng nhau. FAISS là baseline gọn in-memory; Qdrant local lưu payload/persistence. Artifact size không so sánh ngang vì phạm vi lưu trữ khác nhau; p50/p95 ở 156 vector là microbenchmark chứ không phải thông lượng production. Chưa thử IVF/HNSW, Chroma hay Milvus. Không dùng Pinecone/cloud do phạm vi dữ liệu và chi phí [9, 11].")
    add_heading(doc, "4.4. Reranker: chỉ xếp lại candidate", 2)
    rerank_rows = []
    for key, label in (("dense", "Dense BGE-M3"), ("hybrid_rrf", "Hybrid RRF")):
        method = reranker["methods"][key]
        before, after, coverage = method["before_reranking"], method["after_reranking"], method["candidate_coverage_at_20"]
        before_text = f"{fmt_ratio(before['evidence_span_recall'])}; {fmt_ratio(before['complete_evidence_hit'])}; {fmt_decimal(before['first_evidence_mrr']['value'])}"
        after_text = f"{fmt_ratio(after['evidence_span_recall'])}; {fmt_ratio(after['complete_evidence_hit'])}; {fmt_decimal(after['first_evidence_mrr']['value'])}"
        cand = coverage["evidence_span_recall"]
        rerank_rows.append([label, before_text, after_text, f"{fmt_ratio(cand)} spans"])
    add_data_table(doc, "Bảng 4.4. BGE reranker trên candidate pool Top-20", ["Nguồn candidate", "Trước (Recall/Hit/MRR)", "Sau (Recall/Hit/MRR)", "Đủ span trong pool"], rerank_rows, [1.4, 1.8, 1.8, 1.3], f"Run ID: `reranker_5da3bd4d5de54492_20261007T094759Z`; một reranker, development pilot 7 câu/10 span.")
    add_p(doc, "Trong pilot, reranker đưa evidence lên Top-5 ở hai candidate source. Tuy nhiên, một model và bảy câu chưa đủ để khẳng định cải thiện ổn định; chưa đạt mục tiêu so sánh ba reranker. Ở max_length 512 có 99/140 cặp Dense và 110/140 cặp RRF bị cắt ở cuối passage; phép sensitivity 1.024 không đổi thứ hạng trong mẫu nhưng có độ trễ cao hơn. Reranker không khôi phục được span thiếu khỏi candidate list [12].")
    add_heading(doc, "4.5. Generation, citation và từ chối", 2, page_break=True)
    gen_metrics = generation["metrics"]
    retrieval_median = statistics.median(item["retrieval_latency_ms"] for item in generation["results"])
    generation_median = statistics.median(item["generation_latency_ms"] for item in generation["results"])
    invalid_json_count = sum(item["status"] == "invalid_model_json" for item in generation["results"])
    generation_rows = [
        ["Answerable có phản hồi", fmt_count_ratio(gen_metrics["answerable_response_rate"]), "Không đo độ đúng câu trả lời."],
        ["Unanswerable bị ghi nhận non-answer", fmt_count_ratio(gen_metrics["unanswerable_refusal_rate"]), f"Có {invalid_json_count} output JSON không hợp lệ; không tính là refusal diễn đạt thành công."],
        ["Có document ID kỳ vọng", fmt_count_ratio(gen_metrics["answerable_citing_expected_document_rate"]), "Chỉ đối chiếu document ID."],
        ["Citation ID hợp lệ cấu trúc", fmt_count_ratio(gen_metrics["valid_citation_id_rate"]), "Chưa kiểm tra claim entailment."],
        ["Retrieval + rerank median", f"{fmt_decimal(retrieval_median / 1000, 3)} giây", "Local, 10 câu; bao gồm khởi tạo trong phiên."],
        ["Generation median", f"{fmt_decimal(generation_median / 1000, 3)} giây", "Local Ollama/Qwen3:4B; phụ thuộc máy và độ dài."],
    ]
    add_data_table(doc, "Bảng 4.5. Pilot generation cục bộ", ["Chỉ số", "Kết quả từ raw run", "Cách diễn giải"], generation_rows, [1.75, 1.35, 3.2], f"Run ID: `{generation['run_id']}`; snapshot {generation['snapshot_id']}; 10 câu development, Top-5.")
    add_p(doc, "Prompt yêu cầu chỉ dựa vào context, coi văn bản nguồn là dữ liệu chứ không phải chỉ dẫn, trích citation ID và báo thiếu căn cứ. Tuy nhiên, prompt không thay cho một verifier. Ở run này 2/3 câu unanswerable vẫn tạo nội dung; output JSON không hợp lệ làm bộ xử lý trả abstain trong một trường hợp. Vì vậy không chọn refusal threshold. Citation ID hợp lệ chỉ là kiểm tra cấu trúc; chưa chứng minh mệnh đề có trong đoạn dẫn.")
    add_heading(doc, "4.6. Đánh giá RAG và ứng dụng console", 2)
    add_p(doc, "Đánh giá nên chia thành retrieval (evidence recall, complete-evidence, MRR/nDCG), generation (correctness, relevance, faithfulness), citation (ID, source/page, semantic support), refusal (false refusal và unsupported answer) và vận hành (latency, model/config, token, lỗi parse). RAGAS đề xuất metric tự động như faithfulness, answer relevance và context precision/recall; ARES cũng tập trung context relevance, faithfulness và answer relevance. Đây là phép đo hỗ trợ, không phải ground truth tuyệt đối; cần ghi judge model/prompt và đọc lại mẫu lỗi [3, 4].")
    add_p(doc, "Console được giữ ở mức dòng lệnh để thấy từng tầng và metadata nguồn, đúng yêu cầu tập trung kỹ thuật thay vì làm UI. Chạy retrieval: `python -m rag_hcmute.console_app --method bm25 --query \"...\"`; Dense/Hybrid/rerank cần model snapshot local; generation bật `--answer` và yêu cầu Ollama cục bộ. Trước lệnh, dùng executable của env `rag-hcmute` và in `sys.executable`. Không dùng output hiện tại để tư vấn quy định học vụ.")

    add_heading(doc, "CHƯƠNG 5. KẾT LUẬN, GIỚI HẠN VÀ PHẦN CÒN LẠI", 1, page_break=True)
    add_heading(doc, "5.1. Kết luận về mức độ hiểu và kết quả", 2)
    add_p(doc, "RAG được hiểu như một pipeline có thể phân rã và kiểm tra, không phải thao tác “đưa PDF vào vector DB”. Chất lượng phụ thuộc nguồn, trích xuất, chunk, retrieval, context, generator và citation. Những thành phần này có quan hệ nối tiếp: bằng chứng bị OCR sai hoặc không vào candidate pool thì LLM khó bù lại; citation có ID đúng nhưng không liên quan vẫn không đạt mục tiêu truy nguyên.")
    add_p(doc, "Trong PoC hiện có thể dựng lại G0, chạy BM25/dense, so RRF, thử BGE reranker, so hai embedding và hai store, rồi nối generation local vào console. Một số pilot cho thấy dense xếp nhiều evidence lên Top-5 hơn BM25; exact search FAISS/Qdrant trả cùng thứ tự trong phép thử nhỏ; reranker đã cải thiện thứ hạng trong development; còn generation chưa từ chối đáng tin. Các kết quả này có giá trị vì chỉ ra cụ thể điều gì hoạt động và ở đâu hệ thống vẫn sai, chứ không phải vì chúng tạo một điểm tổng hợp cao.")
    add_p(doc, "Mốc 1 chưa thể coi là đã khép theo toàn bộ yêu cầu YC1–YC13. Tập đánh giá còn 10 câu development, không có holdout; mới đo hai embedding model, một reranker và hai vector store exact; OCR/table/image chưa có pipeline tổng quát; chưa chấm semantic correctness, faithfulness hoặc citation entailment. Những giới hạn này được giữ rõ trong `docs/TRUY_VET_YC.md`, thay vì chuyển thành tuyên bố hoàn thành chỉ vì đã có report và demo.")
    add_heading(doc, "5.2. Phần cần hoàn thiện trước khi chốt Mốc 1", 2)
    add_bullet(doc, "Người học tự viết và kiểm tra thêm câu hỏi/gold evidence, mở rộng document class, tách dev/test theo nhóm chủ đề và đóng băng holdout trước khi tune.")
    add_bullet(doc, "Mở rộng phép so sánh embedding/reranker/store theo số model yêu cầu; trước khi tải thêm cần cân nhắc dung lượng, giấy phép, prefix, input length và khả năng chạy trên GPU hiện có.")
    add_bullet(doc, "Rà OCR trên ảnh gốc và các trường hợp số/điều kiện; chưa dùng QĐ 3116 cho đến khi có transcript và metadata được kiểm chứng; khảo sát riêng cấu trúc bảng/hình.")
    add_bullet(doc, "Xây bộ đánh giá end-to-end gồm correctness, faithfulness, answer relevance, citation support và confusion matrix refusal; nếu dùng LLM judge phải có estimate và phê duyệt chi phí trước.")
    add_heading(doc, "5.3. Nhận xét cuối", 2)
    add_p(doc, "Kết quả hiện tại phù hợp với một mốc tìm hiểu nghiêm túc: các phần đã có bằng chứng chạy được, còn những phần chưa chắc chắn được giữ ở đúng trạng thái. Một phép đo nhỏ vẫn hữu ích nếu nó có corpus, split, metric và giới hạn rõ; một kết luận lớn thì cần nhiều hơn một pilot. Tiếp tục phát triển nên ưu tiên chất lượng evidence và khả năng tái lập trước, sau đó mới mở rộng tính năng.")
    add_p(doc, "Giá trị chính của hướng triển khai là xây được chuỗi từ nguồn tài liệu đến đoạn dẫn có thể mở lại, đồng thời biết nơi nào cần người kiểm tra. Nếu không xử lý được trang scan, bảng hoặc hiệu lực phiên bản, hệ thống cần nói rõ điều đó thay vì làm như đã bao phủ toàn bộ kho học vụ. Khi có tập câu hỏi độc lập và kiểm tra citation bằng con người, mới có cơ sở đánh giá RAG như một công cụ tra cứu; trước thời điểm đó, PoC chỉ phục vụ nghiên cứu và trình diễn kỹ thuật.")

    add_heading(doc, "TÀI LIỆU THAM KHẢO", 1, page_break=True)
    references = [
        "[1] P. Lewis et al. (2020). Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks. NeurIPS 2020. https://arxiv.org/abs/2005.11401",
        "[2] Y. Gao et al. (2024). Retrieval-Augmented Generation for Large Language Models: A Survey. https://arxiv.org/abs/2312.10997",
        "[3] S. Es et al. (2024). RAGAs: Automated Evaluation of Retrieval Augmented Generation. EACL 2024. https://aclanthology.org/2024.eacl-demo.16/",
        "[4] A. Saad-Falcon et al. (2024). ARES: An Automated Evaluation Framework for Retrieval-Augmented Generation Systems. NAACL 2024. https://aclanthology.org/2024.naacl-long.20/",
        "[5] J. Chen et al. (2024). BGE M3-Embedding: Multi-Lingual, Multi-Functionality, Multi-Granularity Text Embeddings. https://arxiv.org/abs/2402.03216",
        "[6] A. Asai et al. (2024). Self-RAG: Learning to Retrieve, Generate, and Critique through Self-Reflection. ICLR 2024. https://arxiv.org/abs/2310.11511",
        "[7] Y. Yan et al. (2024). Corrective Retrieval Augmented Generation. https://arxiv.org/abs/2401.15884",
        "[8] H. Wang et al. (2024). Multilingual E5 Text Embeddings: A Technical Report. https://arxiv.org/abs/2402.05672",
        "[9] T. Cormack, C. Clarke, and S. Buettcher (2009). Reciprocal Rank Fusion outperforms Condorcet and individual Rank Learning Methods. SIGIR 2009. https://doi.org/10.1145/1571941.1572114",
        "[10] Tesseract OCR contributors. Tesseract documentation: improving OCR quality and page segmentation. https://tesseract-ocr.github.io/tessdoc/ImproveQuality.html",
        "[11] Facebook Research. FAISS documentation; Qdrant documentation. https://github.com/facebookresearch/faiss/wiki ; https://qdrant.tech/documentation/",
        "[12] BAAI. BGE Reranker v2 M3 model card. https://huggingface.co/BAAI/bge-reranker-v2-m3",
        "[13] T. Pham et al. (2026). VN-MTEB: Vietnamese Massive Text Embedding Benchmark. Findings of EACL 2026. https://aclanthology.org/2026.findings-eacl.86/",
        "[14] S. Robertson and H. Zaragoza (2009). The Probabilistic Relevance Framework: BM25 and Beyond. https://doi.org/10.1561/1500000019",
    ]
    for reference in references:
        add_p(doc, reference, size=12, align=WD_ALIGN_PARAGRAPH.LEFT, first_line=False)

    add_heading(doc, "PHỤ LỤC A. TRUY VẾT CODE VÀ TÁI LẬP", 1, page_break=True)
    add_p(doc, "Cấu trúc và lệnh chạy được duy trì trong README.md. Các thư mục chính: src/rag_hcmute/ingestion/ xử lý extraction/chunking; src/rag_hcmute/retrieval/ chứa BM25, dense, RRF và rerank; src/rag_hcmute/generation/ nối Ollama local; src/rag_hcmute/evaluation/ cùng scripts/ tạo phép thử. tests/ kiểm tra các hợp đồng này.", align=WD_ALIGN_PARAGRAPH.LEFT, first_line=False)
    add_p(doc, "Các báo cáo evidence riêng: chunk-size tại docs/evidence/CHUNK_SIZE_EXACT_EVIDENCE_20260929.md; RRF tại docs/evidence/HYBRID_RRF_ABLATION_20261007.md; reranker tại docs/evidence/RERANKER_RESOURCE_AND_EVAL_PLAN_20261007.md; OCR tại docs/evidence/OCR_DPI_SENSITIVITY_20261007.md; generation tại docs/evidence/GENERATION_PILOT_20261008.md. Các raw JSON được tham chiếu dưới từng bảng và giữ trong vùng Git-ignored.", align=WD_ALIGN_PARAGRAPH.LEFT, first_line=False)
    add_p(doc, "Ma trận yêu cầu chính thức YC1–YC13 và tình trạng từng phần nằm ở docs/TRUY_VET_YC.md. Dataset question policy và schema tương lai ở data/eval/README.md. Đây là điểm kiểm tra để báo cáo, mã nguồn và minh chứng không kể ba câu chuyện khác nhau.", align=WD_ALIGN_PARAGRAPH.LEFT, first_line=False)
    add_p(doc, "Kiểm tra kỹ thuật ngày 08/10/2026: 104 test tự động đạt; compileall cho src/, scripts/ và tests/ đạt. Các kiểm tra này xác nhận hợp đồng phần mềm và hành vi trên fixture, không thay thế đánh giá chất lượng RAG trên tập độc lập.", align=WD_ALIGN_PARAGRAPH.LEFT, first_line=False)


def main() -> None:
    print(sys.executable)
    if sha256(TEMPLATE) != EXPECTED_TEMPLATE_SHA256:
        raise RuntimeError("Template SHA-256 changed; stop and review the source document before editing.")
    if OUTPUT.exists():
        raise FileExistsError(f"Refusing to overwrite existing report: {OUTPUT}")
    for path in RAW.values():
        if not path.exists():
            raise FileNotFoundError(f"Required evidence source not found: {path}")
    document = Document(str(TEMPLATE))
    if len(document.sections) != 2:
        raise RuntimeError(f"Expected two template sections; found {len(document.sections)}")
    remove_old_body_and_update_cover(document)
    build_report(document)
    document.save(str(OUTPUT))
    print(f"Created: {OUTPUT}")
    print(f"Template SHA-256: {EXPECTED_TEMPLATE_SHA256}")
    print(f"Output bytes: {OUTPUT.stat().st_size}")


if __name__ == "__main__":
    main()
