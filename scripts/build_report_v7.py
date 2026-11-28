"""Create v7 from v6 with deterministic scope-aware presentation only."""
import argparse,json,re,sys
from copy import deepcopy
from pathlib import Path
from docx import Document
from docx.table import Table
from docx.shared import Inches
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.opc.constants import RELATIONSHIP_TYPE as RT
from build_m1_report_v3 import add_p,set_run_font

sys.stdout.reconfigure(encoding='utf8');print('Python executable:',sys.executable,flush=True)
ROOT=Path(__file__).resolve().parents[1]
ap=argparse.ArgumentParser();ap.add_argument('--commit',required=True);ap.add_argument('--output',type=Path,required=True);args=ap.parse_args()
if args.output.exists():raise FileExistsError(args.output)
sources=list((ROOT/'reports').glob('*_RAG_Bao_Cao_Cuoi_Ky_v6.docx'))
if len(sources)!=1:raise ValueError('Expected one v6 report')
doc=Document(sources[0]);scope=json.loads((ROOT/'docs/evidence/v7/scope_presentation.json').read_text(encoding='utf8'))
judge=json.loads((ROOT/'docs/evidence/v6/judge_summary.json').read_text(encoding='utf8'))
def find(prefix):
 found=[p for p in doc.paragraphs if p.text.startswith(prefix)]
 if len(found)!=1:raise ValueError((prefix,len(found)))
 return found[0]
def replace(p,text):
 style=deepcopy(p.runs[0]._r.rPr) if p.runs and p.runs[0]._r.rPr is not None else None
 p.clear();r=p.add_run(text)
 if style is not None:r._r.insert(0,style)
 else:set_run_font(r,12)
def textcell(cell,text):
 replace(cell.paragraphs[0],str(text))
 for p in cell.paragraphs[1:]:p._element.getparent().remove(p._element)
def insert(anchor,callback):
 old=set(doc.element.body);callback()
 for node in [x for x in doc.element.body if x not in old]:anchor._p.addprevious(node)
def linked(p,label,url):
 rid=doc.part.relate_to(url,RT.HYPERLINK,is_external=True);h=OxmlElement('w:hyperlink');h.set(qn('r:id'),rid)
 r=OxmlElement('w:r');pr=OxmlElement('w:rPr');fonts=OxmlElement('w:rFonts');fonts.set(qn('w:ascii'),'Times New Roman');fonts.set(qn('w:hAnsi'),'Times New Roman');pr.append(fonts)
 sz=OxmlElement('w:sz');sz.set(qn('w:val'),'24');pr.append(sz);r.append(pr);t=OxmlElement('w:t');t.text=label;r.append(t);h.append(r);p._p.append(h)

caption=find('Bảng 26  Kết quả giám khảo B')
replace(caption,'Bảng 26  Nhãn judge và hành vi với câu thiếu căn cứ')
t=Table(caption._p.getnext(),doc)
headers=['Nhóm','Số','Judge đúng¹','Judge sai¹','Thiếu căn cứ','Đã từ chối','Vẫn trả lời²']
for c,value in zip(t.rows[0].cells,headers):textcell(c,value)
qa=scope['qa'];demo=scope['demo'];groups=judge['groups']
rows=[]
for label,x in [('12 câu RRF',qa),('5 câu demo',demo)]:
 rows.append([label,x['total'],x['judge_labels_on_answerable'].get('correct',0),x['judge_labels_on_answerable'].get('incorrect',0),
              x['unanswerable_draft'],x['unanswerable_model_abstained'],x['unanswerable_answered_should_refuse']])
for label,keys in [('OCR, sáu hình',['image_ocr']),('SmolVLM2, sáu hình',['image_vlm_inference']),('Qwen2.5-VL, sáu hình',['image_qwen_vl']),('Sơ đồ mũi tên',[k for k in groups if k.startswith('arrow_')])]:
 n=sum(groups[k]['valid_count'] for k in keys);correct=sum(groups[k]['labels'].get('correct',0) for k in keys);wrong=sum(groups[k]['labels'].get('incorrect',0) for k in keys)
 rows.append([label,n,correct,wrong,'—','—','—'])
if len(t.rows)!=len(rows)+1:raise ValueError('Unexpected judge table structure')
for row,values in zip(t.rows[1:],rows):
 for cell,value in zip(row.cells,values):textcell(cell,value)
widths=[1.25,.45,.9,.65,.85,1.05,1.15]
t.autofit=False
for col,width in zip(t.columns,widths):col.width=Inches(width)
for row in t.rows:
 for cell,width in zip(row.cells,widths):cell.width=Inches(width)
