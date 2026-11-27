"""Create v5 from v4; preserve old results and add the completed schema run."""
import argparse,json,re,sys
from copy import deepcopy
from pathlib import Path
from collections import Counter
from docx import Document
from docx.table import Table
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from docx.opc.constants import RELATIONSHIP_TYPE as RT
from build_m1_report_v3 import add_p,set_run_font
sys.stdout.reconfigure(encoding='utf8');print('Python executable:',sys.executable,flush=True)
ROOT=Path(__file__).resolve().parents[1]
ap=argparse.ArgumentParser();ap.add_argument('--commit',required=True);ap.add_argument('--output',type=Path,required=True);args=ap.parse_args()
if args.output.exists():raise FileExistsError(args.output)
sources=list((ROOT/'reports').glob('*_RAG_Bao_Cao_Cuoi_Ky_v4.docx'))
if len(sources)!=1:raise ValueError('Expected one v4 report')
doc=Document(sources[0]);run=json.loads((ROOT/'docs/evidence/v5/scope_rrf12.json').read_text(encoding='utf8'))
demo=json.loads((ROOT/'docs/evidence/v5/demo_rrf.json').read_text(encoding='utf8'))
if not run['completed'] or len(run['rows'])!=12 or len(demo['cases'])!=5:raise ValueError('Incomplete evaluation artifacts')
def find(prefix):
 matches=[p for p in doc.paragraphs if p.text.startswith(prefix)]
 if len(matches)!=1:raise ValueError((prefix,len(matches)))
 return matches[0]
def replace(p,text):
 style=deepcopy(p.runs[0]._r.rPr) if p.runs and p.runs[0]._r.rPr is not None else None
 p.clear();r=p.add_run(text)
 if style is not None:r._r.insert(0,style)
 else:set_run_font(r,12)
def insert(anchor,callback):
 old=set(doc.element.body);callback()
 for node in [x for x in doc.element.body if x not in old]:anchor._p.addprevious(node)
def para(s):return add_p(doc,s)
def linked(p,label,url):
 rid=doc.part.relate_to(url,RT.HYPERLINK,is_external=True);h=OxmlElement('w:hyperlink');h.set(qn('r:id'),rid)
 r=OxmlElement('w:r');pr=OxmlElement('w:rPr');fonts=OxmlElement('w:rFonts');fonts.set(qn('w:ascii'),'Times New Roman');fonts.set(qn('w:hAnsi'),'Times New Roman');pr.append(fonts)
 sz=OxmlElement('w:sz');sz.set(qn('w:val'),'24');pr.append(sz);r.append(pr);t=OxmlElement('w:t');t.text=label;r.append(t);h.append(r);p._p.append(h)

yes=[x for x in run['rows'] if x['answerable_draft']];no=[x for x in run['rows'] if not x['answerable_draft']]
counts=Counter(x['status'] for x in run['rows']);no_counts=Counter(x['status'] for x in no)
def new_findings():
 para('Schema scope_schema được điều chỉnh thành hai nhánh đầy đủ: từ chối yêu cầu abstain=true và citation_ids rỗng; trả lời yêu cầu abstain=false và ít nhất một nguồn. Bộ kiểm tra vẫn chặn câu trả lời thiếu nguồn hoặc nguồn không hợp lệ. Không phân loại từ chối bằng cách dò từ khóa trong câu trả lời. Trong log cũ, câu thông báo thiếu căn cứ là thông báo dự phòng của ứng dụng; dữ liệu cũ không lưu JSON gốc nên không xác định được chính xác nội dung mô hình đã trả.')
 para(f"Lượt {run['run_id']} chạy lại 12 câu cũ với BM25 + BGE-M3, RRF k=60, 50 ứng viên mỗi nhánh, không reranker, Qwen3:4B và context 8.192. Có {counts.get('generated_citations_unverified',0)}/12 câu tạo đầu ra có nguồn chưa xác minh ngữ nghĩa, {counts.get('model_abstained',0)}/12 câu được mô hình đánh dấu từ chối. Trong {len(no)} câu nháp thuộc nhóm thiếu căn cứ, {no_counts.get('model_abstained',0)} câu được đánh dấu từ chối và {no_counts.get('generated_citations_unverified',0)} câu vẫn được trả lời. Các trạng thái này chưa phải điểm đúng; cần sinh viên đối chiếu nhãn và tài liệu.")
 para('Bảng 25 giữ kết quả cũ của BM25 và Weighted75 có reranker. Lượt mới dùng RRF và schema mới nên không phải phép so có kiểm soát chỉ thay schema; không suy ra mức cải thiện nhân quả từ chênh lệch hai lượt.')
