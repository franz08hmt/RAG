import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from rag_hcmute.console_app import (
    APPROVED_RERANKER_REVISION,
    _corpus_chunk_count,
    _configure_console_encoding,
    build_parser,
    create_retriever,
    format_retrieval_result,
)
from rag_hcmute.ingestion.chunk import Chunk


def _chunk() -> Chunk:
    return Chunk(
        chunk_id="DOC__c0001",
        document_id="DOC",
        document_title="Synthetic policy",
        pdf_page_start=4,
        pdf_page_end=5,
        printed_page_start=None,
        printed_page_end=None,
        section_path="Chương I > Điều 1",
        text="synthetic marker for console test",
        token_count=6,
        text_sha256="synthetic-hash",
        chunk_method="test",
    )


def test_bm25_console_retriever_loads_local_chunks(tmp_path: Path) -> None:
    chunks_file = tmp_path / "chunks.jsonl"
    chunks_file.write_text(json.dumps(_chunk().to_dict()) + "\n", encoding="utf-8")

    retriever = create_retriever(method="bm25", chunks_path=chunks_file)
    result = retriever.query("synthetic marker", top_k=1)

    assert len(retriever.chunks) == 1
    assert result.hits[0].chunk_id == "DOC__c0001"
    assert result.hits[0].pdf_page_start == 4


def test_dense_and_hybrid_require_an_explicit_existing_local_model(tmp_path: Path) -> None:
    chunks_file = tmp_path / "chunks.jsonl"
    chunks_file.write_text(json.dumps(_chunk().to_dict()) + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match="--dense-model"):
        create_retriever(method="dense", chunks_path=chunks_file)
    with pytest.raises(ValueError, match="--dense-model"):
        create_retriever(method="hybrid", chunks_path=chunks_file)


def test_output_shows_traceable_source_and_labels_result_as_retrieval_only() -> None:
    hit = SimpleNamespace(
        rank=1,
        document_title="Synthetic policy",
        pdf_page_start=4,
        pdf_page_end=5,
        section_path="Chương I > Điều 1",
        document_id="DOC",
        chunk_id="DOC__c0001",
        score=0.91,
        text_preview="synthetic   evidence excerpt",
    )
    output = format_retrieval_result(
        method="bm25",
        result=SimpleNamespace(hits=[hit], latency_ms=1.25),
        top_k=5,
    )

    assert "Synthetic policy" in output
    assert "PDF trang 4–5" in output
    assert "Chương I > Điều 1" in output
    assert "synthetic evidence excerpt" in output
    assert "chưa phải câu trả lời do LLM sinh" in output


def test_empty_retrieval_does_not_claim_a_semantic_refusal() -> None:
    output = format_retrieval_result(
        method="bm25",
        result=SimpleNamespace(hits=[], latency_ms=0.5),
        top_k=5,
    )

    assert "không trả về ứng viên" in output
    assert "chưa phải câu trả lời do LLM sinh" in output
    assert "từ chối" not in output.lower()


def test_console_defaults_to_bm25_and_the_approved_g0_snapshot() -> None:
    args = build_parser().parse_args([])

    assert args.method == "bm25"
    assert args.chunks.name == "chunks.jsonl"
    assert "g0_reproduction" in str(args.chunks)
    assert args.top_k == 5
    assert args.reranker_max_length == 512
    assert args.reranker_batch_size == 4


def test_console_accepts_rerank_method_but_requires_explicit_models(tmp_path: Path) -> None:
    chunks_file = tmp_path / "chunks.jsonl"
    chunks_file.write_text(json.dumps(_chunk().to_dict()) + "\n", encoding="utf-8")
    args = build_parser().parse_args(["--method", "hybrid-rerank"])

    assert args.method == "hybrid-rerank"
    assert APPROVED_RERANKER_REVISION == "953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e"
    with pytest.raises(ValueError, match="--dense-model"):
        create_retriever(method="hybrid-rerank", chunks_path=chunks_file)


def test_reranked_console_output_exposes_candidate_and_truncation_counts() -> None:
    hit = SimpleNamespace(
        rank=1,
        document_title="Synthetic policy",
        pdf_page_start=4,
        pdf_page_end=4,
        section_path="Điều 1",
        document_id="DOC",
        chunk_id="DOC__c0001",
        score=0.91,
        text_preview="synthetic evidence excerpt",
    )
    result = SimpleNamespace(
        hits=[hit],
        latency_ms=12.5,
        retrieval_latency_ms=3.25,
        candidate_count=20,
        candidate_depth=20,
        reranker_latency_ms=9.25,
        truncated_pair_count=7,
        pair_count=20,
    )

    output = format_retrieval_result(method="hybrid-rerank", result=result, top_k=5)

    assert "BGE-Reranker-v2-m3" in output
    assert "thời gian retrieval + rerank" in output
    assert "Candidate pool: 20/20" in output
    assert "retrieval: 3.25 ms" in output
    assert "9.25 ms" in output
    assert "7/20" in output
    assert "chưa phải câu trả lời do LLM sinh" in output


def test_hybrid_console_can_report_shared_corpus_size() -> None:
    hybrid = SimpleNamespace(
        lexical_retriever=SimpleNamespace(chunks=[_chunk(), _chunk()]),
        dense_retriever=SimpleNamespace(chunks=[_chunk(), _chunk()]),
    )

    assert _corpus_chunk_count(hybrid) == 2


def test_console_configures_utf8_for_terminal_streams(monkeypatch) -> None:
    class StreamProbe:
        def __init__(self):
            self.configuration = None

        def reconfigure(self, **kwargs):
            self.configuration = kwargs

    stdout = StreamProbe()
    stderr = StreamProbe()
    monkeypatch.setattr("sys.stdout", stdout)
    monkeypatch.setattr("sys.stderr", stderr)

    _configure_console_encoding()

    assert stdout.configuration == {"encoding": "utf-8", "errors": "replace"}
    assert stderr.configuration == {"encoding": "utf-8", "errors": "replace"}
