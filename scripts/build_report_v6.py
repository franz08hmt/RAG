"""Create v6 with explicitly AI-generated evaluations, preserving v5."""
import argparse,json,re,sys
from copy import deepcopy
from pathlib import Path
from docx import Document
from docx.table import Table
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from docx.opc.constants import RELATIONSHIP_TYPE as RT
from build_m1_report_v3 import add_p,add_data_table,set_run_font
sys.stdout.reconfigure(encoding='utf8');print('Python executable:',sys.executable,flush=True)
ROOT=Path(__file__).resolve().parents[1]
ap=argparse.ArgumentParser();ap.add_argument('--commit',required=True);ap.add_argument('--output',type=Path,required=True);args=ap.parse_args()
if args.output.exists():raise FileExistsError(args.output)
sources=list((ROOT/'reports').glob('*_RAG_Bao_Cao_Cuoi_Ky_v5.docx'))
if len(sources)!=1:raise ValueError('Expected one v5 report')
doc=Document(sources[0]);s=json.loads((ROOT/'docs/evidence/v6/judge_summary.json').read_text(encoding='utf8'))
def find(prefix):
 p=[x for x in doc.paragraphs if x.text.startswith(prefix)]
 if len(p)!=1:raise ValueError((prefix,len(p)))
 return p[0]
def replace(p,text):
 style=deepcopy(p.runs[0]._r.rPr) if p.runs and p.runs[0]._r.rPr is not None else None
 p.clear();r=p.add_run(text)
 if style is not None:r._r.insert(0,style)
 else:set_run_font(r,12)
def insert(anchor,callback):
 old=set(doc.element.body);callback()
 for node in [x for x in doc.element.body if x not in old]:anchor._p.addprevious(node)
def para(text):return add_p(doc,text)
def linked(p,label,url):
 rid=doc.part.relate_to(url,RT.HYPERLINK,is_external=True);h=OxmlElement('w:hyperlink');h.set(qn('r:id'),rid)
 r=OxmlElement('w:r');pr=OxmlElement('w:rPr');fonts=OxmlElement('w:rFonts');fonts.set(qn('w:ascii'),'Times New Roman');fonts.set(qn('w:hAnsi'),'Times New Roman');pr.append(fonts)
 sz=OxmlElement('w:sz');sz.set(qn('w:val'),'24');pr.append(sz);r.append(pr);t=OxmlElement('w:t');t.text=label;r.append(t);h.append(r);p._p.append(h)

