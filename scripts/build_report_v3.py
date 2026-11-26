"""Make a new evidence-linked report from v2; student reviews remain untouched."""
from copy import deepcopy
from pathlib import Path
import argparse, json, re, sys
from docx import Document
from docx.text.paragraph import Paragraph
from docx.table import Table
from docx.opc.constants import RELATIONSHIP_TYPE as RT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from build_m1_report_v3 import add_p, add_data_table, set_run_font

print('Python executable:',sys.executable,flush=True)
ROOT=Path(__file__).resolve().parents[1]
ap=argparse.ArgumentParser();ap.add_argument('--commit',required=True);ap.add_argument('--output',type=Path,required=True)
args=ap.parse_args()
if args.output.exists():raise FileExistsError(args.output)
sources=list((ROOT/'reports').glob('*_RAG_Bao_Cao_Cuoi_Ky_v2.docx'))
if len(sources)!=1:raise ValueError('Expected exactly one v2 report')
doc=Document(sources[0])
def find(prefix):
    matches=[p for p in doc.paragraphs if p.text.startswith(prefix)]
    if len(matches)!=1:raise ValueError((prefix,len(matches)))
    return matches[0]
def replace(p,text):
    formatting=deepcopy(p.runs[0]._r.rPr) if p.runs and p.runs[0]._r.rPr is not None else None
    p.clear(); r=p.add_run(text)
    if formatting is not None:r._r.insert(0,formatting)
    else:set_run_font(r,12)
def delete(p):p._element.getparent().remove(p._element)
def insert(anchor,callback):
    old=set(doc.element.body);callback()
    for x in [x for x in doc.element.body if x not in old]:anchor._p.addprevious(x)
def para(s):return add_p(doc,s)
def table(caption,headers,rows,widths,note):return add_data_table(doc,caption,headers,rows,widths,note)
def linked(p,label,url):
    rid=doc.part.relate_to(url,RT.HYPERLINK,is_external=True);h=OxmlElement('w:hyperlink');h.set(qn('r:id'),rid)
    r=OxmlElement('w:r');pr=OxmlElement('w:rPr');fonts=OxmlElement('w:rFonts');fonts.set(qn('w:ascii'),'Times New Roman');fonts.set(qn('w:hAnsi'),'Times New Roman');pr.append(fonts)
    sz=OxmlElement('w:sz');sz.set(qn('w:val'),'24');pr.append(sz);r.append(pr);t=OxmlElement('w:t');t.text=label;r.append(t);h.append(r);p._p.append(h)

config_table=Table(find('Bảng 1  ')._p.getnext(),doc)
for values in [
    ('Chunking 43 câu','Sáu cách, 57 span','Độ phủ Top-5 và ngân sách 1.000 token'),
    ('Embedding 43 câu','Sáu model; trần chung và riêng','Độ phủ, thứ hạng, thời gian và bộ nhớ'),
    ('Reranker 43 câu','Cùng pool RRF Top-20','Ba model và trần 512/1.024/2.048 token'),
    ('VLM và OCR','Sáu vùng; hai câu mỗi vùng','Đầu ra chờ người học chấm')]:
    new=deepcopy(config_table.rows[-1]._tr);config_table._tbl.append(new)
    row=config_table.rows[-1]
    for cell,value in zip(row.cells,values):replace(cell.paragraphs[0],value)

# Preserve the historical tables in appendix C, together with their captions and source notes.
appendix=find('TÀI LIỆU THAM KHẢO')
appendix.paragraph_format.page_break_before=False
insert(appendix,lambda:para('PHỤ LỤC C KẾT QUẢ THĂM DÒ BẢY CÂU'))
insert(find('Phiên bản model thực chạy'),lambda:para('[23] Qwen2.5-VL 3B, model card Ollama. https://ollama.com/library/qwen2.5vl:3b'))
for n in (11,12):
    caption=find(f'Bảng {n}  '); tbl=caption._p.getnext();note=tbl.getnext()
    if not tbl.tag.endswith('}tbl') or not note.tag.endswith('}p'):raise ValueError('Unexpected table structure')
    for element in (caption._p,tbl,note):appendix._p.addprevious(element)
