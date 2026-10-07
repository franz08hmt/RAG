from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from rag_hcmute.evaluation.evidence_spans import load_exact_evidence_spans  # noqa: E402
from rag_hcmute.evaluation.chunking_ablation import (  # noqa: E402
    GoldLocation,
    chunk_profile,
    evaluate_location_retrieval,
)
from rag_hcmute.evaluation.run_pilot import PilotQuestion, load_pilot_questions  # noqa: E402
from rag_hcmute.ingestion.chunk import chunk_document  # noqa: E402
from rag_hcmute.ingestion.clean import clean_document_pages  # noqa: E402
from rag_hcmute.ingestion.extract import read_pages_jsonl  # noqa: E402
from rag_hcmute.ingestion.sectioning import find_section_markers, is_document_structured  # noqa: E402
from rag_hcmute.retrieval.bm25_index import BM25Retriever  # noqa: E402
from rag_hcmute.retrieval.common import load_chunks  # noqa: E402

CHUNK_TOKENS = 500
OVERLAP_TOKENS = 80
TOP_K = 10
HIT_K = 5
EXPECTED_SNAPSHOT_ID = "5da3bd4d5de54492"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _git_revision() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=PROJECT_ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unavailable"


def _load_manifest() -> tuple[dict[str, dict[str, str]], str]:
    path = PROJECT_ROOT / "data/manifests/corpus_manifest.csv"
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    for row in rows:
        source_path = (PROJECT_ROOT / row["local_path"]).resolve()
        if not source_path.is_file() or _sha256(source_path) != row["file_sha256"].strip().lower():
            raise SystemExit("A corpus source is missing or its SHA-256 differs from the manifest.")
    return {row["document_id"]: row for row in rows}, _sha256(path)


def _chunk_signature(chunks) -> list[tuple]:
    return [
        (
            chunk.chunk_id,
            chunk.text_sha256,
            chunk.token_count,
            chunk.section_path,
            chunk.chunk_method,
            chunk.pdf_page_start,
            chunk.pdf_page_end,
        )
        for chunk in chunks
    ]


def _baseline_difference_summary(baseline_chunks: list, generated_chunks: list) -> str:
    fields = (
        "chunk_id",
        "text_sha256",
        "token_count",
        "section_path",
        "chunk_method",
        "pdf_page_start",
        "pdf_page_end",
    )
    baseline = _chunk_signature(baseline_chunks)
    generated = _chunk_signature(generated_chunks)
    mismatch_fields = {
        field
        for expected_row, actual_row in zip(baseline, generated)
        for field, expected, actual in zip(fields, expected_row, actual_row)
        if expected != actual
    }
    if len(baseline) != len(generated):
        mismatch_fields.add("chunk_count_or_order")
    return f"baseline_chunks={len(baseline)}, regenerated_chunks={len(generated)}, differing_fields={sorted(mismatch_fields)}"


def _build_variant(*, snapshot: dict, pages_by_document: dict, force_structured_windows: bool):
    chunks = []
    structured_documents = []
    for document in snapshot["documents"]:
        document_id = document["document_id"]
        pages = pages_by_document[document_id]
        markers = find_section_markers(pages, lambda text: text.split())
        structured = is_document_structured(markers)
        if structured:
            structured_documents.append(document_id)
        chunks.extend(
            chunk_document(
                pages,
                document_id,
                document["document_title"],
                chunk_tokens=CHUNK_TOKENS,
                overlap_tokens=OVERLAP_TOKENS,
                force_sliding_window=force_structured_windows and structured,
            )
        )
    return chunks, structured_documents


def _create_retriever(method: str, chunks: list, dense_model: str | None):
    if method == "bm25":
        return BM25Retriever(chunks), {"method": "BM25Okapi", "tokenizer": "unicode_word_regex_lowercase"}

    if not dense_model or not Path(dense_model).is_dir():
        raise SystemExit("Dense ablation requires an existing local model directory; network download is disabled.")
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    import torch

    if not torch.cuda.is_available():
        raise SystemExit("Dense ablation requires the approved CUDA environment; CUDA is unavailable.")

    from rag_hcmute.retrieval.dense_index import MAX_SEQ_LENGTH, NORMALIZATION, DenseRetriever

    retriever = DenseRetriever(chunks, model_name=dense_model)
    return retriever, {
        "method": "BGE-M3 + FAISS IndexFlatIP",
        "model_label": "BGE-M3 local snapshot",
        "embedding_dim": retriever._dim,
        "max_seq_length": MAX_SEQ_LENGTH,
        "normalization": NORMALIZATION,
        "device": str(retriever._model.device),
        "network_access": "disabled",
    }


