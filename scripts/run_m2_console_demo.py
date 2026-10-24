"""Real local development demo; full text stays outside Git, metrics contain IDs only."""
from __future__ import annotations

import contextlib
import gc
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time
from dataclasses import asdict
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from rag_hcmute.console_app import create_retriever, format_retrieval_result, _chunks_by_id, _move_retrieval_models
from rag_hcmute.generation.ollama import generate_grounded_answer, sources_from_hits
from rag_hcmute.evaluation.run_pilot import load_pilot_questions
from rag_hcmute.evaluation.reranker import LocalCrossEncoderReranker
from rag_hcmute.retrieval.reranked import RerankedQueryResult


def main():
    print(f'Python executable: {sys.executable}', flush=True)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    out = ROOT / 'artifacts/results/m2_console' / stamp
    out.mkdir(parents=True)
    private = Path('D:/RAG/private_eval/m2_console') / stamp
    private.mkdir(parents=True)
    report = {'run_id': f'm2_console_{stamp}', 'snapshot_id': '5da3bd4d5de54492',
              'partition': 'development', 'model': 'qwen3:4b', 'temperature': 0, 'think': False,
              'review_status': 'human_semantic_review_pending', 'api_cost_usd': 0,
              'git_revision_before_run': subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
              'source_sha256': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in
                 [Path(__file__), ROOT/'src/rag_hcmute/generation/ollama.py',ROOT/'src/rag_hcmute/console_app.py',ROOT/'src/rag_hcmute/retrieval/dense_index.py']},
              'cases': []}
    def save():
        (out/'metrics.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
    save()
    qset = load_pilot_questions(ROOT/'data/question_sets/pilot_questions.csv',partition='development',
        snapshot_path=ROOT/'data/manifests/corpus_snapshot.json',project_root=ROOT)
    retriever = create_retriever(method='hybrid',chunks_path=ROOT/'data/processed/g0_reproduction/chunks/chunks.jsonl',
        dense_model=Path('D:/RAG/models/huggingface/hub/models--BAAI--bge-m3/snapshots/5617a9f61b028005a4858fdac845db406aefb181'),
        dense_batch_size=4,dense_cache=ROOT/'artifacts/indexes/dense_console',
        progress=lambda s: print(s,flush=True))
    report['startup'] = retriever.startup_metrics
    source_sets = {}
    retrieval_rows = {}
    chunks_by_id = _chunks_by_id(retriever)
    initial_results = {q.question_id: retriever.query(q.question,top_k=20) for q in qset}
    report['release_gpu_ms'] = _move_retrieval_models(retriever,'cpu')
    del retriever
    gc.collect()
    import torch
    torch.cuda.empty_cache()
    reranker = LocalCrossEncoderReranker(Path('D:/RAG/models/huggingface/hub/models--BAAI--bge-reranker-v2-m3/snapshots/953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e'),max_length=1024,batch_size=4)
    report['startup']['reranker_load_seconds'] = reranker.load_seconds
    report['startup']['total_seconds'] += reranker.load_seconds
    report['startup']['loading_policy'] = 'sequential embedding then reranker; distinct from interactive cold run'
    for q in qset:
        initial = initial_results[q.question_id]
        ranked = reranker.rerank(query=q.question,candidates=initial.hits,chunks_by_id=chunks_by_id)
        r = RerankedQueryResult(hits=ranked.hits[:5],latency_ms=initial.latency_ms+ranked.latency_ms,
             retrieval_latency_ms=initial.latency_ms,reranker_latency_ms=ranked.latency_ms,
             candidate_count=len(initial.hits),candidate_depth=20,pair_count=len(initial.hits),
             truncated_pair_count=ranked.truncated_pair_count)
        source_sets[q.question_id] = sources_from_hits(r.hits, chunks_by_id)
        retrieval_rows[q.question_id] = {'retrieval_ms': r.latency_ms,
             'candidate_count': r.candidate_count, 'truncated_pairs': r.truncated_pair_count,
             'retrieved_chunk_ids': [h.chunk_id for h in r.hits]}
        with (private/f'{q.question_id}_retrieval.txt').open('w',encoding='utf-8') as stream:
            stream.write(q.question+'\n'+ '\n'.join(f'[{h.rank}] {h.chunk_id} | PDF {h.pdf_page_start}-{h.pdf_page_end} | score {h.score}' for h in r.hits))
    del reranker
    gc.collect()
    torch.cuda.empty_cache()
    for variant in ('standard','scope_check'):
        for q in qset:
            print(f'Local generation {variant} {q.question_id}',flush=True)
            sources = source_sets[q.question_id]
            try:
                generated = generate_grounded_answer(q.question,sources,prompt_variant=variant,timeout_seconds=180,keep_alive='5m')
                result = asdict(generated)
                row = {'qid':q.question_id,'answerability':q.answerability,'prompt_variant':variant,
                       'status':generated.status,'abstained':generated.abstained,'generation_ms':generated.latency_ms,
                       'citation_count':len(generated.citations), 'citation_ids':[s.source_id for s in generated.citations],
                       'inline_citation_present': any(f'[{s.source_id}]' in generated.answer for s in generated.citations),
                       **retrieval_rows[q.question_id]}
            except (RuntimeError,ValueError) as error:
                result = {'error_type':type(error).__name__}
                row = {'qid':q.question_id,'answerability':q.answerability,'prompt_variant':variant,'status':'transport_error'}
            (private/f'{variant}_{q.question_id}.json').write_text(json.dumps(
                {'question':q.question,'sources':[asdict(s) for s in sources],'result':result},ensure_ascii=False,indent=2),encoding='utf-8')
            report['cases'].append(row)
            save()
    report['completed'] = True
    report['private_content_directory'] = str(private)
    save()
    print(f'Metrics: {out / "metrics.json"}',flush=True)


if __name__ == '__main__':
    main()