for prefix in ('Recall ký tự trung bình là 89,44%', 'Kết quả giúp thu hẹp cách diễn giải.',
               'BGE-M3 có độ phủ cao nhất trong lần so sánh này.', 'Thử bỏ tiền tố E5-small',
               'Nguồn M3-EM. Tập 1.175 đoạn'):
    delete(find(prefix))
insert(find('3.5 Mở rộng'),lambda:para('Hai phép so sánh thăm dò trên bảy câu được giữ ở Phụ lục C. Phần kết luận chính bên dưới dựa trên 43 câu và nêu rõ tập đoạn của từng lượt.'))

replace(find('Chia theo ký tự và token phù hợp'), 'Trong sáu cách chia, kết quả còn tùy ngân sách context và việc bằng chứng bị cắt qua ranh giới đoạn. Bảng khuyến nghị dưới đây chỉ áp dụng cho tập quy chế và 43 câu nháp của phép thử; chi phí tính toán chưa được đo riêng cho từng cách.')
cap=find('Bảng 10  ');t=Table(cap._p.getnext(),doc)
guidance={
 'characters':'250 đoạn; phủ 0,749 ở 1.000 token; 8/57 span không nằm trọn. Phù hợp khi tài liệu ít cấu trúc.',
 'tokens':'208 đoạn; phủ 0,704; 6/57 span không nằm trọn. Hữu ích khi phải kiểm soát trần tokenizer.',
 'recursive':'284 đoạn; phủ 0,754; 3/57 span không nằm trọn. Phù hợp văn bản có đoạn và câu.',
 'sentences':'236 đoạn; phủ 0,794; 1/57 span không nằm trọn, ít nhất trong sáu cách. Phù hợp câu hỏi cần trọn câu.',
 'structure':'225 đoạn; phủ 0,873, cao nhất ở 1.000 token; 9/57 span không nằm trọn. Hợp quy chế có Điều rõ.',
 'semantic':'507 đoạn; phủ 0,766; 2/57 span không nằm trọn; cần thêm xử lý để quyết định ranh giới.'}
for row in t.rows[1:]:
    key=row.cells[0].text.strip();replace(row.cells[1].paragraphs[0],guidance[key])
