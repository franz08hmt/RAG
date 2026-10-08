from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_MANIFEST = PROJECT_ROOT / "data/manifests/corpus_manifest.csv"
DEFAULT_QUESTIONS = PROJECT_ROOT / "data/question_sets/pilot_questions.csv"
DEFAULT_ANNOTATIONS = PROJECT_ROOT / "data/question_sets/pilot_evidence_annotations.json"
DEFAULT_TABLE_QUESTIONS = (
    PROJECT_ROOT / "data/question_sets/table_questions_reviewed_ablation_20261005.csv"
)
REVIEWED_STATUS = "reviewed"
TABLE_APPROVED_STATUS = "approved_for_table_retrieval_ablation"


def _read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames is None:
            raise ValueError(f"CSV has no header: {path}")
        return list(reader.fieldnames), list(reader)


def audit_question_coverage(
    *,
    manifest_path: Path,
    questions_path: Path,
    annotations_path: Path,
    table_questions_path: Path,
) -> dict:
    manifest_fields, manifest_rows = _read_csv(manifest_path)
    question_fields, question_rows = _read_csv(questions_path)
    table_fields, table_rows = _read_csv(table_questions_path)
    annotation = json.loads(annotations_path.read_text(encoding="utf-8"))

    if "document_id" not in manifest_fields or "document_type" not in manifest_fields:
        raise ValueError("Corpus manifest must define document_id and document_type.")
    document_types: dict[str, str] = {}
    for row in manifest_rows:
        document_id = row["document_id"].strip()
        if not document_id or document_id in document_types:
            raise ValueError("Corpus manifest contains a blank or duplicate document_id.")
        document_types[document_id] = row["document_type"].strip() or "unspecified"

    required_question_fields = {
        "question_id",
        "category",
        "answerability",
        "status",
        "expected_document",
    }
    if not required_question_fields.issubset(question_fields):
        raise ValueError("Pilot question CSV is missing required metadata fields.")
    all_question_ids = [row["question_id"].strip() for row in question_rows]
    if any(not question_id for question_id in all_question_ids) or len(set(all_question_ids)) != len(all_question_ids):
        raise ValueError("Pilot question CSV contains a blank or duplicate question_id.")

    reviewed_rows = [row for row in question_rows if row["status"].strip() == REVIEWED_STATUS]
    if any(row["answerability"].strip() not in {"answerable", "unanswerable"} for row in reviewed_rows):
        raise ValueError("Reviewed questions must have answerability labeled answerable/unanswerable.")

    answerability_counts = Counter(row["answerability"].strip() for row in reviewed_rows)
    category_counts = Counter(
        (row["answerability"].strip(), row["category"].strip() or "unspecified")
        for row in reviewed_rows
    )
    answerable_rows = [row for row in reviewed_rows if row["answerability"].strip() == "answerable"]
    answerable_by_document_type = Counter()
    for row in answerable_rows:
        document_id = row["expected_document"].strip()
        if not document_id:
            raise ValueError("Reviewed answerable question is missing expected_document.")
        if document_id not in document_types:
            raise ValueError(f"Question references a document outside the manifest: {document_id}")
        answerable_by_document_type[document_types[document_id]] += 1

    annotation_questions = annotation.get("questions", {})
    if not isinstance(annotation_questions, dict):
        raise ValueError("Evidence annotations must contain a questions object.")
    reviewed_answerable_ids = {row["question_id"].strip() for row in answerable_rows}
    annotation_ids = set(annotation_questions)
    annotated_reviewed_ids = reviewed_answerable_ids.intersection(annotation_ids)
    exact_evidence_span_count = sum(
        len(annotation_questions[question_id].get("spans", []))
        for question_id in annotated_reviewed_ids
    )
    split_counts = Counter(
        row.get("split", "").strip().lower()
        for row in reviewed_rows
        if row.get("split", "").strip()
    )

    if "review_status" not in table_fields:
        raise ValueError("Table ablation question CSV is missing review_status.")
    approved_table_rows = [
        row for row in table_rows if row["review_status"].strip() == TABLE_APPROVED_STATUS
    ]
    table_sources = {
        (row.get("source_document_id", "").strip(), row.get("source_reference", "").strip())
        for row in approved_table_rows
    }
    table_sources.discard(("", ""))

    explicit_split_field = "split" in question_fields
    by_document_type = Counter(document_types.values())
    return {
        "corpus": {
            "snapshot_id": annotation.get("snapshot_id"),
            "document_count": len(manifest_rows),
            "document_type_counts": dict(sorted(by_document_type.items())),
        },
        "reviewed_pilot": {
            "question_count": len(reviewed_rows),
            "answerability_counts": dict(sorted(answerability_counts.items())),
            "category_counts": {
                f"{answerability}:{category}": count
                for (answerability, category), count in sorted(category_counts.items())
            },
            "answerable_questions_by_document_type": {
                document_type: answerable_by_document_type.get(document_type, 0)
                for document_type in sorted(by_document_type)
            },
            "answerable_questions_with_exact_evidence_annotations": len(annotated_reviewed_ids),
            "answerable_questions_missing_exact_evidence_annotations": len(
                reviewed_answerable_ids - annotation_ids
            ),
            "exact_evidence_span_count": exact_evidence_span_count,
            "explicit_split_field_present": explicit_split_field,
            "split_label_counts": dict(sorted(split_counts.items())),
            "independent_holdout_recorded": "test" in split_counts,
        },
        "table_ablation_separate": {
            "approved_question_count": len(approved_table_rows),
            "source_document_count": len(
                {row.get("source_document_id", "").strip() for row in approved_table_rows} - {""}
            ),
            "distinct_source_references": len(table_sources),
            "included_in_general_pilot": False,
        },
        "excluded_unreviewed_pilot_rows": len(question_rows) - len(reviewed_rows),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Summarize reviewed RAG question-set coverage without emitting question or source text."
    )
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--questions", type=Path, default=DEFAULT_QUESTIONS)
    parser.add_argument("--annotations", type=Path, default=DEFAULT_ANNOTATIONS)
    parser.add_argument("--table-questions", type=Path, default=DEFAULT_TABLE_QUESTIONS)
    return parser


def main(argv: list[str] | None = None) -> int:
    print(f"Python executable: {sys.executable}", file=sys.stderr)
    args = build_parser().parse_args(argv)
    report = audit_question_coverage(
        manifest_path=args.manifest,
        questions_path=args.questions,
        annotations_path=args.annotations,
        table_questions_path=args.table_questions,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0
