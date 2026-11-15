"""Evaluate predeclared configurations on local, source-anchored draft questions.

The draft labels are not student gold. Questions, excerpts, and answers stay
outside Git. The metrics export contains only identifiers and numerical results.
"""
from __future__ import annotations

import argparse
import csv
import gc
import hashlib
import json
import statistics
import subprocess
import sys
from collections import Counter
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]

from scripts.run_embedding_model_ablation import MODEL_CONFIGS, validate_corpus
from scripts.run_m2_controlled_evaluation import StoredRankingRetriever
from scripts.run_m3_ranking_study import fuse
from rag_hcmute.evaluation.evidence_spans import EvidenceSpan, locate_excerpt_on_page
from rag_hcmute.evaluation.interval_metrics import character_metrics
from rag_hcmute.evaluation.reranker import LocalCrossEncoderReranker
from rag_hcmute.generation.ollama import generate_grounded_answer, sources_from_hits
from rag_hcmute.ingestion.chunk import chunk_document
from rag_hcmute.retrieval.bm25_index import BM25Retriever
from rag_hcmute.retrieval.dense_index import DenseRetriever

DOCUMENT_ID = "HCMUTE_QCDT_1727_2021"
GENERATION_IDS = ("F07", "F13", "F21", "F29", "F35", "F39",
                  "U01", "U04", "U08", "U11", "U13", "U15")
RERANKER_PATH = Path("D:/RAG/models/huggingface/hub/models--BAAI--bge-reranker-v2-m3/"
                     "snapshots/953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def write_json(path, data):
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(path)


def load_cases(case_path, pages):
    raw_path = ROOT / f"data/processed/g0_reproduction/pages/{DOCUMENT_ID}.jsonl"
    raw_pages = {row["pdf_page"]: row["text"].splitlines() for row in
                 map(json.loads, raw_path.read_text(encoding="utf-8").splitlines())}
    clean = {page.pdf_page: page.text for page in pages[DOCUMENT_ID]}
    offsets, cursor = {}, 0
    for number, content in sorted(clean.items()):
        offsets[number] = cursor
        cursor += len(content.split())
    with case_path.open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream, delimiter="\t"))
    by_id, spans = {}, {}
    questions_seen = set()
    for row in rows:
        qid = row["id"]
        if qid in by_id or row["question"].casefold() in questions_seen:
            raise ValueError(f"Duplicate draft question: {qid}")
        questions_seen.add(row["question"].casefold())
        by_id[qid] = row
        row["evidence"] = []
        if row["spans"] == "-":
            continue
        spans[qid] = []
        for index, locator in enumerate(row["spans"].split(";"), 1):
            number, first, last = map(int, locator.split(":"))
            if not 0 <= first <= last < len(raw_pages[number]):
                raise ValueError(f"Out-of-bounds line range: {qid} {locator}")
            quote = " ".join(" ".join(raw_pages[number][first:last+1]).split())
            matches = locate_excerpt_on_page(clean[number], quote)
            if len(matches) != 1:
                raise ValueError(f"Evidence is absent or ambiguous: {qid} {locator}, n={len(matches)}")
            start, end = matches[0]
            base = offsets[number]
            spans[qid].append(EvidenceSpan(qid, f"{qid}-{index}", DOCUMENT_ID, number,
                                           base + start, base + end, sha(quote.encode("utf-8"))))
            row["evidence"].append({"document_id": DOCUMENT_ID, "pdf_page": number, "quote": quote})
    return by_id, spans


