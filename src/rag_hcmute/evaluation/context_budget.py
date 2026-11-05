"""Context selection and source-character coverage for chunking comparisons."""
from rag_hcmute.evaluation.interval_metrics import length, overlap


def pack_ranked_chunks(chunks, count_tokens, budget):
    """Keep whole chunks in rank order; skip oversized candidates, never use gold.

    Token count includes separators in the actual concatenated source text, not
    a sum of separately encoded lengths. Prompt/question/source labels are NOT
    included: this is a source-context budget, not total inference token usage.
    """
    if budget < 1:
        raise ValueError("Context budget must be positive.")
    selected, skipped = [], []
    seen = set()
    for c in chunks:
        if c.chunk_id in seen:
            continue
        seen.add(c.chunk_id)
        candidate = "\n\n".join(x.text for x in [*selected, c])
        if count_tokens(candidate) <= budget:
            selected.append(c)
        else:
            skipped.append(c.chunk_id)
    actual = count_tokens("\n\n".join(c.text for c in selected)) if selected else 0
    return selected, actual, skipped


def source_coordinates(pages):
    result = {}
    for did, doc_pages in pages.items():
        cursor, bounds = 0, []
        for page in sorted(doc_pages, key=lambda p: p.pdf_page):
            for word in page.text.split():
                bounds.append((cursor, cursor + len(word)))
                cursor += len(word) + 1
        result[did] = bounds
    return result


def coverage_of_selection(selected, spans, coordinates):
    def interval(item):
        bounds = coordinates[item.document_id]
        a, b = item.token_start, item.token_end
        if a is None or b is None or not 0 <= a < b <= len(bounds):
            raise ValueError("Invalid source offsets.")
        return bounds[a][0], bounds[b-1][1]
    gold, got = {}, {}
    for span in spans:
        gold.setdefault(span.document_id, []).append(interval(span))
    for c in selected:
        got.setdefault(c.document_id, []).append(interval(c))
    total = sum(length(v) for v in gold.values())
    if not total:
        raise ValueError("Positive gold coverage is required.")
    selected_length = sum(length(v) for v in got.values())
    intersection = sum(overlap(v, gold.get(did, [])) for did, v in got.items())
    return {"character_recall": intersection / total,
            "character_precision": intersection / selected_length if selected_length else 0.,
            "character_iou": intersection / (total + selected_length - intersection),
            "selected_chunk_count": len(selected), "gold_character_count": total,
            "selected_union_character_count": selected_length}
