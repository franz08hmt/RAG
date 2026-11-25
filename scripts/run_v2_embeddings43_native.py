"""Six local embeddings on shared 128-token source windows; dev only.

PhoBERT models receive PyVi-segmented strings, E5 receives role prefixes. Source
intervals always refer to the original whitespace-normalized corpus, not to
preprocessed strings. Native model configurations and timings are recorded.
"""
from __future__ import annotations
import os
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'src')]
for key in ('HF_HUB_OFFLINE','TRANSFORMERS_OFFLINE','HF_HUB_DISABLE_IMPLICIT_TOKEN'):
    os.environ[key]='1'
import gc
import json
import time
import hashlib
import subprocess
import statistics
from functools import lru_cache
from datetime import datetime, timezone
from scripts.run_embedding_model_ablation import validate_corpus, MODEL_CONFIGS
from scripts.run_final_extended_eval import load_cases
from types import SimpleNamespace
from scripts.run_m2_controlled_evaluation import StoredVectorRetriever
from rag_hcmute.evaluation.controlled_embedding import shared_budget_chunks,input_signature
from rag_hcmute.evaluation.evidence_spans import load_exact_evidence_spans
from rag_hcmute.evaluation.run_pilot import load_pilot_questions
from rag_hcmute.evaluation.interval_metrics import character_metrics,paired_bootstrap