replace(t.rows[0].cells[1].paragraphs[0],'Khuyến nghị dựa trên số đo')
replace(find('Độ phủ lấy từ cùng phép thử'), 'Nguồn Bảng 9: cùng phép thử 43 câu; cột cuối là độ phủ Top-5. Phủ 1.000 token và span bị cắt được giải thích trong từng dòng.')
replace(find('Trong điều kiện trần kiến trúc và 156 đoạn G0'), 'Trên dữ liệu học vụ và 43 câu nháp này, BGE-M3 là lựa chọn mạnh về độ phủ: trần riêng đạt 0,949; E5-small đạt 0,930 và nhúng nhanh hơn (1,3 so với 11,8 giây). Khoảng bootstrap chênh lệch độ phủ của E5-small so với BGE-M3 bao gồm 0 nên chưa đủ khẳng định hơn kém ổn định. Bộ nhớ CUDA cấp phát đỉnh lần lượt khoảng 2,52 và 0,52 GiB. Hai model dùng PhoBERT có trần kiến trúc 256, làm cắt 139/156 đoạn G0; cách tách từ và biểu diễn cũng có thể ảnh hưởng. Chưa có phép thử kiểm soát để quy riêng nguyên nhân cho tách từ hay năng lực tiếng Việt của model.')
insert(find('4.2 Reranker'),lambda:para('Kết quả RRF thấp trên bảy câu ở Bảng 15 là phép thử khác: dùng cửa sổ chunk và thiết lập của Mốc 2. Bảng 23 chỉ so BM25, dense và Weighted75 trên 43 câu G0, nên Weighted75 dẫn đầu trong nhóm được đưa vào bảng đó, không phải mọi phương án fusion. Trong phép chọn pool 43 câu ở Bảng 18, RRF đạt độ phủ 0,99994 và MRR 0,903, cao hơn Weighted75 trên cùng lượt. Khác tập câu hỏi, chunk và danh sách phương án không cho phép quy chênh lệch chỉ cho thuật toán.'))
replace(find('Kịch bản năm câu được chạy'), 'Kịch bản năm câu được chạy cục bộ trong lượt console_demo_20261125T061017Z. Câu Bảng 1 trả đúng các số nhưng metadata ghi Điều 15. Dòng tham chiếu “Điều 15 của Quy chế này” đứng đầu dòng sau trích xuất và bị bộ nhận diện xem nhầm là tiêu đề Điều; chunk vì vậy mang nhãn sai dù chứa Bảng 1 ở trang PDF 3. Giữ snapshot cũ để bảo toàn phép đo; khi sửa cần kiểm tra lại nhận diện đề mục và xây lại chỉ mục. Hai câu khác còn thiếu điều kiện, còn câu ngoài phạm vi được từ chối.')
replace(find('Kết quả cho thấy hợp điểm có ích'), 'Trong phép thử trên 43 câu nháp, Weighted75 là cấu hình đối chiếu đầu-cuối, còn RRF cho pool tốt hơn trong lượt so fusion riêng. Kịch bản console đã chạy dùng BM25, Qwen3:4B, JSON Schema và cửa sổ 8.192; cấu hình này dễ quan sát nhưng chưa phải cấu hình đã được xác nhận tốt nhất. Reranker có thể thay đổi thứ hạng và tốn thêm thời gian; cần xem kết quả theo từng trần đầu vào, không mặc định rằng thêm reranker sẽ cải thiện.')
replace(find('Các kết luận giới hạn trong G0'), 'Kết luận giới hạn trong snapshot G0 và bộ câu hỏi chưa được người học xác nhận. Các phép đọc hình đã được chạy nhưng cần chấm đúng sai; OCR cần bản chép chuẩn của người học; đánh giá đầu-cuối còn cần nhãn người và 15 câu test chưa dùng chọn cấu hình. Khi dùng quy định hiện hành phải xác minh hiệu lực, quan hệ giữa các văn bản và sửa lỗi metadata trước khi tin cậy trích dẫn.')
replace(find('Bảng đối chiếu cập nhật đến ngày'), 'Bảng đối chiếu cập nhật đến ngày 26/11/2026; kết quả chấm người và tập test riêng chưa có.')
tools=find('Codex hỗ trợ viết mã');replace(tools,tools.text.replace('SmolVLM2 tạo mô tả ảnh','SmolVLM2 và Qwen2.5-VL tạo mô tả ảnh'))
for x in doc.tables:
    if x.rows[0].cells[0].text.strip()=='YC':
        updates={'YC4':'OCR và hai VLM trên sáu vùng cùng một sơ đồ mũi tên; đang chờ nhãn người.',
                 'YC9':'Ba reranker trên 43 câu; BGE được thử thêm trần 1.024 và 2.048.',
                 'YC11':'Có số đo retrieval và đầu-cuối; chưa có chấm người và test độc lập.',
                 'YC12':'Ứng dụng console; đã chạy kịch bản năm câu và lưu log.'}
        for row in x.rows[1:]:
            key=row.cells[0].text.strip()
            if key in updates:replace(row.cells[1].paragraphs[0],updates[key])

length=json.loads((ROOT/'docs/evidence/v3/reranker_lengths.json').read_text(encoding='utf8'))
vision=json.loads((ROOT/'docs/evidence/v3/vision.json').read_text(encoding='utf8'))
arrow=json.loads((ROOT/'docs/evidence/v3/arrow.json').read_text(encoding='utf8'))
def rerank_extra():
    rows=[]
    for x in length['results']:
        if x['status']=='complete':
            m=x['metrics']['macro'];rows.append([str(x['max_length']),f"{x['truncated_pairs']}/{x['pair_count']}",f"{m['character_recall_at_5']:.3f}".replace('.',','),f"{m['mrr_at_10_threshold_05']:.3f}".replace('.',','),f"{x['latency_p50_ms']:.0f}"])
        else:rows.append([str(x['max_length']),'—','—','—','Không đủ VRAM'])
    table('Bảng X  BGE v2-m3 với trần đầu vào lớn hơn',['Trần token','Cặp bị cắt','Phủ Top-5','MRR@10','p50 ms'],rows,[1.25,1.4,1.2,1.2,1.25],f"Nguồn {length['run_id']}; 43 câu, cùng pool RRF Top-20, batch size 1. Thời gian không so trực tiếp với lượt 512 dùng batch size 4.")
    para('Ở pool này độ phủ trước rerank đã làm tròn 1,000. Lượt 512 token giảm MRR từ 0,903 xuống 0,857; khi nâng lên 1.024 hoặc 2.048, không còn cặp nào bị cắt và MRR trở lại 0,903. Đây là kết quả phù hợp với giả thuyết việc cắt ảnh hưởng thứ hạng, chưa chứng minh toàn bộ nguyên nhân giảm MRR; reranker không làm tăng độ phủ vốn đã gần trần.')
