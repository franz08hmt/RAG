from __future__ import annotations

import csv
import json
import re
from collections import Counter
from pathlib import Path

ANSWER_FIELDS = (
    "run_id",
    "snapshot_id",
    "partition",
    "question_id",
    "answerability_gold",
    "system_abstained",
    "answer_correctness",
    "faithfulness",
    "answer_relevance",
    "citation_present",
    "citation_location_correctness",
    "review_status",
)
CLAIM_FIELDS = (
    "run_id",
    "question_id",
    "claim_id",
    "support_label",
    "citation_present",
    "citation_location_correctness",
    "review_status",
)

_ANSWERABILITY = {"answerable", "unanswerable"}
_BOOL = {"true", "false"}
_REVIEW_STATUS = {"pending", "reviewed", "adjudicated"}
_ANSWER_CORRECTNESS = {"correct", "partially_correct", "incorrect", "not_applicable"}
_FAITHFULNESS = {"fully_supported", "partially_supported", "unsupported", "not_applicable"}
_RELEVANCE = {"direct", "partial", "irrelevant", "not_applicable"}
_LOCATION = {"correct", "incorrect", "not_applicable"}
_CLAIM_SUPPORT = {"supported", "partially_supported", "unsupported", "uncited"}
_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
_PARTITIONS = {"development", "holdout", "ablation_only"}


def write_private_review_bundle(
    directory: Path,
    *,
    project_root: Path,
    run_id: str,
    snapshot_id: str,
    partition: str,
    method: str,
    generator: dict,
    records: list[dict],
) -> Path:
    """Write review material locally, refusing paths inside the Git project."""
    target_dir = directory.resolve()
    repository = project_root.resolve()
    if target_dir == repository or repository in target_dir.parents:
        raise ValueError("Review bundle phải được lưu ngoài thư mục repository.")
    target_dir.mkdir(parents=True, exist_ok=True)
    if not _SAFE_ID.fullmatch(run_id):
        raise ValueError("run_id chỉ được chứa ký tự ID an toàn.")
    output_path = target_dir / f"{run_id}.jsonl"
    with output_path.open("x", encoding="utf-8", newline="\n") as stream:
        for record in records:
            payload = {
                "run_id": run_id,
                "snapshot_id": snapshot_id,
                "partition": partition,
                "method": method,
                "generator": generator,
                **record,
            }
            stream.write(json.dumps(payload, ensure_ascii=False) + "\n")
    return output_path


