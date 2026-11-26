"""Evaluate longer reranker inputs against the exact saved v2 candidate pool."""
import gc, hashlib, json, statistics, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / 'src')]
print('Python executable:', sys.executable, flush=True)
import torch
from scripts.run_embedding_model_ablation import validate_corpus
from scripts.run_final_extended_eval import load_cases, RERANKER_PATH
from scripts.run_m2_controlled_evaluation import StoredRankingRetriever
from rag_hcmute.evaluation.interval_metrics import character_metrics
from rag_hcmute.evaluation.reranker import LocalCrossEncoderReranker
from rag_hcmute.retrieval.common import hit_from_chunk

if not torch.cuda.is_available():
    raise RuntimeError('CUDA unavailable')
source = ROOT / 'docs/evidence/v2/ranking43.json'
prior = json.loads(source.read_text(encoding='utf8'))
snapshot, chunks, pages = validate_corpus()
cases, spans = load_cases(Path('D:/RAG/private_eval/final_20261115/cases.tsv'), pages)
queries = [SimpleNamespace(question_id=qid, question=cases[qid]['question']) for qid in spans]
lookup = {c.chunk_id: c for c in chunks}
pool = {q.question: [hit_from_chunk(i, lookup[cid], 0.) for i, cid in
        enumerate(prior['candidate_ids'][q.question_id][:20], 1)] for q in queries}
stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
out = ROOT / f'artifacts/results/v3/reranker_lengths_{stamp}.json'
out.parent.mkdir(parents=True, exist_ok=True)
report = {'run_id': 'reranker_lengths_' + stamp, 'source_run': prior['run_id'],
          'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
          'revision_before_run': subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
          'runner_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
          'snapshot_id': snapshot['snapshot_id'], 'candidate_depth': 20, 'question_count': len(queries),
          'model': str(RERANKER_PATH.name), 'batch_size': 1, 'results': [], 'completed': False}
def save(): out.write_text(json.dumps(report, indent=2)+'\n',encoding='utf8')
for length in (1024, 2048):
    model = None
    try:
        model = LocalCrossEncoderReranker(RERANKER_PATH, max_length=length, batch_size=1)
        model.rerank(query=queries[0].question,candidates=pool[queries[0].question][:1],chunks_by_id=lookup)
        ranked, ms, truncated = {}, [], 0
        for i,q in enumerate(queries,1):
            result=model.rerank(query=q.question,candidates=pool[q.question],chunks_by_id=lookup)
            ranked[q.question]=result.hits; ms.append(result.latency_ms); truncated += result.truncated_pair_count
            if i % 10 == 0: print(length, i, '/',len(queries),flush=True)
        metric=character_metrics(questions=queries,spans_by_question=spans,chunks=chunks,pages_by_document=pages,retriever=StoredRankingRetriever(ranked))
        report['results'].append({'max_length':length,'status':'complete','truncated_pairs':truncated,'pair_count':len(queries)*20,
                                  'latency_p50_ms':statistics.median(ms),'metrics':metric})
    except torch.cuda.OutOfMemoryError:
        report['results'].append({'max_length':length,'status':'cuda_out_of_memory'})
    finally:
        del model
        gc.collect(); torch.cuda.empty_cache(); save()
report['completed']=True; save(); print(out,flush=True)