insert(find('4.3 Sinh câu trả lời'),rerank_extra)
def vision_extra():
    total=len(vision['questions']);abst=sum(x.get('abstain') is True for x in vision['questions']);valid=sum(x.get('valid_json') is True for x in vision['questions'])
    para(f"Lượt {vision['run_id']} bổ sung Qwen2.5-VL 3B chạy cục bộ trên cùng sáu vùng ảnh, rồi dùng Qwen3:4B trả lời 12 câu theo schema như lượt trước. Có {valid}/{total} đầu ra đúng định dạng, trong đó {abst}/{total} đầu ra có nhãn tự từ chối. Đây là hành vi đầu ra, chưa phải độ chính xác; nhãn đúng sai và so sánh với OCR/SmolVLM2 cần người học chấm. Mô tả hình là nội dung suy ra, không phải trích dẫn nguyên văn.")
    para(f"Lượt {arrow['run_id']} bổ sung một sơ đồ có mũi tên ở Sổ tay trang PDF 136: hai câu hỏi được xử lý qua OCR và hai VLM, tạo sáu đầu ra đúng định dạng. Cần người học chấm thứ tự và chiều mũi tên; không suy ra độ chính xác từ việc mô hình tạo được đầu ra.")
insert(find('CHƯƠNG 3 CHIA ĐOẠN'),vision_extra)
find('CHƯƠNG 3 CHIA ĐOẠN').paragraph_format.page_break_before=False
for p in doc.paragraphs:
    if 'Mẫu chưa có sơ đồ mũi tên nên chưa đo được lỗi đảo chiều hoặc sai quan hệ mũi tên.' in p.text:
        replace(p,p.text.replace('Mẫu chưa có sơ đồ mũi tên nên chưa đo được lỗi đảo chiều hoặc sai quan hệ mũi tên.','Lượt sáu vùng ban đầu chưa có sơ đồ mũi tên; phép bổ sung được mô tả ở đoạn sau.'))
def summary():
    rows=[['Input, OCR, bảng, hình','PyMuPDF, Tesseract; hai VLM','PyMuPDF, OCR khi cần','Bảng 5 và mục 2.6; nội dung hình là suy ra','OCR và hình chưa có nhãn người'],
          ['Chunking','Sáu cách chia','G0 theo Điều, cửa sổ dự phòng','Bảng 9: theo Điều phủ 0,873 ở 1.000 token','9/57 span không nằm trọn một đoạn'],
          ['Embedding','Sáu model, hai trần','BGE-M3','Bảng 13: phủ 0,949 trên G0','Chi phí VRAM; 43 câu chưa được duyệt'],
          ['Vector store','FlatIP, HNSW, IVF','FAISS FlatIP','Bảng 14: đối chiếu exact trên G0 nhỏ','Chưa kết luận cho corpus lớn'],
          ['Retrieval','BM25, dense, RRF, Weighted75','BM25 trong demo; Weighted75 để đối chiếu','Bảng 23; RRF tốt hơn trong lượt fusion riêng','Khác pool và bộ câu, thiếu test độc lập'],
          ['Reranker','Ba model, nhiều trần','Tắt trong demo BM25','Bảng 18 và phép trần mới; không tăng phủ gần 1','Độ trễ, cắt và thay đổi hạng'],
          ['Sinh và từ chối','Qwen3; prompt và schema','Qwen3:4B, schema, 8.192','Bảng 25: còn câu sai và từ chối thiếu','Schema không đảm bảo đúng nội dung'],
          ['Đánh giá','Retrieval, đầu-cuối, OCR, hình','Theo dõi riêng từng tầng','43 câu nháp, 12 câu đầu-cuối','Chưa có nhãn người và 15 câu test']]
    table('Bảng X  Tổng kết lựa chọn theo từng công đoạn',['Công đoạn','Phương án đã thử','Console','Lý do và số liệu','Giới hạn'],rows,[1.05,1.22,1.12,1.65,1.26],'Các lựa chọn phản ánh phiên bản console đã chạy; số liệu chỉ có hiệu lực trong giao thức đã mô tả.')
