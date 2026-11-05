"""Six splitter policies, two retrievers, fixed k and Qwen source-context budgets.

Offline model inference; metrics-only output. Existing seven dev labels only.
"""
from __future__ import annotations
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'src')]
for key in ('HF_HUB_OFFLINE','TRANSFORMERS_OFFLINE','HF_HUB_DISABLE_IMPLICIT_TOKEN'):
    os.environ[key] = '1'

import json
import hashlib
import statistics
import subprocess
import time
from datetime import datetime, timezone

from rag_hcmute.ingestion.experimental_splitters import STRATEGIES, split_document, semantic_units
from rag_hcmute.evaluation.context_budget import source_coordinates, coverage_of_selection, pack_ranked_chunks
from rag_hcmute.evaluation.evidence_spans import load_exact_evidence_spans
from rag_hcmute.evaluation.run_pilot import load_pilot_questions
from rag_hcmute.evaluation.interval_metrics import character_metrics, paired_bootstrap
from rag_hcmute.evaluation.controlled_embedding import input_signature
from rag_hcmute.retrieval.bm25_index import BM25Retriever
from scripts.run_embedding_model_ablation import validate_corpus, MODEL_CONFIGS
from scripts.run_m2_controlled_evaluation import StoredVectorRetriever

QWEN_TOKENIZER = Path('D:/RAG/models/huggingface/hub/models--Qwen--Qwen3-4B/snapshots/1cfa9a7208912126459214e8b04321603b3df60c')


