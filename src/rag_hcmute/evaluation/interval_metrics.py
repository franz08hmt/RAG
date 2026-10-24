"""Character coverage on a single, whitespace-normalized source coordinate system.

Retrieval metrics do not measure answer correctness. Overlapping returned chunks
are unioned, so their repeated characters cannot inflate coverage or precision.
"""
from __future__ import annotations

import math
import random
import statistics


def merged(intervals):
    result = []
    for start, end in sorted(intervals):
        if end <= start:
            raise ValueError("Intervals must have positive length.")
        if result and start <= result[-1][1]:
            result[-1] = (result[-1][0], max(result[-1][1], end))
        else:
            result.append((start, end))
    return result


def length(intervals):
    return sum(end - start for start, end in merged(intervals))


def overlap(left, right):
    return sum(max(0, min(b, d) - max(a, c)) for a, b in merged(left) for c, d in merged(right))


def character_metrics(*, questions, spans_by_question, chunks, pages_by_document, retriever, k=5, threshold=.5):
    coordinates = {}
    for document_id, pages in pages_by_document.items():
        words = [word for page in sorted(pages, key=lambda p: p.pdf_page) for word in page.text.split()]
        starts, ends, cursor = [], [], 0
        for word in words:
            starts.append(cursor)
            ends.append(cursor + len(word))
            cursor += len(word) + 1
        coordinates[document_id] = (starts, ends)

    def interval(document_id, start, end):
        starts, ends = coordinates[document_id]
        if start is None or end is None or not 0 <= start < end <= len(starts):
            raise ValueError("Missing/invalid source interval.")
        return starts[start], ends[end - 1]

    chunk_lookup = {c.chunk_id: c for c in chunks}
    qtext = {q.question_id: q.question for q in questions}
    rows = []
    for qid, spans in sorted(spans_by_question.items()):
        gold = {}
        for span in spans:
            gold.setdefault(span.document_id, []).append(interval(span.document_id, span.token_start, span.token_end))

        def gain(c):
            ci = interval(c.document_id, c.token_start, c.token_end)
            return max((overlap([ci], [g]) / (g[1] - g[0]) for g in gold.get(c.document_id, [])), default=0.)

        hits = retriever.query(qtext[qid], top_k=10).hits
        selected, gains = {}, []
        for rank, hit in enumerate(hits, 1):
            c = chunk_lookup[hit.chunk_id]
            gains.append(gain(c))
            if rank <= k:
                selected.setdefault(c.document_id, []).append(interval(c.document_id, c.token_start, c.token_end))
        intersection = sum(overlap(gold.get(doc, []), ranges) for doc, ranges in selected.items())
        gold_len = sum(length(v) for v in gold.values())
        retrieved_len = sum(length(v) for v in selected.values())
        ideal = sorted((gain(c) for c in chunks), reverse=True)[:k]
        dcg = lambda values: sum(value / math.log2(rank + 1) for rank, value in enumerate(values, 1))
        first = next((rank for rank, value in enumerate(gains, 1) if value >= threshold), None)
        rows.append({"question_id": qid, "retrieved_chunk_ids_top10": [h.chunk_id for h in hits],
                     "character_recall_at_5": intersection / gold_len,
                     "character_precision_at_5": intersection / retrieved_len if retrieved_len else 0.,
                     "character_iou_at_5": intersection / (gold_len + retrieved_len - intersection),
                     "hit_at_5_threshold_05": any(g >= threshold for g in gains[:k]),
                     "mrr_at_10_threshold_05": 1 / first if first else 0.,
                     "ndcg_at_5_linear_span_coverage": dcg(gains[:k]) / dcg(ideal) if dcg(ideal) else 0.})
    keys = [key for key in rows[0] if key not in ("question_id", "retrieved_chunk_ids_top10")]
    return {"coordinate_system": "characters in source whitespace-normalized text; union overlaps within each document",
            "relevance_threshold": threshold, "ndcg_gain": "max character fraction of any gold span per chunk; linear gain",
            "macro": {key: statistics.mean(row[key] for row in rows) for key in keys}, "per_question": rows}


def paired_bootstrap(left, right, *, repetitions=5000, seed=22110068):
    """IID-question percentile interval of mean(right-left); exploratory only."""
    if len(left) != len(right) or not left or repetitions < 1000:
        raise ValueError("Need equal nonempty pairs and at least 1000 repetitions.")
    differences = [b - a for a, b in zip(left, right)]
    rng = random.Random(seed)
    draws = sorted(statistics.mean(rng.choices(differences, k=len(differences))) for _ in range(repetitions))
    return {"mean_right_minus_left": statistics.mean(differences),
            "ci95_percentile": [draws[int(.025 * (repetitions - 1))], draws[int(.975 * (repetitions - 1))]],
            "wins_ties_losses_right": [sum(d > 1e-12 for d in differences), sum(abs(d) <= 1e-12 for d in differences), sum(d < -1e-12 for d in differences)],
            "n": len(left), "repetitions": repetitions, "seed": seed,
            "limitations": "Exploratory dev pairs; shared topics violate strict IID; not population or holdout evidence."}