def _page_locations(questions: list[PilotQuestion], baseline_chunks: list) -> dict[str, GoldLocation]:
    """Build section-independent page labels from reviewed baseline chunk IDs."""
    chunks_by_id = {chunk.chunk_id: chunk for chunk in baseline_chunks}
    locations: dict[str, GoldLocation] = {}
    for question in questions:
        if question.answerability != "answerable" or not question.gold_chunk_ids:
            continue
        missing_ids = question.gold_chunk_ids - chunks_by_id.keys()
        if missing_ids:
            raise ValueError(f"{question.question_id}: baseline gold chunk(s) not found")
        gold_chunks = [chunks_by_id[chunk_id] for chunk_id in question.gold_chunk_ids]
        if any(chunk.document_id != question.expected_document for chunk in gold_chunks):
            raise ValueError(f"{question.question_id}: baseline gold document does not match label")
        locations[question.question_id] = GoldLocation(
            document_id=question.expected_document,
            section_paths=frozenset(),
            pdf_pages=frozenset(
                page
                for chunk in gold_chunks
                for page in range(chunk.pdf_page_start, chunk.pdf_page_end + 1)
            ),
        )
    return locations


def _evidence_metrics_including_uncovered(
    *, questions: list[PilotQuestion], spans_by_question: dict, chunks: list,
    retriever, top_k: int = TOP_K, hit_k: int = HIT_K,
) -> dict:
    """Count spans broken by chunk boundaries as misses, without hiding them."""
    chunk_ids_by_span = {}
    for spans in spans_by_question.values():
        for span in spans:
            chunk_ids_by_span[span.span_id] = frozenset(
                chunk.chunk_id
                for chunk in chunks
                if chunk.document_id == span.document_id
                and chunk.token_start is not None
                and chunk.token_end is not None
                and chunk.token_start <= span.token_start
                and chunk.token_end >= span.token_end
            )

    question_text = {question.question_id: question.question for question in questions}
    all_spans = sum(len(spans) for spans in spans_by_question.values())
    covered_spans = sum(bool(ids) for ids in chunk_ids_by_span.values())
    total_hits_at_k = 0
    complete_questions_at_k = 0
    first_evidence_reciprocals = []
    by_question = []

    for question_id, spans in spans_by_question.items():
        result = retriever.query(question_text[question_id], top_k=top_k)
        ranks = {span.span_id: None for span in spans}
        for hit in result.hits:
            # Access only IDs and ranks; no source/query text is serialized.
            for span in spans:
                if hit.chunk_id in chunk_ids_by_span[span.span_id]:
                    previous = ranks[span.span_id]
                    ranks[span.span_id] = hit.rank if previous is None else min(previous, hit.rank)
        hits = sum(rank is not None and rank <= hit_k for rank in ranks.values())
        total_hits_at_k += hits
        complete = hits == len(spans) and all(chunk_ids_by_span[span.span_id] for span in spans)
        complete_questions_at_k += int(complete)
        first_rank = min((rank for rank in ranks.values() if rank is not None), default=None)
        first_evidence_reciprocals.append(
            1.0 / first_rank if first_rank is not None and first_rank <= top_k else 0.0
        )
        by_question.append(
            {
                "question_id": question_id,
                "evidence_span_count": len(spans),
                "covered_span_count": sum(bool(chunk_ids_by_span[span.span_id]) for span in spans),
                "evidence_span_hits_at_5": hits,
                "complete_evidence_hit_at_5": complete,
            }
        )

    answerable_question_count = len(spans_by_question)
    return {
        "metric_scope": "exact source-token span; uncovered spans count as retrieval misses",
        "top_k": top_k,
        "hit_k": hit_k,
        "evidence_span_coverage": {
            "covered": covered_spans,
            "denominator": all_spans,
            "value": covered_spans / all_spans if all_spans else 0.0,
        },
        "evidence_span_recall_at_5": {
            "hits": total_hits_at_k,
            "denominator": all_spans,
            "value": total_hits_at_k / all_spans if all_spans else 0.0,
        },
        "conditional_recall_at_5_given_covered": {
            "hits": total_hits_at_k,
            "denominator": covered_spans,
            "value": total_hits_at_k / covered_spans if covered_spans else 0.0,
        },
        "complete_evidence_hit_at_5": {
            "hits": complete_questions_at_k,
            "denominator": answerable_question_count,
            "value": complete_questions_at_k / answerable_question_count if answerable_question_count else 0.0,
        },
        "first_evidence_mrr_at_10": {
            "value": sum(first_evidence_reciprocals) / answerable_question_count if answerable_question_count else 0.0,
            "denominator": answerable_question_count,
        },
        "per_question": by_question,
    }


