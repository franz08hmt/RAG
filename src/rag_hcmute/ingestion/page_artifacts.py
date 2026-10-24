"""Page-level input triage and provenance, without claiming visual understanding.

Records contain geometry, counts and hashes only. Native text, raster images,
table values and any OCR remain local; a candidate table is not a verified table.
"""
from __future__ import annotations

import hashlib
import math
import re
from dataclasses import asdict, dataclass
from pathlib import Path

import pymupdf


def _box(rect) -> list[float]:
    return [round(float(value), 3) for value in rect]


def rectangle_union_area(rectangles: list[list[float]]) -> float:
    """Measure covered page area without double-counting overlapping images."""
    xs = sorted({value for box in rectangles for value in (box[0], box[2])})
    area = 0.0
    for left, right in zip(xs, xs[1:]):
        intervals = sorted((b[1], b[3]) for b in rectangles if b[0] < right and b[2] > left)
        if not intervals:
            continue
        low, high = intervals[0]
        length = 0.0
        for next_low, next_high in intervals[1:]:
            if next_low > high:
                length += high - low
                low, high = next_low, next_high
            else:
                high = max(high, next_high)
        area += (right - left) * (length + high - low)
    return area


@dataclass(frozen=True)
class PageArtifacts:
    document_id: str
    source_sha256: str
    pdf_page: int
    page_size_points: list[float]
    native_character_count: int
    text_blocks: list[dict]
    raster_images: list[dict]
    raster_coverage_ratio: float
    vector_drawing_count: int
    table_candidates: list[dict]
    table_detection_error: str | None
    routing_hint: str
    visual_semantics_status: str = "not_interpreted"
    extraction_method: str = "pymupdf_native_geometry"

    def to_dict(self) -> dict:
        return asdict(self)


def inspect_page(page: pymupdf.Page, document_id: str, source_sha256: str) -> PageArtifacts:
    if not re.fullmatch(r"[A-Za-z0-9_-]+", document_id):
        raise ValueError("document_id must contain only letters, digits, '_' and '-'.")
    if not re.fullmatch(r"[a-f0-9]{64}", source_sha256):
        raise ValueError("source_sha256 must be a lowercase SHA-256 digest.")
    # Unrotated MuPDF page coordinates (points) are the geometry contract.
    if page.rotation:
        raise ValueError("Rotated PDF pages need an explicit coordinate transform before artifact extraction.")
    page_number = page.number + 1
    prefix = f"{document_id}__p{page_number:03d}"
    text = page.get_text("text")
    blocks = []
    for block in page.get_text("blocks"):
        if block[6] != 0:
            continue
        blocks.append({
            "artifact_id": f"{prefix}__text{len(blocks) + 1:03d}",
            "bbox_points": _box(block[:4]),
            "character_count": len(block[4].strip()),
            "text_sha256": hashlib.sha256(block[4].encode("utf-8")).hexdigest(),
        })

    images = []
    page_area = page.rect.get_area()
    for info in page.get_image_info(xrefs=True):
        clipped = pymupdf.Rect(info["bbox"]) & page.rect
        if clipped.is_empty or clipped.is_infinite or not all(math.isfinite(value) for value in clipped):
            continue
        images.append({
            "artifact_id": f"{prefix}__image{len(images) + 1:03d}",
            "bbox_points": _box(clipped),
            "width_pixels": info["width"],
            "height_pixels": info["height"],
            "xref": info.get("xref", 0),
            "area_ratio": round(clipped.get_area() / page_area, 6),
            "semantic_status": "not_interpreted",
        })
    coverage = min(1.0, rectangle_union_area([row["bbox_points"] for row in images]) / page_area)

    tables, table_error = [], None
    try:
        for index, table in enumerate(page.find_tables().tables, start=1):
            rows = table.extract()
            tables.append({
                "artifact_id": f"{prefix}__table{index:03d}",
                "bbox_points": _box(table.bbox),
                "row_count": table.row_count,
                "column_count": table.col_count,
                "cell_slots": sum(len(row) for row in rows),
                "null_cell_count": sum(cell is None for row in rows for cell in row),
                "empty_string_cell_count": sum(cell == "" for row in rows for cell in row),
                "cell_bboxes": [None if cell is None else _box(cell) for row in table.rows for cell in row.cells],
                "status": "candidate_requires_visual_review",
            })
    except Exception as error:
        # Preserve the failure without leaking text from arbitrary exception messages.
        table_error = type(error).__name__

    native_count = len(text.strip())
    drawings = len(page.get_drawings())
    if coverage >= 0.70:
        hint = "raster_dominant_with_text_layer_review" if native_count >= 15 else "raster_dominant_sparse_text_review"
    elif images and native_count < 15:
        hint = "sparse_text_with_images_review"
    elif images:
        hint = "native_text_and_images"
    elif native_count >= 15:
        hint = "native_text"
    else:
        hint = "vector_or_blank_review" if drawings else "blank_or_unextractable_review"
    return PageArtifacts(
        document_id=document_id, source_sha256=source_sha256, pdf_page=page_number,
        page_size_points=[page.rect.width, page.rect.height], native_character_count=native_count,
        text_blocks=blocks, raster_images=images, raster_coverage_ratio=round(coverage, 6),
        vector_drawing_count=drawings, table_candidates=tables,
        table_detection_error=table_error, routing_hint=hint,
    )


def render_source_crop(page: pymupdf.Page, bbox: list[float], output_path: Path, *, dpi: int = 180) -> dict:
    """Render a real source region for local review; never draw fabricated OCR."""
    if dpi < 72 or dpi > 600:
        raise ValueError("dpi must be between 72 and 600.")
    if page.rotation:
        raise ValueError("Rotated pages require an explicit coordinate transform.")
    clip = pymupdf.Rect(bbox) & page.rect
    if clip.is_empty or clip.is_infinite or not all(math.isfinite(value) for value in clip):
        raise ValueError("bbox does not intersect the source page.")
    if output_path.exists():
        raise FileExistsError(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    pixmap = page.get_pixmap(dpi=dpi, clip=clip, alpha=False)
    pixmap.save(output_path)
    return {
        "pdf_page": page.number + 1, "bbox_points": _box(clip), "dpi": dpi,
        "width_pixels": pixmap.width, "height_pixels": pixmap.height,
        "png_sha256": hashlib.sha256(output_path.read_bytes()).hexdigest(),
        "kind": "rendered_source_crop", "semantic_description_generated": False,
    }
