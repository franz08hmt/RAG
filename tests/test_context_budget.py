from types import SimpleNamespace as S
import pytest
from rag_hcmute.evaluation.context_budget import pack_ranked_chunks, source_coordinates, coverage_of_selection


def test_pack_uses_actual_joined_string_and_skips_oversized_without_gold():
    chunks = [S(chunk_id="large", text="123456789"), S(chunk_id="a", text="12"),
              S(chunk_id="b", text="34"), S(chunk_id="a", text="12")]
    selected, tokens, skipped = pack_ranked_chunks(chunks, len, 5)
    assert [c.chunk_id for c in selected] == ["a"]
    assert tokens == 2
    assert skipped == ["large", "b"]  # separator would make 6 chars


def test_overlaps_are_unioned_within_document_and_not_across_documents():
    coords = source_coordinates({"D": [S(pdf_page=1, text="aa bb cc dd")],
                                 "E": [S(pdf_page=1, text="aa bb")]})
    span = S(document_id="D", token_start=1, token_end=3)
    chunks = [S(document_id="D", token_start=0, token_end=3),
              S(document_id="D", token_start=1, token_end=4),
              S(document_id="E", token_start=0, token_end=2)]
    m = coverage_of_selection(chunks, [span], coords)
    assert m["character_recall"] == 1
    assert m["selected_union_character_count"] == 16
    assert m["character_precision"] == pytest.approx(5/16)