def main():
    print(f'Python executable: {sys.executable}',flush=True)
    import torch,faiss,numpy as np
    from transformers import AutoTokenizer
    from sentence_transformers import SentenceTransformer
    from pyvi import ViTokenizer
    import importlib.metadata
    if not torch.cuda.is_available(): raise RuntimeError('CUDA is required for this run.')
    faiss.omp_set_num_threads(1)
    entries=[{'model_id':v['model_id'],'path':str(v['path']),'revision':v['path'].name,
              'license':'mit'} for v in MODEL_CONFIGS.values()]
    entries+=json.loads((ROOT/'artifacts/results/m3/downloaded_embeddings.json').read_text(encoding='utf-8'))
    for entry in entries:
        entry['segmented']=entry['model_id'].startswith(('bkai-foundation-models/','dangvantuan/'))
        entry['e5']=entry['model_id'].startswith('intfloat/')
    @lru_cache(maxsize=12000)
    def segment(text): return ViTokenizer.tokenize(text)
    def prepare(text,entry,query=False,no_prefix=False):
        text=segment(text) if entry['segmented'] else text
        return (('query: ' if query else 'passage: ') if entry['e5'] and not no_prefix else '')+text
    tokenizers={e['model_id']:AutoTokenizer.from_pretrained(e['path'],local_files_only=True) for e in entries}
    counters=[lambda text,e=e:len(tokenizers[e['model_id']](prepare(text,e),add_special_tokens=True,truncation=False)['input_ids']) for e in entries]
    snapshot,baseline,pages=validate_corpus()
    # The native-limit comparison uses the same historical G0 chunks for every model.
    chunks=baseline
    qpath=Path('D:/RAG/private_eval/final_20261115/cases.tsv'); apath=qpath
    cases,spans=load_cases(qpath,pages)
    questions=[SimpleNamespace(question_id=qid,question=cases[qid]['question']) for qid in spans]
    answerable=questions
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    output=ROOT/f'artifacts/results/v2/embeddings43_native_{stamp}.json'
    output.parent.mkdir(parents=True,exist_ok=True)
    report={'run_id':f'embeddings43_native_{stamp}','snapshot_id':snapshot['snapshot_id'],'partition':'AI-draft extended; not human verified',
        'holdout_used':False,'question_count':len(answerable),'chunk_count':len(chunks),'chunk_signature':input_signature(chunks),
        'config':{'shared_encoder_tokens':None,'chunk_set':'G0 156 baseline chunks','batch_size':8,'normalized':True,'faiss':'IndexFlatIP'},
        'runtime':{'python':sys.version.split()[0],'torch':torch.__version__,'gpu':torch.cuda.get_device_name(0),
                   'pyvi':importlib.metadata.version('pyvi'),'sentence_transformers':importlib.metadata.version('sentence-transformers')},
        'revision_before_run':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        'source_sha256':{str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in
            [Path(__file__),ROOT/'src/rag_hcmute/evaluation/controlled_embedding.py',ROOT/'src/rag_hcmute/evaluation/interval_metrics.py',qpath,apath]},
        'limitations':['43 AI-draft questions; no student validation or independent holdout.',
            'Common G0 chunks with model native token limits; truncation differs by model and affects fairness.',
            'PhoBERT preprocessing changes input representation but never source offsets; PyVi may introduce segmentation errors.',
            'Single corpus encoding run per model; query timing uses three repetitions after warm-up.'],
        'models':[], 'completed':False}
    def save(): output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    save(); print(f'Shared windows: {len(chunks)}',flush=True)
    for entry in entries:
        print(f'Encoding {entry["model_id"]}',flush=True)
        start=time.perf_counter()
        model=SentenceTransformer(entry['path'],device='cuda',local_files_only=True)
        native_limit=model.max_seq_length
        model.max_seq_length=native_limit
        model.eval(); torch.cuda.synchronize()
        load_seconds=time.perf_counter()-start
        def encode(texts):
            v=model.encode(texts,batch_size=8,normalize_embeddings=True,convert_to_numpy=True,show_progress_bar=False)
            torch.cuda.synchronize()
            return np.asarray(v,dtype='float32')
        variants=[False,True] if entry['model_id']=='intfloat/multilingual-e5-small' else [False]
        for no_prefix in variants:
            texts=[prepare(c.text,entry,no_prefix=no_prefix) for c in chunks]
            query_texts=[prepare(q.question,entry,query=True,no_prefix=no_prefix) for q in answerable]
            lengths=[len(model.tokenizer(t,add_special_tokens=True,truncation=False)['input_ids']) for t in texts+query_texts]
            truncated_count=sum(length > native_limit for length in lengths[:len(texts)])
            truncated_queries=sum(length > native_limit for length in lengths[len(texts):])
            encode(texts[:1]); torch.cuda.reset_peak_memory_stats()
            start=time.perf_counter(); vectors=encode(texts); corpus_seconds=time.perf_counter()-start
            qvectors={}; timings=[]
            encode(query_texts[:1])
            for q,text in zip(answerable,query_texts):
                for repetition in range(3):
                    start=time.perf_counter(); v=encode([text]); timings.append((time.perf_counter()-start)*1000)
                qvectors[q.question]=v
            index=faiss.IndexFlatIP(vectors.shape[1]); index.add(vectors)
            metrics=character_metrics(questions=questions,spans_by_question=spans,chunks=chunks,pages_by_document=pages,
                                     retriever=StoredVectorRetriever(chunks,index,qvectors))
            result={k:v for k,v in entry.items() if k!='path'}
            result.update(variant='no_prefix_ablation' if no_prefix else 'recommended_preprocessing',
                native_max_seq_length=native_limit,actual_max_seq_length=native_limit,dimension=vectors.shape[1],
                input_max=max(lengths),truncated_input_count=truncated_count,truncated_query_count=truncated_queries,load_seconds=load_seconds,corpus_encoding_seconds=corpus_seconds,
                query_encoding_p50_ms=statistics.median(timings),query_encoding_p95_ms=sorted(timings)[-2],
                query_timing_n=len(timings),peak_allocated_vram_bytes=torch.cuda.max_memory_allocated(),
                serialized_index_bytes=int(faiss.serialize_index(index).nbytes),metrics=metrics)
            report['models'].append(result); save()
            print(f'  {result["variant"]}: Recall={metrics["macro"]["character_recall_at_5"]:.4f}',flush=True)
            del vectors,index,qvectors
        del model; gc.collect(); torch.cuda.empty_cache()
    base=report['models'][0]['metrics']['per_question']
    for model in report['models']:
        rows=model['metrics']['per_question']
        assert [r['question_id'] for r in rows]==[r['question_id'] for r in base]
        model['paired_vs_bge']=paired_bootstrap([r['character_recall_at_5'] for r in base],
                                               [r['character_recall_at_5'] for r in rows],repetitions=1000)
    report['completed']=True; save(); print(output,flush=True)


if __name__=='__main__': main()