def _group_evidence_metrics(evidence_result: dict, questions: list[PilotQuestion], document_types: dict[str, str]) -> dict:
    question_by_id = {question.question_id: question for question in questions}
    grouped: dict[str, dict] = defaultdict(
        lambda: {"question_count": 0, "evidence_spans": 0, "covered_spans": 0, "hits_at_5": 0, "complete_questions_at_5": 0}
    )
    for row in evidence_result["per_question"]:
        question = question_by_id[row["question_id"]]
        group = grouped[document_types[question.expected_document]]
        group["question_count"] += 1
        group["evidence_spans"] += row["evidence_span_count"]
        group["covered_spans"] += row["covered_span_count"]
        group["hits_at_5"] += row["evidence_span_hits_at_5"]
        group["complete_questions_at_5"] += int(row["complete_evidence_hit_at_5"])
    return {
        key: {
            **value,
            "coverage": value["covered_spans"] / value["evidence_spans"] if value["evidence_spans"] else 0.0,
            "recall_at_5_including_uncovered": value["hits_at_5"] / value["evidence_spans"] if value["evidence_spans"] else 0.0,
        }
        for key, value in grouped.items()
    }


def _group_page_metrics(page_result: dict, questions: list[PilotQuestion], document_types: dict[str, str]) -> dict:
    question_by_id = {question.question_id: question for question in questions}
    grouped: dict[str, dict] = defaultdict(lambda: {"question_count": 0, "hit_at_5": 0, "reciprocal_rank_sum": 0.0})
    for row in page_result["per_question"]:
        question = question_by_id[row["question_id"]]
        group = grouped[document_types[question.expected_document]]
        rank = row["first_gold_rank_at_10"]
        group["question_count"] += 1
        group["hit_at_5"] += int(rank is not None and rank <= HIT_K)
        group["reciprocal_rank_sum"] += 1.0 / rank if rank else 0.0
    return {
        key: {
            "question_count": value["question_count"],
            "hit_at_5": value["hit_at_5"],
            "hit_rate_at_5": value["hit_at_5"] / value["question_count"] if value["question_count"] else 0.0,
            "mrr_at_10": value["reciprocal_rank_sum"] / value["question_count"] if value["question_count"] else 0.0,
        }
        for key, value in grouped.items()
    }


def run_ablation(*, source_root: Path, method: str, dense_model: str | None) -> dict:
    manifest_by_id, manifest_hash = _load_manifest()
    snapshot_path = source_root / "snapshot.json"
    chunks_path = source_root / "chunks" / "chunks.jsonl"
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    if snapshot.get("snapshot_id") != EXPECTED_SNAPSHOT_ID:
        raise SystemExit("This controlled ablation is pinned to the approved native-only G0 snapshot.")
    if snapshot.get("config", {}).get("ocr", {}).get("enabled", False):
        raise SystemExit("G0 must remain native-only for this chunk-strategy ablation.")

    baseline_chunks = load_chunks(chunks_path)
    pages_by_document = {}
    for document in snapshot["documents"]:
        document_id = document["document_id"]
        pages = read_pages_jsonl(source_root / "pages" / f"{document_id}.jsonl")
        pages_by_document[document_id], _ = clean_document_pages(pages)

    questions_path = PROJECT_ROOT / "data/question_sets/pilot_questions.csv"
    annotations_path = PROJECT_ROOT / "data/question_sets/pilot_evidence_annotations.json"
    questions = load_pilot_questions(questions_path)
    spans_by_question, annotation_metadata = load_exact_evidence_spans(
        questions_path=questions_path,
        annotations_path=annotations_path,
        pages_by_document=pages_by_document,
        snapshot_id=snapshot["snapshot_id"],
    )
    document_types = {document_id: row["document_type"] for document_id, row in manifest_by_id.items()}
    page_gold_locations = _page_locations(questions, baseline_chunks)

    variants = []
    for variant_name, force_windows in (("automatic_section_policy", False), ("forced_windows_on_structured_docs", True)):
        chunks, structured_documents = _build_variant(
            snapshot=snapshot,
            pages_by_document=pages_by_document,
            force_structured_windows=force_windows,
        )
        if not force_windows and _chunk_signature(chunks) != _chunk_signature(baseline_chunks):
            raise SystemExit(
                "Default chunker output differs from the approved G0 baseline; stopping. "
                + _baseline_difference_summary(baseline_chunks, chunks)
            )

        retriever, retrieval_config = _create_retriever(method, chunks, dense_model)
        exact_result = _evidence_metrics_including_uncovered(
            questions=questions,
            spans_by_question=spans_by_question,
            chunks=chunks,
            retriever=retriever,
            top_k=TOP_K,
            hit_k=HIT_K,
        )
        page_proxy = evaluate_location_retrieval(
            questions=questions,
            locations=page_gold_locations,
            chunks=chunks,
            retriever=retriever,
            top_k=TOP_K,
        )
        variants.append(
            {
                "name": variant_name,
                "force_sliding_window_on_structured_documents": force_windows,
                "chunk_count": len(chunks),
                "chunk_profile": chunk_profile(chunks),
                "exact_evidence": exact_result,
                "exact_evidence_by_document_type": _group_evidence_metrics(exact_result, questions, document_types),
                "page_location_proxy": page_proxy,
                "page_location_proxy_by_document_type": _group_page_metrics(
                    page_proxy,
                    questions,
                    document_types,
                ),
                "structured_document_count": len(structured_documents),
            }
        )
        del retriever

    question_counts: dict[str, int] = defaultdict(int)
    for question in questions:
        if question.answerability == "answerable" and question.gold_chunk_ids:
            question_counts[document_types[question.expected_document]] += 1

    return {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "git_revision": _git_revision(),
        "script_sha256": _sha256(Path(__file__).resolve()),
        "chunker_sha256": _sha256(PROJECT_ROOT / "src/rag_hcmute/ingestion/chunk.py"),
        "snapshot_id": snapshot["snapshot_id"],
        "snapshot_sha256": _sha256(snapshot_path),
        "manifest_sha256": manifest_hash,
        "method": method,
        "retrieval_config": retrieval_config,
        "chunking_config": {"chunk_tokens": CHUNK_TOKENS, "overlap_tokens": OVERLAP_TOKENS},
        "evaluation": {
            "answerable_question_count": len(spans_by_question),
            "evidence_span_count": annotation_metadata["evidence_span_count"],
            "answerable_question_count_by_document_type": dict(question_counts),
            "unanswerable_question_count": sum(q.answerability == "unanswerable" for q in questions),
            "metric_scope": "exact source-token evidence spans, not answer correctness or generalization",
            "baseline_content_signature_matches": True,
            "note": "The stored G0 predates document-wide token offsets; offsets were regenerated in memory and the stored snapshot was not modified.",
        },
        "variants": variants,
        "privacy_note": "Aggregate retrieval metrics and content-free chunk metadata only; no query or source text is written.",
    }


