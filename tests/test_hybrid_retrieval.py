from types import SimpleNamespace

import pytest

from rag_hcmute.retrieval.common import RetrievalHit
from rag_hcmute.retrieval.hybrid import ReciprocalRankFusionRetriever


def _hit(chunk_id: str, rank: int) -> RetrievalHit:
    return RetrievalHit(
        rank=rank,
        chunk_id=chunk_id,
        document_id="DOC",
        document_title="Synthetic test document",
        pdf_page_start=1,
        pdf_page_end=1,
        section_path=None,
        score=0.0,
        text_preview="synthetic fixture only",
    )


class StubRetriever:
    def __init__(self, chunk_ids: list[str], ranked_ids: list[str]):
        self.chunks = [SimpleNamespace(chunk_id=chunk_id, text_sha256=f"hash-{chunk_id}") for chunk_id in chunk_ids]
        self.ranked_ids = ranked_ids
        self.requested_k = None

    def query(self, _query_text: str, top_k: int):
        self.requested_k = top_k
        hits = [_hit(chunk_id, rank) for rank, chunk_id in enumerate(self.ranked_ids, start=1)]
        return SimpleNamespace(hits=hits, latency_ms=0.0)


def test_rrf_combines_rankings_and_uses_deterministic_order() -> None:
    lexical = StubRetriever(["A", "B", "C"], ["A", "B"])
    dense = StubRetriever(["A", "B", "C"], ["B", "C"])
    retriever = ReciprocalRankFusionRetriever(
        lexical,
        dense,
        rank_constant=60,
        candidate_k=20,
    )

    result = retriever.query("synthetic query", top_k=3)

    assert lexical.requested_k == dense.requested_k == 20
    assert [hit.chunk_id for hit in result.hits] == ["B", "A", "C"]
    assert [hit.rank for hit in result.hits] == [1, 2, 3]
    assert result.hits[0].score == pytest.approx((1 / 61) + (1 / 62))


def test_rrf_rejects_different_indexed_chunk_sets() -> None:
    lexical = StubRetriever(["A", "B"], ["A"])
    dense = StubRetriever(["A", "C"], ["A"])

    with pytest.raises(ValueError, match="same chunk IDs and content"):
        ReciprocalRankFusionRetriever(lexical, dense)


def test_rrf_rejects_same_chunk_ids_with_different_content() -> None:
    lexical = StubRetriever(["A"], ["A"])
    dense = StubRetriever(["A"], ["A"])
    dense.chunks[0].text_sha256 = "different-content-hash"

    with pytest.raises(ValueError, match="same chunk IDs and content"):
        ReciprocalRankFusionRetriever(lexical, dense)


@pytest.mark.parametrize(
    ("rank_constant", "candidate_k"),
    [(-1, 20), (60, 0)],
)
def test_rrf_rejects_invalid_configuration(rank_constant: int, candidate_k: int) -> None:
    retriever = StubRetriever(["A"], ["A"])

    with pytest.raises(ValueError):
        ReciprocalRankFusionRetriever(
            retriever,
            retriever,
            rank_constant=rank_constant,
            candidate_k=candidate_k,
        )
