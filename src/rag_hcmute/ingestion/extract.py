from __future__ import annotations

import json
import re
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

    def to_dict(self) -> dict:
        return asdict(self)


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
    if stripped_len >= MIN_TEXT_CHARS_FOR_NON_SCAN:
        return False
    try:
        has_images = len(page.get_images(full=True)) > 0
    except Exception:
        has_images = False
    return has_images or stripped_len == 0


def extract_pdf_pages(pdf_path: Path, document_id: str) -> list[PageText]:
    pages: list[PageText] = []
    with pymupdf.open(pdf_path) as doc:
        for index in range(doc.page_count):
            page = doc.load_page(index)
            raw_text = page.get_text("text")
            printed_page, confidence = _detect_printed_page(raw_text)
            notes: list[str] = []

            probable_scan = _is_probable_scan(page, raw_text)
            if probable_scan and len(raw_text.strip()) == 0:
                notes.append("Trang không trích xuất được text (nghi PDF scan hoặc trang trống).")
            elif probable_scan:
                notes.append("Text trích xuất rất ít so với hình ảnh trên trang (nghi PDF scan một phần).")

            if printed_page is None:
                notes.append("Không xác định được số trang in trên văn bản (đã kiểm tra header/footer).")

            pages.append(
                PageText(
                    document_id=document_id,
                    pdf_page=index + 1,
                    text=raw_text,
                    char_count=len(raw_text.strip()),
                    is_probable_scan=probable_scan,
                    printed_page=printed_page,
                    printed_page_confidence=confidence,
                    notes=notes,
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