note=caption._p.getnext().getnext()
if not note.tag.endswith('}p'):raise ValueError('Missing judge-table note')
from docx.text.paragraph import Paragraph
replace(Paragraph(note,doc),f"¹ Cột judge chỉ tính câu có căn cứ theo nhãn nháp; sáu hình và sơ đồ có đáp án tham chiếu nháp. ² Vẫn trả lời khi nhãn nháp yêu cầu từ chối. Dấu —: không áp dụng nhãn phạm vi này cho nhóm hình. Toàn bộ nhãn là AI hoặc nhãn nháp, chưa được xác nhận. Nguồn: {scope['run_id']}; judge {judge['judge_b_run_id']} và {judge['judge_b_text_run_id']}.")
support=find('Theo nhãn Gemma, mức hỗ trợ')
replace(support,support.text+' Đây là các nhãn hỗ trợ thô của Gemma, chưa hiệu chỉnh theo nhãn phạm vi.')
def explain():
 add_p(doc,'Theo nhãn nháp của tập câu hỏi, sáu câu RRF thiếu căn cứ: hệ thống từ chối một và vẫn trả lời năm. Trong năm câu đó, Gemma gán bốn câu U04, U08, U11 và U13 là đúng; các nhãn này không được cộng vào cột đúng vì mâu thuẫn với nhãn phạm vi. Câu U01 cũng vẫn trả lời và được tính vào nhóm đáng ra từ chối, dù Gemma gán sai. Demo có một câu ngoài phạm vi và hệ thống đã từ chối. Không có lỗi kỹ thuật trong hai nhóm câu này. Các kết luận phụ thuộc nhãn phạm vi nháp và cần kiểm định thêm.')
insert(support,explain)
old=find('Kịch bản năm câu đã được chạy lại')
replace(old,'Với BM25 + BGE-M3, RRF k=60 và 50 ứng viên mỗi nhánh, lượt console_rrf_20261127T011915Z báo invalid_or_missing_citation ở câu ngoài phạm vi; thông báo dự phòng không được tính là từ chối hợp lệ. Sau khi schema được ràng buộc thành hai nhánh từ chối và trả lời có nguồn, lượt console_rrf_v5_20261127T013434Z ghi nhận model_abstained ở câu đó. Lượt mới có 5/5 kết quả hợp lệ về mặt kỹ thuật; việc từ chối đúng phạm vi trong một lần chạy không bảo đảm độ ổn định hoặc tính đúng của các câu khác.')
extra=find('Lượt demo mới console_rrf_v5_20261127')
extra._element.getparent().remove(extra._element)
summary=Table(find('Bảng 27  Tổng kết')._p.getnext(),doc)
for row in summary.rows[1:]:
 if row.cells[0].text.strip()=='Input, OCR, bảng, hình':
  textcell(row.cells[2],'PyMuPDF/OCR; đề xuất thử Qwen2.5-VL cho hình, chưa tích hợp console')
  textcell(row.cells[3],'Judge B: Qwen2.5-VL 10/12; OCR 4/12; SmolVLM2 4/12. Mũi tên: 0/6 tổng cộng.')
  textcell(row.cells[4],'Nhãn AI; mẫu nhỏ, được chọn có chủ đích.')
  break
else:raise ValueError('Input summary row missing')
def conclusion():
 add_p(doc,'Trên sáu vùng hình được chọn, judge B gán đúng 10/12 cho Qwen2.5-VL, so với 4/12 cho mỗi đường OCR và SmolVLM2; Qwen2.5-VL vì vậy là phương án đáng thử tiếp cho nội dung hình, chưa phải lựa chọn được xác nhận. Với sơ đồ mũi tên, cả ba đường đều nhận 0/2 theo judge, tổng cộng 0/6; mẫu nhỏ, chọn có chủ đích và nhãn do AI tạo giới hạn kết luận.')
insert(find('Kết luận giới hạn trong snapshot G0'),conclusion)
find('PHỤ LỤC A MINH CHỨNG').paragraph_format.page_break_before=True
for rel in doc.part.rels.values():
 if rel.reltype==RT.HYPERLINK and 'github.com/franz08hmt/RAG/' in rel.target_ref:
  target=re.sub(r'(?<=/blob/)[0-9a-f]{40}(?=/)',args.commit,rel.target_ref)
  rel._target=re.sub(r'(?<=/tree/)[0-9a-f]{40}(?=/|$)',args.commit,target)
replace(find('Mã nguồn và minh chứng tại'),f'Mã nguồn và minh chứng tại https://github.com/franz08hmt/RAG/tree/{args.commit}. Commit minh chứng: {args.commit[:12]}. Các đường dẫn bên dưới cố định theo commit này.')
links=find('Mở commit và danh mục mã nguồn')
linked(links,' · Đối chiếu phạm vi v7',f'https://github.com/franz08hmt/RAG/blob/{args.commit}/docs/evidence/v7/scope_presentation.json')
doc.save(args.output);print(args.output)
