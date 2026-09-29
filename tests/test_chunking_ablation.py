import pytest

from rag_hcmute.evaluation.chunking_ablation import (
    derive_gold_locations,
    matching_gold_chunk_ids,
)
from rag_hcmute.evaluation.run_pilot import PilotQuestion
from rag_hcmute.ingestion.chunk import Chunk


def _chunk(
    chunk_id: str,
    *,
    document_id: str = "DOC",
    page_start: int = 1,
    page_end: int = 1,
    section_path: str | None = None,
) -> Chunk:
    return Chunk(
        chunk_id=chunk_id,
        document_id=document_id,
        document_title="Test document",
        pdf_page_start=page_start,
        pdf_page_end=page_end,
        printed_page_start=None,
        printed_page_end=None,
        section_path=section_path,
        text="test evidence",
        token_count=2,
        text_sha256="test",
        chunk_method="test",
    )


def _question(
    *,
    question_id: str,
    document_id: str = "DOC",
    gold_ids: str = "GOLD",
) -> PilotQuestion:
    return PilotQuestion(
        question_id=question_id,
        question="test query",
        category="test",
        answerability="answerable",
        expected_document=document_id,
        expected_chunk_id=gold_ids,
        evidence_page="1",
    )


def test_structured_gold_maps_to_all_chunks_in_the_same_section() -> None:
    baseline = [_chunk("GOLD", section_path="Chương I > Điều 2")]
    question = _question(question_id="Q1")
    location = derive_gold_locations([question], baseline)["Q1"]

    candidates = [
        _chunk("A", section_path="Chương I > Điều 2"),
        _chunk("B", section_path="Chương I > Điều 2"),
        _chunk("C", section_path="Chương I > Điều 3"),
        _chunk("D", document_id="OTHER", section_path="Chương I > Điều 2"),
    ]

    assert location.section_paths == frozenset({"Chương I > Điều 2"})
    assert matching_gold_chunk_ids(candidates, location) == frozenset({"A", "B"})


def test_unstructured_gold_maps_by_source_page_range() -> None:
    baseline = [_chunk("GOLD", document_id="GUIDE", page_start=2, page_end=3)]
    question = _question(question_id="Q2", document_id="GUIDE")
    location = derive_gold_locations([question], baseline)["Q2"]

    candidates = [
        _chunk("A", document_id="GUIDE", page_start=1, page_end=2),
        _chunk("B", document_id="GUIDE", page_start=3, page_end=4),
        _chunk("C", document_id="GUIDE", page_start=4, page_end=4),
    ]

    assert location.section_paths == frozenset()
    assert location.pdf_pages == frozenset({2, 3})
    assert matching_gold_chunk_ids(candidates, location) == frozenset({"A", "B"})


def test_derive_gold_locations_rejects_missing_baseline_ids() -> None:
    question = _question(question_id="Q3", gold_ids="MISSING")

    with pytest.raises(ValueError, match=r"baseline gold chunk\(s\) not found"):
        derive_gold_locations([question], [])

