"""Prepare local-only question/OCR review material; never manufacture human labels."""
from __future__ import annotations
import argparse
import csv
import hashlib
import html
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from rag_hcmute.evaluation.review_readiness import audit_review_rows

FIELDS = ['question_id','question','snapshot_id','created_by','review_status','verified_by','verified_at',
          'answerability','reference_answer','evidence_json','absence_review_note','tags','leakage_group','split',
          'source_document_hint','source_page_hint']


def main():
    print(f'Python executable: {sys.executable}',flush=True)
    parser = argparse.ArgumentParser()
    parser.add_argument('--generation',type=Path)
    args=parser.parse_args()
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    private=Path('D:/RAG/private_eval/m3_review')/stamp
    private.mkdir(parents=True,exist_ok=False)
    def csvrows(path):
        return list(csv.DictReader(path.open(encoding='utf-8-sig',newline='')))
    snapshot=json.loads((ROOT/'data/manifests/corpus_snapshot.json').read_text(encoding='utf-8'))['snapshot_id']
    rows=[]
    for name in ['pilot_questions.csv','question_candidates_for_student_review.csv','table_question_candidates_for_student_review.csv']:
        for source in csvrows(ROOT/'data/question_sets'/name):
            qid=source.get('question_id') or source['candidate_id']
            row=dict.fromkeys(FIELDS,'')
            row.update(question_id=qid,question=source.get('question') or source['question_draft'],
                       snapshot_id=snapshot,created_by='imported_origin_not_reverified',review_status='pending',
                       evidence_json='[]',source_document_hint=source.get('expected_document') or source.get('source_document_id',''),
                       source_page_hint=source.get('evidence_page') or source.get('source_reference',''),
                       split='development' if qid.startswith('P') else '',
                       leakage_group=f'pilot_{qid}' if qid.startswith('P') else '',
                       tags='requires_table_or_image' if qid.startswith('TB') else '')
            rows.append(row)
    with (private/'question_review.csv').open('x',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=FIELDS); writer.writeheader(); writer.writerows(rows)
    audit=audit_review_rows(rows,snapshot_id=snapshot)
    audit['note']='New review workspace only; existing pilot annotations are unchanged. Pending is not a revocation of historical pilot review.'
    blocks=['<h1>Gói duyệt dữ liệu cho Mốc 3</h1>',
      '<p>Tài liệu cục bộ có nội dung nguồn. Không đưa thư mục này lên Git hoặc dịch vụ ngoài.</p>',
      '<p>Mở question_review.csv để điền. Kiểm từng câu với PDF, viết đáp án tham chiếu, điền evidence_json gồm document_id, pdf_page, quote. '
      'Câu thiếu căn cứ cần ghi lý do đã rà phạm vi. Không chuyển nhãn human_verified khi chưa đọc nguồn. '
      'verified_by và verified_at do người học điền. Các câu P giữ development; câu gần trùng cùng leakage_group. '
      'Mốc 100 câu còn thiếu; 27 mục bên dưới gồm pilot và đề xuất cũ, không phải bộ test đã hoàn tất.</p>']
    for row in rows:
        blocks.append(f'<h2>{html.escape(row["question_id"])}</h2><p>{html.escape(row["question"])}</p>'
                      f'<p>Gợi ý tìm nguồn: {html.escape(row["source_document_hint"])} — {html.escape(row["source_page_hint"])}</p>')
    import pymupdf
    manifest=csvrows(ROOT/'data/manifests/corpus_manifest.csv')
    selected={'HCMUTE_QCDT_1727_2021':[2,6,20,23], 'HCMUTE_FIT_TTTN_2022':[1],
              'HCMUTE_SOTAYSV_2024':[107,109,116,136,140]}
    ocr_rows=[]
    blocks.append('<h1>Trang chuẩn để kiểm tra trích xuất</h1><p>Ảnh và native_draft.txt là đầu vào; gold.txt để trống. '
                  'Chép nội dung theo thứ tự đọc, sửa dấu và khoảng trắng, đánh dấu riêng bảng. '
                  'Có hình không mặc nhiên là PDF scan. Chưa tính CER/WER trước khi gold được người học duyệt.</p>')
    for doc in manifest:
        source=ROOT/doc['local_path']
        if hashlib.sha256(source.read_bytes()).hexdigest()!=doc['file_sha256']:
            raise ValueError('Source hash differs from manifest.')
        with pymupdf.open(source) as pdf:
            for number in selected[doc['document_id']]:
                name=f'{doc["document_id"]}_p{number:03d}'
                folder=private/'ocr'/name; folder.mkdir(parents=True)
                page=pdf[number-1]
                page.get_pixmap(dpi=180,colorspace=pymupdf.csGRAY).save(folder/'source.png')
                (folder/'native_draft.txt').write_text(page.get_text(),encoding='utf-8')
                (folder/'gold.txt').write_text('',encoding='utf-8')
                ocr_rows.append({'document_id':doc['document_id'],'pdf_page':number,'source_sha256':doc['file_sha256'],
                                'review_status':'pending','verified_by':'','verified_at':'','gold_relative_path':f'ocr/{name}/gold.txt'})
                blocks.append(f'<h2>{name}</h2><p><a href="ocr/{name}/native_draft.txt">Bản trích chữ nháp</a> — '
                              f'<a href="ocr/{name}/gold.txt">Bản chép chuẩn cần điền</a></p><img src="ocr/{name}/source.png" alt="Trang nguồn"/>')
    with (private/'ocr_review.csv').open('x',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(ocr_rows[0])); writer.writeheader(); writer.writerows(ocr_rows)
    generation_count=0
    if args.generation:
        metrics=json.loads(args.generation.read_text(encoding='utf-8'))
        if not metrics.get('completed'):
            raise ValueError('Generation run not complete.')
        answer_rows=[]
        blocks.append('<h1>Câu trả lời cần chấm nội dung</h1><p>Đọc câu trả lời và nguồn, không chấm từ trạng thái validator. '
                      'Một quote đúng nguyên văn vẫn có thể bị suy diễn sai. Điền nhãn trong generation_review.csv; không sửa run gốc.</p>')
        for case in metrics['cases']:
            qid,variant=case['question_id'],case['variant']
            raw=json.loads((Path(metrics['private_directory'])/f'{variant}_{qid}.json').read_text(encoding='utf-8'))
            blocks.append(f'<h2>{qid} — {variant}</h2><p>Trạng thái kỹ thuật: {case["status"]}</p>')
            if 'question' in raw:
                blocks.append(f'<p>{html.escape(raw["question"])}</p><pre>{html.escape(raw["result"]["answer"])}</pre>')
                for s in raw['sources']:
                    blocks.append(f'<details><summary>{s["source_id"]} — {html.escape(s["document_id"])} — PDF {s["pdf_page_start"]}–{s["pdf_page_end"]}</summary>'
                                  f'<pre>{html.escape(s["text"])}</pre></details>')
            answer_rows.append({'run_id':metrics['run_id'],'question_id':qid,'variant':variant,'generation_status':case['status'],
                'review_status':'pending','verified_by':'','answer_correctness':'','faithfulness':'','answer_relevance':'',
                'citation_support':'','citation_location':'','refusal_reason_correct':''})
        with (private/'generation_review.csv').open('x',encoding='utf-8-sig',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=list(answer_rows[0])); writer.writeheader(); writer.writerows(answer_rows)
        generation_count=len(answer_rows)
    style='body{max-width:900px;margin:32px auto;font-family:"Times New Roman",serif;font-size:18px;color:#000;background:#fff}p{line-height:1.5}pre{white-space:pre-wrap;font:inherit;border:1px solid #000;padding:14px}img{max-width:100%}h2{margin-top:32px}summary{cursor:pointer}'
    (private/'START_HERE.html').write_text('<!doctype html><html lang="vi"><meta charset="UTF-8"><title>Gói duyệt Mốc 3</title>'
          f'<style>{style}</style><body>'+''.join(blocks)+'</body></html>',encoding='utf-8')
    out=ROOT/f'artifacts/results/m3/review_package_{stamp}.json'
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps({'created_at':stamp,'snapshot_id':snapshot,'private_directory':str(private),
        'question_audit':audit,'ocr_pages_pending':len(ocr_rows),'generation_cases_pending':generation_count,
        'human_labels_written':0,'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},ensure_ascii=False,indent=2),encoding='utf-8')
    print(f'Private review: {private}/START_HERE.html\nSafe audit: {out}',flush=True)


if __name__=='__main__':
    main()
