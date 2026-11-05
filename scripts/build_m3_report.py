"""Build a new Vietnamese milestone report from verified metrics and retained cover."""
import argparse
import hashlib
import json
import statistics
import sys
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.opc.constants import RELATIONSHIP_TYPE as RT
from docx.oxml.ns import qn
from docx.shared import Inches
from PIL import Image, ImageDraw, ImageFont

from build_m1_report_v3 import add_p, add_heading, add_data_table, add_caption

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "reports/22110068_RAG_Bao_Cao_Tien_Do_Moc_2_v3.docx"
TEMPLATE_SHA = "882e62679efb02718cc61690e654c6d5772251deb269896253732b8fd22183f0"
NAMES = {"characters":"Ký tự","tokens":"Token","recursive":"Ưu tiên dấu ngắt",
         "sentences":"Theo câu","structure":"Theo Điều","semantic":"Ngữ nghĩa"}
MODELS = {"bge-m3":"BGE-M3", "multilingual-e5-small":"E5-small", "multilingual-e5-base":"E5-base",
          "vietnamese-bi-encoder":"BKAI", "vietnamese-embedding":"Vietnamese Embedding",
          "paraphrase-multilingual-MiniLM-L12-v2":"MiniLM"}
RERANKERS = {"bge-reranker-v2-m3":"BGE v2-m3","bge-reranker-base":"BGE-base","mmarco-mMiniLMv2-L12-H384-v1":"mMARCO"}


def number(value, precision=3):
    return f"{value:.{precision}f}".replace(".", ",")


def chart(results, filename):
    image = Image.new("RGB",(1600,750),"white")
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype("C:/Windows/Fonts/times.ttf",42)
    left, width = 342, 990
    for index,(key,label) in enumerate(NAMES.items()):
        y = 100+index*103
        scores = results[key]["retrieval"]["dense_bge"]
        a = scores["fixed_top5"]["macro"]["character_recall_at_5"]
        b = scores["context_budgets"]["1000"]["macro"]["character_recall"]
        draw.text((5,y+10),label,fill="black",font=font)
        for offset,value,filled in [(0,a,True),(40,b,False)]:
            end=left+round(width*value)
            draw.rectangle((left,y+offset,end,y+offset+23),fill="black" if filled else "white",outline="black",width=3)
            draw.text((end+12,y+offset-12),number(value,2),fill="black",font=font)
    draw.rectangle((left,20,left+43,45),fill="black")
    draw.text((left+57,9),"Top-5",font=font,fill="black")
    draw.rectangle((left+305,20,left+348,45),outline="black",width=3)
    draw.text((left+365,9),"Ngân sách 1.000 token",font=font,fill="black")
    image.save(filename)


