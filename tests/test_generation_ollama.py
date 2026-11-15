from __future__ import annotations

import io
import json

import pytest

from rag_hcmute.generation.ollama import (
    GroundingSource,
    generate_grounded_answer,
    sources_from_hits,
)
from rag_hcmute.ingestion.chunk import Chunk
from rag_hcmute.retrieval.common import RetrievalHit


def _source(source_id: str = "S1") -> GroundingSource:
    return GroundingSource(
        source_id=source_id,
        chunk_id="DOC__c0001",
        document_id="DOC",
        document_title="Synthetic policy",
        pdf_page_start=3,
        pdf_page_end=3,
        section_path="Điều 2",
        text="Phòng tiếp nhận hồ sơ từ 8 giờ đến 16 giờ.",
    )


def _mock_response(content: str) -> io.BytesIO:
    return io.BytesIO(
        json.dumps({"message": {"content": content}}, ensure_ascii=False).encode("utf-8")
    )


def test_empty_evidence_abstains_without_calling_ollama(monkeypatch) -> None:
    def fail_if_called(*args, **kwargs):
        raise AssertionError("Ollama must not be called without retrieved evidence.")

    monkeypatch.setattr("rag_hcmute.generation.ollama.urlopen", fail_if_called)
    result = generate_grounded_answer("Câu hỏi", [])

    assert result.abstained is True
    assert result.status == "no_retrieved_evidence"
    assert not result.citations


def test_remote_endpoint_is_rejected_before_any_network_call(monkeypatch) -> None:
    def fail_if_called(*args, **kwargs):
        raise AssertionError("No remote network calls are allowed.")

    monkeypatch.setattr("rag_hcmute.generation.ollama.urlopen", fail_if_called)
    with pytest.raises(ValueError, match="loopback"):
        generate_grounded_answer("Câu hỏi", [_source()], base_url="https://example.com")


def test_valid_local_json_response_returns_only_known_inline_citations(monkeypatch) -> None:
    captured = {}

    def fake_urlopen(request, timeout):
        captured["payload"] = json.loads(request.data.decode("utf-8"))
        captured["timeout"] = timeout
        return _mock_response(
            json.dumps(
                {
                    "abstain": False,
                    "answer": "Hồ sơ được tiếp nhận từ 8 giờ đến 16 giờ [S1].",
                    "citation_ids": ["S1"],
                },
                ensure_ascii=False,
            )
        )

    monkeypatch.setattr("rag_hcmute.generation.ollama.urlopen", fake_urlopen)
    result = generate_grounded_answer("Giờ tiếp nhận hồ sơ?", [_source()])

    assert result.abstained is False
    assert result.status == "generated_citations_unverified"
    assert result.citations == (_source(),)
    assert captured["payload"]["think"] is False
    assert captured["payload"]["options"]["temperature"] == 0
    assert captured["payload"]["format"] == "json"
    assert "không đáng tin cậy" in captured["payload"]["messages"][0]["content"]


@pytest.mark.parametrize(
    "content,status",
    [
        ("not json", "invalid_model_json"),
        (
            json.dumps({"abstain": False, "answer": "Câu trả lời [S9].", "citation_ids": ["S9"]}),
            "invalid_or_missing_citation",
        ),
        (
            json.dumps({"abstain": False, "answer": "Câu trả lời.", "citation_ids": []}),
            "invalid_or_missing_citation",
        ),
        (
            json.dumps({"abstain": True, "answer": "Chưa đủ căn cứ.", "citation_ids": []}),
            "model_abstained",
        ),
    ],
)
def test_invalid_model_outputs_fail_closed(monkeypatch, content: str, status: str) -> None:
    monkeypatch.setattr(
        "rag_hcmute.generation.ollama.urlopen", lambda *args, **kwargs: _mock_response(content)
    )
    result = generate_grounded_answer("Câu hỏi", [_source()])

    assert result.abstained is True
    assert result.status == status
    assert result.citations == ()


def test_sources_are_built_from_retrieval_hits_and_full_chunks() -> None:
    chunk = Chunk(
        chunk_id="DOC__c0001",
        document_id="DOC",
        document_title="Synthetic policy",
        pdf_page_start=3,
        pdf_page_end=3,
        printed_page_start=None,
        printed_page_end=None,
        section_path="Điều 2",
        text="Full source passage used by the local generator.",
        token_count=8,
        text_sha256="digest",
        chunk_method="test",
    )
    hit = RetrievalHit(
        rank=1,
        chunk_id=chunk.chunk_id,
        document_id=chunk.document_id,
        document_title=chunk.document_title,
        pdf_page_start=chunk.pdf_page_start,
        pdf_page_end=chunk.pdf_page_end,
        section_path=chunk.section_path,
        score=1.0,
        text_preview="short preview only",
    )

    sources = sources_from_hits([hit], {chunk.chunk_id: chunk})

    assert len(sources) == 1
    assert sources[0].source_id == "S1"
    assert sources[0].text == chunk.text
    assert sources[0].text != hit.text_preview


def test_valid_response_level_citation_ids_are_returned_for_source_list(monkeypatch) -> None:
    content = json.dumps(
        {"abstain": False, "answer": "Câu trả lời dựa trên nguồn được truy xuất.", "citation_ids": ["S1"]},
        ensure_ascii=False,
    )
    monkeypatch.setattr(
        "rag_hcmute.generation.ollama.urlopen", lambda *args, **kwargs: _mock_response(content)
    )

    result = generate_grounded_answer("Câu hỏi", [_source()])

    assert result.abstained is False
    assert [source.source_id for source in result.citations] == ["S1"]


def test_scope_prompt_is_generic_and_invalid_variant_is_rejected(monkeypatch):
    payloads = []
    def fake(request, timeout):
        payloads.append(json.loads(request.data))
        return _mock_response(json.dumps({'abstain': True, 'answer': '', 'citation_ids': []}))
    monkeypatch.setattr('rag_hcmute.generation.ollama.urlopen', fake)
    result = generate_grounded_answer('Một câu hỏi', [_source()], prompt_variant='scope_check', keep_alive=0)
    assert result.status == 'model_abstained'
    assert 'đối chiếu từng yêu cầu' in payloads[0]['messages'][0]['content']
    assert payloads[0]['keep_alive'] == 0
    with pytest.raises(ValueError):
        generate_grounded_answer('Câu hỏi', [_source()], prompt_variant='invented')


def test_scope_schema_rejects_refusal_with_citations(monkeypatch):
    payloads = []

    def fake(request, timeout):
        payloads.append(json.loads(request.data))
        return _mock_response(json.dumps({"abstain": True, "answer": "Thiếu căn cứ", "citation_ids": ["S1"]}))

    monkeypatch.setattr("rag_hcmute.generation.ollama.urlopen", fake)
    result = generate_grounded_answer("Câu hỏi", [_source()], prompt_variant="scope_schema")
    assert result.status == "inconsistent_model_refusal"
    assert result.citations == ()
    assert payloads[0]["format"]["properties"]["citation_ids"]["items"]["enum"] == ["S1"]
    assert "đối chiếu từng yêu cầu" in payloads[0]["messages"][0]["content"]
