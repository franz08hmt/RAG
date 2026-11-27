"""Create v4 from v3; only evidence-backed updates and targeted formatting repairs."""
import argparse,json,re,sys
from copy import deepcopy
from pathlib import Path
from docx import Document
from docx.table import Table
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from docx.opc.constants import RELATIONSHIP_TYPE as RT
from build_m1_report_v3 import add_p,add_data_table,set_run_font
sys.stdout.reconfigure(encoding='utf-8')
print('Python executable:',sys.executable,flush=True)
ROOT=Path(__file__).resolve().parents[1]
ap=argparse.ArgumentParser();ap.add_argument('--commit',required=True);ap.add_argument('--output',type=Path,required=True)
args=ap.parse_args()
if args.output.exists():raise FileExistsError(args.output)
sources=list((ROOT/'reports').glob('*_RAG_Bao_Cao_Cuoi_Ky_v3.docx'))
if len(sources)!=1:raise ValueError('Expected one v3 report')
doc=Document(sources[0]);ranking=json.loads((ROOT/'docs/evidence/v2/ranking43.json').read_text(encoding='utf8'))
demo=json.loads((ROOT/'docs/evidence/v4/demo_rrf.json').read_text(encoding='utf8'))
def find(prefix):
 matches=[p for p in doc.paragraphs if p.text.startswith(prefix)]
 if len(matches)!=1:raise ValueError((prefix,len(matches)))
 return matches[0]
def replace(p,text):
 style=deepcopy(p.runs[0]._r.rPr) if p.runs and p.runs[0]._r.rPr is not None else None
 p.clear();r=p.add_run(text)
 if style is not None:r._r.insert(0,style)
 else:set_run_font(r,12)
def insert(anchor,func):
 old=set(doc.element.body);func()
 for node in [x for x in doc.element.body if x not in old]:anchor._p.addprevious(node)
def para(s):return add_p(doc,s)
def table(c,h,r,w,n):return add_data_table(doc,c,h,r,w,n)
def linked(p,label,url):
 rid=doc.part.relate_to(url,RT.HYPERLINK,is_external=True);h=OxmlElement('w:hyperlink');h.set(qn('r:id'),rid)
 r=OxmlElement('w:r');pr=OxmlElement('w:rPr');fonts=OxmlElement('w:rFonts');fonts.set(qn('w:ascii'),'Times New Roman');fonts.set(qn('w:hAnsi'),'Times New Roman');pr.append(fonts)
 size=OxmlElement('w:sz');size.set(qn('w:val'),'24');pr.append(size);r.append(pr);t=OxmlElement('w:t');t.text=label;r.append(t);h.append(r);p._p.append(h)

# Targeted fixes: the appendix references are section numbers, while exactly
# two pure 1.000 cells in table 16 are ratios, not counts or software versions.
for t in doc.tables:
 if t.rows[0].cells[0].text.strip()=='YC':
  for row in t.rows[1:]:
   p=row.cells[2].paragraphs[0];replace(p,re.sub(r'(?<=\d),(?=\d)', '.', p.text))
 if any('Tổng kết lựa chọn' in p.text for p in doc.paragraphs if p._p.getnext() is t._tbl):
  for row in t.rows:
   for cell in row.cells:
    for p in cell.paragraphs:
     if 'mục 2,6' in p.text:replace(p,p.text.replace('mục 2,6','mục 2.6'))
cap=find('Bảng 16  Ba reranker');t=Table(cap._p.getnext(),doc)
for row in t.rows[1:]:
 if row.cells[1].text.strip()=='1.000':replace(row.cells[1].paragraphs[0],'1,000')

def comparison():
 rows=[]
 for label,key in [('RRF','RRF'),('Weighted75','weighted75')]:
  m=ranking['fusion'][key]['macro']; rows.append([label,*[f"{m[k]:.4f}".replace('.',',') for k in ('character_recall_at_5','mrr_at_10_threshold_05','ndcg_at_5_linear_span_coverage')]])
 table('Bảng X  RRF và Weighted75 trên cùng lượt 43 câu',['Fusion','Phủ ký tự Top-5','MRR@10','nDCG@5'],rows,[1.45,1.75,1.55,1.55],
       f"Run {ranking['run_id']}; cùng 43 câu nháp, 57 span, snapshot G0 và hai danh sách BM25/dense Top-50; cùng hàm chấm. RRF dùng k=60, Weighted75 dùng trọng số dense 0,75.")
 para('Ở cùng lượt trên, RRF cao hơn Weighted75 về cả ba chỉ số. Bảng đối chiếu 43 câu trước đây không có RRF; giá trị Weighted75 0,9956 và 0,8748 khớp giữa hai lượt. Khác biệt không phải do đổi định nghĩa chỉ số hay đổi pool đầu vào của hai nhánh: RRF gộp thứ hạng, Weighted75 chuẩn hóa rồi gộp điểm. Tập câu còn là nhãn nháp dùng chọn cấu hình, chưa phải test độc lập.')