def prepare_review_sheets(
    bundle_path: Path, *, output_root: Path, project_root: Path
) -> tuple[Path, Path, int]:
    """Create pending, ID-only annotation sheets from a private generation bundle."""
    if not bundle_path.is_file():
        raise ValueError("Không tìm thấy private review bundle.")
    target_root = output_root.resolve()
    repository = project_root.resolve()
    if target_root == repository or repository in target_root.parents:
        raise ValueError("Phiếu chấm phải được lưu ngoài thư mục repository.")

    records = []
    with bundle_path.open("r", encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, start=1):
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Bundle JSONL không hợp lệ tại dòng {line_number}.") from exc
            if not isinstance(record, dict):
                raise ValueError(f"Bundle JSONL không hợp lệ tại dòng {line_number}.")
            records.append(record)
    if not records:
        raise ValueError("Bundle không có bản ghi để lập phiếu.")

    first = records[0]
    run_id = first.get("run_id", "")
    if not isinstance(run_id, str) or not _SAFE_ID.fullmatch(run_id):
        raise ValueError("Bundle thiếu run_id hợp lệ.")
    shared_context = (first.get("run_id"), first.get("snapshot_id"), first.get("partition"))
    snapshot_id = shared_context[1]
    partition = shared_context[2]
    if not isinstance(snapshot_id, str) or not _SAFE_ID.fullmatch(snapshot_id):
        raise ValueError("Bundle thiếu snapshot_id hợp lệ.")
    if not isinstance(partition, str) or partition not in _PARTITIONS:
        raise ValueError("Bundle có partition không hợp lệ.")
    seen_questions: set[str] = set()
    answer_sheet_rows = []
    for line_number, record in enumerate(records, start=1):
        if (record.get("run_id"), record.get("snapshot_id"), record.get("partition")) != shared_context:
            raise ValueError(f"Bundle có run/snapshot/partition không đồng nhất tại dòng {line_number}.")
        question_id = record.get("question_id", "")
        if not isinstance(question_id, str) or not _SAFE_ID.fullmatch(question_id) or question_id in seen_questions:
            raise ValueError(f"question_id thiếu, sai định dạng hoặc trùng tại dòng {line_number}.")
        seen_questions.add(question_id)
        answerability = record.get("answerability_gold")
        abstained = record.get("system_abstained")
        citation_ids = record.get("citation_ids")
        if answerability not in _ANSWERABILITY or not isinstance(abstained, bool) or not isinstance(citation_ids, list):
            raise ValueError(f"Metadata đánh giá không hợp lệ tại dòng {line_number}.")
        if abstained and citation_ids:
            raise ValueError(f"Bundle ghi citation cho output abstain tại dòng {line_number}.")
        answer_sheet_rows.append(
            {
                "run_id": run_id,
                "snapshot_id": snapshot_id,
                "partition": partition,
                "question_id": question_id,
                "answerability_gold": answerability,
                "system_abstained": str(abstained).lower(),
                "answer_correctness": "",
                "faithfulness": "",
                "answer_relevance": "",
                "citation_present": str(bool(citation_ids)).lower(),
                "citation_location_correctness": "",
                "review_status": "pending",
            }
        )

    target_root.mkdir(parents=True, exist_ok=True)
    review_dir = target_root / f"review_{run_id}"
    review_dir.mkdir(exist_ok=False)
    answers_path = review_dir / "answer_review.csv"
    claims_path = review_dir / "claim_review.csv"
    with answers_path.open("x", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=ANSWER_FIELDS)
        writer.writeheader()
        writer.writerows(answer_sheet_rows)
    with claims_path.open("x", encoding="utf-8-sig", newline="") as stream:
        csv.writer(stream).writerow(CLAIM_FIELDS)
    return answers_path, claims_path, len(answer_sheet_rows)


def _read_rows(path: Path, expected_fields: tuple[str, ...]) -> list[dict[str, str]]:
    if not path.is_file():
        raise ValueError(f"Không tìm thấy file đánh giá: {path}")
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if tuple(reader.fieldnames or ()) != expected_fields:
            raise ValueError(
                f"Header CSV không đúng schema yêu cầu ({path.name}); "
                "không thêm cột tự do để tránh vô tình xuất nội dung nhạy cảm."
            )
        rows = []
        for row_number, row in enumerate(reader, start=2):
            if None in row or any(value is None for value in row.values()):
                raise ValueError(f"Cấu trúc dòng CSV không hợp lệ tại dòng {row_number}.")
            rows.append({key: (value or "").strip() for key, value in row.items()})
        return rows


def _require_choice(row: dict[str, str], field: str, allowed: set[str], row_number: int) -> str:
    value = row[field].lower()
    if value not in allowed:
        raise ValueError(f"Giá trị không hợp lệ tại dòng {row_number}, cột {field}.")
    return value


def _require_id(row: dict[str, str], field: str, row_number: int) -> str:
    value = row[field]
    if not value or not _SAFE_ID.fullmatch(value):
        raise ValueError(f"Thiếu hoặc sai định dạng mã định danh tại dòng {row_number}, cột {field}.")
    return value


def _parse_bool(row: dict[str, str], field: str, row_number: int) -> bool:
    value = _require_choice(row, field, _BOOL, row_number)
    return value == "true"


