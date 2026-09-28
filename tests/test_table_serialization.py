import pytest

from rag_hcmute.ingestion.tables import (
    TableProvenance,
    table_as_markdown,
    table_as_row_records,
)


@pytest.fixture()
def provenance() -> TableProvenance:
    return TableProvenance(
        document_id="TEST_DOC",
        pdf_page=3,
        table_id="table_01",
        title="Bảng kiểm thử",
    )


def test_markdown_keeps_source_location_headers_and_empty_cells(provenance) -> None:
    result = table_as_markdown(
        provenance,
        headers=["Nhóm", "Mức"],
        rows=[["A", "1"], [None, "2"]],
    )

    assert "Tài liệu: TEST_DOC" in result
    assert "Trang PDF: 3" in result
    assert "Tiêu đề bảng: Bảng kiểm thử" in result
    assert "| Nhóm | Mức |" in result
    assert "|  | 2 |" in result


def test_markdown_escapes_pipe_and_normalizes_multiline_cells(provenance) -> None:
    result = table_as_markdown(
        provenance,
        headers=["Nội dung"],
        rows=[["trái | phải\n dòng tiếp theo"]],
    )

    assert r"trái \| phải dòng tiếp theo" in result


def test_row_records_are_stable_and_do_not_forward_fill_blank_merged_cells(provenance) -> None:
    records = table_as_row_records(
        provenance,
        headers=["Nhóm", "Điều kiện"],
        rows=[["A", "Điều kiện thứ nhất"], [None, "Điều kiện thứ hai"]],
    )

    assert [record.chunk_id for record in records] == [
        "TEST_DOC__table_01__row001",
        "TEST_DOC__table_01__row002",
    ]
    assert "Nhóm: A" in records[0].text
    assert "Nhóm: A" not in records[1].text
    assert "Điều kiện: Điều kiện thứ hai" in records[1].text
    assert "Trang PDF: 3" in records[1].text


def test_row_records_add_only_explicitly_verified_group_context(provenance) -> None:
    records = table_as_row_records(
        provenance,
        headers=["Nhóm", "Điều kiện"],
        rows=[["A", "Điều kiện thứ nhất"], [None, "Điều kiện thứ hai"]],
        verified_group_context_by_row={2: "A (đã đối chiếu thủ công)"},
    )

    assert "Nhóm hàng đã đối chiếu với PDF: A (đã đối chiếu thủ công)" in records[1].text


def test_serializer_rejects_missing_headers_and_extra_cells(provenance) -> None:
    with pytest.raises(ValueError, match="explicit label"):
        table_as_markdown(provenance, headers=[""], rows=[["x"]])

    with pytest.raises(ValueError, match="only 1 headers"):
        table_as_row_records(provenance, headers=["A"], rows=[["x", "y"]])


def test_provenance_requires_positive_page_and_safe_table_id() -> None:
    with pytest.raises(ValueError, match="positive 1-based"):
        TableProvenance(document_id="DOC", pdf_page=0, table_id="t1")

    with pytest.raises(ValueError, match="table_id"):
        TableProvenance(document_id="DOC", pdf_page=1, table_id="table/1")
