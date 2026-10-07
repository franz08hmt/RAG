from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


print(f"Python executable: {sys.executable}")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import pymupdf  # noqa: E402

from rag_hcmute.evaluation.ocr_metrics import (  # noqa: E402
    calculate_ocr_critical_token_metrics,
    calculate_ocr_error_rates,
)
from rag_hcmute.ingestion.extract import (  # noqa: E402
    OCRSettings,
    _resolve_tesseract_cmd,
    _run_page_ocr,
)

PAGES = (107, 109, 116, 136)
DPIS = (200, 300)
PSMS = (4, 11)
DOCUMENT_ID = "HCMUTE_SOTAYSV_2024"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _load_source_hash(manifest_path: Path, document_id: str) -> str:
    with manifest_path.open("r", encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            if row.get("document_id") == document_id:
                return row["file_sha256"].strip().lower()
    raise ValueError(f"Document ID not found in manifest: {document_id}")


def _git_revision() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=PROJECT_ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unavailable"


def _rates_from_counts(reference_count: int, hypothesis_count: int, exact_match_count: int) -> dict:
    return {
        "reference_count": reference_count,
        "hypothesis_count": hypothesis_count,
        "exact_match_count": exact_match_count,
        "precision": exact_match_count / hypothesis_count if hypothesis_count else None,
        "recall": exact_match_count / reference_count if reference_count else None,
    }


def run_sweep(
    *,
    pdf_path: Path,
    reference_dir: Path,
    tessdata_dir: Path,
    tesseract_cmd: Path | None,
) -> dict:
    manifest_hash = _load_source_hash(
        PROJECT_ROOT / "data/manifests/corpus_manifest.csv", DOCUMENT_ID
    )
    actual_hash = _sha256(pdf_path)
    if actual_hash != manifest_hash:
        raise SystemExit("Source PDF SHA-256 differs from the corpus manifest; stopping.")

    language_model = tessdata_dir / "vie.traineddata"
    if not language_model.is_file():
        raise FileNotFoundError(f"Vietnamese OCR model not found: {language_model}")
    language_model_hash = _sha256(language_model)

    base_settings = OCRSettings(
        language="vie",
        tessdata_dir=tessdata_dir.resolve(),
        tesseract_cmd=tesseract_cmd.resolve() if tesseract_cmd else None,
        dpi=DPIS[0],
        page_segmentation_mode=PSMS[0],
    )
    executable = _resolve_tesseract_cmd(base_settings)
    version = subprocess.run(
        [str(executable), "--version"], check=True, capture_output=True, text=True
    ).stdout.splitlines()[0]

    page_results: list[dict] = []
    with pymupdf.open(pdf_path) as document:
        if max(PAGES) > document.page_count:
            raise ValueError("An OCR sample page is outside the source PDF.")

        for page_number in PAGES:
            reference_path = reference_dir / f"g1_ocr_reference_page{page_number}.json"
            with reference_path.open("r", encoding="utf-8") as stream:
                reference_data = json.load(stream)
            if reference_data.get("pdf_page") != page_number:
                raise ValueError(f"Reference page mismatch for page {page_number}.")
            reference_text = reference_data.get("reference_text")
            if not isinstance(reference_text, str):
                raise ValueError(f"Reference text missing for page {page_number}.")

            for dpi in DPIS:
                for psm in PSMS:
                    settings = OCRSettings(
                        language="vie",
                        tessdata_dir=tessdata_dir.resolve(),
                        tesseract_cmd=executable,
                        dpi=dpi,
                        page_segmentation_mode=psm,
                    )
                    hypothesis, confidence = _run_page_ocr(
                        document.load_page(page_number - 1), settings
                    )
                    metrics = calculate_ocr_error_rates(reference_text, hypothesis)
                    metric_data = metrics.to_dict()
                    critical_metrics = calculate_ocr_critical_token_metrics(
                        reference_text, hypothesis
                    )
                    page_results.append(
                        {
                            "pdf_page": page_number,
                            "dpi": dpi,
                            "psm": psm,
                            **metric_data,
                            "numeric_tokens": critical_metrics["numeric_tokens"],
                            "critical_cues": critical_metrics["critical_cues"],
                            "ocr_confidence_mean": confidence,
                        }
                    )

    totals: dict[tuple[int, int], dict[str, int]] = defaultdict(
        lambda: {
            "character_edits": 0,
            "reference_characters": 0,
            "word_edits": 0,
            "reference_words": 0,
            "number_reference_count": 0,
            "number_hypothesis_count": 0,
            "number_exact_match_count": 0,
            "cue_reference_count": 0,
            "cue_hypothesis_count": 0,
            "cue_exact_match_count": 0,
            "page_count": 0,
        }
    )
    for row in page_results:
        group = totals[(row["dpi"], row["psm"])]
        for key in ("character_edits", "reference_characters", "word_edits", "reference_words"):
            group[key] += int(row[key])
        for metric_name, prefix in (("numeric_tokens", "number"), ("critical_cues", "cue")):
            metric = row[metric_name]
            for metric_key, total_key in (
                ("reference_count", f"{prefix}_reference_count"),
                ("hypothesis_count", f"{prefix}_hypothesis_count"),
                ("exact_match_count", f"{prefix}_exact_match_count"),
            ):
                group[total_key] += int(metric[metric_key])
        group["page_count"] += 1

    aggregate_results = []
    for (dpi, psm), counts in sorted(totals.items()):
        numbers = _rates_from_counts(
            counts["number_reference_count"],
            counts["number_hypothesis_count"],
            counts["number_exact_match_count"],
        )
        cues = _rates_from_counts(
            counts["cue_reference_count"],
            counts["cue_hypothesis_count"],
            counts["cue_exact_match_count"],
        )
        aggregate_results.append(
            {
                "dpi": dpi,
                "psm": psm,
                **counts,
                "cer": counts["character_edits"] / counts["reference_characters"],
                "wer": counts["word_edits"] / counts["reference_words"],
                "numeric_tokens": numbers,
                "critical_cues": cues,
            }
        )

    return {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "git_revision": _git_revision(),
        "script_sha256": _sha256(Path(__file__).resolve()),
        "document_id": DOCUMENT_ID,
        "source_pdf_sha256": actual_hash,
        "language": "vie",
        "language_model_sha256": language_model_hash,
        "tesseract_version": version,
        "dpi_values": list(DPIS),
        "psm_values": list(PSMS),
        "sample_pages": list(PAGES),
        "metric_method": "NFC/case-fold; CER preserves punctuation and whitespace; WER separates punctuation",
        "critical_metric_method": "Exact occurrence precision/recall for numeric tokens and a fixed condition/negation cue inventory; identities are not written",
        "privacy_note": "Metrics and configuration only; reference and OCR text or extracted token identities are not written.",
        "page_results": page_results,
        "weighted_aggregates": aggregate_results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compare local Vietnamese OCR metrics at 200 and 300 DPI without saving OCR text."
    )
    parser.add_argument(
        "--pdf", type=Path, default=PROJECT_ROOT / "data/raw/HCMUTE_SOTAYSV_2024.pdf"
    )
    parser.add_argument(
        "--reference-dir", type=Path, default=PROJECT_ROOT / "artifacts/results"
    )
    parser.add_argument(
        "--tessdata-dir", type=Path, default=Path(r"D:\RAG\models\tesseract\tessdata")
    )
    parser.add_argument("--tesseract-cmd", type=Path)
    parser.add_argument(
        "--output-dir", type=Path, default=PROJECT_ROOT / "artifacts/results/ocr_dpi_sensitivity"
    )
    args = parser.parse_args()

    report = run_sweep(
        pdf_path=args.pdf.resolve(),
        reference_dir=args.reference_dir.resolve(),
        tessdata_dir=args.tessdata_dir.resolve(),
        tesseract_cmd=args.tesseract_cmd,
    )

    output_dir = args.output_dir.resolve()
    ignored_root = (PROJECT_ROOT / "artifacts/results").resolve()
    if not output_dir.is_relative_to(ignored_root):
        raise SystemExit("--output-dir must remain under Git-ignored artifacts/results.")
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_path = output_dir / f"ocr_dpi_sensitivity_{timestamp}.json"
    with output_path.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write("\n")

    for row in report["weighted_aggregates"]:
        number_recall = row["numeric_tokens"]["recall"]
        cue_recall = row["critical_cues"]["recall"]
        number_text = f"{number_recall:.4f}" if number_recall is not None else "n/a"
        cue_text = f"{cue_recall:.4f}" if cue_recall is not None else "n/a"
        print(
            f"dpi={row['dpi']} psm={row['psm']} pages={row['page_count']} "
            f"CER={row['cer']:.4f} WER={row['wer']:.4f} "
            f"number_recall={number_text} cue_recall={cue_text}"
        )
    print(f"Metrics-only output (Git-ignored): {output_path}")
    print(f"Tesseract: {report['tesseract_version']} | source SHA-256: {report['source_pdf_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
