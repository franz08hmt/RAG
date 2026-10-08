from __future__ import annotations

import csv
import hashlib
import json
import statistics
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

print(f"Python executable: {sys.executable}", flush=True)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import faiss  # noqa: E402
import numpy as np  # noqa: E402
from qdrant_client import QdrantClient, models  # noqa: E402
from sentence_transformers import SentenceTransformer  # noqa: E402

from rag_hcmute.evaluation.evidence_spans import (  # noqa: E402
    evaluate_exact_evidence_retrieval,
    load_exact_evidence_spans,
)
from rag_hcmute.evaluation.run_pilot import load_pilot_questions  # noqa: E402
from rag_hcmute.ingestion.chunk import chunk_document  # noqa: E402
from rag_hcmute.ingestion.clean import clean_document_pages  # noqa: E402
from rag_hcmute.ingestion.extract import read_pages_jsonl  # noqa: E402
from rag_hcmute.retrieval.common import hit_from_chunk, load_chunks  # noqa: E402

SNAPSHOT_ID = "5da3bd4d5de54492"
BGE_PATH = Path(r"D:\RAG\models\huggingface\hub\models--BAAI--bge-m3\snapshots\5617a9f61b028005a4858fdac845db406aefb181")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_validated_corpus():
    source_root = PROJECT_ROOT / "data/processed/g0_reproduction"
    snapshot = json.loads((source_root / "snapshot.json").read_text(encoding="utf-8"))
    if snapshot.get("snapshot_id") != SNAPSHOT_ID:
        raise SystemExit("Vector-store comparison is pinned to native-only G0.")
    if snapshot.get("config", {}).get("ocr", {}).get("enabled", False):
        raise SystemExit("Expected the native-only G0 snapshot.")
    with (PROJECT_ROOT / "data/manifests/corpus_manifest.csv").open("r", encoding="utf-8-sig", newline="") as stream:
        manifest = list(csv.DictReader(stream))
    for row in manifest:
        source = (PROJECT_ROOT / row["local_path"]).resolve()
        if not source.is_file() or sha256_file(source) != row["file_sha256"].strip().lower():
            raise SystemExit(f"Missing source or SHA-256 mismatch for {row['document_id']}.")

    stored = load_chunks(source_root / "chunks/chunks.jsonl")
    pages = {}
    chunks = []
    for document in snapshot["documents"]:
        doc_id = document["document_id"]
        pages[doc_id], _ = clean_document_pages(read_pages_jsonl(source_root / f"pages/{doc_id}.jsonl"))
        chunks.extend(chunk_document(pages[doc_id], doc_id, document["document_title"]))
    signature = lambda items: [
        (c.chunk_id, c.text_sha256, c.token_count, c.section_path, c.chunk_method, c.pdf_page_start, c.pdf_page_end)
        for c in items
    ]
    if signature(stored) != signature(chunks):
        raise SystemExit("Rebuilt chunks do not match the G0 snapshot signature.")
    return snapshot, chunks, pages


class StoreRetriever:
    def __init__(self, chunks, vectors, queries, store_name, query_fn):
        self.chunks = chunks
        self.vectors = vectors
        self.queries = queries
        self.store_name = store_name
        self.query_fn = query_fn

    def query(self, query_text: str, top_k: int = 10):
        vector = self.queries[query_text]
        start = time.perf_counter()
        rows = self.query_fn(vector, top_k)
        latency_ms = (time.perf_counter() - start) * 1000
        hits = [hit_from_chunk(rank, self.chunks[idx], score) for rank, (idx, score) in enumerate(rows, start=1)]
        return type("QueryResult", (), {"hits": hits, "latency_ms": latency_ms})()


def percentile(values, percent):
    if not values:
        return 0.0
    ordered = sorted(values)
    return round(ordered[min(len(ordered) - 1, int((percent / 100) * (len(ordered) - 1)))], 3)