edits={
'Bộ development chính có 10 câu':lambda t:t.replace(' Chưa có tập test độc lập đã được người học duyệt và đóng băng.',' Tập này được dùng để phát triển, không phải test độc lập.'),
'Kết quả này là thống kê cấu trúc':lambda t:t.replace('phải có danh sách vùng bảng do người kiểm tra đánh dấu','cần một danh sách vùng bảng tham chiếu'),
'Ở Mốc 3, phạm vi kiểm tra được mở':lambda t:'Ở Mốc 3, phép thử OCR mở rộng sang mười trang G0 và ghi nhận số ký tự cùng thời gian xử lý. Không công bố CER/WER cho mười trang vì không có bản chép chuẩn phù hợp để làm mẫu đối chiếu.',
'Trên mười trang chọn trước':lambda t:t.replace(' Mười bản chép chuẩn đang chờ người học duyệt để tính tỷ lệ lỗi ký tự và từ.',''),
'Với sơ đồ, nhận được các nhãn chữ':lambda t:t.replace('yêu cầu người đọc kiểm tra hình gốc','đối chiếu với hình gốc'),
'Đối chiếu sơ bộ do trợ lý AI':lambda t:t.replace('do trợ lý AI thực hiện','do trợ lý AI Codex thực hiện').replace(' Các nhãn này cần sinh viên đối chiếu lại; sáu vùng ảnh được chọn có chủ đích và không đại diện cho mọi tài liệu.',' Sáu vùng ảnh được chọn có chủ đích và không đại diện cho mọi tài liệu.'),
'Lượt vision_20261126':lambda t:t.replace('Đây là hành vi đầu ra, chưa phải độ chính xác; nhãn đúng sai và so sánh với OCR/SmolVLM2 cần người học chấm.','Đây là hành vi đầu ra; nhãn của mô hình chấm được trình bày ở mục 5.5.1.'),
'Lượt arrow_20261126':lambda t:t.replace('Cần người học chấm thứ tự và chiều mũi tên; không suy ra độ chính xác từ việc mô hình tạo được đầu ra.','Thứ tự và chiều mũi tên được đánh giá bởi mô hình chấm; việc tạo được đầu ra không tự chứng minh độ chính xác.'),
'P006 hỏi các điều kiện':lambda t:t.replace('Nhận xét này dùng để phân tích lỗi; chưa được tính thành điểm chấm người.','Nhận xét của trợ lý AI Codex được dùng để phân tích lỗi.'),
'Cột cuối bao gồm cả lời từ chối':lambda t:'Cột cuối bao gồm cả lời từ chối và lỗi kỹ thuật. Ba nhóm chạy mỗi nhóm 10 lượt; bảng phản ánh hành vi vận hành, không phải điểm đúng nội dung.',
'Đánh giá sinh câu trả lời cần thêm':lambda t:'Đánh giá sinh câu trả lời đối chiếu đáp án tham chiếu, nguồn và mệnh đề trong câu trả lời. Các chỉ số vận hành và định dạng không đồng nghĩa độ chính xác; mục 5.5.1 trình bày nhãn do các giám khảo AI tạo.',
'Lượt console kiểm tra lại ngày 25/10':lambda t:t.replace('phần nội dung vẫn chờ đối chiếu ngữ nghĩa','ID hợp lệ không tự chứng minh nội dung được nguồn hỗ trợ'),
'Cột đúng đủ có nguồn dùng':lambda t:t.replace(' Cần người học đối chiếu các nhãn trước khi dùng cho kết luận đánh giá độc lập.',''),
'Lượt scope_rrf12_20261127':lambda t:t.replace(' Các trạng thái này chưa phải điểm đúng; cần sinh viên đối chiếu nhãn và tài liệu.',' Các trạng thái này chưa phải điểm đúng; kết quả mô hình chấm nằm ở mục 5.5.1.'),
'Cấu hình mặc định được chọn':lambda t:t.replace('Các lựa chọn cần được kiểm chứng lại bằng câu hỏi độc lập và nhãn người.','Các lựa chọn cần được thử trên dữ liệu độc lập.'),
'Kết luận giới hạn trong snapshot G0':lambda t:'Kết luận giới hạn trong snapshot G0, tập câu hỏi nháp và các nhãn do AI tạo. Trong lượt scope_rrf12, 5/6 câu nháp thiếu căn cứ vẫn được hệ thống trả lời; ví dụ U13 hỏi quy định một trường khác nhưng dùng nguồn HCMUTE. Chưa có kiểm định bởi người; judge có thể thiên lệch, diễn giải sai nguồn hoặc lặp lại sai lệch của đáp án tham chiếu, vì vậy điểm judge chỉ mang tính tham khảo [13, 14]. Với mười trang OCR không có bản chép chuẩn phù hợp nên chỉ trình bày thống kê ký tự và thời gian; CER/WER của bốn trang Mốc 1 được giữ riêng. Khi dùng quy định hiện hành phải xác minh hiệu lực và sửa lỗi metadata trước khi tin cậy trích dẫn.'}
for prefix,fn in edits.items():
 p=find(prefix);replace(p,fn(p.text))
tool=find('Codex hỗ trợ viết mã')
replace(tool,'Codex hỗ trợ viết mã, tổ chức thực nghiệm, biên tập báo cáo và tạo nhãn đối chiếu sơ bộ cho các đầu ra hình. Gemma 3 4B chạy qua Ollama là giám khảo AI thứ hai; Qwen3:4B sinh câu trả lời, Tesseract trích chữ, SmolVLM2 và Qwen2.5-VL tạo mô tả ảnh. Claude Code hỗ trợ bản tiến độ trước. Sinh viên chịu trách nhiệm về báo cáo; các nhãn trong mục 5.5.1 đều do AI tạo.')

table1=Table(find('Bảng 1  ')._p.getnext(),doc)
for row in table1.rows:
 for cell in row.cells:
  for p in cell.paragraphs:
   if 'Đầu ra chờ người học chấm' in p.text:replace(p,'Mô hình Gemma chấm; một phần có nhãn Codex')
