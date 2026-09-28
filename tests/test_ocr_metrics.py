import pytest

from rag_hcmute.evaluation.ocr_metrics import calculate_ocr_error_rates


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