def load_answer_reviews(path: Path) -> list[dict[str, str]]:
    rows = _read_rows(path, ANSWER_FIELDS)
    seen: set[tuple[str, str]] = set()
    for row_number, row in enumerate(rows, start=2):
        key = (_require_id(row, "run_id", row_number), _require_id(row, "question_id", row_number))
        if key in seen:
            raise ValueError(f"Trùng run_id/question_id tại dòng {row_number}.")
        seen.add(key)
        _require_id(row, "snapshot_id", row_number)
        partition = _require_id(row, "partition", row_number)
        if partition.lower() not in _PARTITIONS:
            raise ValueError(f"Partition không hợp lệ tại dòng {row_number}.")
        answerability = _require_choice(row, "answerability_gold", _ANSWERABILITY, row_number)
        abstained = _parse_bool(row, "system_abstained", row_number)
        citation_present = _parse_bool(row, "citation_present", row_number)
        review_status = _require_choice(row, "review_status", _REVIEW_STATUS, row_number)
        labels = {
            "answer_correctness": _ANSWER_CORRECTNESS,
            "faithfulness": _FAITHFULNESS,
            "answer_relevance": _RELEVANCE,
            "citation_location_correctness": _LOCATION,
        }
        for field, allowed in labels.items():
            if row[field]:
                _require_choice(row, field, allowed, row_number)
            elif review_status != "pending":
                raise ValueError(f"Thiếu nhãn đã chấm tại dòng {row_number}, cột {field}.")
        correctness = row["answer_correctness"].lower()
        faithfulness = row["faithfulness"].lower()
        relevance = row["answer_relevance"].lower()
        location = row["citation_location_correctness"].lower()

        if abstained:
            if citation_present or location not in {"", "not_applicable"}:
                raise ValueError(f"Dữ liệu citation mâu thuẫn với abstain tại dòng {row_number}.")
            if review_status != "pending" and any(
                value != "not_applicable" for value in (correctness, faithfulness, relevance)
            ):
                raise ValueError(f"Câu từ chối phải dùng not_applicable cho chất lượng câu trả lời tại dòng {row_number}.")
        else:
            if review_status != "pending" and citation_present == (location == "not_applicable"):
                raise ValueError(f"Nhãn vị trí citation không khớp citation_present tại dòng {row_number}.")
            if review_status != "pending" and "not_applicable" in (correctness, faithfulness, relevance):
                raise ValueError(f"Câu đã sinh cần được chấm đầy đủ tại dòng {row_number}.")

        if answerability not in _ANSWERABILITY:  # Defensive; validated above.
            raise ValueError(f"answerability không hợp lệ tại dòng {row_number}.")
    return rows


def load_claim_reviews(path: Path) -> list[dict[str, str]]:
    rows = _read_rows(path, CLAIM_FIELDS)
    seen: set[tuple[str, str, str]] = set()
    for row_number, row in enumerate(rows, start=2):
        key = (
            _require_id(row, "run_id", row_number),
            _require_id(row, "question_id", row_number),
            _require_id(row, "claim_id", row_number),
        )
        if key in seen:
            raise ValueError(f"Trùng run_id/question_id/claim_id tại dòng {row_number}.")
        seen.add(key)
        citation_present = _parse_bool(row, "citation_present", row_number)
        status = _require_choice(row, "review_status", _REVIEW_STATUS, row_number)
        support = row["support_label"].lower()
        location = row["citation_location_correctness"].lower()
        if support:
            _require_choice(row, "support_label", _CLAIM_SUPPORT, row_number)
        elif status != "pending":
            raise ValueError(f"Thiếu nhãn claim đã chấm tại dòng {row_number}, cột support_label.")
        if location:
            _require_choice(row, "citation_location_correctness", _LOCATION, row_number)
        elif status != "pending":
            raise ValueError(f"Thiếu nhãn vị trí đã chấm tại dòng {row_number}.")
        if not citation_present and status != "pending" and (support != "uncited" or location != "not_applicable"):
            raise ValueError(f"Claim không citation phải được gắn uncited/not_applicable tại dòng {row_number}.")
        if citation_present and status != "pending" and (support == "uncited" or location == "not_applicable"):
            raise ValueError(f"Claim có citation cần đánh giá mức hỗ trợ và vị trí tại dòng {row_number}.")
    return rows


