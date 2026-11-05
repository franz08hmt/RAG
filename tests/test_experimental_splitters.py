from types import SimpleNamespace

import pytest

from rag_hcmute.ingestion.experimental_splitters import STRATEGIES, split_document, semantic_units


def page(text, n=1):
    return SimpleNamespace(text=text, pdf_page=n, printed_page=None,
                           extraction_method="native", ocr_confidence_mean=None)


@pytest.mark.parametrize("strategy", STRATEGIES)
def test_every_strategy_preserves_source_coverage_offsets_and_budget(strategy):
    pages = [page("Điều 1. Nội dung thứ nhất.\nDòng kế tiếp.\n\nMột đoạn khác."),
             page("Điều 2. Quy định cuối.", 2)]
    counter = lambda s: len(s.split()) + 2
    chunks = split_document(pages, "D", "Doc", strategy=strategy, count_tokens=counter,
                            token_budget=8, character_budget=35, semantic_boundaries=[7, 15])
    words = [w for p in pages for w in p.text.split()]
    assert chunks[0].token_start == 0
    assert chunks[-1].token_end == len(words)
    for i, c in enumerate(chunks):
        assert c.text == " ".join(words[c.token_start:c.token_end])
        assert counter(c.text) <= 8
        assert 1 <= c.pdf_page_start <= c.pdf_page_end <= 2
        if i:
            assert chunks[i-1].token_end == c.token_start


def test_semantic_does_not_silently_fallback_without_embeddings():
    with pytest.raises(ValueError, match="computed"):
        split_document([page("one two")], "D", "Doc", strategy="semantic", count_tokens=len)


def test_long_sentence_is_split_before_semantic_encoding():
    units = semantic_units([page("a b c d e f.")], lambda s: len(s.split()), 2)
    assert [(a, b) for a, b, _ in units] == [(0, 2), (2, 4), (4, 6)]


def test_one_unrepresentable_unit_fails_instead_of_truncating():
    with pytest.raises(ValueError, match="single source unit"):
        split_document([page("abcdef")], "D", "Doc", strategy="tokens", count_tokens=len, token_budget=2)
