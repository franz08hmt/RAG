"""Create a local readable companion page for the student's new 12-answer sheet."""
import argparse,csv,html,sys
from pathlib import Path
print('Python executable:',sys.executable,flush=True)
ap=argparse.ArgumentParser();ap.add_argument('sheet',type=Path);ap.add_argument('--output',type=Path,required=True);args=ap.parse_args()
if args.output.exists():raise FileExistsError(args.output)
with args.sheet.open(encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f))
if len(rows)!=12:raise ValueError('Expected 12 new answers')
esc=html.escape
parts=['<!doctype html><html lang="vi"><meta charset="utf-8"><title>Phiếu chấm 12 câu RRF</title>',
 '<style>body{max-width:1000px;margin:2em auto;font:17px/1.5 Georgia,serif;color:#111}article{border-top:1px solid #aaa;padding:1em 0}pre{white-space:pre-wrap;overflow-wrap:anywhere;font:15px/1.45 Georgia,serif}details{margin:.8em 0}</style>',
 '<h1>Đối chiếu 12 câu hỏi và câu trả lời mới</h1><p>Điền nhãn trong tệp CSV cùng thư mục. Nguồn tham chiếu là nhãn đề xuất chưa được sinh viên duyệt; cần mở PDF gốc để xác nhận. Các nguồn truy xuất là dữ liệu cục bộ, không đưa lên Git.</p>']
for r in rows:
 parts.append(f"<article><h2>{esc(r['question_id'])}</h2><b>Câu hỏi:</b> {esc(r['question'])}<p><b>Câu trả lời:</b> {esc(r['answer'])}</p><p><b>Trạng thái kỹ thuật:</b> {esc(r['status'])} · <b>Nguồn được dẫn:</b> {esc(r['cited_source_ids'])}</p><details><summary>Đoạn tham chiếu đề xuất</summary><pre>{esc(r['draft_reference_evidence'] or 'Không có đoạn tham chiếu trong nhãn nháp.')}</pre></details><details><summary>Xem các đoạn đã truy xuất</summary><pre>{esc(r['retrieved_sources'])}</pre></details></article>")
parts.append('</html>');args.output.write_text('\n'.join(parts),encoding='utf8');print('Local review page:',args.output)