summary=Table(find('Bảng 26  Tổng kết')._p.getnext(),doc)
for row in summary.rows[1:]:
 key=row.cells[0].text.strip()
 if key=='Input, OCR, bảng, hình':replace(row.cells[4].paragraphs[0],'Mẫu hình nhỏ; nhận xét do AI tạo')
 elif key=='Embedding':replace(row.cells[4].paragraphs[0],'Chi phí VRAM; 43 câu nháp')
 elif key=='Đánh giá':
  replace(row.cells[1].paragraphs[0],'Retrieval, đầu-cuối, OCR, hình và judge AI')
  replace(row.cells[2].paragraphs[0],'Theo dõi từng tầng; Gemma 3 4B')
  replace(row.cells[3].paragraphs[0],'59 đầu ra; hai lượt mỗi đầu ra')
  replace(row.cells[4].paragraphs[0],'Đồng thuận AI không chứng minh độ đúng')
for t in doc.tables:
 if t.rows[0].cells[0].text.strip()=='YC':
  changes={'YC4':'OCR và hai VLM; 42 đầu ra hình được Gemma chấm hai lượt.',
           'YC10':'RRF, schema, trích dẫn và từ chối; có phân tích lỗi và nhãn judge AI.',
           'YC11':'Các chỉ số retrieval; nhãn Codex/Gemma và độ ổn định, có giới hạn.'}
  for row in t.rows[1:]:
   key=row.cells[0].text.strip()
   if key in changes:replace(row.cells[1].paragraphs[0],changes[key])
replace(find('Bảng đối chiếu cập nhật đến ngày'),'Bảng đối chiếu cập nhật đến ngày 28/11/2026; nhãn đánh giá trong báo cáo do AI tạo.')
find('PHỤ LỤC C KẾT QUẢ').paragraph_format.keep_with_next=True

def judge_section():
 heading=doc.add_paragraph('5.5.1 Đánh giá bằng mô hình chấm (LLM-as-judge)',style='Heading 2')
 for run in heading.runs:set_run_font(run,13,bold=True)
 para('Giám khảo A là trợ lý AI Codex với 24 nhãn có sẵn cho OCR và SmolVLM2 trên sáu vùng hình. Codex đối chiếu câu hỏi, đáp án gợi ý và nội dung ảnh, gán đúng, đúng một phần hoặc sai; các lượt mô hình từ chối được giữ thành nhãn hành vi riêng. Không có nhãn A sẵn cho 12 câu RRF, năm câu demo, Qwen2.5-VL và sơ đồ mũi tên; không tạo hồi tố nhãn A cho các lượt này.')
 para('Giám khảo B là Gemma 3 4B qua Ollama, khác họ Qwen; dữ liệu và ảnh chỉ xử lý cục bộ, không gọi Gemini. Mỗi đầu ra được chấm hai lần ở temperature 0 theo JSON schema, với câu hỏi, đáp án gợi ý, nguồn, đầu ra và ảnh nếu có. Đối với văn bản, judge được cung cấp cả ID nguồn thực sự được dẫn. Rubric gồm: đúng, đúng một phần, sai, từ chối đúng và trả lời khi đáng ra phải từ chối; mức nguồn hỗ trợ được ghi riêng là đủ, một phần, không hỗ trợ hoặc không áp dụng.')
 groups=s['groups']; specs=[('12 câu RRF',['qa12']),('5 câu demo',['demo5']),('OCR, sáu hình',['image_ocr']),('SmolVLM2, sáu hình',['image_vlm_inference']),('Qwen2.5-VL, sáu hình',['image_qwen_vl']),('Sơ đồ mũi tên',[x for x in groups if x.startswith('arrow_')])]
 keys=['correct','partial','incorrect','correct_refusal','should_refuse'];rows=[]
 for label,names in specs:
  n=sum(groups[g]['valid_count'] for g in names)
  vals=[sum(groups[g]['labels'].get(k,0) for g in names) for k in keys]
  rows.append([label,str(n),*[str(v) for v in vals]])
 add_data_table(doc,'Bảng X  Kết quả giám khảo B theo đầu ra',['Nhóm','Số','Đúng','Một phần','Sai','Từ chối đúng','Đáng ra từ chối'],rows,[1.35,.45,.63,.7,.6,1.12,1.45],
  f"Nhãn do AI Gemma tạo, lượt thứ nhất. Run hình {s['judge_b_run_id']}; run văn bản {s['judge_b_text_run_id']}; tổng hợp {s['run_id']}. Đây không phải độ chính xác đã được xác nhận.")
 support={k:sum(v['support'].get(k,0) for v in groups.values()) for k in ('supported','partial','unsupported','not_applicable')}
 para(f"Theo nhãn Gemma, mức hỗ trợ là đủ {support['supported']}/59, một phần {support['partial']}/59, không hỗ trợ {support['unsupported']}/59 và không áp dụng {support['not_applicable']}/59. Một câu từ chối trong demo vẫn bị Gemma gán không hỗ trợ thay vì không áp dụng; nhãn được giữ nguyên và cho thấy judge chưa tuân thủ rubric hoàn toàn.")
 stable=s['judge_b_repeat_stability'];pair=s['judge_a_vs_b'];kap=pair['cohen_kappa'];k='không xác định' if kap is None else f'{kap:.2f}'.replace('.',',')
 para(f"Lặp lại cùng đầu vào: Gemma trùng nhãn {stable['label_agree']}/{stable['paired_valid']} và trùng nhãn hỗ trợ {stable['support_agree']}/{stable['paired_valid']}. Codex có 24 nhãn hình, trong đó 14 nhãn chỉ ghi hành vi model_abstained chứ không đánh giá đúng/sai nên không đưa vào kappa. Trên {pair['comparable_count']} cặp nhãn còn lại, hai giám khảo AI đồng thuận {pair['observed_agreement']*100:.0f}% và Cohen’s kappa = {k}; mẫu nhỏ, không diễn giải là độ chính xác. Lặp lại ổn định cũng không chứng minh nhãn đúng.")
 para('Hai trường hợp lệch nhãn: I04-Q2 với SmolVLM2 được Codex chấm sai còn Gemma chấm đúng; lý do của Gemma nhắc đáp án mẫu nhưng không giải thích vì sao đầu ra ngắn khớp. I06-Q2 với OCR được Codex chấm một phần còn Gemma chấm đúng; đầu ra rút gọn chủ đề trong khi câu hỏi yêu cầu tiêu đề đầy đủ. Đây là sự khác nhau giữa hai nhãn AI, không tự xác định giám khảo nào đúng.')
 para('Gemma có dấu hiệu bỏ sót phạm vi: bốn trong năm câu nháp thiếu căn cứ nhưng vẫn được hệ thống trả lời lại bị judge gán đúng. Ví dụ U13 hỏi quy định của một trường khác, trong khi nguồn thuộc HCMUTE. Bởi vậy không dùng số “đúng” trong bảng làm bằng chứng rằng RAG trả lời chính xác; cần xem các đầu ra và lý do chấm kèm theo.')
