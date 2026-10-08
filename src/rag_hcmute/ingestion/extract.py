from __future__ import annotations

import hashlib
import json
import re
import shutil
import statistics
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

import pymupdf

MIN_TEXT_CHARS_FOR_NON_SCAN = 15
FOOTER_HEADER_SCAN_LINES = 3
PRINTED_PAGE_PATTERNS = (
    re.compile(r"^\s*(\d{1,4})\s*$"),
    re.compile(r"^\s*[Tt]rang\s+(\d{1,4})\s*(?:/\s*\d{1,4})?\s*$"),
    re.compile(r"^\s*-\s*(\d{1,4})\s*-\s*$"),
)


@dataclass
class PageText:
    document_id: str
    pdf_page: int
    text: str
    char_count: int
    is_probable_scan: bool
    printed_page: int | None
    printed_page_confidence: str
    notes: list[str] = field(default_factory=list)
    extraction_method: str = "native"
    ocr_confidence_mean: float | None = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class OCRSettings:
    language: str
    tessdata_dir: Path
    tesseract_cmd: Path | None = None
    dpi: int = 200
    page_segmentation_mode: int = 6
    minimum_native_chars: int = MIN_TEXT_CHARS_FOR_NON_SCAN
    ocr_full_page_images: bool = False

    def __post_init__(self) -> None:
        if not self.language.strip():
            raise ValueError("OCR language must not be empty.")
        if self.dpi < 72:
            raise ValueError("OCR DPI must be at least 72.")
        if not 0 <= self.page_segmentation_mode <= 13:
            raise ValueError("Tesseract page segmentation mode must be between 0 and 13.")
        if self.minimum_native_chars < 0:
            raise ValueError("Minimum native-text threshold must not be negative.")


def _configure_tesseract(settings: OCRSettings):
    import pytesseract

    model_path = settings.tessdata_dir / f"{settings.language}.traineddata"
    if not model_path.is_file():
        raise FileNotFoundError(f"OCR language model not found: {model_path}")
    tesseract_cmd = _resolve_tesseract_cmd(settings)
    pytesseract.pytesseract.tesseract_cmd = str(tesseract_cmd)
    return pytesseract, model_path


def _resolve_tesseract_cmd(settings: OCRSettings) -> Path:
    if settings.tesseract_cmd is not None:
        if not settings.tesseract_cmd.is_file():
            raise FileNotFoundError(f"Tesseract executable not found: {settings.tesseract_cmd}")
        return settings.tesseract_cmd

    # Calling an env's python.exe directly does not necessarily activate its
    # Library/bin (Windows) or bin (Unix) directory on PATH.
    executable_names = ("tesseract.exe", "tesseract") if sys.platform == "win32" else ("tesseract",)
    env_candidates = (
        Path(sys.prefix) / "Library" / "bin" / executable_names[0],
        Path(sys.prefix) / "bin" / executable_names[-1],
    )
    for candidate in env_candidates:
        if candidate.is_file():
            return candidate

    on_path = shutil.which("tesseract")
    if on_path:
        return Path(on_path)
    raise FileNotFoundError(
        "Tesseract executable not found. Install it in the active environment, "
        "add it to PATH, or pass --tesseract-cmd."
    )


def ocr_settings_metadata(settings: OCRSettings) -> dict[str, object]:
    """Return reproducibility metadata without recording local executable paths."""
    pytesseract, model_path = _configure_tesseract(settings)
    digest = hashlib.sha256(model_path.read_bytes()).hexdigest()
    return {
        "enabled": True,
        "engine": "tesseract",
        "engine_version": str(pytesseract.get_tesseract_version()),
        "language": settings.language,
        "dpi": settings.dpi,
        "page_segmentation_mode": settings.page_segmentation_mode,
        "minimum_native_chars": settings.minimum_native_chars,
        "ocr_full_page_images": settings.ocr_full_page_images,
        "traineddata_sha256": digest,
    }


def _page_has_images(page: pymupdf.Page) -> bool:
    try:
        return bool(page.get_images(full=True))
    except Exception:
        return False


def _page_has_full_page_image(page: pymupdf.Page, minimum_area_ratio: float = 0.70) -> bool:
    """Detect a page-sized raster, including scans that already carry noisy OCR text."""
    try:
        page_area = page.rect.get_area()
        if page_area <= 0:
            return False
        for image_info in page.get_image_info(xrefs=True):
            image_rect = pymupdf.Rect(image_info["bbox"]) & page.rect
            if image_rect.get_area() / page_area >= minimum_area_ratio:
                return True
    except Exception:
        return False
    return False


