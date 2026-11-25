import pytest

from rag_hcmute.ingestion.chunk import chunk_document
from rag_hcmute.ingestion.document import Document, chunk_provenance
from rag_hcmute.ingestion.extract import PageText


def test_document_chunk_offsets_and_neighbors_with_unicode():
    pages = [PageText('D', 1, 'Điều một\n' + 'nghỉ học ' * 35, 300, False, 8, 'certain'),
             PageText('D', 2, 'nộp đơn ' * 35, 280, False, 9, 'certain')]
    row = {'document_id': 'D', 'document_title': 'Quy chế', 'document_number': '1',
           'source_url': 'https://example.org', 'file_sha256': 'a' * 64, 'page_count': '2'}
    document = Document.from_manifest(row, pages)
    chunks = chunk_document(pages, 'D', 'Quy chế', chunk_tokens=70, overlap_tokens=0,
                            force_sliding_window=True)
    views = chunk_provenance(document, chunks, {'example': lambda text: 42})
    normalized = ' '.join(page.text for page in pages).split()
    text = ' '.join(normalized)
    assert all(text[v.char_start:v.char_end] == c.text for v, c in zip(views, chunks))
    assert views[0].token_counts['example'] == 42
    assert views[0].next_chunk_id == views[1].chunk_id
    assert views[1].previous_chunk_id == views[0].chunk_id
    with pytest.raises(ValueError):
        Document.from_manifest({**row, 'page_count': '3'}, pages)
