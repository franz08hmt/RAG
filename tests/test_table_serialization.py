import pytest

from rag_hcmute.ingestion.tables import (
    TableProvenance,
    table_as_markdown,
    table_as_markdown_chunk,
    table_as_row_chunks,
    table_as_row_records,
)
from rag_hcmute.retrieval.bm25_index import BM25Retriever


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


def test_table_variants_convert_to_existing_chunk_schema(provenance) -> None:
    headers = ["Năm", "Tổng số tín chỉ"]
    rows = [["Năm thứ nhất", "dưới 36"], ["Năm thứ ba", "72 đến 107"]]

    markdown_chunk = table_as_markdown_chunk(
        provenance, "Quy chế kiểm thử", headers, rows
    )
    row_chunks = table_as_row_chunks(provenance, "Quy chế kiểm thử", headers, rows)

    assert markdown_chunk.chunk_method == "table_markdown"
    assert markdown_chunk.pdf_page_start == markdown_chunk.pdf_page_end == 3
    assert markdown_chunk.printed_page_start is None
    assert markdown_chunk.token_count > 0
    assert len(markdown_chunk.text_sha256) == 64
    assert all(chunk.chunk_method == "table_row_context" for chunk in row_chunks)
    assert [chunk.chunk_id for chunk in row_chunks] == [
        "TEST_DOC__table_01__row001",
        "TEST_DOC__table_01__row002",
    ]


def test_row_context_chunks_work_with_existing_bm25_retriever(provenance) -> None:
    chunks = table_as_row_chunks(
        provenance,
        "Quy chế kiểm thử",
        headers=["Năm", "Tổng số tín chỉ"],
        rows=[
            ["Năm thứ nhất", "dưới 36"],
            ["Năm thứ hai", "36 đến 71"],
            ["Năm thứ ba", "72 đến 107"],
            ["Năm thứ tư", "108 đến 149"],
        ],
    )

    result = BM25Retriever(chunks).query("năm thứ ba 72 107", top_k=3)

    assert result.hits[0].chunk_id == "TEST_DOC__table_01__row003"
    assert result.hits[0].pdf_page_start == 3