def main() -> int:
    snapshot, chunks, pages = load_validated_corpus()
    questions = load_pilot_questions(
        PROJECT_ROOT / "data/question_sets/pilot_questions.csv",
        partition="development",
        partition_manifest_path=PROJECT_ROOT / "data/question_sets/question_partition_manifest.csv",
        snapshot_path=PROJECT_ROOT / "data/manifests/corpus_snapshot.json",
        project_root=PROJECT_ROOT,
    )
    spans, annotation_meta = load_exact_evidence_spans(
        questions_path=PROJECT_ROOT / "data/question_sets/pilot_questions.csv",
        annotations_path=PROJECT_ROOT / "data/question_sets/pilot_evidence_annotations.json",
        pages_by_document=pages,
        snapshot_id=snapshot["snapshot_id"],
        question_ids={q.question_id for q in questions},
    )
    model = SentenceTransformer(str(BGE_PATH), local_files_only=True)
    model.max_seq_length = 1024
    vectors = np.asarray(
        model.encode([chunk.text for chunk in chunks], normalize_embeddings=True, convert_to_numpy=True, show_progress_bar=False, batch_size=8),
        dtype="float32",
    )
    query_vectors = np.asarray(
        model.encode([q.question for q in questions], normalize_embeddings=True, convert_to_numpy=True, show_progress_bar=False, batch_size=8),
        dtype="float32",
    )
    query_map = {q.question: query_vectors[i] for i, q in enumerate(questions)}

    results = []
    with tempfile.TemporaryDirectory(prefix="rag-qdrant-vector-bench-") as temp_dir:
        # FAISS baseline: exact inner-product search over the same normalized FP32 vectors.
        t0 = time.perf_counter()
        faiss_index = faiss.IndexFlatIP(vectors.shape[1])
        faiss_index.add(vectors)
        faiss_build_ms = (time.perf_counter() - t0) * 1000
        faiss_file = Path(temp_dir) / "faiss.index"
        faiss.write_index(faiss_index, str(faiss_file))

        def faiss_query(vector, top_k):
            scores, ids = faiss_index.search(np.asarray(vector, dtype="float32").reshape(1, -1), top_k)
            return [(int(i), float(s)) for i, s in zip(ids[0], scores[0]) if i >= 0]

        faiss_adapter = StoreRetriever(chunks, vectors, query_map, "faiss", faiss_query)
        metrics = evaluate_exact_evidence_retrieval(
            questions=questions, spans_by_question=spans, chunks=chunks, retriever=faiss_adapter, top_k=10, hit_k=5
        )
        faiss_latencies = []
        for question in questions:
            for _ in range(50):
                result = faiss_adapter.query(question.question, 10)
                faiss_latencies.append(result.latency_ms)
        results.append({
            "store": "FAISS IndexFlatIP (in-memory exact)",
            "build_ms": round(faiss_build_ms, 3),
            "artifact_bytes": faiss_file.stat().st_size,
            "query_p50_ms": percentile(faiss_latencies, 50),
            "query_p95_ms": percentile(faiss_latencies, 95),
            "exact_top10_match_rate_vs_faiss": 1.0,
            "metrics": {
                "evidence_span_recall_at_5": metrics["evidence_span_recall_at_k"],
                "complete_evidence_hit_at_5": metrics["complete_evidence_hit_at_k"],
                "first_evidence_mrr_at_10": metrics["first_evidence_mrr_at_top_k"],
            },
        })

        # Qdrant local persistent mode; payload contains IDs/provenance only, never source text.
        qdrant_path = Path(temp_dir) / "qdrant"
        client = QdrantClient(path=str(qdrant_path))
        t0 = time.perf_counter()
        client.create_collection(
            collection_name="hcmute_g0",
            vectors_config=models.VectorParams(size=vectors.shape[1], distance=models.Distance.DOT),
        )
        client.upsert(
            collection_name="hcmute_g0",
            points=[
                models.PointStruct(
                    id=i,
                    vector=vectors[i].tolist(),
                    payload={
                        "chunk_id": chunk.chunk_id,
                        "document_id": chunk.document_id,
                        "pdf_page_start": chunk.pdf_page_start,
                        "pdf_page_end": chunk.pdf_page_end,
                        "section_path": chunk.section_path or "",
                    },
                )
                for i, chunk in enumerate(chunks)
            ],
            wait=True,
        )
        qdrant_build_ms = (time.perf_counter() - t0) * 1000
        id_to_index = {chunk.chunk_id: i for i, chunk in enumerate(chunks)}

        def qdrant_query(vector, top_k):
            response = client.query_points(
                collection_name="hcmute_g0",
                query=np.asarray(vector, dtype="float32").tolist(),
                limit=top_k,
                with_payload=True,
                search_params=models.SearchParams(exact=True),
            )
            return [(id_to_index[p.payload["chunk_id"]], float(p.score)) for p in response.points]

        qdrant_adapter = StoreRetriever(chunks, vectors, query_map, "qdrant", qdrant_query)
        qdrant_metrics = evaluate_exact_evidence_retrieval(
            questions=questions, spans_by_question=spans, chunks=chunks, retriever=qdrant_adapter, top_k=10, hit_k=5
        )
        qdrant_latencies = []
        top10_matches = 0
        comparisons = 0
        for question in questions:
            expected = [idx for idx, _ in faiss_query(query_map[question.question], 10)]
            actual = [idx for idx, _ in qdrant_query(query_map[question.question], 10)]
            comparisons += 1
            top10_matches += int(actual == expected)
            for _ in range(50):
                qdrant_latencies.append(qdrant_adapter.query(question.question, 10).latency_ms)
        client.close()
        qdrant_bytes = sum(path.stat().st_size for path in qdrant_path.rglob("*") if path.is_file())
        results.append({
            "store": "Qdrant local persistent, exact search",
            "client_version": __import__("importlib.metadata", fromlist=["version"]).version("qdrant-client"),
            "build_ms": round(qdrant_build_ms, 3),
            "artifact_bytes": qdrant_bytes,
            "query_p50_ms": percentile(qdrant_latencies, 50),
            "query_p95_ms": percentile(qdrant_latencies, 95),
            "exact_top10_match_rate_vs_faiss": round(top10_matches / comparisons, 3),
            "metrics": {
                "evidence_span_recall_at_5": qdrant_metrics["evidence_span_recall_at_k"],
                "complete_evidence_hit_at_5": qdrant_metrics["complete_evidence_hit_at_k"],
                "first_evidence_mrr_at_10": qdrant_metrics["first_evidence_mrr_at_top_k"],
            },
        })

    output = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "snapshot_id": snapshot["snapshot_id"],
        "partition": "development",
        "question_count": len(questions),
        "answerable_count": len(spans),
        "gold_span_count": annotation_meta["evidence_span_count"],
        "chunk_count": len(chunks),
        "embedding_model": "BAAI/bge-m3",
        "embedding_revision": BGE_PATH.name,
        "dimension": int(vectors.shape[1]),
        "search": "exact dot product over the same L2-normalized FP32 query/chunk vectors; top-10, exact-span metrics at top-5",
        "latency_protocol": "50 repetitions per 7 development queries; embedding time excluded; CPU vector-store search only",
        "stores": results,
        "limitations": [
            "156 vectors is too few for a production-scale throughput claim; local timings are microbenchmarks.",
            "FAISS is an in-memory library index while Qdrant local persists metadata and vector data to disk; artifact sizes are not like-for-like database storage accounting.",
            "Development pilot only; no independent holdout. Query set is not a statistical sample of production traffic.",
        ],
    }
    outdir = PROJECT_ROOT / "artifacts/results/vector_store_ablation"
    outdir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    outpath = outdir / f"vector_store_{snapshot['snapshot_id']}_{stamp}.json"
    outpath.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(output, ensure_ascii=False, indent=2))
    print(f"Metrics-only output: {outpath}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
