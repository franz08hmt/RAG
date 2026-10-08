from __future__ import annotations

from collections.abc import Iterable


def summarize_generation_pilot(rows: Iterable[dict]) -> dict:
    results = list(rows)
    answerable = [row for row in results if row["answerability"] == "answerable"]
    unanswerable = [row for row in results if row["answerability"] == "unanswerable"]
    if len(answerable) + len(unanswerable) != len(results):
        raise ValueError("Mỗi nhãn answerability phải là answerable hoặc unanswerable.")

    answered_answerable = sum(not row["abstained"] for row in answerable)
    refused_unanswerable = sum(row["abstained"] for row in unanswerable)
    cited_expected_document = sum(row["cited_expected_document"] for row in answerable)
    generated = [row for row in results if not row["abstained"]]
    valid_generated_citations = sum(row["citation_ids_valid"] is True for row in generated)
    return {
        "question_count": len(results),
        "answerable_count": len(answerable),
        "unanswerable_count": len(unanswerable),
        "answerable_response_rate": {
            "count": answered_answerable,
            "denominator": len(answerable),
            "value": answered_answerable / len(answerable) if answerable else None,
        },
        "unanswerable_refusal_rate": {
            "count": refused_unanswerable,
            "denominator": len(unanswerable),
            "value": refused_unanswerable / len(unanswerable) if unanswerable else None,
        },
        "answerable_citing_expected_document_rate": {
            "count": cited_expected_document,
            "denominator": len(answerable),
            "value": cited_expected_document / len(answerable) if answerable else None,
        },
        "valid_citation_id_rate": {
            "count": valid_generated_citations,
            "denominator": len(generated),
            "value": (
                valid_generated_citations / len(generated)
                if generated
                else None
            ),
        },
        "interpretation": (
            "Development-only process metrics. Answer text is not judged for correctness or entailment; "
            "source-ID validity and expected-document overlap are not semantic citation verification."
        ),
    }