insert(find('PHỤ LỤC A MINH CHỨNG'),summary)

# Link the exact pushed source revision; keep previously existing evidence paths.
for rel in doc.part.rels.values():
    if rel.reltype==RT.HYPERLINK and 'github.com/franz08hmt/RAG/' in rel.target_ref:
        rel._target=re.sub(r'(?<=/blob/)[0-9a-f]{40}(?=/)',args.commit,rel.target_ref)
        rel._target=re.sub(r'(?<=/tree/)[0-9a-f]{40}(?=/|$)',args.commit,rel._target)
location=find('Mã nguồn và minh chứng có thể đối chiếu')
replace(location,f'Mã nguồn và minh chứng tại https://github.com/franz08hmt/RAG/tree/{args.commit}. Commit minh chứng: {args.commit[:12]}. Các đường dẫn bên dưới cố định theo commit này.')
links=find('Mở commit và danh mục mã nguồn')
for label,name in [(' · Reranker dài','reranker_lengths.json'),(' · VLM local','vision.json'),(' · Sơ đồ mũi tên','arrow.json')]:
    linked(links,label,f'https://github.com/franz08hmt/RAG/blob/{args.commit}/docs/evidence/v3/{name}')

# Renumber captions and prose cross-references simultaneously, including moved tables.
mapping={};idx=0
for p in doc.paragraphs:
    match=re.match(r'^Bảng (\d+|X)  ',p.text)
    if match:
        idx+=1
        if match.group(1)!='X':mapping[int(match.group(1))]=idx
        replace(p,re.sub(r'^Bảng (?:\d+|X)',f'Bảng {idx}',p.text,count=1))
for p in doc.paragraphs:
    if re.match(r'^Bảng \d+  ',p.text):continue
    for run in p.runs:
        if run._r.xpath('.//w:drawing | .//w:pict'):continue
        updated=re.sub(r'Bảng (\d+)(?!\d)',lambda m:'Bảng '+str(mapping.get(int(m.group(1)),int(m.group(1)))),run.text)
        if updated!=run.text:run.text=updated

# Decimal commas for data, while retaining thousands, headings, URLs, IDs and model names.
def commas(run):
    if run._r.xpath('.//w:drawing | .//w:pict'):return
    s=run.text
    s=re.sub(r'(?<![\w/.:])0\.(\d+)(?![\w/.])',r'0,\1',s)
    s=re.sub(r'(?<![\w/.:])(\d{1,2})\.(\d{1,2})(?=\s*(?:giây|GiB|ms|;|$))',r'\1,\2',s)
    s=s.replace('Prec.','Độ chính xác ký tự').replace('TB token','Token trung bình')
    if s!=run.text:run.text=s
for p in doc.paragraphs:
    for r in p.runs:commas(r)
for tbl in doc.tables:
    for row in tbl.rows:
        for cell in row.cells:
            for p in cell.paragraphs:
                for r in p.runs:
                    if r._r.xpath('.//w:drawing | .//w:pict'):continue
                    updated=re.sub(r'Bảng (\d+)(?!\d)',lambda m:'Bảng '+str(mapping.get(int(m.group(1)),int(m.group(1)))),r.text)
                    if updated!=r.text:r.text=updated
                    commas(r)
                    if re.fullmatch(r'\d{2,}\.\d{2,}',r.text):r.text=r.text.replace('.',',')
doc.save(args.output);print(args.output,flush=True)
