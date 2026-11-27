"""Run the existing 12 draft questions with the approved RRF console configuration."""
import argparse,csv,hashlib,json,subprocess,sys
from collections import Counter
from dataclasses import asdict
from datetime import datetime,timezone
from pathlib import Path
from urllib.request import urlopen
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'src')]
sys.stdout.reconfigure(encoding='utf8');print('Python executable:',sys.executable,flush=True)
from scripts.run_embedding_model_ablation import validate_corpus,MODEL_CONFIGS
from scripts.run_final_extended_eval import load_cases,GENERATION_IDS
from rag_hcmute.console_app import create_retriever,_move_retrieval_models,_chunks_by_id,DEFAULT_CHUNKS_PATH
from rag_hcmute.generation.ollama import generate_grounded_answer,sources_from_hits

ap=argparse.ArgumentParser();ap.add_argument('--private-out',type=Path,required=True);ap.add_argument('--metrics',type=Path,required=True)
args=ap.parse_args()
if args.private_out.exists() or args.metrics.exists() or args.private_out.resolve().is_relative_to(ROOT):raise ValueError('Use fresh private output outside the repo')
import torch
if not torch.cuda.is_available():raise RuntimeError('CUDA required')
snapshot,chunks,pages=validate_corpus()
cases,spans=load_cases(Path('D:/RAG/private_eval/final_20261115/cases.tsv'),pages)
if not all(qid in cases for qid in GENERATION_IDS):raise ValueError('Missing existing question')
retriever=create_retriever(method='hybrid',chunks_path=DEFAULT_CHUNKS_PATH,dense_model=MODEL_CONFIGS['bge-m3']['path'])
_move_retrieval_models(retriever,'cuda');lookup=_chunks_by_id(retriever)
sources={qid:sources_from_hits(retriever.query(cases[qid]['question'],top_k=5).hits,lookup) for qid in GENERATION_IDS}
_move_retrieval_models(retriever,'cpu')
with urlopen('http://127.0.0.1:11434/api/tags',timeout=10) as response:
 digest=next(x['digest'] for x in json.load(response)['models'] if x['name']=='qwen3:4b')
args.private_out.mkdir(parents=True,exist_ok=False);args.metrics.parent.mkdir(parents=True,exist_ok=True)
stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
data={'run_id':'scope_rrf12_'+stamp,'snapshot_id':snapshot['snapshot_id'],'partition':'12 existing AI-drafted questions, not human verified',
 'revision_before_run':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
 'runner_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
 'generator_sha256':hashlib.sha256((ROOT/'src/rag_hcmute/generation/ollama.py').read_bytes()).hexdigest(),
 'model':'qwen3:4b','model_digest':digest,'retrieval':'RRF k=60, BM25+BGE-M3, branch top50',
 'reranker':False,'context_window':8192,'prompt_variant':'scope_schema','temperature':0,'max_output_tokens':384,
 'rows':[],'completed':False}
reviews=[]
def save():
 args.metrics.write_text(json.dumps(data,indent=2)+'\n',encoding='utf8')
 if reviews:
  with (args.private_out/'phieu_12_cau_v5.csv').open('w',encoding='utf-8-sig',newline='') as stream:
   w=csv.DictWriter(stream,fieldnames=list(reviews[0]));w.writeheader();w.writerows(reviews)
for qid in GENERATION_IDS:
 src=sources[qid];case=cases[qid]
 result=generate_grounded_answer(case['question'],src,model='qwen3:4b',prompt_variant='scope_schema',context_window=8192,max_output_tokens=384,keep_alive='5m')
 payload={'question_id':qid,'case':case,'sources':[asdict(x) for x in src],'result':asdict(result)}
 (args.private_out/f'{qid}.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
 labels='\n'.join(f'{x.source_id} | {x.document_title} | PDF {x.pdf_page_start}–{x.pdf_page_end} | {x.section_path or ""}\n{x.text}' for x in src)
 expected='\n'.join(f"PDF {e['pdf_page']} | {e['quote']}" for e in case['evidence'])
 reviews.append({'question_id':qid,'question':case['question'],'draft_reference_evidence':expected,'retrieved_sources':labels,'answer':result.answer,
   'status':result.status,'cited_source_ids':','.join(x.source_id for x in result.citations),
   'student_correctness':'','student_supported_by_sources':'','student_should_abstain':'','student_notes':''})
 data['rows'].append({'question_id':qid,'answerable_draft':qid in spans,'status':result.status,'abstained':result.abstained,
   'citation_count':len(result.citations),'context_chunk_ids':[x.chunk_id for x in src],
   'cited_chunk_ids':[x.chunk_id for x in result.citations],'generation_ms':result.latency_ms})
 save();print(qid,result.status,flush=True)
data['completed']=True;data['status_counts']=dict(Counter(x['status'] for x in data['rows']));save()
print('run_id',data['run_id'],'private_review',args.private_out/'phieu_12_cau_v5.csv',flush=True)
