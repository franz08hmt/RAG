"""Offline, development-only comparison with identical, untruncated model inputs."""
from __future__ import annotations

import argparse
import gc
import hashlib
import importlib.metadata
import json
import os
import platform
import statistics
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from rag_hcmute.evaluation.controlled_embedding import input_signature, shared_budget_chunks
from rag_hcmute.evaluation.interval_metrics import character_metrics, paired_bootstrap
from rag_hcmute.evaluation.evidence_spans import load_exact_evidence_spans
from rag_hcmute.evaluation.run_pilot import load_pilot_questions
from rag_hcmute.retrieval.bm25_index import BM25Retriever
from rag_hcmute.retrieval.common import hit_from_chunk
from rag_hcmute.retrieval.hybrid import ReciprocalRankFusionRetriever
from scripts.run_chunk_strategy_ablation import _evidence_metrics_including_uncovered
from scripts.run_embedding_model_ablation import MODEL_CONFIGS, sha256_file, validate_corpus


def timing_summary(values):
    ordered = sorted(values)
    return {"n": len(values), "p50_ms": statistics.median(ordered),
            "p95_nearest_rank_ms": ordered[max(0, __import__("math").ceil(.95 * len(ordered)) - 1)]}


class StoredVectorRetriever:
    """Query vectors are precomputed; time here is index search only."""
    def __init__(self, chunks, index, query_vectors):
        self.chunks, self.index, self.query_vectors = chunks, index, query_vectors

    def query(self, question, top_k=10):
        started = time.perf_counter()
        scores, indices = self.index.search(self.query_vectors[question], top_k)
        latency = (time.perf_counter() - started) * 1000
        hits = [hit_from_chunk(rank, self.chunks[int(i)], float(score))
                for rank, (i, score) in enumerate(zip(indices[0], scores[0]), 1) if i >= 0]
        return SimpleNamespace(hits=hits, latency_ms=latency)


class StoredRankingRetriever:
    def __init__(self, rankings):
        self.rankings = rankings

    def query(self, question, top_k=10):
        return SimpleNamespace(hits=self.rankings[question][:top_k], latency_ms=0.0)


