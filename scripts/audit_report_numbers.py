"""List potentially ambiguous number formats; never rewrite the source document."""
import argparse,csv,re,sys
from pathlib import Path
from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph
sys.stdout.reconfigure(encoding='utf-8')
print('Python executable:',sys.executable,flush=True)
ap=argparse.ArgumentParser();ap.add_argument('docx',type=Path);ap.add_argument('--output',type=Path,required=True)
args=ap.parse_args()
if args.output.exists():raise FileExistsError(args.output)
d=Document(args.docx);rows=[];caption='Phần đầu'
def inspect(text,where,section_column=False):
    if section_column and re.search(r'\d,\d',text):
        rows.append({'position':where,'type':'số mục có dấu phẩy','context':text})
    for m in re.finditer(r'(?i)\b(?:mục|chương|phần|bảng|hình)\s+\d+,\d+',text):
        rows.append({'position':where,'type':'tham chiếu có dấu phẩy','context':m.group(0)})
    for m in re.finditer(r'(?<![\w/])\d+\.\d{2,}(?![\w/])',text):
        rows.append({'position':where,'type':'dấu chấm cần phân biệt thập phân/nghìn/phiên bản','context':text[max(0,m.start()-35):min(len(text),m.end()+35)]})
for n,element in enumerate(d.element.body):
    if element.tag.endswith('}p'):
        p=Paragraph(element,d);text=p.text
        if re.match(r'^Bảng \d+',text):caption=text
        inspect(text,f'đoạn {n}')
    elif element.tag.endswith('}tbl'):
        table=Table(element,d);yc=bool(table.rows and table.rows[0].cells[0].text.strip()=='YC')
        for ri,row in enumerate(table.rows):
            for ci,cell in enumerate(row.cells):
                inspect(cell.text,f'{caption}, hàng {ri+1}, cột {ci+1}',yc and ci==2 and ri>0)
args.output.parent.mkdir(parents=True,exist_ok=True)
with args.output.open('w',encoding='utf-8-sig',newline='') as f:
    writer=csv.DictWriter(f,fieldnames=['position','type','context']);writer.writeheader();writer.writerows(rows)
print('Các vị trí cần xem:',len(rows));print('Danh sách:',args.output)
