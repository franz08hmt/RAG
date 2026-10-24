from types import SimpleNamespace as NS

import pytest

from rag_hcmute.evaluation.interval_metrics import character_metrics, length, overlap, paired_bootstrap


def test_union_does_not_double_count():
    assert length([(0, 5), (3, 8), (8, 10)]) == 10
    assert overlap([(0, 5), (3, 8)], [(2, 7)]) == 5
    with pytest.raises(ValueError):
        length([(2, 2)])


def test_two_chunks_jointly_cover_gold_and_wrong_document_is_noise():
    pages = {"A": [NS(pdf_page=1, text="ab cd ef gh")], "B": [NS(pdf_page=1, text="ab cd")]}
    chunks = [NS(chunk_id="a", document_id="A", token_start=0, token_end=2),
              NS(chunk_id="b", document_id="A", token_start=2, token_end=4),
              NS(chunk_id="c", document_id="B", token_start=0, token_end=2)]
    retriever = NS(query=lambda *args, **kwargs: NS(hits=[NS(chunk_id="a"), NS(chunk_id="b"), NS(chunk_id="c")]))
    out = character_metrics(questions=[NS(question_id="q", question="q")],
        spans_by_question={"q": [NS(document_id="A", token_start=0, token_end=4)]},
        chunks=chunks, pages_by_document=pages, retriever=retriever)
    row = out["per_question"][0]
    # The whitespace gap between chunks is a real character not returned by either.
    assert row["character_recall_at_5"] == pytest.approx(10 / 11)
    assert row["character_precision_at_5"] == pytest.approx(10 / 15)
    assert row["character_iou_at_5"] == pytest.approx(10 / 16)


def test_paired_bootstrap_is_reproducible_and_zero_for_ties():
    result = paired_bootstrap([0, 1], [0, 1])
    assert result["ci95_percentile"] == [0, 0]
    assert result["wins_ties_losses_right"] == [0, 2, 0]
    assert result == paired_bootstrap([0, 1], [0, 1])