def main() -> int:
    print(f"Python executable: {sys.executable}")
    parser = argparse.ArgumentParser(
        description="Compare the current section-aware chunker with fixed windows at the same chunk size."
    )
    parser.add_argument(
        "--source-root",
        type=Path,
        default=PROJECT_ROOT / "data/processed/g0_reproduction",
    )
    parser.add_argument("--method", choices=("bm25", "dense"), default="bm25")
    parser.add_argument("--dense-model", default=None, help="Existing local model directory; no downloads are allowed.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROJECT_ROOT / "artifacts/results/chunk_strategy_ablation",
    )
    args = parser.parse_args()

    report = run_ablation(
        source_root=args.source_root.resolve(),
        method=args.method,
        dense_model=args.dense_model,
    )
    output_dir = args.output_dir.resolve()
    ignored_root = (PROJECT_ROOT / "artifacts/results").resolve()
    if not output_dir.is_relative_to(ignored_root):
        raise SystemExit("--output-dir must remain under Git-ignored artifacts/results.")
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_path = output_dir / f"{report['method']}_{report['snapshot_id']}_{timestamp}.json"
    with output_path.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write("\n")

    print(f"Snapshot: {report['snapshot_id']} | method: {report['method']}")
    print(f"Evaluation coverage: {report['evaluation']['answerable_question_count_by_document_type']}")
    for variant in report["variants"]:
        retrieval = variant["exact_evidence"]
        exact = retrieval["evidence_span_recall_at_5"]
        coverage = retrieval["evidence_span_coverage"]
        complete = retrieval["complete_evidence_hit_at_5"]
        print(
            f"{variant['name']} | chunks={variant['chunk_count']} | "
            f"evidence coverage={coverage['covered']}/{coverage['denominator']} ({coverage['value']:.3f}) | "
            f"end-to-end evidence Recall@5={exact['hits']}/{exact['denominator']} ({exact['value']:.3f}) | "
            f"complete Hit@5={complete['hits']}/{complete['denominator']} ({complete['value']:.3f})"
        )
        for document_type, metrics in variant["exact_evidence_by_document_type"].items():
            print(
                f"  {document_type}: questions={metrics['question_count']}, "
                f"span coverage={metrics['covered_spans']}/{metrics['evidence_spans']} ({metrics['coverage']:.3f}), "
                f"end-to-end Recall@5={metrics['hits_at_5']}/{metrics['evidence_spans']} "
                f"({metrics['recall_at_5_including_uncovered']:.3f})"
            )
        page = variant["page_location_proxy"]["hit_at_5"]
        print(f"  page-location proxy Hit@5={page['hits']}/{page['denominator']} ({page['value']:.3f})")
    print(f"Metrics-only output (Git-ignored): {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