insert(find('4.2 Reranker'),comparison)
replace(find('Kết quả RRF thấp trên bảy câu'), 'RRF thấp hơn dense trong phép thử bảy câu ở Bảng 13, dùng cửa sổ chunk và thiết lập Mốc 2. Phép 43 câu dùng snapshot G0 khác; các con số không trực tiếp đối chiếu để suy nguyên nhân. Trong phép fusion cùng 43 câu dưới đây, RRF và Weighted75 nhận cùng hai danh sách ứng viên Top-50 và dùng cùng định nghĩa chỉ số.')
replace(find('Kịch bản năm câu được chạy'), f"Kịch bản năm câu đã được chạy lại trên console với BM25 + BGE-M3, RRF k=60, 50 ứng viên mỗi nhánh, không reranker, Qwen3:4B và JSON Schema với context 8.192. Lượt {demo['run_id']} có {sum(x['success'] for x in demo['cases'])}/5 lượt thành công về mặt kỹ thuật. Câu ngoài phạm vi báo invalid_or_missing_citation, không được tính là từ chối hợp lệ. Câu Bảng 1 còn metadata Điều 15 sai; câu chương trình thứ hai thiếu điều kiện về năm học, câu học trước/tiên quyết gộp hai điều kiện. Log giữ cục bộ; thành công kỹ thuật không chứng minh câu trả lời đúng.")
old_demo=find('Trong lượt BM25 sinh cục bộ')
replace(old_demo,old_demo.text.replace('Trong lượt BM25 sinh cục bộ','Trong lượt đối chứng BM25 trước đây'))
replace(find('Trong phép thử trên 43 câu nháp'), 'Cấu hình mặc định được chọn là G0, BM25 kết hợp BGE-M3 bằng RRF k=60 với 50 ứng viên mỗi nhánh, không bật reranker; Qwen3:4B tạo câu trả lời theo JSON Schema trong context 8.192. RRF đạt kết quả cao hơn Weighted75 trên cùng lượt 43 câu nháp. BGE reranker trần 1.024 token có MRR 0,903, bằng trước rerank, trong khi thêm độ trễ; vì vậy tắt mặc định trong phạm vi mẫu này. BM25 đơn lẻ được giữ làm cấu hình đối chứng. Các lựa chọn cần được kiểm chứng lại bằng câu hỏi độc lập và nhãn người.')
replace(find('Bảng đối chiếu cập nhật đến ngày'), 'Bảng đối chiếu cập nhật đến ngày 27/11/2026; kết quả chấm người và tập test riêng chưa có.')
summary=Table(find('Bảng 25  Tổng kết')._p.getnext(),doc)
updates={'Chunking':('G0 500/80, có ranh giới Điều và cửa sổ dự phòng','Bảng 9: phép chia theo Điều phủ 0,873 ở 1.000 token'),
 'Retrieval':('BM25 + BGE-M3, RRF k=60, Top-50 mỗi nhánh','RRF hơn Weighted75 trong lượt 43 câu; BM25 làm đối chứng'),
 'Reranker':('Tắt mặc định','Trần 1.024: MRR 0,903, bằng trước rerank; thêm độ trễ'),
 'Sinh và từ chối':('Qwen3:4B, schema, 8.192','Schema không chứng minh câu trả lời đúng')}
for row in summary.rows[1:]:
 key=row.cells[0].text.strip()
 if key in updates:
  replace(row.cells[2].paragraphs[0],updates[key][0]);replace(row.cells[3].paragraphs[0],updates[key][1])
for t in doc.tables:
 if t.rows[0].cells[0].text.strip()=='YC':
  for row in t.rows[1:]:
   if row.cells[0].text.strip()=='YC12':replace(row.cells[1].paragraphs[0],'Console RRF Top-50, năm lượt demo; BM25 làm đối chứng.')

# Link evidence to the pushed commit; existing external links stay intact.
for rel in doc.part.rels.values():
 if rel.reltype==RT.HYPERLINK and 'github.com/franz08hmt/RAG/' in rel.target_ref:
  target=re.sub(r'(?<=/blob/)[0-9a-f]{40}(?=/)',args.commit,rel.target_ref)
  rel._target=re.sub(r'(?<=/tree/)[0-9a-f]{40}(?=/|$)',args.commit,target)
replace(find('Mã nguồn và minh chứng tại'),f'Mã nguồn và minh chứng tại https://github.com/franz08hmt/RAG/tree/{args.commit}. Commit minh chứng: {args.commit[:12]}. Các đường dẫn bên dưới cố định theo commit này.')
linked(find('Mở commit và danh mục mã nguồn'),' · Demo RRF',f'https://github.com/franz08hmt/RAG/blob/{args.commit}/docs/evidence/v4/demo_rrf.json')

# Renumber captions and cross-references without touching image drawing runs.
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
  new=re.sub(r'Bảng (\d+)(?!\d)',lambda m:'Bảng '+str(mapping.get(int(m.group(1)),int(m.group(1)))),r.text)
  if new!=r.text:r.text=new
for p in doc.paragraphs:refs(p)
for t in doc.tables:
 for row in t.rows:
  for cell in row.cells:
   for p in cell.paragraphs:refs(p)
doc.save(args.output);print(args.output)