def main():
    print(f"Python executable: {sys.executable}")
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    if hashlib.sha256(TEMPLATE.read_bytes()).hexdigest()!=TEMPLATE_SHA:
        raise ValueError("M2 template hash mismatch")
    def load(name):
        return json.loads((args.evidence/(name+".json")).read_text(encoding="utf-8"))
    c,e,r,g,o,a = [load(name) for name in ("chunking","embeddings","ranking","generation","ocr","review")]
    if not all(x["completed"] for x in (c,e,r,g)):
        raise ValueError("Require complete runs")
    doc = Document(TEMPLATE)
    past_cover = False
    for child in list(doc._element.body):
        if past_cover and child.tag != qn("w:sectPr"):
            doc._element.body.remove(child)
        elif child.tag==qn("w:p") and child.find("w:pPr/w:sectPr",doc._element.nsmap) is not None:
            past_cover=True
    if not past_cover: raise ValueError("Missing cover break")
    for paragraph in doc.paragraphs:
        for run in paragraph.runs:
            if "Tháng 10 năm 2026" in run.text:
                run.text=run.text.replace("Tháng 10 năm 2026","Tháng 11 năm 2026")
    p = lambda text:add_p(doc,text)
    h = lambda text:add_heading(doc,text,2)
    def section(text,new=True):
        heading = add_heading(doc,text)
        heading.paragraph_format.page_break_before = new
    def table(title,labels,rows,widths,note):
        return add_data_table(doc,title,labels,rows,widths,note)
    section("Báo cáo tiến độ Mốc 3",False)
    h("Phạm vi thực nghiệm")
    p("Hệ thống tiếp nhận câu hỏi học vụ bằng tiếng Việt và tìm các đoạn liên quan trong ba tài liệu HCMUTE. Đợt này khảo sát hai quyết định ảnh hưởng trực tiếp đến câu trả lời. Quyết định thứ nhất là cách chia và xếp các đoạn trong lượng ngữ cảnh có thể cấp cho mô hình. Quyết định thứ hai là cách kiểm tra một phát biểu khi mô hình gắn nguồn cho phát biểu đó.")
    p("Mốc 2 đã nối được console từ truy xuất đến sinh câu trả lời. Ở Mốc 3, cùng một câu hỏi được chạy qua nhiều cấu hình để xác định sai khác xuất hiện ở khâu nào. Truy xuất dùng bảy câu có bằng chứng, còn phép thử sinh dùng cả mười câu phát triển, gồm ba câu thiếu căn cứ. Các kết quả dưới đây chỉ áp dụng cho tập phát triển này.")
    h("Từ trang nguồn đến trích dẫn")
    p("Kho G0 gồm Quy chế đào tạo 1727, hướng dẫn thực tập tốt nghiệp của Khoa Công nghệ Thông tin và Sổ tay sinh viên 2024, tổng cộng 182 trang. Manifest lưu danh tính và mã băm tài liệu. PageText lưu văn bản theo trang. Chunk giữ mã tài liệu, khoảng trang và khoảng vị trí trong văn bản gốc. Vì nhiều cách chia có thể tạo mã chunk khác nhau, bằng chứng được gắn vào khoảng nguồn ổn định.")
    p("Khi trả lời, ứng dụng chuyển mã nguồn tạm như S1 về chunk, tài liệu và trang PDF tương ứng. Sổ tay và quyết định trong kho là các phiên bản dùng cho thực nghiệm. Muốn áp dụng một quy định cho sinh viên hiện tại còn phải kiểm tra đối tượng và hiệu lực văn bản.")
    h("Xử lý trang có ảnh")
    item=next(x for x in o["pages"] if x["document_id"]=="HCMUTE_SOTAYSV_2024" and x["pdf_page"]==116)
    p(f'Trên mười trang chọn trước, Tesseract đọc ảnh xám 180 dpi bằng bộ tiếng Việt. Trang PDF 116 của sổ tay có {item["native_characters"]} ký tự khi trích lớp chữ và {item["ocr_characters"]:,} ký tự khi OCR.'.replace("1,428","1.428")+" Chênh lệch này giúp nhận ra trang cần kiểm bằng mắt. Thứ tự dòng, dấu tiếng Việt và các ô trong bảng vẫn phải đối chiếu với ảnh. Mười bản chép chuẩn đang chờ người học duyệt để tính tỷ lệ lỗi ký tự và từ.")
    h("Kiểm tra lại trên console")
    p("Với câu P007 hỏi thủ tục nghỉ học tạm thời, BM25 trả về Điều 17 của Quy chế 1727 ở hạng đầu, đoạn c0038, trang PDF 23–24. Kết quả hạng hai nằm trong Sổ tay sinh viên và cũng nhắc đến nghỉ học. Khi trả lời về thủ tục, cần mở Điều 17 để kiểm tra cả trường hợp được nghỉ và bước nộp đơn. Chỉ nhìn thấy cụm “nghỉ học” chưa đủ căn cứ cho cả hai ý.")
    section("Chia đoạn và lựa chọn ngữ cảnh")
    p("Sáu cách chia dùng chung văn bản nguồn, trần 384 token BGE kể cả token đặc biệt và không chồng lấn. Các ranh giới được đặt trước khi đối chiếu bằng chứng. Mỗi đoạn vẫn ánh xạ về khoảng nguồn ban đầu để hai đoạn trùng nhau chỉ đóng góp một lần vào độ phủ.")
    p("Cửa sổ ký tự dừng gần 1.200 ký tự và giữ trọn đơn vị phân cách bằng khoảng trắng. Cửa sổ token đo trực tiếp bằng tokenizer. Cách ưu tiên dấu ngắt lần lượt tìm ranh giới trang hoặc đoạn, dòng rồi câu. Cách theo câu gom các câu nhận diện bằng dấu kết thúc. Cách theo Điều ưu tiên tiêu đề pháp quy, còn cách ngữ nghĩa ngắt tại những cặp câu liền nhau có độ tương đồng thấp trong từng tài liệu.")
    p("Chia theo Điều giữ được quan hệ giữa điều khoản và tiêu đề khi bộ nhận diện tìm đúng ranh giới. Cách theo câu ít phụ thuộc bố cục nhưng có thể nhầm chữ viết tắt. Cách ngữ nghĩa phải nhúng các câu trước khi tìm điểm ngắt. Trong lần chạy này, nó tạo 507 đoạn, so với 208 đoạn của cửa sổ token.")
    fig=ROOT/"artifacts/results/m3_docqa/chunk_recall.png"
    fig.parent.mkdir(parents=True,exist_ok=True)
    chart(c["strategies"],fig)
    add_caption(doc,"Hình 1  Độ phủ bằng chứng khi truy xuất bằng BGE-M3")
    pic=doc.add_paragraph()
    pic.alignment=WD_ALIGN_PARAGRAPH.CENTER
    pic.add_run().add_picture(str(fig),width=Inches(6.15))
    add_p(doc,"Trung bình theo bảy câu. Thanh đặc lấy năm đoạn đầu. Thanh rỗng lấy các đoạn còn vừa ngân sách 1.000 token Qwen3 trong 50 ứng viên.",italic=True,first_line=False)
    section("Đọc kết quả theo từng câu hỏi")
    p("Độ phủ ký tự là tỷ lệ ký tự của bằng chứng được tìm lại. Tử số lấy phần giao giữa hợp các khoảng truy xuất và hợp các khoảng bằng chứng trong đúng tài liệu. Khi cùng lấy năm đoạn, đoạn dài có thể bao phủ nhiều ký tự nhưng chiếm nhiều chỗ trong ngữ cảnh. Vì vậy phép đo còn đếm token trên chuỗi ghép thật, gồm dấu phân cách giữa các đoạn.")
    cases=[("P002","Rút bớt học phần","characters"),("P003","Cảnh báo học tập","tokens"),("P004","Học lại","tokens"),("P007","Nghỉ học tạm thời","recursive"),("P008","Buộc thôi học","structure")]
    rows=[]
    for qid,topic,key in cases:
        m=c["strategies"][key]["retrieval"]["dense_bge"]
        fixed=next(x for x in m["fixed_top5"]["per_question"] if x["question_id"]==qid)
        limited=next(x for x in m["context_budgets"]["1000"]["per_question"] if x["question_id"]==qid)
        rows.append([qid,topic,NAMES[key],number(fixed["character_recall_at_5"]),number(limited["character_recall"])])
    table("Bảng 1  Độ phủ của năm trường hợp trong tập phát triển",["Câu","Chủ đề","Cách chia","Top-5","1.000 token"],rows,[.6,1.6,1.65,1.15,1.3],
          "Cùng truy xuất dense và cùng nhãn vị trí. Giá trị 1 biểu thị toàn bộ khoảng bằng chứng đã nằm trong các đoạn được chọn.")
    p("P004 là trường hợp dễ bỏ sót khi chỉ xem một cột. Với cửa sổ token, năm kết quả đầu chứa đủ bằng chứng về đăng ký học lại. Khi đóng gói theo ngân sách 1.000 token, phần được chọn không còn phủ bằng chứng. Chia theo câu vẫn đạt độ phủ 1 ở cùng ngân sách cho câu này. Với P008, cách theo Điều chỉ phủ một phần bằng chứng trong cả hai phép đo.")
    p("Kết quả còn phụ thuộc bộ truy xuất. Với BM25, độ phủ Top-5 trung bình của cách chia ngữ nghĩa là "+number(c["strategies"]["semantic"]["retrieval"]["bm25"]["fixed_top5"]["macro"]["character_recall_at_5"])+". Cùng tập đoạn đó, bộ dense đạt "+number(c["strategies"]["semantic"]["retrieval"]["dense_bge"]["fixed_top5"]["macro"]["character_recall_at_5"])+". Sự khác biệt cần được kiểm lại trên các câu ít trùng từ vựng và câu cần nhiều nguồn. Đợt này mới khảo sát một mức kích thước và một chính sách overlap.")
    section("So sánh embedding cho câu hỏi tiếng Việt")
    p(f'Sáu bộ mã hóa nhận cùng {e["chunk_count"]:,} đoạn nguồn.'.replace("1,175","1.175")+" Mỗi đoạn vừa trần 128 token của tất cả model sau bước chuẩn bị đầu vào. Với hai model dựa trên PhoBERT, PyVi nối các âm tiết thuộc cùng từ. Với E5, câu hỏi và đoạn tài liệu lần lượt nhận tiền tố query và passage. Vị trí bằng chứng vẫn được tính trên văn bản nguồn.")
    rows=[]
    for model in e["models"]:
        if model["variant"]!="recommended_preprocessing": continue
        metric=model["metrics"]["macro"]
        rows.append([MODELS[model["model_id"].split("/")[-1]],str(model["dimension"]),number(metric["character_recall_at_5"]),number(metric["mrr_at_10_threshold_05"]),number(model["corpus_encoding_seconds"],1)])
    table("Bảng 2  Cùng đoạn nguồn và cùng chỉ mục tìm kiếm chính xác",["Bộ mã hóa","Số chiều","Độ phủ @5","MRR @10","Nhúng kho (s)"],rows,[1.85,.85,1.15,1.1,1.35],
          "Bảy câu có đáp án. MRR tính nghịch đảo hạng đầu tiên có đoạn phủ ít nhất một nửa một span chuẩn. Thời gian nhúng là một lượt GPU cho mỗi cấu hình.")
    p("BGE-M3 có độ phủ cao nhất trong lần so sánh này. E5-small có thể là lựa chọn khi cần index gọn hơn nhờ vector 384 chiều. Hai model chuyên Việt đạt độ phủ thấp hơn trên mẫu học vụ đang xét. Để tách ảnh hưởng của loại câu và độ dài đoạn, cần lặp lại trên tập đã duyệt và cả cấu hình G0 dùng đoạn dài.")
    p("Thử bỏ tiền tố E5-small giữ độ phủ Top-5 ở mức "+number(e["models"][1]["metrics"]["macro"]["character_recall_at_5"])+", trong khi MRR thay đổi từ "+number(e["models"][1]["metrics"]["macro"]["mrr_at_10_threshold_05"])+" xuống "+number(e["models"][2]["metrics"]["macro"]["mrr_at_10_threshold_05"])+". Hai danh sách có thể tìm lại cùng lượng bằng chứng nhưng đưa đoạn hữu ích lên các hạng khác nhau.")
    section("Hợp kết quả và xếp hạng lại")
    p("Thí nghiệm này trở về 156 chunk G0. BM25 tìm theo từ và BGE-M3 tìm theo vector. RRF cộng điểm dựa trên thứ hạng của từng nhánh. Cách hợp điểm có trọng số đưa điểm từng nhánh về khoảng từ 0 đến 1 trong 50 ứng viên rồi cộng hai điểm. Trọng số của nhánh dense được thử ở 25%, 50% và 75%.")
    p("Cấu hình được chọn trên bảy câu phát triển theo độ phủ Top-5, sau đó theo MRR nếu bằng điểm. Kết quả chọn là "+r["chosen_on_dev"]+". Ba reranker đều nhận cùng thứ tự ứng viên ban đầu của từng câu. Mỗi model đọc đồng thời câu hỏi và đoạn văn, tính lại mức liên quan rồi sắp thứ hạng. Nếu bằng chứng đã nằm ngoài danh sách ứng viên, bước này không thể đưa nó trở lại.")
    rows=[]
    for x in r["rerankers"]:
        if x["depth"]!=20:continue
        m=x["metrics"]["macro"]
        rows.append([RERANKERS[x["model_id"].split("/")[-1]],number(m["character_recall_at_5"]),number(m["mrr_at_10_threshold_05"]),f'{x["truncated_pairs"]}/{x["pair_count"]}',number(x["latency_p50_ms"],0)])
    before=r["fusion"][r["chosen_on_dev"]]["macro"]
    table("Bảng 3  Xếp lại 20 ứng viên của cùng một truy vấn",["Cấu hình","Độ phủ @5","MRR @10","Cặp bị cắt","p50 (ms)"],[["Trước rerank",number(before["character_recall_at_5"]),number(before["mrr_at_10_threshold_05"]),"—","—"],*rows],[1.55,1.2,1.15,1.3,1.1],
          "Giới hạn 512 token mỗi cặp. p50 là trung vị bảy lượt xếp hạng, gồm cả bước kiểm độ dài. Hồ sơ thực nghiệm còn có N bằng 10 và 50.")
    p("Ở độ sâu 20, BGE v2-m3 đưa toàn bộ các khoảng bằng chứng của bảy câu vào năm kết quả đầu. Độ phủ trước khi xếp lại đạt "+number(before["character_recall_at_5"])+". Hai mô hình còn lại cho độ phủ thấp hơn cấu hình ban đầu. BGE-base chủ yếu hướng tới tiếng Trung và tiếng Anh, nên kết quả ở đây chỉ có giá trị đối chiếu trên kho tiếng Việt này.")
    p("Cột cặp bị cắt đếm những cặp câu hỏi và đoạn vượt giới hạn đầu vào. Nếu bằng chứng nằm cuối đoạn, mô hình có thể xếp hạng mà chưa đọc đến phần đó. Khi chấm câu trả lời vẫn cần mở đúng trang nguồn để kiểm tra các điều kiện và ngoại lệ.")
    section("Trích dẫn và xử lý câu thiếu căn cứ")
    p("Ba cách sinh được kiểm tra trên cùng mười câu và cùng năm đoạn nguồn đã lưu từ Mốc 2. Qwen3:4B chạy cục bộ. Cấu hình đầu yêu cầu JSON thông thường. Cấu hình thứ hai giữ lời nhắc và ràng buộc kiểu dữ liệu bằng schema. Cấu hình thứ ba yêu cầu liệt kê những ý cần trả lời, sau đó đưa từng phát biểu kèm mã nguồn và trích đoạn nguyên văn.")
    rows=[]
    for v,label in [("standard","JSON"),("schema","JSON có schema"),("evidence_first","Kiểm quote")]:
        s=g["summary"][v]
        rows.append([label,str(s["answerable_response_rate"]["count"])+"/7",str(s["unanswerable_refusal_rate"]["count"])+"/3",str(s["unanswerable_output_withheld_rate"]["count"])+"/3"])
    table("Bảng 4  Phân biệt lời từ chối của model và đầu ra bị chặn",["Cách sinh","Đã trả lời câu có đáp án","Model từ chối câu thiếu căn cứ","Tổng đầu ra bị giữ trên câu thiếu căn cứ"],rows,[1.35,1.55,1.6,1.8],
          "Cột cuối bao gồm cả lời từ chối và lỗi kỹ thuật. Ba nhóm chạy mỗi nhóm 10 lượt. Nhãn đúng nội dung và mức hỗ trợ của trích dẫn đang chờ chấm.")
    p("Ở P009 hỏi lịch thi, cấu hình kiểm quote tự từ chối. Ở P010 hỏi học phí, đầu ra bị chặn do không tìm được quote khớp nguồn. Với P006 hỏi điều kiện làm khóa luận, cấu hình này vẫn xuất câu trả lời có quote khớp dù kho thiếu căn cứ cho câu hỏi. Kiểm được vị trí trích dẫn chưa đủ để xác nhận quy định được diễn giải đúng.")
    p("Cách kiểm quote chỉ xuất được 2 trong 7 câu có đáp án. Năm câu còn lại bị chặn ở phép đối chiếu trích đoạn. Vì vậy, cấu hình này được giữ để phân tích lỗi. Khi chấm, cần xem từng phát biểu, đoạn được dẫn và điều kiện ngoại lệ của nguồn trước khi kết luận về chất lượng câu trả lời.")
    section("Phần cần kiểm chứng trước lần đánh giá độc lập")
    p("Các phép đo hiện đã cho thấy tác động riêng của ranh giới đoạn, giới hạn ngữ cảnh và thứ hạng bằng chứng. Bước tiếp theo là bổ sung câu hỏi do sinh viên viết, duyệt đáp án và nguồn, rồi khóa tập test trước khi chọn cấu hình cuối. Bộ thử dự kiến tối thiểu 80 câu, hướng tới 100 câu, phân bổ cả trường hợp thiếu căn cứ, khác từ vựng, cần nhiều đoạn và dựa vào bảng hoặc hình.")
    p(f'Gói duyệt hiện có {a["row_count"]} mục, gồm 10 câu pilot, 12 đề xuất và 5 mục bảng. Các câu pilot đã dùng để phát triển tiếp tục thuộc dev. Mười trang OCR có ảnh gốc, bản trích chữ máy và chỗ điền bản chép chuẩn. Ba mươi lượt sinh có câu trả lời và nguồn để đối chiếu theo từng ý. Mọi số đo correctness, faithfulness và lỗi OCR còn phụ thuộc lượt chấm này.')
    p("Sau khi khóa dữ liệu, tiến hành so baseline với cấu hình chọn trên dev, giữ cùng generator. Báo cáo tiếp theo cần phân biệt truy xuất trượt, bằng chứng bị chia hoặc cắt, reranker đổi hạng, câu sinh vượt nguồn và lỗi định dạng. Kết luận về model tiếng Việt sẽ ghi rõ phạm vi tài liệu, nhóm câu và chi phí vận hành.")
    p("Phần lưu trữ vector kế thừa thử nghiệm ở Mốc 2. Lần này giữ nguyên cách tìm kiếm khi so embedding để chênh lệch do mô hình mã hóa dễ quan sát hơn. Với 156 đoạn G0, số đo trên máy cá nhân chưa cho biết hệ nào phù hợp khi kho tăng lên hàng trăm nghìn đoạn.")
    h("Minh chứng thực nghiệm")
    p("Bản làm việc cục bộ của repository franz08hmt/RAG dùng nhánh tim-hieu-rag-dot2. Mỗi bảng có thể đối chiếu trong thư mục docs/evidence/m3/runs theo tên phép thử. Tệp manifest.json ở thư mục cha lưu tên bản ghi gốc và mã SHA-256 của từng bản xuất.")
    h("Tài liệu kỹ thuật và công cụ hỗ trợ")
    p("Cách dùng model được đối chiếu từ thẻ BAAI/bge-m3, intfloat/multilingual-e5, BKAI/vietnamese-bi-encoder, dangvantuan/vietnamese-embedding và Sentence Transformers MiniLM trên Hugging Face. Phần sinh tham khảo tài liệu Structured outputs của Ollama. Danh mục đường dẫn và revision dùng thực tế đi kèm hồ sơ Mốc 3.")
    p("Công cụ AI hỗ trợ rà mã, tổ chức thực nghiệm, tổng hợp số liệu và soạn bản tiến độ. Các chỉ số trong bảng lấy từ lượt chạy cục bộ. Việc duyệt câu hỏi và chấm ngữ nghĩa được lưu riêng để sinh viên thực hiện trên tài liệu gốc.")
    doc.core_properties.title="Tìm hiểu Retrieval Augmented Generation (RAG)"
    doc.core_properties.subject="Báo cáo tiến độ Mốc 3"
    # Removing the old body does not release its binary images in python-docx.
    embedded = set(doc._element.xpath("//@r:embed | //@r:id | //@r:link"))
    for rid, relationship in list(doc.part.rels.items()):
        if relationship.reltype == RT.IMAGE and rid not in embedded:
            doc.part.drop_rel(rid)
    doc.save(args.output)
    print(args.output)


if __name__ == "__main__":
    main()
