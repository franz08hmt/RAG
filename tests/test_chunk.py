from pathlib import Path

import pytest

from rag_hcmute.ingestion.chunk import chunk_document, tokenize
from rag_hcmute.ingestion.clean import clean_document_pages
from rag_hcmute.ingestion.extract import extract_pdf_pages
from rag_hcmute.ingestion.sectioning import find_section_markers, is_document_structured

FIXTURE = Path(__file__).parent / "fixtures" / "sample_quy_dinh.pdf"


def _find_sublist(haystack: list[str], needle: list[str]) -> int:
    if not needle:
        return 0
    n = len(needle)
    for i in range(len(haystack) - n + 1):
        if haystack[i : i + n] == needle:
            return i
    return -1


@pytest.fixture()
def cleaned_pages():
    pages = extract_pdf_pages(FIXTURE, "TEST_DOC")
    cleaned, _ = clean_document_pages(pages)
    return cleaned


@pytest.fixture()
def chunks(cleaned_pages):
    return chunk_document(cleaned_pages, "TEST_DOC", "Quy dinh mau kiem thu")


def test_document_is_detected_as_dieu_structured(cleaned_pages) -> None:
    markers = find_section_markers(cleaned_pages, tokenize)
    assert is_document_structured(markers)
    dieu_labels = [m.dieu_label for m in markers if m.dieu_label is not None]
    assert dieu_labels == ["1", "2", "3", "4", "5"]


def test_every_chunk_traces_back_to_its_declared_pdf_pages(cleaned_pages, chunks) -> None:
    pages_by_number = {p.pdf_page: p for p in cleaned_pages}

    for chunk in chunks:
        page_range = range(chunk.pdf_page_start, chunk.pdf_page_end + 1)
        source_tokens: list[str] = []
        for page_number in page_range:
            source_tokens.extend(tokenize(pages_by_number[page_number].text))

        chunk_tokens = tokenize(chunk.text)
        position = _find_sublist(source_tokens, chunk_tokens)
        assert position != -1, (
            f"{chunk.chunk_id}: khong the truy nguoc noi dung chunk ve dung cac "
            f"trang PDF {chunk.pdf_page_start}-{chunk.pdf_page_end} da khai bao"
        )


def test_chunk_ids_are_stable_across_reruns(cleaned_pages) -> None:
    first_run = chunk_document(cleaned_pages, "TEST_DOC", "Quy dinh mau kiem thu")
    second_run = chunk_document(cleaned_pages, "TEST_DOC", "Quy dinh mau kiem thu")
    assert [c.chunk_id for c in first_run] == [c.chunk_id for c in second_run]
    assert [c.text_sha256 for c in first_run] == [c.text_sha256 for c in second_run]


def test_dieu_boundaries_are_preserved_as_single_chunks_when_short(chunks) -> None:
    section_paths = {c.section_path for c in chunks if c.section_path}
    assert "Chương I > Điều 1" in section_paths
    assert "Chương II > Điều 3" in section_paths

    dieu_1_chunks = [c for c in chunks if c.section_path == "Chương I > Điều 1"]
    assert len(dieu_1_chunks) == 1
    assert dieu_1_chunks[0].chunk_method == "dieu_bounded_single"


def test_magic_strings_land_in_the_expected_dieu_chunk(chunks) -> None:
    chunk_with_ma_mot = next(c for c in chunks if "MA_KIEM_THU_DIEU_MOT" in c.text)
    assert chunk_with_ma_mot.section_path == "Chương I > Điều 1"

    chunk_with_ma_ba = next(c for c in chunks if "MA_KIEM_THU_DIEU_BA" in c.text)
    assert chunk_with_ma_ba.section_path == "Chương II > Điều 3"
