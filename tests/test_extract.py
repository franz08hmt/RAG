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
    assert all(page.extraction_method == "native" for page in pages)
    assert all(page.ocr_confidence_mean is None for page in pages)


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


def test_ocr_fallback_runs_only_on_sparse_pages_with_images(tmp_path: Path, monkeypatch) -> None:
    import io

    import pymupdf
    from PIL import Image

    from rag_hcmute.ingestion import extract
    from rag_hcmute.ingestion.extract import OCRSettings

    image_buffer = io.BytesIO()
    Image.new("RGB", (120, 120), color="white").save(image_buffer, format="PNG")
    pdf_path = tmp_path / "scan.pdf"
    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842)
    page.insert_image(page.rect, stream=image_buffer.getvalue())
    doc.save(pdf_path)
    doc.close()

    calls = []

    def fake_ocr(page, settings):
        calls.append(page.number)
        return "Recognized local text", 88.5

    monkeypatch.setattr(extract, "_run_page_ocr", fake_ocr)
    settings = OCRSettings(language="vie", tessdata_dir=tmp_path)
    pages = extract_pdf_pages(pdf_path, "SCAN_DOC", ocr_settings=settings)

    assert calls == [0]
    assert pages[0].text == "Recognized local text"
    assert pages[0].extraction_method == "ocr"
    assert pages[0].ocr_confidence_mean == 88.5
    assert pages[0].is_probable_scan is True


def test_ocr_is_not_run_on_text_rich_pages_even_if_they_contain_images(
    tmp_path: Path, monkeypatch
) -> None:
    import io

    import pymupdf
    from PIL import Image

    from rag_hcmute.ingestion import extract
    from rag_hcmute.ingestion.extract import OCRSettings

    image_buffer = io.BytesIO()
    Image.new("RGB", (120, 120), color="white").save(image_buffer, format="PNG")
    pdf_path = tmp_path / "text_and_image.pdf"
    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842)
    page.insert_text((72, 72), "This page has enough native text to skip OCR.")
    page.insert_image(pymupdf.Rect(72, 100, 192, 220), stream=image_buffer.getvalue())
    doc.save(pdf_path)
    doc.close()

    def unexpected_ocr(*_args):
        raise AssertionError("OCR should not run on a text-rich page")

    monkeypatch.setattr(extract, "_run_page_ocr", unexpected_ocr)
    settings = OCRSettings(language="vie", tessdata_dir=tmp_path)
    pages = extract_pdf_pages(pdf_path, "TEXT_IMAGE_DOC", ocr_settings=settings)

    assert pages[0].extraction_method == "native"
    assert pages[0].ocr_confidence_mean is None
    assert "This page has enough native text" in pages[0].text


def test_full_page_scan_with_ocr_text_layer_is_flagged_and_can_be_forced_through_ocr(
    tmp_path: Path, monkeypatch
) -> None:
    import io

    import pymupdf
    from PIL import Image

    from rag_hcmute.ingestion import extract
    from rag_hcmute.ingestion.extract import OCRSettings

    image_buffer = io.BytesIO()
    Image.new("RGB", (120, 120), color="white").save(image_buffer, format="PNG")
    pdf_path = tmp_path / "scan_with_ocr_layer.pdf"
    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842)
    page.insert_image(page.rect, stream=image_buffer.getvalue())
    page.insert_text((72, 72), "This OCR text layer is readable but may be inaccurate.")
    doc.save(pdf_path)
    doc.close()

    calls = []

    def fake_ocr(page, settings):
        calls.append(page.number)
        return "Forced OCR output", 91.0

    monkeypatch.setattr(extract, "_run_page_ocr", fake_ocr)

    native_pages = extract_pdf_pages(pdf_path, "SCAN_WITH_OCR_LAYER")
    assert native_pages[0].is_probable_scan is True
    assert native_pages[0].extraction_method == "native"

    settings = OCRSettings(
        language="vie",
        tessdata_dir=tmp_path,
        ocr_full_page_images=True,
    )
    ocr_pages = extract_pdf_pages(
        pdf_path,
        "SCAN_WITH_OCR_LAYER",
        ocr_settings=settings,
    )

    assert calls == [0]
    assert ocr_pages[0].is_probable_scan is True
    assert ocr_pages[0].extraction_method == "ocr"
    assert ocr_pages[0].text == "Forced OCR output"
    assert ocr_pages[0].ocr_confidence_mean == 91.0
    assert any("phủ gần toàn trang" in note for note in ocr_pages[0].notes)


def test_blank_page_without_image_does_not_attempt_ocr(tmp_path: Path, monkeypatch) -> None:
    import pymupdf

    from rag_hcmute.ingestion import extract
    from rag_hcmute.ingestion.extract import OCRSettings

    pdf_path = tmp_path / "blank.pdf"
    doc = pymupdf.open()
    doc.new_page(width=595, height=842)
    doc.save(pdf_path)
    doc.close()

    def unexpected_ocr(*_args):
        raise AssertionError("A blank page without an image should not invoke OCR")

    monkeypatch.setattr(extract, "_run_page_ocr", unexpected_ocr)
    settings = OCRSettings(language="vie", tessdata_dir=tmp_path)
    pages = extract_pdf_pages(pdf_path, "BLANK_DOC", ocr_settings=settings)

    assert pages[0].is_probable_scan is True
    assert pages[0].extraction_method == "native"


def test_configure_tesseract_finds_executable_in_python_environment(tmp_path: Path, monkeypatch) -> None:
    import pytesseract

    from rag_hcmute.ingestion import extract
    from rag_hcmute.ingestion.extract import OCRSettings

    env_root = tmp_path / "env"
    executable = env_root / "Library" / "bin" / "tesseract.exe"
    executable.parent.mkdir(parents=True)
    executable.write_bytes(b"test executable placeholder")
    tessdata_dir = tmp_path / "tessdata"
    tessdata_dir.mkdir()
    (tessdata_dir / "vie.traineddata").write_bytes(b"test language data")

    monkeypatch.setattr(extract.sys, "prefix", str(env_root))
    monkeypatch.setattr(extract.shutil, "which", lambda _name: None)
    monkeypatch.setattr(pytesseract.pytesseract, "tesseract_cmd", "tesseract")

    pytesseract_module, model_path = extract._configure_tesseract(
        OCRSettings(language="vie", tessdata_dir=tessdata_dir)
    )

    assert pytesseract_module is pytesseract
    assert model_path.name == "vie.traineddata"
    assert Path(pytesseract.pytesseract.tesseract_cmd) == executable
