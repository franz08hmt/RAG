"""Validate a local question-review CSV without changing labels or creating test."""
import argparse
import csv
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from rag_hcmute.evaluation.review_readiness import audit_review_rows
from rag_hcmute.ingestion.extract import read_pages_jsonl
from rag_hcmute.ingestion.clean import clean_document_pages
from rag_hcmute.ingestion.manifest import sha256_file


def main():
    print(f'Python executable: {sys.executable}',flush=True)
    parser=argparse.ArgumentParser()
    parser.add_argument('--input',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.input.resolve().is_relative_to(ROOT):
        raise ValueError('Private review input must remain outside the repository.')
    if args.output.exists():
        raise FileExistsError(args.output)
    with (ROOT/'data/manifests/corpus_manifest.csv').open(encoding='utf-8-sig',newline='') as f:
        sources=list(csv.DictReader(f))
    for source in sources:
        if sha256_file(ROOT/source['local_path'])!=source['file_sha256']:
            raise ValueError('Source hash mismatch.')
    snapshot=json.loads((ROOT/'data/processed/g0_reproduction/snapshot.json').read_text(encoding='utf-8'))
    pages={}
    for doc in snapshot['documents']:
        did=doc['document_id']
        clean,_=clean_document_pages(read_pages_jsonl(ROOT/f'data/processed/g0_reproduction/pages/{did}.jsonl'))
        pages.update({(did,p.pdf_page):p.text for p in clean})
    with args.input.open(encoding='utf-8-sig',newline='') as f:
        rows=list(csv.DictReader(f))
    report=audit_review_rows(rows,snapshot_id=snapshot['snapshot_id'],source_pages=pages)
    report['input_sha256']=sha256_file(args.input)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f'Rows={report["row_count"]}; pending={report["pending_rows"]}; ready={report["ready_for_freeze"]}; errors={len(report["errors"])}')


if __name__=='__main__':
    main()
