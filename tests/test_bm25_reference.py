import numpy as np
import pytest
from rank_bm25 import BM25Okapi
from rag_hcmute.retrieval.bm25_reference import BM25Reference


@pytest.mark.parametrize('query',[['học'],['học','học','lại'],['ngoài'],[]])
def test_reference_scores_match_library(query):
    corpus = [['học','lại','học'],['học','phí'],['học','bổng'],[]]
    np.testing.assert_allclose(BM25Reference(corpus).get_scores(query),BM25Okapi(corpus).get_scores(query),rtol=1e-12,atol=1e-12)


def test_reject_empty_vocabulary():
    with pytest.raises(ValueError):
        BM25Reference([[]])