def main():
    print(f"Python executable: {sys.executable}", flush=True)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepare-only", action="store_true", help="Tokenizers/CPU only; no model weights.")
    parser.add_argument("--reranker-model", type=Path)
    args = parser.parse_args()
    for key in ("HF_HUB_OFFLINE", "TRANSFORMERS_OFFLINE", "HF_HUB_DISABLE_IMPLICIT_TOKEN", "HF_HUB_DISABLE_TELEMETRY"):
        os.environ[key] = "1"
    from transformers import AutoTokenizer

    snapshot, baseline_chunks, pages = validate_corpus()
    questions_path = ROOT / "data/question_sets/pilot_questions.csv"
    annotation_path = ROOT / "data/question_sets/pilot_evidence_annotations.json"
    questions = load_pilot_questions(
        questions_path, partition="development",
        partition_manifest_path=ROOT / "data/question_sets/question_partition_manifest.csv",
        snapshot_path=ROOT / "data/manifests/corpus_snapshot.json", project_root=ROOT,
    )
    tokenizers = {key: AutoTokenizer.from_pretrained(str(config["path"]), local_files_only=True)
                  for key, config in MODEL_CONFIGS.items()}
    counters = [lambda text, tok=tokenizers[key], prefix=config["passage_prefix"]:
                len(tok(prefix + text, add_special_tokens=True, truncation=False)["input_ids"])
                for key, config in MODEL_CONFIGS.items()]
    chunks = []
    for document in snapshot["documents"]:
        chunks.extend(shared_budget_chunks(pages[document["document_id"]], document["document_id"],
                                          document["document_title"], counters))
    # Only now consult gold: construction never adapts to questions or annotations.
    spans, annotation_meta = load_exact_evidence_spans(
        questions_path=questions_path, annotations_path=annotation_path, pages_by_document=pages,
        snapshot_id=snapshot["snapshot_id"], question_ids={q.question_id for q in questions},
    )
    answerable = [q for q in questions if q.question_id in spans]
    def metrics(retriever):
        strict = _evidence_metrics_including_uncovered(
            questions=questions, spans_by_question=spans, chunks=chunks, retriever=retriever)
        strict["character_coverage"] = character_metrics(
            questions=questions, spans_by_question=spans, chunks=chunks,
            pages_by_document=pages, retriever=retriever)
        return strict
    baseline_lengths = {}
    controlled_lengths = {}
    for (key, config), counter in zip(MODEL_CONFIGS.items(), counters):
        before = [counter(chunk.text) for chunk in baseline_chunks]
        after = [counter(chunk.text) for chunk in chunks]
        qlengths = [len(tokenizers[key](config["query_prefix"] + q.question,
                    add_special_tokens=True, truncation=False)["input_ids"]) for q in questions]
        if max(after + qlengths) > 512:
            raise RuntimeError("Shared inputs still exceed 512 tokens; refuse silent truncation.")
        baseline_lengths[key] = {"over_original_limit": sum(n > config["max_seq_length"] for n in before),
                                 "original_limit": config["max_seq_length"], "max": max(before)}
        controlled_lengths[key] = {"over_512": sum(n > 512 for n in after), "max": max(after),
                                   "median": statistics.median(after), "query_max": max(qlengths)}
    bm25 = BM25Retriever(chunks)
    report = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "git_revision_before_run": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "source_sha256": {str(path.relative_to(ROOT)): sha256_file(path) for path in [
            Path(__file__), ROOT / "src/rag_hcmute/evaluation/controlled_embedding.py",
            ROOT / "src/rag_hcmute/evaluation/interval_metrics.py",
            ROOT / "scripts/run_chunk_strategy_ablation.py", questions_path, annotation_path,
            ROOT / "data/manifests/corpus_manifest.csv",
            ROOT / "data/processed/g0_reproduction/snapshot.json"]},
        "snapshot_id": snapshot["snapshot_id"], "partition": "development", "holdout_used": False,
        "human_review_status": "No new human labels; reuse existing evidence annotations; generation not evaluated",
        "question_count": len(questions), "answerable_count": len(spans),
        "gold_span_count": annotation_meta["evidence_span_count"],
        "baseline_chunk_count": len(baseline_chunks), "shared_chunk_count": len(chunks),
        "shared_chunk_signature": input_signature(chunks),
        "chunk_policy": {"word_cap": 250, "overlap_whitespace_tokens": 40, "model_token_cap": 512,
                         "section_aware": False, "gold_used_in_construction": False,
                         "description": "document-wide sliding windows; decrease end until both prefix+text+special-token lengths fit; no tail merge"},
        "baseline_input_lengths": baseline_lengths, "shared_input_lengths": controlled_lengths,
        "retrieval": {"bm25": metrics(bm25)}, "embedding_models": [], "vector_indexes": [], "reranking": {},
        "runtime": {"python": sys.version.split()[0], "platform": platform.platform()},
        "limitations": [
            "Development-only, seven answerable questions and ten source spans; no independent holdout.",
            "Both models see identical complete passage text; prefixes/pooling/model size remain model-specific.",
            "This experiment changes chunk policy from the production section-aware 500/80 baseline; cross-run differences are not pure model effects.",
            "A gold span split across chunks is counted as missed even if two returned chunks jointly cover it; coverage is reported separately.",
            "Three unanswerable questions have no positive evidence labels and are excluded from retrieval recall/MRR, not counted as retrieval successes.",
            "Latency measurements are sequential on one machine and a tiny corpus, not a production capacity benchmark.",
        ],
    }
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    outdir = ROOT / "artifacts/results/m2_eval"
    outdir.mkdir(parents=True, exist_ok=True)
    output = outdir / f"controlled_{'prepare' if args.prepare_only else 'run'}_{stamp}.json"

    def save():
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    save()
    print(f"Shared corpus: {len(chunks)} chunks; both input lengths <=512; prepared metrics: {output}", flush=True)
    if args.prepare_only:
        return 0

    import faiss
    import numpy as np
    import torch
    from sentence_transformers import SentenceTransformer
    if not torch.cuda.is_available():
        raise RuntimeError("The approved CUDA environment is required for this run.")
    faiss.omp_set_num_threads(1)
    report["runtime"].update({"torch": torch.__version__, "cuda": torch.version.cuda,
        "gpu": torch.cuda.get_device_name(0), "faiss_threads": 1,
        "sentence_transformers": importlib.metadata.version("sentence-transformers"),
        "transformers": importlib.metadata.version("transformers")})
    rankings = {}
    for key, config in MODEL_CONFIGS.items():
        print(f"Loading local model: {key}", flush=True)
        t0 = time.perf_counter()
        model = SentenceTransformer(str(config["path"]), local_files_only=True, device="cuda")
        model.max_seq_length = 512
        model.eval()
        torch.cuda.synchronize()
        load_seconds = time.perf_counter() - t0

        def encode(texts):
            values = model.encode(texts, normalize_embeddings=True, convert_to_numpy=True,
                                  batch_size=8, show_progress_bar=False)
            torch.cuda.synchronize()
            return np.asarray(values, dtype="float32")

        encode([config["passage_prefix"] + chunks[0].text])
        t0 = time.perf_counter()
        vectors = encode([config["passage_prefix"] + chunk.text for chunk in chunks])
        corpus_seconds = time.perf_counter() - t0
        query_vectors = {}
        encode_times = []
        per_question_encode = {}
        for q in answerable:
            timings = []
            for _ in range(3):
                started = time.perf_counter()
                query_vectors[q.question] = encode([config["query_prefix"] + q.question])
                timings.append((time.perf_counter() - started) * 1000)
            encode_times.extend(timings)
            per_question_encode[q.question_id] = timings
        index = faiss.IndexFlatIP(vectors.shape[1])
        started = time.perf_counter()
        index.add(vectors)
        build_ms = (time.perf_counter() - started) * 1000
        dense = StoredVectorRetriever(chunks, index, query_vectors)
        hybrid = ReciprocalRankFusionRetriever(bm25, dense, rank_constant=60, candidate_k=20)
        report["retrieval"][f"dense_{key}"] = metrics(dense)
        report["retrieval"][f"rrf_{key}"] = metrics(hybrid)
        for method, retriever in ((f"dense_{key}", dense), (f"rrf_{key}", hybrid)):
            rankings[method] = {q.question: retriever.query(q.question, top_k=20).hits for q in answerable}
        report["embedding_models"].append({
            "key": key, "model_id": config["model_id"], "revision": config["path"].name,
            "dimension": vectors.shape[1], "input_signature": input_signature(chunks),
            "max_seq_length": 512, "dtype": str(next(model.parameters()).dtype),
            "query_prefix": config["query_prefix"], "passage_prefix": config["passage_prefix"],
            "truncated_passages": 0, "load_seconds": load_seconds,
            "corpus_encode_seconds_after_one_warmup": corpus_seconds,
            "query_encode_latency": timing_summary(encode_times),
            "query_encode_latency_ms_by_question": per_question_encode,
            "latency_scope": "query encoding includes tokenizer, CPU/GPU transfer and synchronization; 3 repetitions per 7 queries"})
        if key == "bge-m3":
            expected_ids = {q.question: index.search(query_vectors[q.question], 10)[1][0].tolist() for q in answerable}
            indexes = [("FlatIP", index, build_ms, None)]
            for ef in (8, 32, 64):
                hnsw = faiss.IndexHNSWFlat(vectors.shape[1], 16, faiss.METRIC_INNER_PRODUCT)
                hnsw.hnsw.efConstruction = 40
                hnsw.hnsw.efSearch = ef
                started = time.perf_counter()
                hnsw.add(vectors)
                indexes.append((f"HNSW_M16_ef{ef}", hnsw, (time.perf_counter() - started) * 1000, ef))
            # Small corpus: four IVF lists, no production-scale claim.
            for nprobe in (1, 2, 4):
                ivf = faiss.IndexIVFFlat(faiss.IndexFlatIP(vectors.shape[1]), vectors.shape[1], 4, faiss.METRIC_INNER_PRODUCT)
                ivf.cp.seed = 22110068
                ivf.nprobe = nprobe
                started = time.perf_counter()
                ivf.train(vectors)
                ivf.add(vectors)
                indexes.append((f"IVF4_nprobe{nprobe}", ivf, (time.perf_counter() - started) * 1000, None))
            for name, tested, build, ef in indexes:
                adapter = StoredVectorRetriever(chunks, tested, query_vectors)
                for q in answerable:
                    adapter.query(q.question, 10)  # per-query warm-up
                latencies, overlaps, exact = [], [], []
                for q in answerable:
                    actual = tested.search(query_vectors[q.question], 10)[1][0].tolist()
                    expected = expected_ids[q.question]
                    overlaps.append(len(set(actual) & set(expected)) / 10)
                    exact.append(actual == expected)
                    for _ in range(50):
                        latencies.append(adapter.query(q.question, 10).latency_ms)
                report["vector_indexes"].append({
                    "name": name, "M": 16 if ef else None, "efConstruction": 40 if ef else None,
                    "efSearch": ef, "nlist": 4 if name.startswith("IVF") else None,
                    "nprobe": tested.nprobe if name.startswith("IVF") else None,
                    "build_ms": build, "serialized_index_bytes": int(faiss.serialize_index(tested).nbytes),
                    "mean_neighbor_recall_at_10_vs_flat": statistics.mean(overlaps),
                    "exact_order_match_at_10_vs_flat": statistics.mean(exact),
                    "search_latency": timing_summary(latencies), "retrieval_metrics": metrics(adapter),
                    "latency_scope": "CPU index.search only, precomputed normalized vectors, single thread, 50 repeats x 7 queries after one warmup"})
        save()
        del hybrid, dense, model, vectors, index
        gc.collect()
        torch.cuda.empty_cache()

    if args.reranker_model:
        from rag_hcmute.evaluation.reranker import LocalCrossEncoderReranker
        reranker = LocalCrossEncoderReranker(args.reranker_model, max_length=1024, batch_size=4)
        chunks_by_id = {c.chunk_id: c for c in chunks}
        # Explicit warmup before timing each fixed candidate pool.
        first = answerable[0]
        reranker.rerank(query=first.question, candidates=rankings["dense_bge-m3"][first.question], chunks_by_id=chunks_by_id)
        for method in ("dense_bge-m3", "rrf_bge-m3"):
            reranked, latencies, truncated = {}, [], 0
            for q in answerable:
                for repetition in range(2):
                    result = reranker.rerank(query=q.question, candidates=rankings[method][q.question], chunks_by_id=chunks_by_id)
                    latencies.append(result.latency_ms)
                    if repetition == 0:
                        reranked[q.question] = result.hits
                        truncated += result.truncated_pair_count
            report["reranking"][method] = {"before": report["retrieval"][method],
                "after": metrics(StoredRankingRetriever(reranked)),
                "candidate_count_per_query": 20, "max_length": 1024, "truncated_pairs_first_pass": truncated,
                "model_revision": args.reranker_model.name, "load_seconds": reranker.load_seconds,
                "latency": timing_summary(latencies), "latency_scope": "2 passes per 7 queries, same fixed top20, after one warmup; tokenization/truncation audit included"}
            save()
    left = report["retrieval"]["dense_bge-m3"]["character_coverage"]["per_question"]
    right = report["retrieval"]["dense_multilingual-e5-small"]["character_coverage"]["per_question"]
    assert [r["question_id"] for r in left] == [r["question_id"] for r in right]
    report["paired_comparison_e5_minus_bge"] = {
        key: paired_bootstrap([r[key] for r in left], [r[key] for r in right])
        for key in ("character_recall_at_5", "mrr_at_10_threshold_05")}
    report["completed"] = True
    save()
    for key, result in report["retrieval"].items():
        print(f"{key}: span Recall@5={result['evidence_span_recall_at_5']}", flush=True)
    print(f"Completed content-free metrics: {output}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
