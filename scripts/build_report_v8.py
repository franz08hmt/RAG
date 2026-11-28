"""Create v8 from v7 with one requested note and pinned evidence links."""
import argparse,re,sys
from copy import deepcopy
from pathlib import Path
from docx import Document
from docx.oxml import OxmlElement
from docx.opc.constants import RELATIONSHIP_TYPE as RT
from docx.text.paragraph import Paragraph
from docx.table import Table

sys.stdout.reconfigure(encoding='utf8');print('Python executable:',sys.executable,flush=True)
root=Path(__file__).resolve().parents[1]
ap=argparse.ArgumentParser();ap.add_argument('--commit',required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args()
if not re.fullmatch(r'[0-9a-f]{40}',a.commit):raise ValueError('Expected full commit SHA')
if a.output.exists():raise FileExistsError(a.output)
sources=list((root/'reports').glob('*_RAG_Bao_Cao_Cuoi_Ky_v7.docx'))
if len(sources)!=1:raise ValueError('Expected one v7 report')
doc=Document(sources[0]);caps=[p for p in doc.paragraphs if p.text.startswith('Bảng 26  ')]
if len(caps)!=1:raise ValueError('Expected a single table caption')
caps[0].paragraph_format.page_break_before=True
table=caps[0]._p.getnext();note=table.getnext()
if not table.tag.endswith('}tbl') or not note.tag.endswith('}p'):raise ValueError('Unexpected table note structure')
node=OxmlElement('w:p');note.addnext(node);paragraph=Paragraph(node,doc)
if note.pPr is not None:node.insert(0,deepcopy(note.pPr))
run=paragraph.add_run('Gemma gán đúng cả 4/4 câu demo có căn cứ, dù câu chương trình thứ hai thiếu điều kiện năm học, câu học trước và tiên quyết gộp hai điều kiện, còn câu Bảng 1 dẫn nhầm Điều 15, cho thấy judge có thể chấm dễ dãi.')
old_note=Paragraph(note,doc)
if old_note.runs and old_note.runs[0]._r.rPr is not None:run._r.insert(0,deepcopy(old_note.runs[0]._r.rPr))
for row in Table(table,doc).rows:
 for cell in row.cells:
  for p in cell.paragraphs:p.paragraph_format.keep_with_next=True
old_note.paragraph_format.keep_with_next=True
paragraph.paragraph_format.keep_with_next=False
for rel in doc.part.rels.values():
 if rel.reltype==RT.HYPERLINK and 'github.com/franz08hmt/RAG/' in rel.target_ref:
  target=re.sub(r'(?<=/blob/)[0-9a-f]{40}(?=/)',a.commit,rel.target_ref)
  rel._target=re.sub(r'(?<=/tree/)[0-9a-f]{40}(?=/|$)',a.commit,target)
matches=[p for p in doc.paragraphs if p.text.startswith('Mã nguồn và minh chứng tại')]
if len(matches)!=1:raise ValueError('Expected a single appendix commit paragraph')
p=matches[0]
for r in p.runs:
 text=re.sub(r'(?<=/tree/)[0-9a-f]{40}',a.commit,r.text)
 text=re.sub(r'(?<=Commit minh chứng: )[0-9a-f]{12}',a.commit[:12],text)
 if text!=r.text:r.text=text
doc.save(a.output);print(a.output)
