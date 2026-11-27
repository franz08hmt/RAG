import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from rag_hcmute.console_app import (
    APPROVED_RERANKER_REVISION,
    _corpus_chunk_count,
    _configure_console_encoding,
    _run_one,
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


def test_console_defaults_to_rrf_schema_and_the_approved_g0_snapshot() -> None:
    args = build_parser().parse_args([])

    assert args.method == "hybrid"
    assert args.prompt_variant == "scope_schema"
    assert args.context_window == 8192
    assert args.chunks.name == "chunks.jsonl"
    assert "g0_reproduction" in str(args.chunks)
    assert args.top_k == 5
    assert args.reranker_max_length == 512
    assert args.reranker_batch_size == 4


def test_hybrid_console_queries_50_candidates_per_branch(tmp_path: Path, monkeypatch) -> None:
    import rag_hcmute.retrieval.dense_index as dense_index

    chunks_file = tmp_path / "chunks.jsonl"
    chunks_file.write_text(json.dumps(_chunk().to_dict()) + "\n", encoding="utf-8")
    model_path = tmp_path / "model"
    model_path.mkdir()

    class DenseStub:
        def __init__(self, chunks, **_kwargs):
            self.chunks = chunks
            self.startup_metrics = {}

    monkeypatch.setattr(dense_index, "DenseRetriever", DenseStub)
    retriever = create_retriever(method="hybrid", chunks_path=chunks_file, dense_model=model_path)
    assert retriever.rank_constant == 60
    assert retriever.candidate_k == 50


def test_console_accepts_rerank_method_but_requires_explicit_models(tmp_path: Path) -> None:
    chunks_file = tmp_path / "chunks.jsonl"
    chunks_file.write_text(json.dumps(_chunk().to_dict()) + "\n", encoding="utf-8")
    args = build_parser().parse_args(["--method", "hybrid-rerank"])

    assert args.method == "hybrid-rerank"
    assert APPROVED_RERANKER_REVISION == "953dc6f6f85a1b2dbfca4c34a2796e7dde08d41e"
    with pytest.raises(ValueError, match="--dense-model"):
        create_retriever(method="hybrid-rerank", chunks_path=chunks_file)


def test_console_can_pass_full_retrieved_chunks_to_local_generation(monkeypatch, capsys) -> None:
    chunk = _chunk()
    hit = SimpleNamespace(
        rank=1,
        chunk_id=chunk.chunk_id,
        document_title=chunk.document_title,
        pdf_page_start=chunk.pdf_page_start,
        pdf_page_end=chunk.pdf_page_end,
        section_path=chunk.section_path,
        document_id=chunk.document_id,
        score=1.0,
        text_preview="preview only",
    )
    retriever = SimpleNamespace(
        chunks=[chunk],
        query=lambda _query, top_k: SimpleNamespace(hits=[hit], latency_ms=1.0),
    )
    captured = {}

    def fake_generate(question, sources, **kwargs):
        captured["question"] = question
        captured["sources"] = sources
        return SimpleNamespace(
            model="qwen3:4b",
            latency_ms=10.0,
            answer="Trả lời thử.",
            citations=sources[:1],
            abstained=False,
            status="generated_citations_unverified",
        )

    monkeypatch.setattr("rag_hcmute.console_app.generate_grounded_answer", fake_generate)
    _run_one(retriever, method="bm25", query="Câu hỏi", top_k=1, answer=True)

    output = capsys.readouterr().out
    assert captured["question"] == "Câu hỏi"
    assert captured["sources"][0].text == chunk.text
    assert "preview only" not in captured["sources"][0].text
    assert "Trả lời thử." in output


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


def test_console_reports_generation_error_as_failure(monkeypatch, capsys):
    retriever = SimpleNamespace(chunks=[], query=lambda _q, top_k: SimpleNamespace(hits=[], latency_ms=1))
    def fail(*args, **kwargs):
        raise RuntimeError("local service unavailable")
    monkeypatch.setattr("rag_hcmute.console_app.generate_grounded_answer", fail)
    metrics = {}
    assert _run_one(retriever, method="bm25", query="test", top_k=1, answer=True, metrics=metrics) is False
    assert metrics["status"] == "generation_error"
    assert "Không tạo được câu trả lời" in capsys.readouterr().out


def test_console_does_not_count_malformed_output_as_semantic_refusal(monkeypatch, capsys):
    retriever = SimpleNamespace(chunks=[], query=lambda _q, top_k: SimpleNamespace(hits=[], latency_ms=1))
    monkeypatch.setattr("rag_hcmute.console_app.generate_grounded_answer", lambda *args, **kwargs:
        SimpleNamespace(model="qwen3:4b", latency_ms=1, answer="", citations=[], abstained=True, status="invalid_model_json"))
    assert _run_one(retriever, method="bm25", query="test", top_k=1, answer=True) is False
    assert "lỗi kỹ thuật" in capsys.readouterr().out