def _distribution(values: list[str]) -> dict:
    counts = Counter(values)
    denominator = len(values)
    return {
        "denominator": denominator,
        "counts": dict(sorted(counts.items())),
        "rates": {
            label: (count / denominator if denominator else None)
            for label, count in sorted(counts.items())
        },
    }


def _rate(numerator: int, denominator: int) -> dict:
    return {
        "count": numerator,
        "denominator": denominator,
        "value": numerator / denominator if denominator else None,
    }


def summarize_manual_reviews(
    answer_rows: list[dict[str, str]], claim_rows: list[dict[str, str]]
) -> dict:
    run_contexts = {
        (row["run_id"], row["snapshot_id"], row["partition"])
        for row in answer_rows
    }
    if len(run_contexts) > 1:
        raise ValueError("Mỗi lần tổng hợp chỉ được có một run_id, snapshot_id và partition.")
    answer_keys = {(row["run_id"], row["question_id"]): row for row in answer_rows}
    for claim in claim_rows:
        answer = answer_keys.get((claim["run_id"], claim["question_id"]))
        if answer is None:
            raise ValueError("Có claim review không khớp với dòng answer review.")
        if answer["system_abstained"].lower() == "true":
            raise ValueError("Không ghi claim cho câu trả lời đã từ chối.")

    reviewed = [row for row in answer_rows if row["review_status"].lower() in {"reviewed", "adjudicated"}]
    answered = [row for row in reviewed if row["system_abstained"].lower() == "false"]
    cited = [row for row in reviewed if row["citation_present"].lower() == "true"]
    reviewed_claims = [
        row for row in claim_rows if row["review_status"].lower() in {"reviewed", "adjudicated"}
    ]
    unanswerable = [row for row in reviewed if row["answerability_gold"].lower() == "unanswerable"]
    answerable = [row for row in reviewed if row["answerability_gold"].lower() == "answerable"]
    unanswerable_refusals = sum(row["system_abstained"].lower() == "true" for row in unanswerable)
    answerable_false_refusals = sum(row["system_abstained"].lower() == "true" for row in answerable)

    return {
        "answer_review": {
            "row_count": len(answer_rows),
            "reviewed_count": len(reviewed),
            "pending_count": len(answer_rows) - len(reviewed),
            "answer_correctness": _distribution([row["answer_correctness"].lower() for row in answered]),
            "faithfulness": _distribution([row["faithfulness"].lower() for row in answered]),
            "answer_relevance": _distribution([row["answer_relevance"].lower() for row in answered]),
            "citation_location_correctness": _distribution(
                [row["citation_location_correctness"].lower() for row in cited]
            ),
            "unanswerable_output_withheld_rate": _rate(unanswerable_refusals, len(unanswerable)),
            "answerable_output_withheld_rate": _rate(answerable_false_refusals, len(answerable)),
        },
        "claim_review": {
            "row_count": len(claim_rows),
            "reviewed_count": len(reviewed_claims),
            "pending_count": len(claim_rows) - len(reviewed_claims),
            "support_distribution": _distribution([row["support_label"].lower() for row in reviewed_claims]),
            "citation_location_correctness": _distribution(
                [
                    row["citation_location_correctness"].lower()
                    for row in reviewed_claims
                    if row["citation_present"].lower() == "true"
                ]
            ),
        },
        "interpretation": (
            "Descriptive human-review counts only; do not combine these dimensions into one score. "
            "Rates use reviewed rows and their stated denominators; the development pilot is not a holdout. "
            "Legacy review sheets record system_abstained without a refusal cause. Withheld-output rates "
            "cannot be interpreted as semantic refusal correctness; join the original generation statuses separately."
        ),
        "privacy_note": "Only IDs, labels, counts and rates are included; question, answer and source text are not serialized.",
    }
