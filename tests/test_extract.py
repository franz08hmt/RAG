from pathlib import Path

from rag_hcmute.ingestion.extract import extract_pdf_pages

FIXTURE = Path(__file__).parent / "fixtures" / "sample_quy_dinh.pdf"


def test_extract_returns_one_entry_per_pdf_page() -> None:
    pages = extract_pdf_pages(FIXTURE, "TEST_DOC")
    assert len(pages) == 3
    assert [p.pdf_page for p in pages] == [1, 2, 3]


def test_extract_finds_known_text_on_expected_page() -> None:
    pages = extract_pdf_pages(FIXTURE, "TEST_DOC")
    assert "MA_KIEM_THU_DIEU_MOT" in pages[0].text
    assert "MA_KIEM_THU_DIEU_BA" in pages[1].text


def test_extract_detects_printed_page_number_from_footer() -> None:
    pages = extract_pdf_pages(FIXTURE, "TEST_DOC")
    assert pages[0].printed_page is None
    assert pages[1].printed_page == 2
    assert pages[2].printed_page == 3


def test_extract_does_not_flag_normal_text_pages_as_scan() -> None:
    pages = extract_pdf_pages(FIXTURE, "TEST_DOC")
    assert all(not p.is_probable_scan for p in pages)


def test_extract_flags_blank_page_as_probable_scan(tmp_path: Path) -> None:
    import pymupdf

    blank_pdf = tmp_path / "blank.pdf"
    doc = pymupdf.open()
    doc.new_page(width=595, height=842)
    doc.save(blank_pdf)
    doc.close()

    pages = extract_pdf_pages(blank_pdf, "BLANK_DOC")
    assert len(pages) == 1
    assert pages[0].is_probable_scan is True
    assert pages[0].char_count == 0
