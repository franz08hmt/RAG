"""Check exact metadata filtering and persistence on the validated G0 vectors."""
import argparse
import hashlib
import json
import statistics
import sys
import tempfile
import time
from importlib.metadata import version
from pathlib import Path

import faiss
import numpy as np
from qdrant_client import QdrantClient, models

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]
from scripts.run_embedding_model_ablation import MODEL_CONFIGS, validate_corpus
from rag_hcmute.retrieval.dense_index import _load_cached_embeddings, embedding_cache_key


def main():
    print(f"Python executable: {sys.executable}", flush=True)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metrics", required=True, type=Path)
    args = parser.parse_args()
    snapshot, chunks, _ = validate_corpus()
    model_path = MODEL_CONFIGS["bge-m3"]["path"]
    key = embedding_cache_key(chunks, model_path)
    vectors = _load_cached_embeddings(ROOT / f"artifacts/indexes/dense_console/{key}.npz",
                                      key=key, count=len(chunks))
    if vectors is None:
        raise ValueError("Run the validated dense pipeline to produce the G0 vector cache first.")
    doc_ids = list(dict.fromkeys(chunk.document_id for chunk in chunks))
    global_index = faiss.IndexFlatIP(vectors.shape[1])
    global_index.add(vectors)
    query_indices = np.linspace(0, len(chunks) - 1, 9, dtype=int)
    rows = []
    with tempfile.TemporaryDirectory(prefix="rag-final-vector-") as directory:
        temp = Path(directory)
        faiss_path = temp / "g0.faiss"
        qdrant_path = temp / "qdrant"
        faiss.write_index(global_index, str(faiss_path))
        assert faiss.read_index(str(faiss_path)).ntotal == len(chunks)
        client = QdrantClient(path=str(qdrant_path))
        client.create_collection("g0", vectors_config=models.VectorParams(size=vectors.shape[1],
                                                                          distance=models.Distance.DOT))
        client.upsert("g0", points=[models.PointStruct(id=i, vector=row.tolist(),
                         payload={"document_id": chunks[i].document_id}) for i, row in enumerate(vectors)], wait=True)
        client.close()
        client = QdrantClient(path=str(qdrant_path))
        try:
            for doc_id in doc_ids:
                eligible = [i for i, c in enumerate(chunks) if c.document_id == doc_id]
                flat = faiss.IndexFlatIP(vectors.shape[1])
                flat.add(vectors[eligible])
                filter_doc = models.Filter(must=[models.FieldCondition(key="document_id",
                                           match=models.MatchValue(value=doc_id))])
                for query_id in query_indices:
                    query = vectors[query_id:query_id+1]
                    count = min(5, len(eligible))
                    t0 = time.perf_counter()
                    _, ids = flat.search(query, count)
                    subset_ms = (time.perf_counter() - t0) * 1000
                    exact = [eligible[int(i)] for i in ids[0]]
                    t0 = time.perf_counter()
                    points = client.query_points("g0", query=query[0].tolist(), query_filter=filter_doc,
                                                 search_params=models.SearchParams(exact=True),
                                                 limit=5, with_payload=True).points
                    filtered_ms = (time.perf_counter() - t0) * 1000
                    _, ids = global_index.search(query, 5)
                    postfiltered = set(ids[0]).intersection(eligible)
                    if any(p.payload.get("document_id") != doc_id for p in points):
                        raise ValueError("Result violates metadata filter.")
                    rows.append({"document_id": doc_id, "query_chunk_id": chunks[query_id].chunk_id,
                                 "eligible_vectors": len(eligible), "expected_count": count,
                                 "qdrant_exact_ids_match": set(exact) == {p.id for p in points},
                                 "postfilter_count": len(postfiltered),
                                 "faiss_subset_query_ms": subset_ms, "qdrant_local_query_ms": filtered_ms})
        finally:
            client.close()
        sizes = {"faiss_global_vectors_only": faiss_path.stat().st_size,
                 "qdrant_with_metadata": sum(p.stat().st_size for p in qdrant_path.rglob("*") if p.is_file())}
    result = {"snapshot_id": snapshot["snapshot_id"], "vectors": len(chunks), "dimension": vectors.shape[1],
              "bge_revision": model_path.name, "vector_sha256": hashlib.sha256(vectors.tobytes()).hexdigest(),
              "runner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "faiss_version": faiss.__version__, "qdrant_client_version": version("qdrant-client"),
              "sizes_bytes": sizes, "queries": len(rows),
              "same_exact_ids": sum(row["qdrant_exact_ids_match"] for row in rows),
              "postfilter_short_cases": sum(row["postfilter_count"] < row["expected_count"] for row in rows),
              "faiss_subset_p50_ms": statistics.median(row["faiss_subset_query_ms"] for row in rows),
              "qdrant_local_p50_ms": statistics.median(row["qdrant_local_query_ms"] for row in rows), "rows": rows}
    with args.metrics.open("x", encoding="utf-8") as output:
        json.dump(result, output, indent=2)
    print({k: v for k, v in result.items() if k != "rows"})


if __name__ == "__main__":
    main()

