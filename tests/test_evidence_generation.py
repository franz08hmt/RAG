import time

from rag_hcmute.generation.ollama import GroundingSource, _validate_evidence_answer


def payload(quote="Hồ sơ nộp tại văn phòng khoa.", text="Nộp hồ sơ tại văn phòng khoa."):
    return {"abstain": False, "requirements": [{"requirement": "Nơi nộp hồ sơ", "supported": True}],
            "claims": [{"text": text, "source_id": "S1", "quote": quote}]}


def validate(p):
    sources = [GroundingSource("S1", "D_c1", "D", "Doc", 1, 1, None,
                               "Hồ sơ nộp tại văn phòng khoa. Hạn nộp là ngày 15.")]
    return _validate_evidence_answer(p, sources, "local", time.perf_counter())


def test_exact_quote_is_checked_but_not_called_semantic_proof():
    result = validate(payload())
    assert result.status == "generated_quotes_verified_semantics_pending"
    assert result.answer.endswith("[S1]")
    assert not result.abstained


def test_invented_quote_is_rejected():
    assert validate(payload("Nộp ở một nơi hoàn toàn khác.")).status == "invalid_evidence_quote"


def test_missing_core_requirement_blocks_output_without_counting_semantic_refusal():
    p = payload()
    p["requirements"][0]["supported"] = False
    assert validate(p).status == "inconsistent_evidence_assessment"


def test_injected_source_markers_in_claim_are_rejected():
    assert validate(payload(text="Nộp hồ sơ [S9].")).status == "invalid_claim_citation_markup"


def test_refusal_with_claims_is_not_a_success():
    p = payload()
    p["abstain"] = True
    assert validate(p).status == "inconsistent_model_refusal"


def test_quote_match_alone_cannot_detect_non_entailing_claim():
    # Deliberate limitation: human support judgment remains necessary.
    assert validate(payload(text="Sinh viên được miễn toàn bộ học phí.")).status == "generated_quotes_verified_semantics_pending"
