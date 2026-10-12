from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from rag_hcmute.console_app import create_retriever  # noqa: E402
from rag_hcmute.evaluation.generation_pilot import summarize_generation_pilot  # noqa: E402
from rag_hcmute.evaluation.manual_review import write_private_review_bundle  # noqa: E402
from rag_hcmute.evaluation.run_pilot import load_pilot_questions  # noqa: E402
from rag_hcmute.generation.ollama import (  # noqa: E402
    DEFAULT_BASE_URL,
    DEFAULT_MODEL,
    generate_grounded_answer,
    sources_from_hits,
)
from rag_hcmute.retrieval.common import load_chunks  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Evaluate local RAG answer/refusal workflow on the reviewed development partition."
    )
    parser.add_argument("--questions", type=Path, default=PROJECT_ROOT / "data/question_sets/pilot_questions.csv")
    parser.add_argument("--chunks", type=Path, default=PROJECT_ROOT / "data/processed/g0_reproduction/chunks/chunks.jsonl")
    parser.add_argument("--snapshot-manifest", type=Path, default=PROJECT_ROOT / "data/manifests/corpus_snapshot.json")
    parser.add_argument("--partition", choices=("development", "holdout"), default="development")
    parser.add_argument("--method", choices=("bm25", "dense", "hybrid", "dense-rerank", "hybrid-rerank"), default="hybrid-rerank")
    parser.add_argument("--dense-model", type=Path)
    parser.add_argument("--reranker-model", type=Path)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--ollama-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--output-dir", type=Path, default=PROJECT_ROOT / "artifacts/results/generation_pilot")
    parser.add_argument(
        "--review-bundle-dir",
        type=Path,
        help=(
            "Opt-in: lưu câu hỏi, câu trả lời và toàn văn các nguồn đã truy xuất để chấm thủ công. "
            "Bắt buộc đặt ngoài repository; mặc định không lưu nội dung này."
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")
    print(f"Python executable: {sys.executable}")
    args = build_parser().parse_args(argv)
    if args.top_k < 1:
        raise SystemExit("--top-k must be positive.")
    if not args.questions.is_file() or not args.chunks.is_file() or not args.snapshot_manifest.is_file():
        raise SystemExit("Question set, chunks, or snapshot manifest is missing.")

    snapshot = json.loads(args.snapshot_manifest.read_text(encoding="utf-8"))
    snapshot_id = snapshot["snapshot_id"]
    try:
        questions = load_pilot_questions(
            args.questions,
            partition=args.partition,
            snapshot_path=args.snapshot_manifest,
            project_root=PROJECT_ROOT,
        )
        retriever = create_retriever(
            method=args.method,
            chunks_path=args.chunks,
            dense_model=args.dense_model,
            reranker_model=args.reranker_model,
        )
    except (OSError, RuntimeError, ValueError) as exc:
        raise SystemExit(f"Generation pilot stopped: {exc}") from exc

    chunks_by_id = {chunk.chunk_id: chunk for chunk in load_chunks(args.chunks)}
    per_question = []
    review_records = []
    run_id = f"generation_{args.method}_{snapshot_id}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    for question in questions:
        retrieval = retriever.query(question.question, top_k=args.top_k)
        sources = sources_from_hits(retrieval.hits, chunks_by_id)
        generated = generate_grounded_answer(
            question.question,
            sources,
            model=args.model,
            base_url=args.ollama_url,
        )
        cited_document_ids = {source.document_id for source in generated.citations}
        per_question.append(
            {
                "question_id": question.question_id,
                "answerability": question.answerability,
                "abstained": generated.abstained,
                "status": generated.status,
                "citation_count": len(generated.citations),
                "citation_ids_valid": (
                    None
                    if generated.abstained
                    else bool(generated.citations)
                    and all(source.source_id in {s.source_id for s in sources} for source in generated.citations)
                ),
                "cited_expected_document": (
                    question.answerability == "answerable"
                    and question.expected_document in cited_document_ids
                ),
                "retrieval_latency_ms": round(retrieval.latency_ms, 2),
                "generation_latency_ms": round(generated.latency_ms, 2),
            }
        )
        if args.review_bundle_dir is not None:
            review_records.append(
                {
                    "question_id": question.question_id,
                    "question": question.question,
                    "answerability_gold": question.answerability,
                    "expected_document_id": question.expected_document,
                    "system_abstained": generated.abstained,
                    "generation_status": generated.status,
                    "answer": generated.answer,
                    "citation_ids": [source.source_id for source in generated.citations],
                    "cited_sources": [
                        {
                            "source_id": source.source_id,
                            "chunk_id": source.chunk_id,
                            "document_id": source.document_id,
                            "document_title": source.document_title,
                            "pdf_page_start": source.pdf_page_start,
                            "pdf_page_end": source.pdf_page_end,
                            "section_path": source.section_path,
                        }
                        for source in generated.citations
                    ],
                    "retrieved_sources": [
                        {
                            "source_id": source.source_id,
                            "chunk_id": source.chunk_id,
                            "document_id": source.document_id,
                            "document_title": source.document_title,
                            "pdf_page_start": source.pdf_page_start,
                            "pdf_page_end": source.pdf_page_end,
                            "section_path": source.section_path,
                            "text": source.text,
                        }
                        for source in sources
                    ],
                }
            )

    report = {
        "run_id": run_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "snapshot_id": snapshot_id,
        "partition": args.partition,
        "method": args.method,
        "generator": {"provider": "Ollama local loopback", "model": args.model, "temperature": 0},
        "top_k": args.top_k,
        "metrics": summarize_generation_pilot(per_question),
        "results": per_question,
        "privacy_note": "No question text, generated answer, evidence text, citation excerpt, or vector is serialized.",
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    output_path = args.output_dir / f"{report['run_id']}.json"
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    review_bundle_path = None
    if args.review_bundle_dir is not None:
        try:
            review_bundle_path = write_private_review_bundle(
                args.review_bundle_dir,
                project_root=PROJECT_ROOT,
                run_id=run_id,
                snapshot_id=snapshot_id,
                partition=args.partition,
                method=args.method,
                generator=report["generator"],
                records=review_records,
            )
        except (OSError, ValueError) as exc:
            raise SystemExit(f"Private review bundle stopped: {exc}") from exc
    print(f"Snapshot: {snapshot_id} | partition: {args.partition} | method: {args.method}")
    print(f"Answerable response rate: {report['metrics']['answerable_response_rate']}")
    print(f"Unanswerable refusal rate: {report['metrics']['unanswerable_refusal_rate']}")
    print(f"Expected-document citation rate: {report['metrics']['answerable_citing_expected_document_rate']}")
    print(f"Metrics-only result: {output_path}")
    if review_bundle_path is not None:
        print(f"Private review bundle (contains question/answer/source text): {review_bundle_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
