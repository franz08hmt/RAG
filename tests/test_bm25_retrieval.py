from pathlib import Path

import pytest

from rag_hcmute.ingestion.chunk import chunk_document
from rag_hcmute.ingestion.clean import clean_document_pages
from rag_hcmute.ingestion.extract import extract_pdf_pages
from rag_hcmute.retrieval.bm25_index import BM25Retriever

FIXTURE = Path(__file__).parent / "fixtures" / "sample_quy_dinh.pdf"


@pytest.fixture()
def retriever() -> BM25Retriever:
    pages = extract_pdf_pages(FIXTURE, "TEST_DOC")
    cleaned, _ = clean_document_pages(pages)
    chunks = chunk_document(cleaned, "TEST_DOC", "Quy dinh mau kiem thu")
    return BM25Retriever(chunks)


def test_unique_marker_query_retrieves_its_own_dieu_as_top1(retriever: BM25Retriever) -> None:
    result = retriever.query("MA_KIEM_THU_DIEU_MOT", top_k=3)
    assert result.hits[0].chunk_id == "TEST_DOC__c0001"
    assert result.hits[0].section_path == "Chương I > Điều 1"


def test_different_unique_marker_retrieves_different_dieu(retriever: BM25Retriever) -> None:
    result = retriever.query("MA_KIEM_THU_DIEU_BA", top_k=3)
    assert result.hits[0].chunk_id == "TEST_DOC__c0003"
    assert result.hits[0].section_path == "Chương II > Điều 3"


def test_natural_language_query_ranks_relevant_dieu_first(retriever: BM25Retriever) -> None:
    result = retriever.query("điều kiện được công nhận hoàn thành kiểm thử", top_k=3)
    assert result.hits[0].chunk_id == "TEST_DOC__c0003"


def test_top_k_is_respected(retriever: BM25Retriever) -> None:
    result = retriever.query("kiểm thử module", top_k=2)
    assert len(result.hits) == 2
    assert [hit.rank for hit in result.hits] == [1, 2]


def test_hits_carry_traceable_metadata_not_just_raw_text(retriever: BM25Retriever) -> None:
    result = retriever.query("MA_KIEM_THU_DIEU_MOT", top_k=1)
    hit = result.hits[0]
    assert hit.document_id == "TEST_DOC"
    assert hit.pdf_page_start >= 1
    assert hit.pdf_page_end >= hit.pdf_page_start
