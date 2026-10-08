from __future__ import annotations

import csv
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

print(f"Python executable: {sys.executable}", flush=True)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import faiss  # noqa: E402
import numpy as np  # noqa: E402
from sentence_transformers import SentenceTransformer  # noqa: E402

from rag_hcmute.evaluation.evidence_spans import (  # noqa: E402
    evaluate_exact_evidence_retrieval,
    load_exact_evidence_spans,
)
from rag_hcmute.evaluation.run_pilot import load_pilot_questions  # noqa: E402
from rag_hcmute.ingestion.chunk import chunk_document  # noqa: E402
from rag_hcmute.ingestion.clean import clean_document_pages  # noqa: E402
from rag_hcmute.ingestion.extract import read_pages_jsonl  # noqa: E402
from rag_hcmute.retrieval.common import RetrievalHit, hit_from_chunk, load_chunks  # noqa: E402

SNAPSHOT_ID = "5da3bd4d5de54492"
MODEL_CONFIGS = {
    "bge-m3": {
        "model_id": "BAAI/bge-m3",
        "path": Path(r"D:\RAG\models\huggingface\hub\models--BAAI--bge-m3\snapshots\5617a9f61b028005a4858fdac845db406aefb181"),
        "max_seq_length": 1024,
        "query_prefix": "",
        "passage_prefix": "",
    },
    "multilingual-e5-small": {
        "model_id": "intfloat/multilingual-e5-small",
        "path": Path.home() / ".cache/huggingface/hub/models--intfloat--multilingual-e5-small/snapshots/614241f622f53c4eeff9890bdc4f31cfecc418b3",
        "max_seq_length": 512,
        "query_prefix": "query: ",
        "passage_prefix": "passage: ",
    },
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate_corpus() -> tuple[dict, list, dict]:
    source_root = PROJECT_ROOT / "data/processed/g0_reproduction"
    snapshot = json.loads((source_root / "snapshot.json").read_text(encoding="utf-8"))
    if snapshot.get("snapshot_id") != SNAPSHOT_ID:
        raise SystemExit("Embedding comparison is pinned to native-only G0.")
    if snapshot.get("config", {}).get("ocr", {}).get("enabled", False):
        raise SystemExit("Expected the native-only G0 snapshot.")

    manifest_path = PROJECT_ROOT / "data/manifests/corpus_manifest.csv"
    with manifest_path.open("r", encoding="utf-8-sig", newline="") as stream:
        manifest = list(csv.DictReader(stream))
    for row in manifest:
        source = (PROJECT_ROOT / row["local_path"]).resolve()
        if not source.is_file() or sha256_file(source) != row["file_sha256"].strip().lower():
            raise SystemExit(f"Missing source or SHA-256 mismatch for {row['document_id']}.")

    stored = load_chunks(source_root / "chunks/chunks.jsonl")
    pages_by_document = {}
    chunks = []
    for document in snapshot["documents"]:
        document_id = document["document_id"]
        pages_by_document[document_id], _ = clean_document_pages(
            read_pages_jsonl(source_root / f"pages/{document_id}.jsonl")
        )
        chunks.extend(
            chunk_document(
                pages_by_document[document_id],
                document_id,
                document["document_title"],
            )
        )
    signature = lambda items: [
        (c.chunk_id, c.text_sha256, c.token_count, c.section_path, c.chunk_method,
         c.pdf_page_start, c.pdf_page_end)
        for c in items
    ]
    if signature(stored) != signature(chunks):
        raise SystemExit("Rebuilt chunks do not match the G0 snapshot signature.")
    return snapshot, chunks, pages_by_document


class DenseIndex:
    def __init__(self, model, chunks, model_config):
        self.model = model
        self.chunks = chunks
        self.model_config = model_config
        passages = [model_config["passage_prefix"] + chunk.text for chunk in chunks]
        self.vectors = self._encode(passages)
        self.index = faiss.IndexFlatIP(self.vectors.shape[1])
        self.index.add(self.vectors)

    def _encode(self, texts):
        vectors = self.model.encode(
            texts,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
            batch_size=8,
        )
        return np.asarray(vectors, dtype="float32")

    def query_vector(self, question: str):
        return self._encode([self.model_config["query_prefix"] + question])

    def query(self, question: str, top_k: int = 10):
        vector = self.query_vector(question)
        scores, indices = self.index.search(vector, top_k)
        hits = [
            hit_from_chunk(rank, self.chunks[index], float(score))
            for rank, (index, score) in enumerate(zip(indices[0], scores[0]), start=1)
            if index >= 0
        ]
        return type("QueryResult", (), {"hits": hits, "latency_ms": 0.0})()


def main() -> int:
    snapshot, chunks, pages = validate_corpus()
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

    output = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "snapshot_id": snapshot["snapshot_id"],
        "partition": "development",
        "question_count": len(questions),
        "answerable_count": len(spans),
        "gold_span_count": annotation_meta["evidence_span_count"],
        "chunk_count": len(chunks),
        "metrics_scope": "exact source evidence, retrieval only; not a holdout",
        "models": [],
    }

    for key, config in MODEL_CONFIGS.items():
        if not config["path"].is_dir():
            raise SystemExit(f"Local model snapshot missing: {config['path']}")
        model = SentenceTransformer(str(config["path"]), local_files_only=True)
        model.max_seq_length = config["max_seq_length"]
        start = time.perf_counter()
        dense = DenseIndex(model, chunks, config)
        corpus_encode_seconds = time.perf_counter() - start

        tok = model.tokenizer
        passage_lengths = [
            len(tok(config["passage_prefix"] + c.text, add_special_tokens=True, truncation=False)["input_ids"])
            for c in chunks
        ]
        question_lengths = [
            len(tok(config["query_prefix"] + q.question, add_special_tokens=True, truncation=False)["input_ids"])
            for q in questions
        ]
        retrieval = evaluate_exact_evidence_retrieval(
            questions=questions,
            spans_by_question=spans,
            chunks=chunks,
            retriever=dense,
            top_k=10,
            hit_k=5,
        )
        output["models"].append(
            {
                "key": key,
                "model_id": config["model_id"],
                "revision": config["path"].name,
                "embedding_dim": dense.vectors.shape[1],
                "max_seq_length": config["max_seq_length"],
                "query_prefix": bool(config["query_prefix"]),
                "passage_prefix": bool(config["passage_prefix"]),
                "device": str(model.device),
                "corpus_encode_seconds": round(corpus_encode_seconds, 3),
                "chunks_over_limit": sum(n > config["max_seq_length"] for n in passage_lengths),
                "passage_token_min_median_max": [
                    min(passage_lengths), sorted(passage_lengths)[len(passage_lengths) // 2], max(passage_lengths)
                ],
                "questions_over_limit": sum(n > config["max_seq_length"] for n in question_lengths),
                "metrics": {
                    "evidence_span_recall_at_5": retrieval["evidence_span_recall_at_k"],
                    "complete_evidence_hit_at_5": retrieval["complete_evidence_hit_at_k"],
                    "first_evidence_mrr_at_10": retrieval["first_evidence_mrr_at_top_k"],
                },
                "per_question_span_ranks": [
                    {"question_id": row["question_id"], "span_ranks": row["span_ranks"]}
                    for row in retrieval["per_question"]
                ],
            }
        )
        del dense, model

    outdir = PROJECT_ROOT / "artifacts/results/embedding_model_ablation"
    outdir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    outpath = outdir / f"embedding_{snapshot['snapshot_id']}_{stamp}.json"
    outpath.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(output, ensure_ascii=False, indent=2))
    print(f"Metrics-only output: {outpath}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
