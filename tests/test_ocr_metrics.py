import pytest

from rag_hcmute.evaluation.ocr_metrics import (
    calculate_ocr_critical_token_metrics,
    calculate_ocr_error_rates,
)


def test_ocr_metrics_ignore_case_and_canonical_unicode_variants() -> None:
    rates = calculate_ocr_error_rates("Tâm thần\nViệt Nam", "tâm thần   việt nam")

    assert rates.cer == 0.0
    assert rates.wer == 0.0


def test_ocr_metrics_keep_diacritic_errors_and_normalize_word_punctuation() -> None:
    rates = calculate_ocr_error_rates("sức khỏe tâm thần", "sức khỏe tâm thân!")

    assert rates.character_edits > 0
    assert rates.word_edits == 1
    assert rates.reference_words == 4


def test_ocr_metrics_reject_empty_reference() -> None:
    with pytest.raises(ValueError, match="reference"):
        calculate_ocr_error_rates("   ", "some OCR text")


def test_critical_token_metrics_return_only_aggregate_exact_match_rates() -> None:
    metrics = calculate_ocr_critical_token_metrics(
        "Điều 3 năm 2024: không được rút ngắn thời hạn.",
        "Điều 3 năm 2024: không được rút ngắn thời hạn; xem mục 5.",
    )

    assert metrics["numeric_tokens"] == {
        "reference_count": 2,
        "hypothesis_count": 3,
        "exact_match_count": 2,
        "precision": pytest.approx(2 / 3),
        "recall": 1.0,
    }
    assert metrics["critical_cues"] == {
        "reference_count": 1,
        "hypothesis_count": 1,
        "exact_match_count": 1,
        "precision": 1.0,
        "recall": 1.0,
    }
    assert "2024" not in str(metrics)
    assert "không" not in str(metrics)


def test_critical_token_metrics_normalize_case_and_unicode() -> None:
    metrics = calculate_ocr_critical_token_metrics(
        "Tối thiểu 2 lần; chưa đủ.",
        "TỐI THIỂU 2 lần; CHƯA đủ.",
    )

    assert metrics["numeric_tokens"]["recall"] == 1.0
    assert metrics["critical_cues"]["recall"] == 1.0
