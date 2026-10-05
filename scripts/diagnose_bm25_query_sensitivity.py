from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


print(f"Python executable: {sys.executable}")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from rag_hcmute.evaluation.table_ablation import build_matched_table_variants  # noqa: E402
from rag_hcmute.retrieval.bm25_index import BM25Retriever  # noqa: E402

TOP_K = 5
EXPECTED_SNAPSHOT = "5da3bd4d5de54492"
QUESTION_PATH = PROJECT_ROOT / (
    "data/question_sets/table_questions_reviewed_ablation_20261005.csv"
)
EVIDENCE_PATH = PROJECT_ROOT / (
    "data/question_sets/table_question_variant_evidence_20261005.csv"
)
TABLE_HEADER_TERMS = "Năm đào tạo sinh viên Tổng số tín chỉ đã tích lũy"
SHORT_QUERIES = {
    "TB001": "85 tín chỉ thuộc năm đào tạo nào",
    "TB002": "Khoảng tín chỉ tích lũy năm đào tạo thứ hai là bao nhiêu",
    "TB003": "Năm đào tạo thứ tư tương ứng với khoảng tổng số tín chỉ tích lũy nào",
    "TB004": "Điều kiện tín chỉ tích lũy cho năm đào tạo thứ năm như thế nào",
    "TB005": "71 tín chỉ và 72 tín chỉ lần lượt thuộc năm đào tạo nào",
}


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


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


def _load_inputs() -> tuple[list[dict[str, str]], dict[tuple[str, str], list[str]]]:
    questions = _read_csv(QUESTION_PATH)
    evidence_rows = _read_csv(EVIDENCE_PATH)
    if len(questions) != 5 or {row["question_id"] for row in questions} != set(
        SHORT_QUERIES
    ):
        raise SystemExit("Expected the five approved questions TB001-TB005.")
    if any(
        row["review_status"] != "approved_for_table_retrieval_ablation"
        or row["answerability"] != "answerable"
        or row["source_snapshot_id"] != EXPECTED_SNAPSHOT
        for row in questions
    ):
        raise SystemExit("Question status or snapshot differs from the approved set.")

    expected: dict[tuple[str, str], list[str]] = {}
    for row in evidence_rows:
        key = (row["question_id"], row["variant"])
        chunk_ids = [value for value in row["expected_chunk_ids"].split(";") if value]
        if (
            key in expected
            or row["mapping_status"] != "approved_for_table_retrieval_ablation"
            or row["source_snapshot_id"] != EXPECTED_SNAPSHOT
            or not chunk_ids
            or int(row["required_evidence_units"]) != len(chunk_ids)
        ):
            raise SystemExit(f"Invalid approved evidence mapping: {key}.")
        expected[key] = chunk_ids
    required_keys = {
        (row["question_id"], variant)
        for row in questions
        for variant in ("B0", "T1", "T2")
    }
    if set(expected) != required_keys:
        raise SystemExit("Evidence map does not cover exactly TB001-TB005 / B0-T1-T2.")
    return questions, expected


def _query_styles(question: dict[str, str]) -> dict[str, str]:
    question_id = question["question_id"]
    canonical = question["question"]
    short = SHORT_QUERIES[question_id]
    return {
        "canonical": canonical,
        "canonical_plus_header": f"{canonical} {TABLE_HEADER_TERMS}",
        "short": short,
        "short_plus_header": f"{short} {TABLE_HEADER_TERMS}",
    }


def build_report() -> dict:
    questions, evidence = _load_inputs()
    corpora = build_matched_table_variants(PROJECT_ROOT)
    report = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "diagnostic_only_not_benchmark",
        "scope": "BM25 query wording sensitivity for five reviewed questions on QĐ 1727/2021 Table 5.",
        "not_a_benchmark": True,
        "snapshot_id": EXPECTED_SNAPSHOT,
        "question_set_sha256": _sha256(QUESTION_PATH),
        "evidence_map_sha256": _sha256(EVIDENCE_PATH),
        "git_revision": _git_revision(),
        "retrieval": {
            "method": "rank_bm25.BM25Okapi",
            "tokenizer": "regex_\\w+_unicode_lowercase",
            "top_k_for_diagnostic_hit_count": TOP_K,
            "full_corpus_ranks_recorded": True,
            "header_terms": TABLE_HEADER_TERMS,
        },
        "query_styles": {},
        "corpora": [],
        "limitations": [
            "Query variants are exploratory and do not replace approved questions or official ablation results.",
            "Only five questions about one table are included; no general query-rewriting claim is supported.",
            "No index, corpus, evidence annotation, or default retrieval configuration is modified.",
        ],
    }

    for question in questions:
        report["query_styles"][question["question_id"]] = _query_styles(question)

    for variant, chunks in corpora.items():
        retriever = BM25Retriever(chunks)
        chunk_index = {chunk.chunk_id: index for index, chunk in enumerate(chunks)}
        variant_results = []
        style_hits = {style: 0 for style in next(iter(report["query_styles"].values()))}
        for question in questions:
            question_id = question["question_id"]
            required_ids = evidence[(question_id, variant)]
            if not set(required_ids) <= chunk_index.keys():
                raise SystemExit(f"Missing approved evidence for {question_id}/{variant}.")

            query_results = {}
            for style, query in _query_styles(question).items():
                # Request all hits so the evidence's full-corpus rank is recorded.
                hits = retriever.query(query, top_k=len(chunks)).hits
                ranks = {
                    hit.chunk_id: hit.rank
                    for hit in hits
                    if hit.chunk_id in required_ids
                }
                required_ranks = [ranks.get(chunk_id) for chunk_id in required_ids]
                complete = all(rank is not None and rank <= TOP_K for rank in required_ranks)
                style_hits[style] += int(complete)
                query_results[style] = {
                    "query": query,
                    "required_chunk_ids": required_ids,
                    "required_chunk_ranks": required_ranks,
                    "complete_evidence_in_top_5": complete,
                    "top_5_chunk_ids": [hit.chunk_id for hit in hits[:TOP_K]],
                }
            variant_results.append({"question_id": question_id, "queries": query_results})

        report["corpora"].append(
            {
                "variant": variant,
                "chunk_count": len(chunks),
                "complete_evidence_hits_at_5_by_query_style": {
                    style: {"hits": hits, "denominator": len(questions)}
                    for style, hits in style_hits.items()
                },
                "questions": variant_results,
            }
        )
    return report


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Diagnose BM25 rank sensitivity to question wording for the approved Table 5 set. "
            "Query variants are exploratory only and do not change the benchmark."
        )
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROJECT_ROOT / "artifacts/results/bm25_query_sensitivity",
    )
    args = parser.parse_args()
    report = build_report()

    output_dir = args.output_dir.resolve()
    ignored_root = (PROJECT_ROOT / "artifacts/results").resolve()
    if not output_dir.is_relative_to(ignored_root):
        raise SystemExit("--output-dir must remain under Git-ignored artifacts/results.")
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_path = output_dir / f"bm25_query_sensitivity_{timestamp}.json"
    with output_path.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write("\n")

    print(f"Status: {report['status']}")
    for corpus in report["corpora"]:
        counts = corpus["complete_evidence_hits_at_5_by_query_style"]
        shown = ", ".join(f"{style}={values['hits']}/5" for style, values in counts.items())
        print(f"{corpus['variant']} ({corpus['chunk_count']} chunks): {shown}")
    print(f"Raw output (Git-ignored): {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
