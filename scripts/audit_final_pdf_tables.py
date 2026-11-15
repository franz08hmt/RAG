"""Compare extraction with reference cells transcribed from selected G0 table rows."""
import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parents[1]
DOC_ID = "HCMUTE_QCDT_1727_2021"


def main():
    print(f"Python executable: {sys.executable}")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", required=True, type=Path)
    parser.add_argument("--metrics", required=True, type=Path)
    args = parser.parse_args()
    with (ROOT / "data/manifests/corpus_manifest.csv").open(encoding="utf-8-sig", newline="") as stream:
        source = next(row for row in csv.DictReader(stream) if row["document_id"] == DOC_ID)
    pdf = ROOT / source["local_path"]
    digest = hashlib.sha256(pdf.read_bytes()).hexdigest()
    if digest != source["file_sha256"]:
        raise ValueError("Source PDF checksum mismatch.")
    reference = json.loads(args.reference.read_text(encoding="utf-8"))
    tables, results = {}, []
    with pymupdf.open(pdf) as document:
        for page in sorted({row[0] for row in reference}):
            page_obj = document[page-1]
            tables[page] = {strategy: [table.extract() for table in page_obj.find_tables(strategy=strategy).tables]
                            for strategy in ("lines", "text")}
        for index, (page, table_id, row_id, offset, expected) in enumerate(reference, 1):
            table = tables[page]["lines"][table_id]
            actual = [" ".join((cell or "").split()) for cell in table[row_id][offset:offset+len(expected)]]
            matched = sum(a == b for a, b in zip(actual, expected))
            results.append({"reference_id": index, "pdf_page": page, "table_index": table_id,
                            "row_index": row_id, "exact_cells": matched, "reference_cells": len(expected),
                            "exact_row": actual == expected})
    output = {"source_sha256": digest, "reference_sha256": hashlib.sha256(args.reference.read_bytes()).hexdigest(),
              "reference_origin": "visual_transcription_by_ai_assistant_not_student_verified",
              "pymupdf_version": pymupdf.__version__, "rows": results,
              "exact_rows": sum(row["exact_row"] for row in results), "reference_rows": len(results),
              "exact_cells": sum(row["exact_cells"] for row in results),
              "reference_cells": sum(row["reference_cells"] for row in results),
              "detected_shapes": {page: {strategy: [[len(table),len(table[0])] for table in items]
                                         for strategy, items in by_strategy.items()}
                                  for page, by_strategy in tables.items()}}
    with args.metrics.open("x", encoding="utf-8") as stream:
        json.dump(output, stream, indent=2)


if __name__ == "__main__":
    main()

