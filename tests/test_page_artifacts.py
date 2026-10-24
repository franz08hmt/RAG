import io
from pathlib import Path

import pymupdf
import pytest
from PIL import Image

from rag_hcmute.ingestion.page_artifacts import inspect_page, rectangle_union_area, render_source_crop


def _image() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (32, 32), "white").save(buffer, format="PNG")
    return buffer.getvalue()


def test_union_does_not_double_count_images():
    assert rectangle_union_area([[0, 0, 10, 10], [5, 0, 15, 10]]) == 150
    assert rectangle_union_area([]) == 0


def test_native_text_and_logo_is_not_classified_as_full_page_raster():
    with pymupdf.open() as doc:
        page = doc.new_page(width=400, height=500)
        page.insert_text((20, 40), "Enough native document text for a normal text page.")
        page.insert_image(pymupdf.Rect(20, 80, 60, 120), stream=_image())
        item = inspect_page(page, "TEST", "a" * 64)
    assert item.routing_hint == "native_text_and_images"
    assert item.raster_coverage_ratio == 0.008
    assert item.visual_semantics_status == "not_interpreted"
    assert item.text_blocks[0]["artifact_id"] == "TEST__p001__text001"
    assert "Enough native" not in str(item.to_dict())


def test_scan_with_existing_text_layer_is_still_marked_for_review():
    with pymupdf.open() as doc:
        page = doc.new_page(width=400, height=500)
        page.insert_image(page.rect, stream=_image(), keep_proportion=False)
        page.insert_text((20, 40), "Existing OCR text does not prove scan quality.")
        item = inspect_page(page, "SCAN", "b" * 64)
    assert item.raster_coverage_ratio == 1
    assert item.routing_hint == "raster_dominant_with_text_layer_review"


def test_tiled_scan_uses_union_of_image_rectangles():
    with pymupdf.open() as doc:
        page = doc.new_page(width=400, height=500)
        page.insert_image(pymupdf.Rect(0, 0, 400, 250), stream=_image(), keep_proportion=False)
        page.insert_image(pymupdf.Rect(0, 250, 400, 500), stream=_image(), keep_proportion=False)
        item = inspect_page(page, "TILES", "c" * 64)
    assert len(item.raster_images) == 2
    assert item.raster_coverage_ratio == 1
    assert item.routing_hint == "raster_dominant_sparse_text_review"


def test_blank_is_not_asserted_to_be_scan():
    with pymupdf.open() as doc:
        item = inspect_page(doc.new_page(), "BLANK", "d" * 64)
    assert item.routing_hint == "blank_or_unextractable_review"


def test_candidate_table_carries_page_geometry_not_values():
    with pymupdf.open() as doc:
        page = doc.new_page(width=400, height=500)
        for x in [20, 100, 180]:
            page.draw_line((x, 50), (x, 150))
        for y in [50, 100, 150]:
            page.draw_line((20, y), (180, y))
        for point, value in [((30, 75), "A"), ((110, 75), "B"), ((30, 125), "C"), ((110, 125), "D")]:
            page.insert_text(point, value)
        item = inspect_page(page, "TABLE", "e" * 64)
    table = item.table_candidates[0]
    assert table["row_count"] == table["column_count"] == 2
    assert table["cell_slots"] == 4
    assert table["status"] == "candidate_requires_visual_review"
    assert len(table["cell_bboxes"]) == 4


def test_render_keeps_source_page_and_refuses_overwrite(tmp_path: Path):
    with pymupdf.open() as doc:
        page = doc.new_page(width=400, height=500)
        page.insert_text((20, 40), "REAL SOURCE")
        path = tmp_path / "source.png"
        rendered = render_source_crop(page, [0, 0, 200, 100], path, dpi=144)
        assert rendered["width_pixels"] == 400
        assert rendered["height_pixels"] == 200
        assert rendered["pdf_page"] == 1
        assert rendered["semantic_description_generated"] is False
        with pytest.raises(FileExistsError):
            render_source_crop(page, [0, 0, 200, 100], path)


def test_rotated_pages_fail_explicitly_instead_of_wrong_geometry():
    with pymupdf.open() as doc:
        page = doc.new_page()
        page.set_rotation(90)
        with pytest.raises(ValueError, match="coordinate transform"):
            inspect_page(page, "ROTATED", "f" * 64)
