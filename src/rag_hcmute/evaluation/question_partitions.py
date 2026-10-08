from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_PARTITION_MANIFEST = PROJECT_ROOT / "data/question_sets/question_partition_manifest.csv"
DEFAULT_SNAPSHOT = PROJECT_ROOT / "data/manifests/corpus_snapshot.json"
REQUIRED_FIELDS = {
    "source_set",
    "question_id",
    "partition",
    "corpus_snapshot_id",
    "review_status_field",
    "reviewed_status",
}
GENERAL_PARTITIONS = {"development", "holdout"}


def _read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames is None:
            raise ValueError(f"CSV has no header: {path.name}")
        return list(reader.fieldnames), list(reader)


def _source_key(path: Path, project_root: Path) -> str:
    resolved = path.resolve()
    try:
        relative = resolved.relative_to(project_root.resolve())
    except ValueError as exc:
        raise ValueError("Question-set files must be inside the project root.") from exc
    return relative.as_posix()


def _partition_allowed(review_status_field: str, partition: str) -> bool:
    if review_status_field == "status":
        return partition in GENERAL_PARTITIONS
    if review_status_field == "review_status":
        return partition == "ablation_only"
    return False


def validate_question_partition_manifest(
    *,
    registry_path: Path = DEFAULT_PARTITION_MANIFEST,
    snapshot_path: Path = DEFAULT_SNAPSHOT,
    project_root: Path = PROJECT_ROOT,
) -> dict:
    """Validate reviewed question IDs, their purpose, and their corpus snapshot.

    Only metadata is returned; question text, expected answers, and source excerpts
    are intentionally excluded from the report.
    """
    fields, registry_rows = _read_csv(registry_path)
    if not REQUIRED_FIELDS.issubset(fields):
        raise ValueError("Question partition manifest is missing required columns.")
    if not registry_rows:
        raise ValueError("Question partition manifest has no assignments.")

    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    active_snapshot_id = str(snapshot.get("snapshot_id", "")).strip()
    if not active_snapshot_id:
        raise ValueError("Active corpus snapshot has no snapshot_id.")

    assignments: dict[tuple[str, str], dict[str, str]] = {}
    rows_by_source: dict[str, list[dict[str, str]]] = {}
    global_question_ids: set[str] = set()
    for row in registry_rows:
        source_set = row["source_set"].strip().replace("\\", "/")
        question_id = row["question_id"].strip()
        partition = row["partition"].strip().lower()
        registered_snapshot = row["corpus_snapshot_id"].strip()
        status_field = row["review_status_field"].strip()
        reviewed_status = row["reviewed_status"].strip()
        if not all((source_set, question_id, partition, registered_snapshot, status_field, reviewed_status)):
            raise ValueError("Question partition manifest contains a blank required value.")
        source_path = Path(source_set)
        if source_path.is_absolute() or ".." in source_path.parts:
            raise ValueError("Question-set source paths must be project-relative and contained.")
        if registered_snapshot != active_snapshot_id:
            raise ValueError("A question assignment targets a different corpus snapshot.")
        if not _partition_allowed(status_field, partition):
            raise ValueError("A question partition is not allowed for its review-status field.")
        key = (source_set, question_id)
        if key in assignments:
            raise ValueError("Question partition manifest contains a duplicate assignment.")
        if question_id in global_question_ids:
            raise ValueError("Question IDs must be unique across registered question sets.")
        assignments[key] = row
        rows_by_source.setdefault(source_set, []).append(row)
        global_question_ids.add(question_id)

    counts: Counter[tuple[str, str]] = Counter()
    for source_set, source_assignments in rows_by_source.items():
        source_path = (project_root / Path(source_set)).resolve()
        try:
            source_path.relative_to(project_root.resolve())
        except ValueError as exc:
            raise ValueError("Question-set source paths must remain inside the project root.") from exc
        if not source_path.is_file():
            raise ValueError(f"Registered question set is missing: {source_set}")
        source_fields, source_rows = _read_csv(source_path)
        first_assignment = source_assignments[0]
        status_field = first_assignment["review_status_field"].strip()
        reviewed_status = first_assignment["reviewed_status"].strip()
        if any(
            row["review_status_field"].strip() != status_field
            or row["reviewed_status"].strip() != reviewed_status
            for row in source_assignments
        ):
            raise ValueError("A question set mixes review policies.")
        if "question_id" not in source_fields or status_field not in source_fields:
            raise ValueError(f"Registered question set is missing required metadata: {source_set}")

        source_ids = [row["question_id"].strip() for row in source_rows]
        if any(not question_id for question_id in source_ids) or len(source_ids) != len(set(source_ids)):
            raise ValueError(f"Registered question set has blank or duplicate IDs: {source_set}")
        reviewed_ids = {
            row["question_id"].strip()
            for row in source_rows
            if row.get(status_field, "").strip() == reviewed_status
        }
        registered_ids = {row["question_id"].strip() for row in source_assignments}
        if registered_ids != reviewed_ids:
            raise ValueError(f"Reviewed question assignments do not match the source set: {source_set}")
        for row in source_assignments:
            counts[(source_set, row["partition"].strip().lower())] += 1

    return {
        "snapshot_id": active_snapshot_id,
        "assignment_count": len(registry_rows),
        "question_sets": [
            {
                "source_set": source_set,
                "partition": partition,
                "question_count": count,
            }
            for (source_set, partition), count in sorted(counts.items())
        ],
        "holdout_question_count": sum(
            count for (_, partition), count in counts.items() if partition == "holdout"
        ),
    }


def question_ids_for_partition(
    question_path: Path,
    partition: str,
    *,
    registry_path: Path = DEFAULT_PARTITION_MANIFEST,
    snapshot_path: Path = DEFAULT_SNAPSHOT,
    project_root: Path = PROJECT_ROOT,
) -> frozenset[str]:
    """Return only IDs assigned to the requested partition after full validation."""
    if partition not in {"development", "holdout", "ablation_only"}:
        raise ValueError("Unsupported question partition.")
    validate_question_partition_manifest(
        registry_path=registry_path,
        snapshot_path=snapshot_path,
        project_root=project_root,
    )
    source_key = _source_key(question_path, project_root)
    _, rows = _read_csv(registry_path)
    selected = frozenset(
        row["question_id"].strip()
        for row in rows
        if row["source_set"].strip().replace("\\", "/") == source_key
        and row["partition"].strip().lower() == partition
    )
    if not selected:
        raise ValueError("No reviewed questions are registered for the requested partition.")
    return selected
