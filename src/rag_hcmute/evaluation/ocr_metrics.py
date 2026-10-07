from __future__ import annotations

import re
import unicodedata
from collections import Counter
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class OCRErrorRates:
    character_edits: int
    reference_characters: int
    word_edits: int
    reference_words: int

    @property
    def cer(self) -> float:
        return self.character_edits / self.reference_characters

    @property
    def wer(self) -> float:
        return self.word_edits / self.reference_words

    def to_dict(self) -> dict[str, int | float]:
        return {**asdict(self), "cer": self.cer, "wer": self.wer}


def _normalize_text(text: str, *, keep_punctuation: bool) -> str:
    normalized = unicodedata.normalize("NFC", text).casefold()
    characters: list[str] = []
    for character in normalized:
        category = unicodedata.category(character)
        if character.isspace():
            characters.append(" ")
        elif not keep_punctuation and category[0] in {"P", "S"}:
            characters.append(" ")
        else:
            characters.append(character)
    return " ".join("".join(characters).split())


def _edit_distance(reference: str | list[str], hypothesis: str | list[str]) -> int:
    if len(reference) < len(hypothesis):
        reference, hypothesis = hypothesis, reference

    previous_row = list(range(len(hypothesis) + 1))
    for reference_index, reference_item in enumerate(reference, start=1):
        current_row = [reference_index]
        for hypothesis_index, hypothesis_item in enumerate(hypothesis, start=1):
            insertion = current_row[hypothesis_index - 1] + 1
            deletion = previous_row[hypothesis_index] + 1
            substitution = previous_row[hypothesis_index - 1] + (reference_item != hypothesis_item)
            current_row.append(min(insertion, deletion, substitution))
        previous_row = current_row
    return previous_row[-1]


def calculate_ocr_error_rates(reference: str, hypothesis: str) -> OCRErrorRates:
    """Compute NFC-normalized CER/WER while preserving Vietnamese diacritics.

    CER preserves punctuation and counts normalized whitespace characters. WER
    treats punctuation/symbols as token separators. Both metrics are case-folded.
    """
    reference_chars = _normalize_text(reference, keep_punctuation=True)
    hypothesis_chars = _normalize_text(hypothesis, keep_punctuation=True)
    reference_words = _normalize_text(reference, keep_punctuation=False).split()
    hypothesis_words = _normalize_text(hypothesis, keep_punctuation=False).split()
    if not reference_chars or not reference_words:
        raise ValueError("OCR reference must contain at least one non-whitespace character.")

    return OCRErrorRates(
        character_edits=_edit_distance(reference_chars, hypothesis_chars),
        reference_characters=len(reference_chars),
        word_edits=_edit_distance(reference_words, hypothesis_words),
        reference_words=len(reference_words),
    )


_NUMBERISH_TOKEN = re.compile(r"(?u)(?<!\w)[\w]+(?:[./,:%+\-][\w]+)*%?(?!\w)")
_CRITICAL_CUE_TERMS = (
    "không được",
    "tối thiểu",
    "ít nhất",
    "tối đa",
    "không",
    "chưa",
    "chỉ",
    "trừ",
    "nếu",
    "phải",
)
_CRITICAL_CUE = re.compile(
    r"(?u)(?<!\w)(?:"
    + "|".join(re.escape(term) for term in sorted(_CRITICAL_CUE_TERMS, key=len, reverse=True))
    + r")(?!\w)"
)


def _normalized_occurrences(
    pattern: re.Pattern[str], text: str, *, numeric_only: bool = False
) -> Counter[str]:
    normalized = unicodedata.normalize("NFC", text).casefold()
    occurrences = Counter(match.group(0) for match in pattern.finditer(normalized))
    if numeric_only:
        return Counter(
            {
                token: count
                for token, count in occurrences.items()
                if any(char.isdigit() for char in token)
            }
        )
    return occurrences


def _occurrence_rates(
    reference: Counter[str], hypothesis: Counter[str]
) -> dict[str, int | float | None]:
    reference_count = sum(reference.values())
    hypothesis_count = sum(hypothesis.values())
    exact_match_count = sum((reference & hypothesis).values())
    return {
        "reference_count": reference_count,
        "hypothesis_count": hypothesis_count,
        "exact_match_count": exact_match_count,
        "precision": exact_match_count / hypothesis_count if hypothesis_count else None,
        "recall": exact_match_count / reference_count if reference_count else None,
    }


def calculate_ocr_critical_token_metrics(
    reference: str, hypothesis: str
) -> dict[str, dict[str, int | float | None]]:
    """Measure exact occurrence precision/recall for numeric tokens and critical cues.

    The returned data contains aggregate counts and rates only; token/cue strings
    are intentionally not included. This is a targeted OCR diagnostic, not a
    substitute for reviewing the underlying page against its source.
    """
    reference_numbers = _normalized_occurrences(_NUMBERISH_TOKEN, reference, numeric_only=True)
    hypothesis_numbers = _normalized_occurrences(_NUMBERISH_TOKEN, hypothesis, numeric_only=True)
    reference_cues = _normalized_occurrences(_CRITICAL_CUE, reference)
    hypothesis_cues = _normalized_occurrences(_CRITICAL_CUE, hypothesis)
    return {
        "numeric_tokens": _occurrence_rates(reference_numbers, hypothesis_numbers),
        "critical_cues": _occurrence_rates(reference_cues, hypothesis_cues),
    }
