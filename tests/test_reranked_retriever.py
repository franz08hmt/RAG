from types import SimpleNamespace

from rag_hcmute.ingestion.chunk import Chunk
from rag_hcmute.retrieval.common import RetrievalHit
from rag_hcmute.retrieval.reranked import RerankedRetriever


def _chunk() -> Chunk:
    return Chunk(
        chunk_id="DOC__c0001",
        document_id="DOC",
        document_title="Synthetic policy",
        pdf_page_start=1,
        pdf_page_end=1,
        printed_page_start=None,
        printed_page_end=None,
        section_path="Điều 1",
        text="evidence text",
        token_count=2,
        text_sha256="test",
        chunk_method="test",
    )


def _hit(rank: int) -> RetrievalHit:
    return RetrievalHit(
        rank=rank,
        document_id="DOC",
        document_title="Synthetic policy",
        chunk_id="DOC__c0001",
        pdf_page_start=1,
        pdf_page_end=1,
        section_path="Điều 1",
        score=float(10 - rank),
        text_preview="evidence text",
    )


class FakeBaseRetriever:
    chunks = [_chunk()]

    def __init__(self):
        self.requested_top_k = None

    def query(self, query: str, *, top_k: int):
        self.requested_top_k = top_k
        return SimpleNamespace(hits=[_hit(1), _hit(2)], latency_ms=2.0)


class FakeReranker:
    def __init__(self):
        self.received_candidates = None

    def rerank(self, *, query, candidates, chunks_by_id):
        self.received_candidates = candidates
        assert chunks_by_id["DOC__c0001"].text == "evidence text"
        return SimpleNamespace(
            hits=[_hit(2), _hit(1)],
            latency_ms=3.5,
            pair_count=len(candidates),
            truncated_pair_count=1,
        )


def test_wrapper_retrieves_fixed_candidate_depth_then_reranks_and_reports_latency() -> None:
    base = FakeBaseRetriever()
    reranker = FakeReranker()
    retriever = RerankedRetriever(base, reranker, [_chunk()], candidate_depth=20)

    result = retriever.query("question", top_k=1)

    assert base.requested_top_k == 20
    assert len(reranker.received_candidates) == 2
    assert result.hits[0].rank == 2
    assert result.hits[0].score == 8.0
    assert result.latency_ms == 5.5
    assert result.retrieval_latency_ms == 2.0
    assert result.reranker_latency_ms == 3.5
    assert result.candidate_count == 2
    assert result.candidate_depth == 20
    assert result.truncated_pair_count == 1