insert(find('5.6 Minh họa qua console'),judge_section)
insert(find('Phiên bản model thực chạy'),lambda:para('[24] Ollama. Gemma 3 4B model card và cấu hình local. https://ollama.com/library/gemma3:4b'))

for rel in doc.part.rels.values():
 if rel.reltype==RT.HYPERLINK and 'github.com/franz08hmt/RAG/' in rel.target_ref:
  target=re.sub(r'(?<=/blob/)[0-9a-f]{40}(?=/)',args.commit,rel.target_ref)
  rel._target=re.sub(r'(?<=/tree/)[0-9a-f]{40}(?=/|$)',args.commit,target)
replace(find('Mã nguồn và minh chứng tại'),f'Mã nguồn và minh chứng tại https://github.com/franz08hmt/RAG/tree/{args.commit}. Commit minh chứng: {args.commit[:12]}. Các đường dẫn bên dưới cố định theo commit này.')
links=find('Mở commit và danh mục mã nguồn')
for label,name in [(' · Kết quả judge AI','judge_summary.json'),(' · Nhãn từng lượt','judge_rows.json'),(' · Cấu hình judge','judge_configs.json')]:
 linked(links,label,f'https://github.com/franz08hmt/RAG/blob/{args.commit}/docs/evidence/v6/{name}')
mapping={};count=0
for p in doc.paragraphs:
 m=re.match(r'^Bảng (\d+|X)  ',p.text)
 if m:
  count+=1
  if m.group(1)!='X':mapping[int(m.group(1))]=count
  replace(p,re.sub(r'^Bảng (?:\d+|X)',f'Bảng {count}',p.text,count=1))
def refs(p):
 if re.match(r'^Bảng \d+  ',p.text):return
 for r in p.runs:
  if r._r.xpath('.//w:drawing | .//w:pict'):continue
  updated=re.sub(r'Bảng (\d+)(?!\d)',lambda m:'Bảng '+str(mapping.get(int(m.group(1)),int(m.group(1)))),r.text)
  if updated!=r.text:r.text=updated
for p in doc.paragraphs:refs(p)
for t in doc.tables:
 for row in t.rows:
  for cell in row.cells:
   for p in cell.paragraphs:refs(p)
doc.save(args.output);print(args.output)