def _run_page_ocr(page: pymupdf.Page, settings: OCRSettings) -> tuple[str, float | None]:
    pytesseract, _ = _configure_tesseract(settings)
    from PIL import Image

    pixmap = page.get_pixmap(dpi=settings.dpi, colorspace=pymupdf.csRGB, alpha=False)
    image = Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)
    config = f"--tessdata-dir {settings.tessdata_dir} --psm {settings.page_segmentation_mode}"
    data = pytesseract.image_to_data(
        image,
        lang=settings.language,
        config=config,
        output_type=pytesseract.Output.DICT,
    )

    text_parts: list[str] = []
    confidences: list[float] = []
    previous_line: tuple[int, int, int] | None = None
    for index, raw_word in enumerate(data["text"]):
        word = raw_word.strip()
        try:
            confidence = float(data["conf"][index])
        except (TypeError, ValueError):
            continue
        if not word or confidence < 0:
            continue

        line_key = (
            int(data["block_num"][index]),
            int(data["par_num"][index]),
            int(data["line_num"][index]),
        )
        if previous_line is not None:
            text_parts.append("\n\n" if line_key[:2] != previous_line[:2] else "\n" if line_key != previous_line else " ")
        text_parts.append(word)
        confidences.append(confidence)
        previous_line = line_key

    text = "".join(text_parts).strip()
    mean_confidence = statistics.fmean(confidences) if confidences else None
    return text, round(mean_confidence, 2) if mean_confidence is not None else None


def _detect_printed_page(text: str) -> tuple[int | None, str]:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if not lines:
        return None, "khong_xac_dinh"

    candidates = lines[-FOOTER_HEADER_SCAN_LINES:] + lines[:FOOTER_HEADER_SCAN_LINES]
    for line in candidates:
        for pattern in PRINTED_PAGE_PATTERNS:
            match = pattern.match(line)
            if match:
                value = int(match.group(1))
                if 0 < value < 2000:
                    return value, "heuristic_footer_header"
    return None, "khong_xac_dinh"


def _is_probable_scan(page: pymupdf.Page, text: str) -> bool:
    stripped_len = len(text.strip())
    if _page_has_full_page_image(page):
        return True
    if stripped_len >= MIN_TEXT_CHARS_FOR_NON_SCAN:
        return False
    has_images = _page_has_images(page)
    return has_images or stripped_len == 0


def extract_pdf_pages(
    pdf_path: Path,
    document_id: str,
    *,
    ocr_settings: OCRSettings | None = None,
) -> list[PageText]:
    pages: list[PageText] = []
    with pymupdf.open(pdf_path) as doc:
        for index in range(doc.page_count):
            page = doc.load_page(index)
            native_text = page.get_text("text")
            selected_text = native_text
            extraction_method = "native"
            ocr_confidence_mean: float | None = None
            notes: list[str] = []

            has_images = _page_has_images(page)
            has_full_page_image = _page_has_full_page_image(page)
            probable_scan = _is_probable_scan(page, native_text)
            ocr_candidate = (
                ocr_settings is not None
                and has_images
                and (
                    len(native_text.strip()) < ocr_settings.minimum_native_chars
                    or (ocr_settings.ocr_full_page_images and has_full_page_image)
                )
            )
            if ocr_candidate and ocr_settings is not None:
                ocr_text, ocr_confidence_mean = _run_page_ocr(page, ocr_settings)
                if ocr_text:
                    selected_text = ocr_text
                    extraction_method = "ocr"
                    if has_full_page_image and ocr_settings.ocr_full_page_images:
                        notes.append("OCR local được bật cho trang có ảnh phủ gần toàn trang.")
                    else:
                        notes.append("OCR local áp dụng do trang có ít text native và có ảnh raster.")
                else:
                    notes.append("OCR cục bộ không tạo được văn bản; giữ kết quả trích xuất native.")

            printed_page, confidence = _detect_printed_page(selected_text)
            if has_full_page_image:
                notes.append("Ảnh raster phủ gần toàn trang; có thể là bản scan hoặc trang có lớp OCR, cần kiểm tra.")
            elif probable_scan and len(native_text.strip()) == 0:
                notes.append("Trang không trích xuất được text (nghi PDF scan hoặc trang trống).")
            elif probable_scan:
                notes.append("Text trích xuất rất ít so với hình ảnh trên trang (nghi PDF scan một phần).")

            if printed_page is None:
                notes.append("Không xác định được số trang in trên văn bản (đã kiểm tra header/footer).")

            pages.append(
                PageText(
                    document_id=document_id,
                    pdf_page=index + 1,
                    text=selected_text,
                    char_count=len(selected_text.strip()),
                    is_probable_scan=probable_scan,
                    printed_page=printed_page,
                    printed_page_confidence=confidence,
                    notes=notes,
                    extraction_method=extraction_method,
                    ocr_confidence_mean=ocr_confidence_mean,
                )
            )
    return pages


def write_pages_jsonl(pages: list[PageText], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as stream:
        for page in pages:
            stream.write(json.dumps(page.to_dict(), ensure_ascii=False))
            stream.write("\n")


def read_pages_jsonl(input_path: Path) -> list[PageText]:
    pages: list[PageText] = []
    with input_path.open("r", encoding="utf-8") as stream:
        for line in stream:
            line = line.strip()
            if not line:
                continue
            data = json.loads(line)
            pages.append(PageText(**data))
    return pages