def main():
    print(f'Python executable: {sys.executable}', flush=True)
    import torch
    import faiss
    import numpy as np
    from transformers import AutoTokenizer
    from sentence_transformers import SentenceTransformer
    if not torch.cuda.is_available():
        raise RuntimeError('Expected approved CUDA environment.')
    faiss.omp_set_num_threads(1)
    snapshot, baseline, pages = validate_corpus()
    qpath = ROOT/'data/question_sets/pilot_questions.csv'
    apath = ROOT/'data/question_sets/pilot_evidence_annotations.json'
    questions = load_pilot_questions(qpath, partition='development', project_root=ROOT,
                                    snapshot_path=ROOT/'data/manifests/corpus_snapshot.json')
    bge_path = MODEL_CONFIGS['bge-m3']['path']
    model = SentenceTransformer(str(bge_path), device='cuda', local_files_only=True)
    model.max_seq_length = 384
    model.eval()
    count = lambda text: len(model.tokenizer(text, add_special_tokens=True, truncation=False)['input_ids'])
    qtok = AutoTokenizer.from_pretrained(str(QWEN_TOKENIZER), local_files_only=True)
    qcount = lambda text: len(qtok(text, add_special_tokens=False, truncation=False)['input_ids'])
    def encode(texts):
        v = model.encode(texts, batch_size=4, normalize_embeddings=True, convert_to_numpy=True, show_progress_bar=False)
        torch.cuda.synchronize()
        return np.asarray(v, dtype='float32')
    encode(['Khởi động bộ mã hóa.'])
    query_vectors = {q.question: encode([q.question]) for q in questions}
    semantic_cuts, semantic_meta = {}, {}
    for doc in snapshot['documents']:
        did = doc['document_id']
        started = time.perf_counter()
        units = semantic_units(pages[did], count)
        vectors = encode([u[2] for u in units])
        scores = np.sum(vectors[:-1] * vectors[1:], axis=1)
        threshold = float(np.percentile(scores, 25)) if len(scores) else None
        cuts = [int(units[i][1]) for i, value in enumerate(scores) if value <= threshold]
        semantic_cuts[did] = cuts
        semantic_meta[did] = {'unit_count': len(units), 'cut_count': len(cuts),
                              'adjacent_cosine_percentile25': threshold,
                              'seconds': time.perf_counter()-started}
        print(f'Semantic preparation: {did}, units={len(units)}', flush=True)
    # Gold is read only after source-only boundary preparation.
    spans, meta = load_exact_evidence_spans(questions_path=qpath, annotations_path=apath,
        pages_by_document=pages, snapshot_id=snapshot['snapshot_id'], question_ids={q.question_id for q in questions})
    answerable = [q for q in questions if q.question_id in spans]
    coords = source_coordinates(pages)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    output = ROOT/f'artifacts/results/m3/chunking_{stamp}.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    tracked_sources = [Path(__file__), ROOT/'src/rag_hcmute/ingestion/experimental_splitters.py',
        ROOT/'src/rag_hcmute/evaluation/context_budget.py', ROOT/'src/rag_hcmute/evaluation/interval_metrics.py',
        qpath, apath, ROOT/'data/manifests/corpus_manifest.csv']
    report = {'run_id': f'chunking_{stamp}', 'snapshot_id': snapshot['snapshot_id'],
        'partition': 'development', 'holdout_used': False, 'question_count': len(answerable),
        'gold_span_count': meta['evidence_span_count'], 'semantic_preparation': semantic_meta,
        'revision_before_run': subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        'source_sha256': {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in tracked_sources},
        'config': {'bge_revision': bge_path.name, 'encoder_tokens_including_special':384,
                   'character_budget':1200,'overlap':0,'candidate_depth':50,'top_k':5,
                   'qwen_tokenizer_revision':QWEN_TOKENIZER.name,'context_budgets':[1000,2000],
                   'packing':'whole chunks, greedy skip if does not fit, joined with two newlines; no gold'},
        'runtime':{'python':sys.version.split()[0], 'torch':torch.__version__, 'gpu':torch.cuda.get_device_name(0)},
        'limitations':['Seven existing dev questions; no human label expansion or independent test.',
            'Zero overlap and one size setting; not a full hyperparameter sweep.',
            'Sentence splitting is punctuation heuristic; recursive is a custom boundary-priority policy, not LangChain.',
            'Semantic uses BGE-M3 adjacent unit similarity 25th percentile per document; may favor the same dense model.',
            'Qwen token budgets count source text and separators only; exclude question, labels and chat template.',
            'Timing is a single development execution, not a latency distribution or production benchmark.'],
        'strategies':{}, 'completed':False}
    def save():
        output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    save()
    for strategy in STRATEGIES:
        started = time.perf_counter()
        chunks = []
        for doc in snapshot['documents']:
            chunks.extend(split_document(pages[doc['document_id']],doc['document_id'],doc['document_title'],
                strategy=strategy,count_tokens=count,semantic_boundaries=semantic_cuts[doc['document_id']]))
        construction_seconds = time.perf_counter()-started
        lengths = [count(c.text) for c in chunks]
        if max(lengths) > 384:
            raise RuntimeError('Unexpected truncation.')
        started = time.perf_counter()
        vectors = encode([c.text for c in chunks])
        embedding_seconds = time.perf_counter()-started
        index = faiss.IndexFlatIP(vectors.shape[1])
        index.add(vectors)
        entry = {'chunk_count':len(chunks),'signature':input_signature(chunks),
            'length_tokens':{'min':min(lengths),'median':statistics.median(lengths),'max':max(lengths),'truncated':0},
            'construction_seconds_excluding_semantic_preparation':construction_seconds,'embedding_seconds':embedding_seconds,
            'gold_spans_not_contained_in_any_single_chunk':sum(not any(c.document_id==s.document_id and c.token_start<=s.token_start and c.token_end>=s.token_end for c in chunks) for values in spans.values() for s in values),
            'retrieval':{}}
        lookup = {c.chunk_id:c for c in chunks}
        for name, retriever in [('bm25',BM25Retriever(chunks)),('dense_bge',StoredVectorRetriever(chunks,index,query_vectors))]:
            fixed = character_metrics(questions=questions,spans_by_question=spans,chunks=chunks,
                                     pages_by_document=pages,retriever=retriever)
            budgets = {}
            for budget in (1000,2000):
                rows = []
                for q in answerable:
                    hits = retriever.query(q.question,top_k=50).hits
                    selected, actual, skipped = pack_ranked_chunks([lookup[h.chunk_id] for h in hits],qcount,budget)
                    rows.append({'question_id':q.question_id,**coverage_of_selection(selected,spans[q.question_id],coords),
                        'context_tokens':actual,'selected_ids':[c.chunk_id for c in selected], 'skipped_count':len(skipped)})
                budgets[str(budget)] = {'macro':{key:statistics.mean(r[key] for r in rows) for key in
                    ('character_recall','character_precision','character_iou','context_tokens','selected_chunk_count')},'per_question':rows}
            entry['retrieval'][name] = {'fixed_top5':fixed,'context_budgets':budgets}
        report['strategies'][strategy] = entry
        save()
        print(f'{strategy}: {len(chunks)} chunks, dense R@5={entry["retrieval"]["dense_bge"]["fixed_top5"]["macro"]["character_recall_at_5"]:.4f}',flush=True)
    report['paired_dev_comparisons_vs_tokens'] = {}
    base = report['strategies']['tokens']['retrieval']['dense_bge']['fixed_top5']['per_question']
    for strategy, entry in report['strategies'].items():
        rows = entry['retrieval']['dense_bge']['fixed_top5']['per_question']
        assert [r['question_id'] for r in rows] == [r['question_id'] for r in base]
        report['paired_dev_comparisons_vs_tokens'][strategy] = paired_bootstrap(
            [r['character_recall_at_5'] for r in base],[r['character_recall_at_5'] for r in rows],repetitions=1000)
    report['completed'] = True
    save()
    print(output,flush=True)


if __name__ == '__main__':
    main()
