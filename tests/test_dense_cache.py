from dataclasses import replace

import numpy as np

from rag_hcmute.ingestion.chunk import Chunk
from rag_hcmute.retrieval.dense_index import (
    _load_cached_embeddings, _save_cached_embeddings, embedding_cache_key,
)


def _chunk():
    return Chunk(chunk_id="D__1", document_id="D", document_title="Synthetic",
                 pdf_page_start=1, pdf_page_end=1, printed_page_start=None,
                 printed_page_end=None, section_path=None, text="original text",
                 token_count=2, text_sha256="deliberately-stale", chunk_method="test")


def test_cache_identity_changes_with_actual_text_and_model_content(tmp_path):
    model = tmp_path / "model"
    model.mkdir()
    weight = model / "model.safetensors"
    weight.write_bytes(b"first weights")
    chunk = _chunk()
    original = embedding_cache_key([chunk], model)
    assert original != embedding_cache_key([replace(chunk, text="changed text")], model)
    assert original != embedding_cache_key([replace(chunk, chunk_id="D__2")], model)
    weight.write_bytes(b"other weights")
    assert original != embedding_cache_key([chunk], model)


def test_cache_roundtrip_and_bad_metadata_fail_closed(tmp_path):
    path = tmp_path / "cache.npz"
    values = np.array([[1, 0], [0, 1]], dtype=np.float32)
    _save_cached_embeddings(path, "key", values)
    assert np.array_equal(_load_cached_embeddings(path, key="key", count=2), values)
    assert _load_cached_embeddings(path, key="other", count=2) is None
    assert _load_cached_embeddings(path, key="key", count=3) is None
    path.write_bytes(b"broken npz")
    assert _load_cached_embeddings(path, key="key", count=2) is None


def test_cache_rejects_unnormalized_vectors_and_tampered_digest(tmp_path):
    path = tmp_path / "cache.npz"
    _save_cached_embeddings(path, "key", np.array([[2, 0]], dtype=np.float32))
    assert _load_cached_embeddings(path, key="key", count=1) is None
    np.savez(path, key="key", embeddings=np.array([[1, 0]], dtype=np.float32), sha256="wrong")
    assert _load_cached_embeddings(path, key="key", count=1) is None
