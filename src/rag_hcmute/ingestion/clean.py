from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass

from rag_hcmute.ingestion.extract import PageText

MULTI_BLANK_LINES = re.compile(r"\n{3,}")
MULTI_SPACES = re.compile(r"[ \t]{2,}")
MIN_PAGES_FOR_BOILERPLATE_DETECTION = 4
BOILERPLATE_MIN_LINE_LEN = 6


@dataclass
class CleanResult:
    document_id: str
    boilerplate_lines_removed: list[str]
    pages_cleaned: int


def _normalize_line(line: str) -> str:
    return re.sub(r"\s+", " ", line.strip())


def detect_boilerplate_lines(pages: list[PageText]) -> set[str]:
    if len(pages) < MIN_PAGES_FOR_BOILERPLATE_DETECTION:
        return set()

    line_counts: Counter[str] = Counter()
    for page in pages:
        seen_this_page: set[str] = set()
        for raw_line in page.text.splitlines():
            norm = _normalize_line(raw_line)
            if len(norm) < BOILERPLATE_MIN_LINE_LEN:
                continue
            if norm in seen_this_page:
                continue
            seen_this_page.add(norm)
            line_counts[norm] += 1

    threshold = max(3, int(0.4 * len(pages)))
    return {line for line, count in line_counts.items() if count >= threshold}


def clean_page_text(text: str, boilerplate: set[str]) -> str:
    kept_lines = []
    for raw_line in text.splitlines():
        norm = _normalize_line(raw_line)
        if norm in boilerplate:
            continue
        kept_lines.append(raw_line.rstrip())

    joined = "\n".join(kept_lines)
    joined = MULTI_SPACES.sub(" ", joined)
    joined = MULTI_BLANK_LINES.sub("\n\n", joined)
    return joined.strip("\n")


def clean_document_pages(pages: list[PageText]) -> tuple[list[PageText], CleanResult]:
    boilerplate = detect_boilerplate_lines(pages)
    cleaned_pages = []
    for page in pages:
        cleaned_text = clean_page_text(page.text, boilerplate)
        cleaned_pages.append(
            PageText(
                document_id=page.document_id,
                pdf_page=page.pdf_page,
                text=cleaned_text,
                char_count=len(cleaned_text.strip()),
                is_probable_scan=page.is_probable_scan,
                printed_page=page.printed_page,
                printed_page_confidence=page.printed_page_confidence,
                notes=list(page.notes),
            )
        )

    document_id = pages[0].document_id if pages else ""
    result = CleanResult(
        document_id=document_id,
        boilerplate_lines_removed=sorted(boilerplate),
        pages_cleaned=len(cleaned_pages),
    )
    return cleaned_pages, result
