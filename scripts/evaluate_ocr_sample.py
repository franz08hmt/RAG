from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

print(f"Python executable: {sys.executable}")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import pymupdf  # noqa: E402

from rag_hcmute.evaluation.ocr_metrics import calculate_ocr_error_rates  # noqa: E402
from rag_hcmute.ingestion.extract import OCRSettings, _run_page_ocr  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Evaluate one local PDF page against a manually transcribed JSON reference."
    )
    parser.add_argument("--pdf", type=Path, required=True)
    parser.add_argument("--page", type=int, required=True, help="1-indexed PDF page number.")
    parser.add_argument("--reference", type=Path, required=True, help="Local JSON containing reference_text.")
    parser.add_argument("--language", default="vie")
    parser.add_argument("--tessdata-dir", type=Path, required=True)
    parser.add_argument("--tesseract-cmd", type=Path)
    parser.add_argument("--dpi", type=int, default=200)
    parser.add_argument("--psm", type=int, default=6)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.page < 1:
        raise SystemExit("--page must be a 1-indexed positive integer.")

    with args.reference.open("r", encoding="utf-8") as reference_file:
        reference_data = json.load(reference_file)
    reference_page = reference_data.get("pdf_page")
    if reference_page is not None and reference_page != args.page:
        raise SystemExit(f"Reference is for PDF page {reference_page}, but --page={args.page}.")
    reference_text = reference_data.get("reference_text")
    if not isinstance(reference_text, str):
        raise SystemExit("Reference JSON must contain a string field named 'reference_text'.")

    settings = OCRSettings(
        language=args.language,
        tessdata_dir=args.tessdata_dir.resolve(),
        tesseract_cmd=args.tesseract_cmd.resolve() if args.tesseract_cmd else None,
        dpi=args.dpi,
        page_segmentation_mode=args.psm,
    )
    with pymupdf.open(args.pdf) as document:
        if args.page > document.page_count:
            raise SystemExit(f"PDF has {document.page_count} pages; --page={args.page} is out of range.")
        hypothesis, confidence = _run_page_ocr(document.load_page(args.page - 1), settings)

    metrics = calculate_ocr_error_rates(reference_text, hypothesis)
    result = metrics.to_dict()
    result.update(
        {
            "pdf_page": args.page,
            "ocr_confidence_mean": confidence,
            "language": settings.language,
            "dpi": settings.dpi,
            "page_segmentation_mode": settings.page_segmentation_mode,
            "reference_id": reference_data.get("reference_id"),
        }
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