insert(find('5.6 Minh họa qua console'),new_findings)
def demo_findings():
 statuses=Counter(x['status'] for x in demo['cases'])
 old=[x for x in demo['cases'] if x['id']=='demo_04'][0]
 para(f"Lượt demo mới {demo['run_id']} có {sum(x['success'] for x in demo['cases'])}/5 lượt hoàn tất về mặt kỹ thuật; {statuses.get('generated_citations_unverified',0)} câu có nguồn chưa xác minh ngữ nghĩa và {statuses.get('model_abstained',0)} câu được mô hình đánh dấu từ chối. Câu ngoài phạm vi (demo 04) có trạng thái {old['status']}; lượt trước là invalid_or_missing_citation. Một lần chạy không xác nhận độ chính xác nội dung hay độ ổn định của từ chối.")
insert(find('5.7 Kết luận'),demo_findings)
summary=Table(find('Bảng 26  Tổng kết')._p.getnext(),doc)
for row in summary.rows[1:]:
 if row.cells[0].text.strip()=='Chunking':
  replace(row.cells[2].paragraphs[0],'Giữ G0 500/80; có ranh giới Điều và cửa sổ dự phòng')
  replace(row.cells[3].paragraphs[0],'Giữ cùng G0 cho các lượt đối chiếu embedding, fusion và reranker trên G0.')
  replace(row.cells[4].paragraphs[0],'Chia theo Điều phủ 0,873 ở 1.000 token, cắt 9/57 span; cần kiểm với cùng cấu hình truy xuất ở vòng sau.')
  break
else:raise ValueError('Chunking summary row not found')
current=find('Cấu hình mặc định được chọn')
replace(current,current.text+' G0 được giữ để các lượt embedding, fusion và reranker trên G0 dùng chung tập đoạn; lượt embedding trần chung có tập đoạn riêng. Cách chia theo Điều được cân nhắc cho vòng sau, chưa kiểm với cùng cấu hình truy xuất.')
find('PHỤ LỤC A MINH CHỨNG').paragraph_format.page_break_before=False
find('PHỤ LỤC B ĐỐI CHIẾU').paragraph_format.page_break_before=False
replace(find('Bảng đối chiếu cập nhật đến ngày'), 'Bảng đối chiếu cập nhật đến ngày 27/11/2026; kết quả chấm người và tập test riêng chưa có.')
for rel in doc.part.rels.values():
 if rel.reltype==RT.HYPERLINK and 'github.com/franz08hmt/RAG/' in rel.target_ref:
  target=re.sub(r'(?<=/blob/)[0-9a-f]{40}(?=/)',args.commit,rel.target_ref)
  rel._target=re.sub(r'(?<=/tree/)[0-9a-f]{40}(?=/|$)',args.commit,target)
replace(find('Mã nguồn và minh chứng tại'),f'Mã nguồn và minh chứng tại https://github.com/franz08hmt/RAG/tree/{args.commit}. Commit minh chứng: {args.commit[:12]}. Các đường dẫn bên dưới cố định theo commit này.')
links=find('Mở commit và danh mục mã nguồn')
for label,name in [(' · 12 câu schema mới','scope_rrf12.json'),(' · Demo schema mới','demo_rrf.json')]:
 linked(links,label,f'https://github.com/franz08hmt/RAG/blob/{args.commit}/docs/evidence/v5/{name}')
doc.save(args.output);print(args.output)
