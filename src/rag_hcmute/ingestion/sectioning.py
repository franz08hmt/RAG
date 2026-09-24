from __future__ import annotations

import re
from dataclasses import dataclass

from rag_hcmute.ingestion.extract import PageText

CHUONG_PATTERN = re.compile(r"^\s*Ch[uư]ơng\s+([IVXLCDM]+|\d+)\b\.?\s*(.*)$", re.IGNORECASE)
DIEU_PATTERN = re.compile(r"^\s*Đi[eề]u\s+(\d+)\s*[.:]?\s*(.*)$", re.IGNORECASE)
# 4 is deliberately conservative: a document that merely *quotes* one or two
# articles from another instrument (e.g. "Điều 5 Nghị định 20/2021/NĐ-CP...")
# should fall back to plain sliding-window chunking, not be treated as if it
# were itself organized by Điều. Seen in practice on HCMUTE_SOTAYSV_2024,
# which cites decree articles twice without being Điều-structured itself.
MIN_DIEU_MARKERS_FOR_STRUCTURED_DOC = 4


@dataclass
class SectionMarker:
    token_offset: int
    pdf_page: int
    chuong_label: str | None
    dieu_label: str | None
    dieu_title: str

    @property
    def section_path(self) -> str | None:
        parts = []
        if self.chuong_label:
            parts.append(f"Chương {self.chuong_label}")
        if self.dieu_label:
            parts.append(f"Điều {self.dieu_label}")
        return " > ".join(parts) if parts else None


def find_section_markers(pages: list[PageText], tokenize) -> list[SectionMarker]:
    # token_offset is accumulated per line (not per page) so that two Điều
    # headings on the same page still get distinct, correctly ordered offsets.
    # This relies on tokenize() being whitespace-based, so
    # sum(len(tokenize(line)) for line in text.splitlines()) == len(tokenize(text)).
    markers: list[SectionMarker] = []
    current_chuong: str | None = None
    token_offset = 0

    for page in pages:
        for raw_line in page.text.splitlines():
            line = raw_line.strip()
            if line:
                chuong_match = CHUONG_PATTERN.match(line)
                if chuong_match:
                    current_chuong = chuong_match.group(1)
                else:
                    dieu_match = DIEU_PATTERN.match(line)
                    if dieu_match:
                        markers.append(
                            SectionMarker(
                                token_offset=token_offset,
                                pdf_page=page.pdf_page,
                                chuong_label=current_chuong,
                                dieu_label=dieu_match.group(1),
                                dieu_title=dieu_match.group(2).strip(),
                            )
                        )
            token_offset += len(tokenize(raw_line))

    return markers


def is_document_structured(markers: list[SectionMarker]) -> bool:
    dieu_markers = [m for m in markers if m.dieu_label is not None]
    return len(dieu_markers) >= MIN_DIEU_MARKERS_FOR_STRUCTURED_DOC