def main():
    print(f"Python executable: {sys.executable}", flush=True)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, required=True)
    parser.add_argument("--private-dir", type=Path, required=True)
    parser.add_argument("--metrics", type=Path, required=True)
    args = parser.parse_args()
    import torch
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is required for the configured BGE comparison.")
    if args.metrics.exists():
        raise FileExistsError(args.metrics)
    snapshot, chunks, pages = validate_corpus()
    cases, spans = load_cases(args.cases, pages)
    if not all(qid in cases for qid in GENERATION_IDS):
        raise ValueError("Missing predeclared generation case.")
    args.private_dir.mkdir(parents=True, exist_ok=False)
    args.metrics.parent.mkdir(parents=True, exist_ok=True)
    questions = [SimpleNamespace(question_id=qid, question=cases[qid]["question"]) for qid in spans]
    config = {"run_id": datetime.now(timezone.utc).strftime("extended_%Y%m%dT%H%M%SZ"),
              "data_status": "ai_authored_source_anchored_not_student_verified",
              "snapshot_id": snapshot["snapshot_id"], "draft_sha256": sha(args.cases.read_bytes()),
              "revision_before_run": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
              "runner_sha256": sha(Path(__file__).read_bytes()),
              "answerable_count": len(spans), "unanswerable_count": len(cases) - len(spans),
              "source_span_count": sum(map(len, spans.values())),
              "tag_counts": dict(Counter(tag for row in cases.values() for tag in row["tags"].split("|") if tag)),
              "embedding_revision": MODEL_CONFIGS["bge-m3"]["path"].name,
              "reranker_revision": RERANKER_PATH.name, "branch_depth": 50, "dense_weight": .75,
              "reranker_depth": 20, "reranker_max_tokens": 512, "generation_ids": GENERATION_IDS,
              "generation_configurations": ["BM25", "Weighted75+rerank"],
              "generation_model": "qwen3:4b", "generation_prompt": "scope_check",
              "generation_context_chunks": 5, "generation_max_output_tokens": 384,
              "generation_temperature": 0, "generation_think": False}
    write_json(args.private_dir / "locked_protocol.json", config)
    write_json(args.private_dir / "draft_questions.json", cases)
    report = {"config": config, "retrieval": {}, "chunk_sensitivity": {}, "generation": [], "completed": False}
    write_json(args.metrics, report)
    print(f"Locked {len(cases)} cases and {config['source_span_count']} anchored intervals", flush=True)
    lookup = {chunk.chunk_id: chunk for chunk in chunks}
    bm = BM25Retriever(chunks)
    lexical = {row["question"]: bm.query(row["question"], top_k=50).hits for row in cases.values()}
    dense = DenseRetriever(chunks, str(MODEL_CONFIGS["bge-m3"]["path"]), batch_size=4,
                           cache_dir=ROOT / "artifacts/indexes/dense_console")
    semantic = {row["question"]: dense.query(row["question"], top_k=50).hits for row in cases.values()}
    del dense
    gc.collect()
    torch.cuda.empty_cache()
    fused = {question: fuse(lexical[question], semantic[question], .75) for question in lexical}
    reranker = LocalCrossEncoderReranker(RERANKER_PATH, max_length=512, batch_size=4)
    reranked, rerank_ms, truncated = {}, [], 0
    ranking_questions = dict.fromkeys([q.question for q in questions] +
                                      [cases[qid]["question"] for qid in GENERATION_IDS])
    for index, question in enumerate(ranking_questions, 1):
        result = reranker.rerank(query=question, candidates=fused[question][:20], chunks_by_id=lookup)
        reranked[question] = result.hits
        rerank_ms.append(result.latency_ms)
        truncated += result.truncated_pair_count
        if index % 10 == 0:
            print(f"Reranked {index}/{len(ranking_questions)}", flush=True)
    del reranker
    gc.collect()
    torch.cuda.empty_cache()
    report["reranker_runtime"] = {"queries": len(ranking_questions), "median_ms": statistics.median(rerank_ms),
                                  "truncated_pairs": truncated,
                                  "pair_count": sum(min(20, len(fused[q])) for q in ranking_questions)}
    modes = {"BM25": lexical, "Dense BGE": semantic, "Weighted75": fused, "Weighted75+rerank": reranked}

    def measure(passages, rankings):
        metric = character_metrics(questions=questions, spans_by_question=spans, chunks=passages,
                                   pages_by_document=pages, retriever=StoredRankingRetriever(rankings))
        for tag in ("requires_table_or_image", "multi_span", "lexical_gap"):
            selected = [row for row in metric["per_question"] if tag in cases[row["question_id"]]["tags"].split("|")]
            if selected:
                metric.setdefault("strata", {})[tag] = {
                    "n": len(selected), "character_recall_at_5":
                        statistics.mean(row["character_recall_at_5"] for row in selected)}
        return metric

    report["retrieval"] = {name: measure(chunks, ranks) for name, ranks in modes.items()}
    for length, overlap in ((250, 0), (250, 40), (500, 0), (500, 80), (750, 120)):
        passages = [chunk for doc in snapshot["documents"]
                    for chunk in chunk_document(pages[doc["document_id"]], doc["document_id"],
                                                doc["document_title"], length, overlap,
                                                force_sliding_window=True)]
        index = BM25Retriever(passages)
        result = measure(passages, {q.question: index.query(q.question, top_k=10).hits for q in questions})
        report["chunk_sensitivity"][f"{length}/{overlap}"] = {"chunks": len(passages), "macro": result["macro"]}
    write_json(args.metrics, report)
    print("Retrieval and chunk sensitivity saved.", flush=True)
    with urlopen("http://127.0.0.1:11434/api/tags", timeout=10) as response:
        tags = json.load(response)
    report["ollama_model_digest"] = next(row["digest"] for row in tags["models"] if row["name"] == "qwen3:4b")
    for qid in GENERATION_IDS:
        case = cases[qid]
        for name in ("BM25", "Weighted75+rerank"):
            print(f"Generation {qid} {name}", flush=True)
            sources = sources_from_hits(modes[name][case["question"]][:5], lookup)
            row = {"question_id": qid, "configuration": name, "answerable": qid in spans,
                   "context_chunk_ids": [source.chunk_id for source in sources]}
            payload = {"case": case, "sources": [asdict(source) for source in sources]}
            try:
                result = generate_grounded_answer(case["question"], sources, prompt_variant="scope_check",
                                                  timeout_seconds=180, max_output_tokens=384)
                row.update(status=result.status, generation_ms=result.latency_ms,
                           cited_chunk_ids=[source.chunk_id for source in result.citations])
                payload["result"] = asdict(result)
            except RuntimeError as exc:
                row["status"] = "transport_error"
                payload["error"] = str(exc)
            write_json(args.private_dir / f"{qid}_{'bm25' if name == 'BM25' else 'rerank'}.json", payload)
            report["generation"].append(row)
            write_json(args.metrics, report)
    report["completed"] = True
    write_json(args.metrics, report)


if __name__ == "__main__":
    main()
