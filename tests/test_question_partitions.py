import csv
import json
from pathlib import Path

import pytest

from rag_hcmute.evaluation.question_partitions import (
    question_row_sha256,
    question_ids_for_partition,
    validate_question_partition_manifest,
)
from rag_hcmute.evaluation.run_pilot import load_pilot_questions


def _write_csv(path: Path, headers: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)


def _fixture(root: Path) -> tuple[Path, Path, Path]:
    snapshot_path = root / "data/manifests/corpus_snapshot.json"
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    snapshot_path.write_text(json.dumps({"snapshot_id": "snap-1"}), encoding="utf-8")
    questions_path = root / "data/question_sets/pilot.csv"
    question_rows = [
        {
            "question_id": "P001",
            "question": "development private text",
            "category": "general",
            "answerability": "answerable",
            "status": "reviewed",
            "expected_document": "DOC",
            "expected_chunk_id": "DOC__c1",
            "evidence_page": "1",
        },
        {
            "question_id": "P002",
            "question": "holdout private text",
            "category": "general",
            "answerability": "answerable",
            "status": "reviewed",
            "expected_document": "DOC",
            "expected_chunk_id": "DOC__c2",
            "evidence_page": "2",
        },
    ]
    _write_csv(questions_path, list(question_rows[0]), question_rows)
    registry_path = root / "data/question_sets/question_partition_manifest.csv"
    _write_csv(
        registry_path,
        [
            "source_set",
            "question_id",
            "partition",
            "corpus_snapshot_id",
            "review_status_field",
            "reviewed_status",
            "reviewed_row_sha256",
        ],
        [
            {
                "source_set": "data/question_sets/pilot.csv",
                "question_id": "P001",
                "partition": "development",
                "corpus_snapshot_id": "snap-1",
                "review_status_field": "status",
                "reviewed_status": "reviewed",
                "reviewed_row_sha256": question_row_sha256(question_rows[0]),
            },
            {
                "source_set": "data/question_sets/pilot.csv",
                "question_id": "P002",
                "partition": "holdout",
                "corpus_snapshot_id": "snap-1",
                "review_status_field": "status",
                "reviewed_status": "reviewed",
                "reviewed_row_sha256": question_row_sha256(question_rows[1]),
            },
        ],
    )
    return questions_path, registry_path, snapshot_path


def test_partition_registry_validates_and_only_returns_requested_ids(tmp_path: Path) -> None:
    questions_path, registry_path, snapshot_path = _fixture(tmp_path)

    report = validate_question_partition_manifest(
        registry_path=registry_path,
        snapshot_path=snapshot_path,
        project_root=tmp_path,
    )
    development_ids = question_ids_for_partition(
        questions_path,
        "development",
        registry_path=registry_path,
        snapshot_path=snapshot_path,
        project_root=tmp_path,
    )
    holdout_ids = question_ids_for_partition(
        questions_path,
        "holdout",
        registry_path=registry_path,
        snapshot_path=snapshot_path,
        project_root=tmp_path,
    )

    assert report["holdout_question_count"] == 1
    assert development_ids == {"P001"}
    assert holdout_ids == {"P002"}


def test_pilot_loader_filters_questions_by_partition_without_rewriting_csv(tmp_path: Path) -> None:
    questions_path, registry_path, snapshot_path = _fixture(tmp_path)

    questions = load_pilot_questions(
        questions_path,
        partition="development",
        partition_manifest_path=registry_path,
        snapshot_path=snapshot_path,
        project_root=tmp_path,
    )

    assert [question.question_id for question in questions] == ["P001"]
    assert "holdout private text" not in questions[0].question


def test_partition_registry_rejects_unmapped_reviewed_question(tmp_path: Path) -> None:
    questions_path, registry_path, snapshot_path = _fixture(tmp_path)
    with questions_path.open("a", encoding="utf-8") as stream:
        stream.write("P003,new private text,general,answerable,reviewed,DOC,DOC__c3,3\n")

    with pytest.raises(ValueError, match="do not match"):
        validate_question_partition_manifest(
            registry_path=registry_path,
            snapshot_path=snapshot_path,
            project_root=tmp_path,
        )


def test_partition_registry_rejects_snapshot_mismatch(tmp_path: Path) -> None:
    _, registry_path, snapshot_path = _fixture(tmp_path)
    snapshot_path.write_text(json.dumps({"snapshot_id": "new-snapshot"}), encoding="utf-8")

    with pytest.raises(ValueError, match="different corpus snapshot"):
        validate_question_partition_manifest(
            registry_path=registry_path,
            snapshot_path=snapshot_path,
            project_root=tmp_path,
        )


def test_partition_registry_rejects_edited_reviewed_question_or_gold(tmp_path: Path) -> None:
    questions_path, registry_path, snapshot_path = _fixture(tmp_path)
    fields, rows = [], []
    with questions_path.open("r", encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        fields = reader.fieldnames or []
        rows = list(reader)
    rows[0]["expected_chunk_id"] = "changed-gold-without-review"
    _write_csv(questions_path, fields, rows)

    with pytest.raises(ValueError, match="content fingerprint mismatch"):
        validate_question_partition_manifest(
            registry_path=registry_path,
            snapshot_path=snapshot_path,
            project_root=tmp_path,
        )


def test_partition_registry_does_not_emit_question_content(tmp_path: Path) -> None:
    _, registry_path, snapshot_path = _fixture(tmp_path)
    report = validate_question_partition_manifest(
        registry_path=registry_path,
        snapshot_path=snapshot_path,
        project_root=tmp_path,
    )

    serialized = json.dumps(report)
    assert "private text" not in serialized
    assert "P001" not in serialized
