"""Build the final DOCX from the reviewed cumulative report and measured evidence."""
import argparse
import hashlib
import json
import sys
from pathlib import Path

from docx import Document
from docx.shared import Pt

from build_m1_report_v3 import add_data_table, add_heading, add_p, set_run_font

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "reports/22110068_RAG_Bao_Cao_Tien_Do_Tong_Hop_Moc_1_2_3_v1.docx"


def replace_text(paragraph, content, size=12, bold=False):
    paragraph.clear()
    set_run_font(paragraph.add_run(content), size, bold=bold)


def main():
    print(f"Python executable: {sys.executable}", flush=True)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence-commit", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    evidence = ROOT / "docs/evidence/final"

    def read(name):
        return json.loads((evidence / f"{name}.json").read_text(encoding="utf-8"))

    manifest = read("manifest")
    for file in manifest["files"]:
        if hashlib.sha256((evidence / file["file"]).read_bytes()).hexdigest() != file["sha256"]:
            raise ValueError(f"Evidence changed: {file['file']}")
    run = read("extended_a")
    cfg = run["config"]
    review = read("review_summary")["results"]
    vector = read("vector_filter")
    pdf = read("pdf_tables")
    context = read("context_lengths")
    counts = list(context["template_estimated_prompt_tokens"].values())
    if not run["completed"] or not read("scope_8192")["completed"] or not read("scope_schema")["completed"]:
        raise ValueError("The report requires all three complete generation runs.")

    doc = Document(TEMPLATE)
    original = {p.text.strip(): p for p in doc.paragraphs if p.text.strip()}
    first = original["BÁO CÁO TIẾN ĐỘ TỔNG HỢP"]
    replace_text(first, "BÁO CÁO CUỐI KỲ", 14, True)

    def find(prefix):
        matches = [p for text, p in original.items() if text.startswith(prefix)]
        if len(matches) != 1:
            raise ValueError(f"Ambiguous template anchor: {prefix!r} ({len(matches)})")
        return matches[0]

    replace_text(find("Tài liệu tổng hợp nội dung tìm hiểu"),
                 "Đề tài tìm hiểu cách hệ thống RAG trả lời câu hỏi tiếng Việt dựa vào tài liệu học vụ. "
                 "Bản thử nghiệm dùng ba PDF của HCMUTE và chạy trên console. Trọng tâm là giải thích "
                 "đường đi từ trang tài liệu đến câu trả lời, đo từng khâu và chỉ ra nguyên nhân khi kết quả sai.")
    replace_text(find("Kết quả chính dùng ba tài liệu"),
                 "Thực nghiệm theo công đoạn dùng ba tài liệu gồm 182 trang và tập phát triển ban đầu 10 câu. "
                 f"Phép thử mở rộng có {cfg['answerable_count']} câu gắn với đoạn nguồn và "
                 f"{cfg['unanswerable_count']} câu thiếu căn cứ theo phạm vi kho dữ liệu. "
                 "Kết quả đầu-cuối trên 12 câu cho thấy việc tìm được nguồn và định dạng được câu trả lời chỉ "
                 "giải quyết một phần bài toán. Câu trả lời vẫn có thể thiếu điều kiện, nhầm thang điểm hoặc dùng sai phạm vi văn bản.")
    replace_text(find("Nội dung được tổ chức thành năm chương"),
                 "Năm chương lần lượt trình bày bài toán, xử lý tài liệu, chia đoạn và chỉ mục, truy xuất và sinh, "
                 "rồi đánh giá đầu-cuối và cách chạy ứng dụng. Mỗi phép thử ghi tập dữ liệu, cấu hình và giới hạn kết luận.")
    replace_text(find("Lượt kiểm lại BM25 ngày 05/11"),
                 f"Bộ kiểm thử phần mềm có {manifest['software_tests_passed']} trường hợp đạt ở bản mã nguồn cuối. "
                 "Các kiểm thử bao gồm truy vết, hợp đồng truy xuất và kiểm cấu trúc đầu ra. Chất lượng câu trả lời được xem riêng "
                 "trong mục đánh giá. Lượt console hỏi về nghỉ học tạm thời đã truy đúng Điều 17 ở hạng 1.")
    replace_text(find("CHƯƠNG 5 ĐÁNH GIÁ"), "CHƯƠNG 5 ĐÁNH GIÁ THỰC NGHIỆM VÀ KẾT LUẬN", 14, True)

    def insert(anchor, author):
        prior = set(doc.element.body)
        author()
        added = [element for element in doc.element.body if element not in prior]
        for element in added:
            anchor._p.addprevious(element)

    def p(content, **kwargs):
        paragraph = add_p(doc, content, **kwargs)
        paragraph.paragraph_format.keep_together = True
        return paragraph

    def h(content):
        return add_heading(doc, content, 2)

    def table(caption, headers, rows, widths, note):
        result = add_data_table(doc, caption, headers, rows, widths, note)
        for row in result.rows[:-1]:
            for cell in row.cells:
                for para in cell.paragraphs:
                    para.paragraph_format.keep_with_next = True
        return result

    def pdf_update():
        p(f"Kiểm thêm {pdf['reference_rows']} hàng trên các trang 3, 15, 19 và 20 của Quyết định 1727 bằng ảnh nguồn. "
          f"PyMuPDF với đường kẻ khớp {pdf['exact_cells']}/{pdf['reference_cells']} ô và "
          f"{pdf['exact_rows']}/{pdf['reference_rows']} hàng của mẫu. Ba hàng lệch đều do ô Đạt được gộp dọc "
          "trong bảng quy đổi. Khi xuất lưới, nhãn nằm ở hàng đầu vùng gộp và các hàng dưới nhận ô rỗng. "
          "Ở trang 3, chế độ theo chữ tạo một vùng 61 hàng và 13 cột, trong khi chế độ đường kẻ trả bảng 14 hàng "
          "và 5 cột. Bảng phân loại hệ niên chế còn nối qua hai trang. Vì vậy cần lưu ranh giới ô gộp, tên nhóm "
          "và liên kết phần tiếp theo trước khi chuyển hàng thành chunk. Minh chứng CK-BANG.")
    insert(find("2.6 Nội dung hình"), pdf_update)

    def vector_update():
        p(f"Kiểm tra lọc document_id dùng {vector['vectors']} vector G0. Với chín vector truy vấn tham chiếu "
          f"lần lượt lọc ba tài liệu, Qdrant local sau khi đóng và mở lại trả cùng tập ID với FAISS trên tập con "
          f"ở {vector['same_exact_ids']}/{vector['queries']} lượt. Lấy Top-5 toàn kho rồi lọc bị thiếu "
          f"ở {vector['postfilter_short_cases']}/{vector['queries']} lượt. Đây là phép kiểm logic lọc theo metadata. "
          "Các vector truy vấn được chọn từ chỉ mục để kiểm tập ID. Kết quả tốc độ local và bộ nhớ ở quy mô này "
          "chỉ dùng để hướng dẫn chọn cách tổ chức dữ liệu. Minh chứng CK-LOC.")
    insert(find("CHƯƠNG 4 TRUY XUẤT"), vector_update)

    start = find("5.3 Chuẩn bị dữ liệu")
    end = find("PHỤ LỤC A MINH CHỨNG")
    body = list(doc.element.body)
    for child in body[body.index(start._p):body.index(end._p)]:
        doc.element.body.remove(child)

    def add_evaluation():
        h("5.3 Thiết kế đánh giá mở rộng")
        p(f"Tập mở rộng gồm {cfg['answerable_count']} câu có {cfg['source_span_count']} khoảng bằng chứng từ Quyết định 1727 "
          f"và {cfg['unanswerable_count']} câu thiếu dữ liệu vì hỏi hồ sơ cá nhân, sự kiện tương lai hoặc thông tin ngoài "
          "HCMUTE. Chỉ mục vẫn chứa cả ba PDF để có đoạn nhiễu. Có 10 câu đọc bảng, 14 câu dùng nhiều khoảng bằng chứng "
          "và 24 câu diễn đạt khác từ vựng nguồn. Các nhóm có thể giao nhau. Câu hỏi, chỉ số và cấu hình được khóa bằng mã băm "
          "trước lượt chạy. Trích đoạn được khớp duy nhất trên từng trang đã làm sạch.")
        p("Các câu mới do công cụ AI soạn dựa trên văn bản. Đáp án và vị trí nguồn dùng để đối chiếu kỹ thuật theo phạm vi "
          "hẹp của phép thử. Phiếu rà soát gồm 85 mục, trong đó có 27 mục chuyển từ gói cũ. Chưa có bộ câu hỏi độc lập "
          "do sinh viên tự viết và xác nhận đủ theo kế hoạch. Do câu hỏi gắn với một quy chế, kết quả có thể cao hơn khi gặp "
          "cách hỏi tự nhiên hoặc câu cần hiểu nhiều văn bản khác nhau.")
        h("5.4 Kết quả truy xuất trên mẫu mở rộng")
        rows = []
        fmt = lambda x: f"{x:.4f}".replace(".", ",")
        for method, value in run["retrieval"].items():
            macro = value["macro"]
            rows.append([method, fmt(macro["character_recall_at_5"]), fmt(macro["character_precision_at_5"]),
                         fmt(macro["mrr_at_10_threshold_05"]), fmt(macro["ndcg_at_5_linear_span_coverage"])])
        table("Bảng 19  Độ phủ bằng chứng và thứ hạng trên 43 câu",
              ["Cấu hình", "Phủ ký tự Top-5", "Precision ký tự", "MRR@10", "nDCG@5"], rows,
              [1.82, 1.14, 1.28, 1.03, 1.03],
              f"Minh chứng CK-R. {cfg['run_id']}. MRR tính hạng đầu của đoạn phủ ít nhất nửa một khoảng bằng chứng.")
        p("Hợp điểm Weighted75 phủ thêm bằng chứng so với từng nhánh riêng. Reranker nâng độ phủ từ 0,9956 lên "
          "0,9999 nhưng MRR giảm từ 0,8748 còn 0,8566. Hai chỉ số phản ánh hai mục tiêu khác nhau. Trong 49 câu "
          "được rerank, 723/980 cặp bị cắt ở trần 512 token. Đoạn bằng chứng ở cuối cửa sổ có thể được giữ trong chỉ mục "
          "nhưng bị bỏ ở lần chấm lại.")
        p("Mười câu bảng đều đạt độ phủ ký tự 1,00 ở Top-5 với cả bốn cấu hình. Mẫu F39 ở phần sinh cho thấy "
          "vẫn có thể lẫn điểm học phần với xếp loại học tập. Precision ký tự thấp vì đoạn trả về dài hơn nhiều so với "
          "vùng đáp án đã gắn nhãn. Chỉ số này đo phần chữ giao với bằng chứng, không gán nhãn phần còn lại là sai.")
        rows = [[key, str(value["chunks"]), fmt(value["macro"]["character_recall_at_5"]),
                 fmt(value["macro"]["character_precision_at_5"])] for key, value in run["chunk_sensitivity"].items()]
        table("Bảng 20  Độ nhạy của cửa sổ tách đoạn với BM25",
              ["Kích thước và overlap", "Số đoạn", "Phủ ký tự Top-5", "Precision ký tự"], rows,
              [2.1, .9, 1.65, 1.65], "Minh chứng CK-R. Cùng 43 câu. Cửa sổ cố định, đơn vị tách theo khoảng trắng.")
        p("Ở kích thước 250, thêm overlap 40 cải thiện độ phủ từ 0,8925 lên 0,9566, đồng thời tăng số đoạn "
          "từ 243 lên 288. Ở kích thước 500, độ phủ thay đổi ít. Cửa sổ 750 trả nhiều văn bản hơn "
          "cho cùng số đoạn nhưng giảm cả độ phủ và precision ký tự trên mẫu này. Đây là căn cứ để thử đoạn ngắn "
          "hơn với ngân sách context cố định ở vòng sau.")
        h("5.5 Đánh giá đầu-cuối và độ tin cậy của nguồn")
        p("Chọn trước 12 câu gồm sáu câu gắn nguồn và sáu câu thiếu căn cứ. BM25 và Weighted75 có reranker "
          "đều cấp Top-5 cho cùng Qwen3:4B. Sau lượt đầu, chạy lại chính các nguồn đó theo đúng thứ tự để quan sát "
          "ảnh hưởng của JSON Schema và cửa sổ ngữ cảnh. Ba lượt so sánh dùng cùng giới hạn sinh 384 token, "
          "temperature 0 và cùng digest mô hình.")
        reserve = sum(n + context["output_budget"] > context["active_context"] for n in counts)
        over = sum(n > context["active_context"] for n in counts)
        p(f"Đếm bằng tokenizer Qwen trên mẫu chat tương ứng cho thấy {over}/{len(counts)} prompt ước tính vượt 4.096 token "
          f"trước khi sinh và {reserve}/{len(counts)} vượt nếu cộng ngân sách tối đa 384 token. Đây là ước tính từ tokenizer, "
          "không phải log vị trí token bị cắt. Chạy lại với num_ctx 8.192 giúp kiểm tra ảnh hưởng của giới hạn này.")
        variants = {"scope_check": "Prompt phạm vi", "scope_schema": "Thêm JSON Schema",
                    "scope_8192": "Schema và 8.192 token"}
        rows = []
        for key, name in variants.items():
            for method, groups in review[key].items():
                a, u = groups["answerable"], groups["unanswerable"]
                rows.append([name, "BM25" if method == "BM25" else "Hợp + rerank",
                             f"{a.get('correct_supported', 0)}/{a['unambiguous_total']}",
                             f"{u.get('model_abstained', 0)}/{u['total']}",
                             f"{u.get('answer_emitted', 0)}/{u['total']}",
                             f"{a.get('technical_block', 0) + u.get('technical_block', 0)}/12"])
        table("Bảng 21  Kết quả sinh và từ chối theo cấu hình",
              ["Cách sinh", "Truy xuất", "Đúng đủ có nguồn", "Từ chối thật", "Vẫn trả lời", "Chặn kỹ thuật"],
              rows, [1.6, 1.16, 1.06, .79, .81, .88],
              "Minh chứng CK-G. Cột vẫn trả lời xét sáu câu thiếu căn cứ. Chặn kỹ thuật xét cả 12 câu mỗi cấu hình.")
        p("Cột đúng đủ có nguồn dùng bước đối chiếu đáp án và nguồn bởi trợ lý AI. Câu F39 không ghi rõ "
          "thang điểm 10 nên được giữ trong thống kê chạy và loại khỏi mẫu số chấm nội dung. Nhãn đúng yêu cầu toàn bộ "
          "ý chính và nguồn dẫn hỗ trợ. Một câu đúng một phần được ghi riêng. Cần người học đối chiếu các nhãn trước khi "
          "dùng cho kết luận đánh giá độc lập.")
        p("Ở F07, BM25 dẫn đoạn về điều kiện học hai chương trình dù câu hỏi yêu cầu phân biệt học phần học trước "
          "và học phần tiên quyết. Reranker tìm được phần tiên quyết nhưng câu trả lời bỏ điều kiện điểm tổng kết khác 0 "
          "của học phần học trước. F13 với BM25 trả đúng năm tuần học và ít nhất một tuần đánh giá ở cửa sổ 8.192. "
          "Cùng câu đó, phương án reranker vẫn nêu sai thời lượng. Trường hợp này cho thấy cần xem cùng lúc vị trí nguồn và "
          "cách mô hình đọc ngữ cảnh.")
        p("JSON Schema giảm số lượt chặn vì cấu trúc từ 11 xuống 4 trên 24 đầu ra khi giữ cửa sổ mặc định. "
          "Ở sáu câu thiếu căn cứ mỗi phương án, hiện tượng trả lời vẫn phổ biến. U01 đưa ra khẳng định về bảng điểm cá nhân "
          "từ tài liệu chung. U13 dùng dữ liệu HCMUTE cho một trường khác. Kết quả ở 8.192 có một lượt BM25 chủ động từ chối "
          "trên sáu câu thiếu căn cứ, cho thấy tăng cửa sổ chỉ giải quyết một phần lỗi.")
        h("5.6 Minh họa qua console")
        pause, summer, outside = [read(f"console_{name}") for name in ("pause", "summer", "outside")]
        assert pause["query"]["citation_ids"] == ["S1"] and summer["query"]["citation_ids"] == ["S3"]
        assert outside["query"]["status"] == "model_abstained"
        p("Trong lượt BM25 sinh cục bộ với JSON Schema và cửa sổ 8.192, câu về nghỉ học tạm thời trả nguồn S1, "
          "Quy chế đào tạo trình độ đại học, Điều 17, PDF trang 23–24. Mở trang 24 để kiểm hai hạn nộp: trước khi kết thúc "
          "học kỳ ít nhất hai tuần khi xin nghỉ và trước khi đăng ký học phần ít nhất hai tuần khi xin học tiếp. "
          "Ở câu về học kỳ phụ, nguồn đúng ở S3, PDF trang 9. Câu hỏi giờ mở cửa thư viện ở Cần Thơ nhận trạng thái "
          "model_abstained. Ba lượt là ca minh họa vận hành. Số đo toàn bộ của 12 câu nằm ở Bảng 21.")
        h("5.7 Kết luận và giới hạn")
        p("Đồ án đã xây dựng được luồng hỏi đáp có thể quan sát từ tài liệu nguồn, đoạn truy xuất đến câu trả lời. "
          "Lưu mã tài liệu và ranh giới nguồn cho phép xác định lỗi nảy sinh ở bước nào. Với trang PDF có bảng, "
          "cấu trúc ô gộp và nhãn hàng có thể mang thông tin mà chuỗi chữ không giữ được. Với trang nhiều hình, cần xem lại "
          "quan hệ giữa vùng ảnh, chữ và bố cục trước khi dùng làm căn cứ.")
        p("Kết quả cho thấy hợp điểm có ích cho độ phủ truy xuất trong mẫu câu hỏi học vụ. Reranker có thể tăng độ phủ "
          "mà làm giảm thứ hạng nguồn đầu tiên. Ở khâu sinh, định dạng chặt hơn giúp nhận được nhiều đầu ra hợp lệ, "
          "song chất lượng phụ thuộc nguồn có đúng phạm vi, còn đủ điều kiện và thực sự đến được mô hình. "
          "Báo cáo giữ BM25 như cấu hình gọn để trình bày và giữ phương án hợp điểm có reranker để đối chiếu.")
        p("Các kết luận giới hạn trong G0 và giao thức thực nghiệm đã mô tả. Cần hoàn thiện bản chép OCR "
          "cho các trang mới, kiểm nội dung hình bằng câu hỏi gắn vùng ảnh và đánh giá đầu-cuối trên tập có người duyệt "
          "chưa dùng để chọn cấu hình. Khi áp dụng cho quy định hiện hành, phải xác minh ngày hiệu lực và "
          "quan hệ giữa các văn bản trước khi cập nhật chỉ mục.")
    insert(end, add_evaluation)

    replace_text(find("Mã nguồn và số liệu đã tích lũy"),
                 f"Mã nguồn và kết quả thực nghiệm dùng commit {args.evidence_commit[:12]} trên nhánh tim-hieu-rag-dot2 "
                 "của dự án https://github.com/franz08hmt/RAG. Gói kết quả chỉ gồm mã mẫu, mã đoạn, cấu hình và số liệu. "
                 "Tệp câu hỏi, bản chép và đầu ra đầy đủ nằm trong gói đánh giá cục bộ.")
    replace_text(find("Bảng 18  Danh mục minh chứng"), "Bảng 22  Danh mục minh chứng theo phép thử", 12, True)
    replace_text(find("Bảng 19  Nội dung đã khảo sát"), "Bảng 23  Đối chiếu nội dung với yêu cầu của giảng viên", 12, True)
    replace_text(find("Mở PowerShell tại D:"), "Xem docs/BAN_GIAO_CUOI_KY.md để chạy lại console và các phép thử.")
    for prefix in (".\\scripts\\demo_m2.ps1 -Method", ".\\scripts\\demo_m2.ps1 -Question", "Hướng dẫn tái lập từng thí nghiệm"):
        obsolete = find(prefix)
        obsolete._p.getparent().remove(obsolete._p)
    replace_text(find("Trạng thái cập nhật tới ngày 05/11"), "Bảng đối chiếu cập nhật đến ngày 15/11/2026.")
    replace_text(find("Công cụ AI hỗ trợ rà mã"),
                 "Công cụ AI hỗ trợ chuẩn bị câu hỏi, rà mã, chạy thí nghiệm, đối chiếu đầu ra và biên tập báo cáo. "
                 "Báo cáo ghi nguồn của từng loại số liệu và phân biệt kết quả đo chương trình với nhãn nội dung "
                 "do công cụ đối chiếu. Sinh viên có thể mở dữ liệu gốc để kiểm và hiệu chỉnh nhãn.")
    updates = {
        "YC4": "OCR và bảng có lưới, ô gộp, nối trang. Chưa có đánh giá hiểu hình độc lập.",
        "YC5": "Sáu cách chia, ngân sách ngữ cảnh và độ nhạy kích thước/overlap.",
        "YC7": "FAISS, Qdrant, Flat/HNSW/IVF và lọc metadata trên G0.",
        "YC10": "Trích nguồn, schema và context 8.192. Còn nhầm phạm vi và thiếu điều kiện.",
        "YC11": "43 câu truy xuất, 12 câu đầu-cuối. Nhãn do AI đối chiếu, chờ kiểm độc lập.",
        "YC12": "Console chạy truy xuất và sinh cục bộ, ba ca minh họa có kết quả lưu.",
    }
    targets = {"YC4": "2.3–2.6", "YC5": "3.1–3.3, 5.4", "YC7": "3.6",
               "YC10": "4.3–4.4, 5.5", "YC11": "5.1, 5.3–5.5", "YC12": "5.2, 5.6"}
    for existing in doc.tables:
        if existing.rows[0].cells[0].text == "YC":
            for row in existing.rows[1:]:
                code = row.cells[0].text
                if code in updates:
                    replace_text(row.cells[1].paragraphs[0], updates[code])
                    replace_text(row.cells[2].paragraphs[0], targets[code])
    def evidence_index():
        h("Minh chứng kiểm tra cuối kỳ")
        for code, files in (
            ("CK-R", "extended_a.json lưu kết quả retrieval, các biến thể chunking và lượt sinh ban đầu."),
            ("CK-BANG", "pdf_tables.json lưu mẫu ô và hàng so với ảnh nguồn."),
            ("CK-LOC", "vector_filter.json lưu 27 lượt đối chiếu lọc."),
            ("CK-G", "scope_schema.json, scope_8192.json, context_lengths.json và review_summary.json lưu so sánh sinh."),
            ("CK-C", "Các tệp console lưu thứ hạng và trạng thái của lượt trình diễn.")
        ):
            p(f"{code} · {files}", first_line=False)
        p("Các tệp nằm trong docs/evidence/final. Manifest lưu SHA-256 của từng bản xuất.")
    insert(find("PHỤ LỤC B ĐỐI CHIẾU"), evidence_index)

    doc.core_properties.title = "Tìm hiểu Retrieval Augmented Generation (RAG)"
    doc.core_properties.subject = "Báo cáo cuối kỳ IT Project"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    doc.save(args.output)
    print(args.output)


if __name__ == "__main__":
    main()
