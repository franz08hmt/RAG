from __future__ import annotations

import io
import json
from pathlib import Path

from rag_hcmute.generation.ollama import generate_grounded_answer, sources_from_hits
from rag_hcmute.ingestion.chunk import chunk_document
from rag_hcmute.ingestion.clean import clean_document_pages
from rag_hcmute.ingestion.extract import extract_pdf_pages
from rag_hcmute.retrieval.bm25_index import BM25Retriever


FIXTURE = Path(__file__).parent / "fixtures" / "sample_quy_dinh.pdf"


def test_retrieved_chunk_provenance_survives_generation_citation(monkeypatch) -> None:
    pages = extract_pdf_pages(FIXTURE, "TEST_DOC")
    cleaned_pages, _ = clean_document_pages(pages)
    chunks = chunk_document(cleaned_pages, "TEST_DOC", "Quy định mẫu kiểm thử")
    retriever = BM25Retriever(chunks)

    retrieval = retriever.query("MA_KIEM_THU_DIEU_MOT", top_k=1)
    hit = retrieval.hits[0]
    chunk_by_id = {chunk.chunk_id: chunk for chunk in chunks}
    sources = sources_from_hits(retrieval.hits, chunk_by_id)

    assert len(sources) == 1
    source = sources[0]
    source_chunk = chunk_by_id[hit.chunk_id]
    assert source.source_id == "S1"
    assert source.chunk_id == hit.chunk_id == source_chunk.chunk_id
    assert source.document_id == hit.document_id == source_chunk.document_id
    assert source.document_title == source_chunk.document_title
    assert source.pdf_page_start == hit.pdf_page_start == source_chunk.pdf_page_start
    assert source.pdf_page_end == hit.pdf_page_end == source_chunk.pdf_page_end
    assert source.section_path == hit.section_path == source_chunk.section_path
    assert source.text == source_chunk.text

    model_output = json.dumps(
        {
            "abstain": False,
            "answer": "Câu trả lời thử nghiệm có nguồn [S1].",
            "citation_ids": ["S1"],
        },
        ensure_ascii=False,
    )
    response = io.BytesIO(
        json.dumps({"message": {"content": model_output}}, ensure_ascii=False).encode("utf-8")
    )
    monkeypatch.setattr("rag_hcmute.generation.ollama.urlopen", lambda *args, **kwargs: response)

    answer = generate_grounded_answer("Câu hỏi kiểm thử", sources)

    assert answer.abstained is False
    assert answer.status == "generated_citations_unverified"
    assert answer.citations == (source,)
    assert answer.citations[0].chunk_id == hit.chunk_id
    assert answer.citations[0].pdf_page_start == hit.pdf_page_start
    assert answer.citations[0].section_path == hit.section_path
