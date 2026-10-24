"""Readable BM25Okapi reference, including rank_bm25's negative-IDF flooring.

This is an educational implementation, not a replacement for the pinned baseline.
Both implementations must receive exactly the same tokenized corpus.
"""
from collections import Counter
import math


class BM25Reference:
    def __init__(self, corpus, k1=1.5, b=.75, epsilon=.25):
        if not corpus or not any(corpus):
            raise ValueError('Nonempty vocabulary required.')
        if k1 <= 0 or not 0 <= b <= 1 or epsilon < 0:
            raise ValueError('Invalid BM25 parameters.')
        self.frequencies = [Counter(doc) for doc in corpus]
        self.lengths = [len(doc) for doc in corpus]
        self.average_length = sum(self.lengths) / len(corpus)
        self.k1, self.b = k1, b
        df = Counter(term for freq in self.frequencies for term in freq)
        self.idf = {term: math.log(len(corpus) - count + .5) - math.log(count + .5) for term, count in df.items()}
        floor = epsilon * sum(self.idf.values()) / len(self.idf)
        self.idf = {term: floor if value < 0 else value for term, value in self.idf.items()}

    def get_scores(self, query):
        scores = []
        for freq, size in zip(self.frequencies, self.lengths):
            normalization = self.k1 * (1 - self.b + self.b * size / self.average_length)
            scores.append(sum(self.idf.get(term, 0.) * freq[term] * (self.k1 + 1) /
                              (freq[term] + normalization) for term in query))
        return scores
