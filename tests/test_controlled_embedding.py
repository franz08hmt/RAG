import pytest

from rag_hcmute.evaluation.controlled_embedding import shared_budget_chunks
from rag_hcmute.ingestion.extract import PageText


def page(number, text):
    return PageText("D", number, text, len(text), False, number, "test")


def test_shared_budget_respects_both_tokenizers_and_keeps_source_offsets():
    words = [f"word{i}" for i in range(11)]
    pages = [page(1, " ".join(words[:5])), page(2, " ".join(words[5:]))]
    counters = [lambda text: len(text.split()) + 2, lambda text: len(text.split()) * 2 + 3]
    chunks = shared_budget_chunks(pages, "D", "fixture", counters,
                                 max_model_tokens=11, max_whitespace_tokens=7,
                                 overlap_whitespace_tokens=1)
    covered = set()
    for chunk in chunks:
        assert all(counter(chunk.text) <= 11 for counter in counters)
        assert chunk.text == " ".join(words[chunk.token_start:chunk.token_end])
        covered.update(range(chunk.token_start, chunk.token_end))
    assert covered == set(range(11))
    assert [(c.token_start, c.token_end) for c in chunks] == [(0, 4), (3, 7), (6, 10), (9, 11)]
    assert chunks[1].pdf_page_start == 1 and chunks[1].pdf_page_end == 2


def test_oversized_single_unit_fails_instead_of_silent_truncation():
    with pytest.raises(ValueError, match="One source whitespace unit"):
        shared_budget_chunks([page(1, "oversized")], "D", "fixture", [lambda _: 99],
                             max_model_tokens=10)


def test_short_chunk_with_overlap_larger_than_fit_still_terminates():
    chunks = shared_budget_chunks([page(1, "a b c d")], "D", "fixture",
                                 [lambda text: len(text.split())], max_model_tokens=1,
                                 max_whitespace_tokens=5, overlap_whitespace_tokens=3)
    assert [c.text for c in chunks] == ["a", "b", "c", "d"]
