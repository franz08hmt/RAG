from __future__ import annotations

import csv
import json

import pytest

from rag_hcmute.evaluation.manual_review import (
    ANSWER_FIELDS,
    CLAIM_FIELDS,
    load_answer_reviews,
    load_claim_reviews,
    prepare_review_sheets,
    summarize_manual_reviews,
    write_private_review_bundle,
)


def _write_csv(path, fields, rows):
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def _answer(**overrides):
    row = {
        "run_id": "run-1",
        "snapshot_id": "snapshot-1",
        "partition": "development",
        "question_id": "Q001",
        "answerability_gold": "answerable",
        "system_abstained": "false",
        "answer_correctness": "correct",
        "faithfulness": "fully_supported",
        "answer_relevance": "direct",
        "citation_present": "true",
        "citation_location_correctness": "correct",
        "review_status": "reviewed",
    }
    row.update(overrides)
    return row


def _claim(**overrides):
    row = {
        "run_id": "run-1",
        "question_id": "Q001",
        "claim_id": "C01",
        "support_label": "supported",
        "citation_present": "true",
        "citation_location_correctness": "correct",
        "review_status": "reviewed",
    }
    row.update(overrides)
    return row


def test_manual_review_summary_keeps_dimensions_and_denominators_separate(tmp_path):
    answers_path = tmp_path / "answers.csv"
    claims_path = tmp_path / "claims.csv"
    _write_csv(
        answers_path,
        ANSWER_FIELDS,
        [
            _answer(),
            _answer(
                question_id="Q002",
                answerability_gold="unanswerable",
                system_abstained="true",
                answer_correctness="not_applicable",
                faithfulness="not_applicable",
                answer_relevance="not_applicable",
                citation_present="false",
                citation_location_correctness="not_applicable",
            ),
            _answer(
                question_id="Q003",
                answerability_gold="unanswerable",
                system_abstained="false",
                answer_correctness="incorrect",
                faithfulness="unsupported",
                answer_relevance="direct",
                citation_location_correctness="incorrect",
            ),
            _answer(
                question_id="Q004",
                answerability_gold="answerable",
                system_abstained="true",
                answer_correctness="not_applicable",
                faithfulness="not_applicable",
                answer_relevance="not_applicable",
                citation_present="false",
                citation_location_correctness="not_applicable",
            ),
        ],
    )
    _write_csv(
        claims_path,
        CLAIM_FIELDS,
        [
            _claim(),
            _claim(claim_id="C02", support_label="partially_supported"),
        ],
    )

    answers = load_answer_reviews(answers_path)
    claims = load_claim_reviews(claims_path)
    summary = summarize_manual_reviews(answers, claims)

    answer_summary = summary["answer_review"]
    assert answer_summary["unanswerable_refusal_rate"] == {"count": 1, "denominator": 2, "value": 0.5}
    assert answer_summary["answerable_false_refusal_rate"] == {"count": 1, "denominator": 2, "value": 0.5}
    assert answer_summary["answer_correctness"]["counts"] == {"correct": 1, "incorrect": 1}
    assert summary["claim_review"]["support_distribution"]["counts"] == {
        "partially_supported": 1,
        "supported": 1,
    }
    assert "overall_score" not in summary


def test_pending_rows_may_leave_human_labels_blank(tmp_path):
    path = tmp_path / "pending.csv"
    row = _answer(
        answer_correctness="",
        faithfulness="",
        answer_relevance="",
        citation_location_correctness="",
        review_status="pending",
    )
    _write_csv(path, ANSWER_FIELDS, [row])

    loaded = load_answer_reviews(path)
    assert loaded[0]["review_status"] == "pending"
    summary = summarize_manual_reviews(loaded, [])
    assert summary["answer_review"]["pending_count"] == 1
    assert summary["answer_review"]["answer_correctness"]["denominator"] == 0


