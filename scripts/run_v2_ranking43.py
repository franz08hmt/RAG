"""Compare fusion and reranking with a fixed candidate list per development query."""
import gc
import hashlib
import json
import statistics
import subprocess
import sys
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/"src")]
from scripts.run_embedding_model_ablation import validate_corpus, MODEL_CONFIGS
from scripts.run_final_extended_eval import load_cases
from types import SimpleNamespace
from scripts.run_m2_controlled_evaluation import StoredRankingRetriever
from rag_hcmute.evaluation.interval_metrics import character_metrics
from rag_hcmute.evaluation.context_budget import coverage_of_selection, source_coordinates
from rag_hcmute.evaluation.evidence_spans import load_exact_evidence_spans
from rag_hcmute.evaluation.run_pilot import load_pilot_questions
from rag_hcmute.evaluation.reranker import LocalCrossEncoderReranker
from rag_hcmute.retrieval.bm25_index import BM25Retriever
from rag_hcmute.retrieval.dense_index import DenseRetriever


def fuse(lexical, dense, weight):
    hits = {h.chunk_id:h for h in [*lexical, *dense]}
    scores = dict.fromkeys(hits, 0.)
    for branch, factor in ((lexical, 1-weight if weight is not None else 1),
                           (dense, weight if weight is not None else 1)):
        low, high = min(h.score for h in branch), max(h.score for h in branch)
        for h in branch:
            value = (1 / (60+h.rank) if weight is None else
                     (h.score-low)/(high-low) if high>low else 0.)
            scores[h.chunk_id] += factor*value
    order = sorted(scores, key=lambda cid:(-scores[cid], cid))[:50]
    return [replace(hits[cid],rank=rank,score=scores[cid]) for rank,cid in enumerate(order,1)]


def main():
    print(f"Python executable: {sys.executable}", flush=True)
    import torch
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA required.")
    snapshot, chunks, pages = validate_corpus()
    qpath = Path('D:/RAG/private_eval/final_20261115/cases.tsv')
    cases, spans = load_cases(qpath, pages)
    qs = [SimpleNamespace(question_id=qid, question=cases[qid]['question']) for qid in spans]
    lookup = {c.chunk_id:c for c in chunks}
    coords = source_coordinates(pages)
    bm = BM25Retriever(chunks)
    dense = DenseRetriever(chunks,str(MODEL_CONFIGS["bge-m3"]["path"]),batch_size=4,cache_dir=ROOT/"artifacts/indexes/dense_console")
    pools = {}
    for q in qs:
        branches = (bm.query(q.question,top_k=50).hits,dense.query(q.question,top_k=50).hits)
        for name,weight in (("RRF",None),("weighted25",.25),("weighted50",.5),("weighted75",.75)):
            pools.setdefault(name,{})[q.question] = fuse(*branches,weight)
    del dense
    gc.collect()
    torch.cuda.empty_cache()
    def measure(rankings):
        return character_metrics(questions=qs,spans_by_question=spans,chunks=chunks,pages_by_document=pages,
                                 retriever=StoredRankingRetriever(rankings))
    fusion = {name:measure(rankings) for name,rankings in pools.items()}
    chosen = max(fusion,key=lambda name:(fusion[name]["macro"]["character_recall_at_5"],fusion[name]["macro"]["mrr_at_10_threshold_05"]))
    pool = pools[chosen]
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output = ROOT/f"artifacts/results/v2/ranking43_{stamp}.json"
    output.parent.mkdir(parents=True,exist_ok=True)
    report = {"run_id":f"ranking43_{stamp}","snapshot_id":snapshot["snapshot_id"],"partition":"AI-draft extended; not human verified",
        "holdout_used":False,"question_count":len(qs),"fusion":fusion,"chosen_on_dev":chosen,
        "selection_rule":"macro character recall@5, then MRR@10; ties preserve configuration order",
        "branch_depth":50,"rrf_k":60,"weighted_fusion":"minmax within each top50, missing=0, integer suffix is dense percentage",
        "candidate_ids":{q.question_id:[h.chunk_id for h in pool[q.question]] for q in qs},
        "pool_coverage":{}, "rerankers":[], "completed":False,"max_pair_tokens":512,
        "revision_before_run":subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(),
        "source_sha256":{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in
                         [Path(__file__),ROOT/"src/rag_hcmute/evaluation/reranker.py",ROOT/"src/rag_hcmute/evaluation/interval_metrics.py"]}}
    for n in (10,20,50):
        report["pool_coverage"][str(n)] = statistics.mean(coverage_of_selection(
            [lookup[h.chunk_id] for h in pool[q.question][:n]],spans[q.question_id],coords)["character_recall"] for q in qs)
    path = Path("D:/RAG/models/huggingface/hub/models--BAAI--bge-reranker-v2-m3/snapshots/953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e")
    models = [{"model_id":"BAAI/bge-reranker-v2-m3","path":str(path),"revision":path.name}]
    models += json.loads((ROOT/"artifacts/results/m3/downloaded_rerankers.json").read_text())
    def save():
        output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    for entry in models:
        model = LocalCrossEncoderReranker(Path(entry["path"]),max_length=512,batch_size=4)
        model.rerank(query=qs[0].question,candidates=pool[qs[0].question][:4],chunks_by_id=lookup)
        for n in (10,20,50):
            ranked, ms, truncated = {}, [], 0
            for q in qs:
                result = model.rerank(query=q.question,candidates=pool[q.question][:n],chunks_by_id=lookup)
                ranked[q.question] = result.hits
                ms.append(result.latency_ms)
                truncated += result.truncated_pair_count
            report["rerankers"].append({"model_id":entry["model_id"],"revision":entry["revision"],"depth":n,
                "metrics":measure(ranked),"truncated_pairs":truncated,"pair_count":len(qs)*n,
                "latency_p50_ms":statistics.median(ms),"latency_ms":ms,"load_seconds":model.load_seconds})
            save()
            print(entry["model_id"],n,flush=True)
        del model
        gc.collect()
        torch.cuda.empty_cache()
    report["completed"] = True
    save()
    print(output,flush=True)


if __name__=="__main__":
    main()
