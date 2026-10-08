import csv
import json
from pathlib import Path

from rag_hcmute.evaluation.question_coverage import audit_question_coverage


def _write_csv(path: Path, headers: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)


def test_audit_counts_reviewed_coverage_without_emitting_question_content(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.csv"
    questions = tmp_path / "questions.csv"
    annotations = tmp_path / "annotations.json"
    table_questions = tmp_path / "table_questions.csv"
    question_rows = [
        {
            "question_id": "Q1",
            "question": "private synthetic question",
            "category": "policy_topic",
            "answerability": "answerable",
            "status": "reviewed",
            "expected_document": "POLICY",
        },
        {
            "question_id": "Q2",
            "question": "another private synthetic question",
            "category": "out_of_scope",
            "answerability": "unanswerable",
            "status": "reviewed",
            "expected_document": "",
        },
        {
            "question_id": "Q3",
            "question": "unreviewed candidate should not be counted",
            "category": "draft",
            "answerability": "answerable",
            "status": "draft",
            "expected_document": "POLICY",
        },
    ]
    _write_csv(manifest, ["document_id", "document_type"], [
        {"document_id": "POLICY", "document_type": "quyet_dinh"},
        {"document_id": "HANDBOOK", "document_type": "so_tay"},
    ])
    _write_csv(questions, list(question_rows[0]), question_rows)
    annotations.write_text(
        json.dumps(
            {
                "snapshot_id": "snapshot-test",
                "questions": {
                    "Q1": {"spans": [{"span_id": "Q1-S1"}, {"span_id": "Q1-S2"}]}
                },
            }
        ),
        encoding="utf-8",
    )
    _write_csv(
        table_questions,
        ["question_id", "review_status", "source_document_id", "source_reference"],
        [
            {
                "question_id": "T1",
                "review_status": "approved_for_table_retrieval_ablation",
                "source_document_id": "POLICY",
                "source_reference": "Table A",
            }
        ],
    )

    result = audit_question_coverage(
        manifest_path=manifest,
        questions_path=questions,
        annotations_path=annotations,
        table_questions_path=table_questions,
    )

    assert result["reviewed_pilot"]["question_count"] == 2
    assert result["reviewed_pilot"]["answerability_counts"] == {
        "answerable": 1,
        "unanswerable": 1,
    }
    assert result["reviewed_pilot"]["exact_evidence_span_count"] == 2
    assert result["reviewed_pilot"]["answerable_questions_by_document_type"] == {
        "quyet_dinh": 1,
        "so_tay": 0,
    }
    assert result["reviewed_pilot"]["explicit_split_field_present"] is False
    assert result["reviewed_pilot"]["independent_holdout_recorded"] is False
    assert result["table_ablation_separate"]["approved_question_count"] == 1
    assert result["table_ablation_separate"]["included_in_general_pilot"] is False
    assert "private synthetic question" not in json.dumps(result)
    assert result["excluded_unreviewed_pilot_rows"] == 1
