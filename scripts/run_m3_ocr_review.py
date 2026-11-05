"""Run local Vietnamese OCR on the ten review images. Keep all text private."""
import argparse
import csv
import hashlib
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


def main():
    print(f"Python executable: {sys.executable}", flush=True)
    parser = argparse.ArgumentParser()
    parser.add_argument("--package", required=True, type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    private = Path("D:/RAG/private_eval/m3_review").resolve()
    package = args.package.resolve()
    if not package.is_relative_to(private):
        raise ValueError("Expected a local review package outside Git.")
    exe = Path(sys.prefix) / "Library/bin/tesseract.exe"
    tessdata = Path("D:/RAG/models/tesseract/tessdata")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    outputs = package / f"ocr_predictions_{stamp}"
    outputs.mkdir(exist_ok=False)
    report = {"run_id": f"ocr_{stamp}", "engine": subprocess.check_output([exe, "--version"], text=True).splitlines()[0],
              "image_dpi": 180, "psm": 6, "language": "vie",
              "traineddata_sha256": hashlib.sha256((tessdata/"vie.traineddata").read_bytes()).hexdigest(),
              "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "accuracy_evaluation": "pending_human_transcription", "pages": []}
    with (package/"ocr_review.csv").open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    for row in rows:
        folder = (package / row["gold_relative_path"]).resolve().parent
        if not folder.is_relative_to(package):
            raise ValueError("Unexpected review path.")
        image = folder / "source.png"
        started = time.perf_counter()
        process = subprocess.run([exe, str(image), "stdout", "--tessdata-dir", str(tessdata),
                                  "-l", "vie", "--psm", "6", "--dpi", "180"],
                                 check=True, capture_output=True, timeout=120)
        elapsed = time.perf_counter() - started
        text = process.stdout.decode("utf-8")
        (outputs/f"{folder.name}.txt").write_text(text, encoding="utf-8")
        report["pages"].append({"document_id": row["document_id"], "pdf_page": int(row["pdf_page"]),
            "pdf_sha256":row["source_sha256"], "image_sha256":hashlib.sha256(image.read_bytes()).hexdigest(),
            "ocr_characters":len(text.strip()), "native_characters":len((folder/"native_draft.txt").read_text(encoding="utf-8").strip()),
            "seconds":elapsed})
    output = root / f"artifacts/results/m3/ocr_{stamp}.json"
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(f"{len(rows)} pages. Metrics: {output}")


if __name__ == "__main__":
    main()