def test_csv_schema_rejects_free_text_columns(tmp_path):
    path = tmp_path / "unsafe.csv"
    _write_csv(path, (*ANSWER_FIELDS, "answer_text"), [])

    with pytest.raises(ValueError, match="không thêm cột tự do"):
        load_answer_reviews(path)


def test_duplicate_answer_keys_are_rejected(tmp_path):
    path = tmp_path / "duplicates.csv"
    _write_csv(path, ANSWER_FIELDS, [_answer(), _answer()])

    with pytest.raises(ValueError, match="Trùng run_id/question_id"):
        load_answer_reviews(path)


def test_claim_must_match_answer_and_cannot_be_attached_to_refusal():
    abstained = _answer(
        system_abstained="true",
        answer_correctness="not_applicable",
        faithfulness="not_applicable",
        answer_relevance="not_applicable",
        citation_present="false",
        citation_location_correctness="not_applicable",
    )
    with pytest.raises(ValueError, match="Không ghi claim"):
        summarize_manual_reviews([abstained], [_claim()])
    with pytest.raises(ValueError, match="không khớp"):
        summarize_manual_reviews([_answer()], [_claim(question_id="Q999")])


def test_private_bundle_refuses_repository_paths_and_never_overwrites(tmp_path):
    repository = tmp_path / "repo"
    repository.mkdir()
    with pytest.raises(ValueError, match="ngoài thư mục repository"):
        write_private_review_bundle(
            repository / "artifacts",
            project_root=repository,
            run_id="run-1",
            snapshot_id="snap",
            partition="development",
            method="hybrid",
            generator={"model": "local"},
            records=[],
        )
    output = write_private_review_bundle(
        tmp_path / "private_eval",
        project_root=repository,
        run_id="run-2",
        snapshot_id="snap",
        partition="development",
        method="hybrid",
        generator={"model": "local"},
        records=[{"question_id": "Q1", "answer": "private answer", "retrieved_sources": []}],
    )
    payload = json.loads(output.read_text(encoding="utf-8").strip())
    assert payload["answer"] == "private answer"
    assert payload["snapshot_id"] == "snap"
    with pytest.raises(FileExistsError):
        write_private_review_bundle(
            tmp_path / "private_eval",
            project_root=repository,
            run_id="run-2",
            snapshot_id="snap",
            partition="development",
            method="hybrid",
            generator={"model": "local"},
            records=[],
        )


def test_prepare_review_sheets_copy_only_ids_and_machine_metadata(tmp_path):
    repository = tmp_path / "repo"
    repository.mkdir()
    bundle = tmp_path / "private.jsonl"
    record = {
        "run_id": "run-1",
        "snapshot_id": "snapshot-1",
        "partition": "development",
        "question_id": "Q001",
        "question": "Private question text",
        "answerability_gold": "answerable",
        "system_abstained": False,
        "answer": "Private answer text",
        "citation_ids": ["S1"],
        "retrieved_sources": [{"text": "Private source passage"}],
    }
    bundle.write_text(json.dumps(record, ensure_ascii=False) + "\n", encoding="utf-8")

    answers_path, claims_path, row_count = prepare_review_sheets(
        bundle,
        output_root=tmp_path / "private-output",
        project_root=repository,
    )
    answer_content = answers_path.read_text(encoding="utf-8-sig")
    claim_content = claims_path.read_text(encoding="utf-8-sig")
    loaded = load_answer_reviews(answers_path)

    assert row_count == 1
    assert loaded[0]["review_status"] == "pending"
    assert loaded[0]["citation_present"] == "true"
    assert "Private question text" not in answer_content
    assert "Private answer text" not in answer_content
    assert "Private source passage" not in answer_content + claim_content
    assert claim_content.strip() == ",".join(CLAIM_FIELDS)


def test_manual_summary_rejects_mixed_runs():
    with pytest.raises(ValueError, match="một run_id"):
        summarize_manual_reviews(
            [_answer(), _answer(run_id="run-2")],
            [],
        )
