from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import time

print(f"Python executable: {sys.executable}")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import pymupdf
from rag_hcmute.ingestion.manifest import read_manifest, sha256_file
from rag_hcmute.ingestion.page_artifacts import inspect_page, render_source_crop


def main() -> int:
    parser = argparse.ArgumentParser(description="Local metadata audit of text/table/image page artifacts; G0 is unchanged.")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "artifacts/results/m2_input")
    parser.add_argument("--include-3116", type=Path)
    parser.add_argument("--export-review-pages", action="store_true", help="Render the fixed public academic-content examples locally for visual/PII review.")
    args = parser.parse_args()
    output = args.output_dir.resolve()
    if not output.is_relative_to((ROOT / "artifacts/results").resolve()):
        parser.error("Output must stay inside ignored artifacts/results.")
    _, rows = read_manifest(ROOT / "data/manifests/corpus_manifest.csv")
    sources = [(row["document_id"], ROOT / row["local_path"], row["file_sha256"], row["source_url"], True) for row in rows]
    if args.include_3116:
        sources.append(("HCMUTE_QCDT_3116_2025", args.include_3116.resolve(), "604ca10460ab92f3b329e3cc3572cff6c148fad4a40b243ff50e095eee34d8a9", "https://aao.hcmute.edu.vn/?ArticleId=fb49599f-d6e6-402e-806f-94cbc153e9e1", False))
    # Validate every source before producing any output.
    for doc_id, path, digest, _, _ in sources:
        if sha256_file(path) != digest:
            raise ValueError(f"SHA-256 mismatch for {doc_id}; audit stopped.")
    output.mkdir(parents=True, exist_ok=True)
    metrics_path = output / "input_artifacts_metrics.json"
    if metrics_path.exists():
        raise FileExistsError(metrics_path)
    selected = {"HCMUTE_QCDT_1727_2021": [20], "HCMUTE_SOTAYSV_2024": [107, 109, 116, 136], "HCMUTE_QCDT_3116_2025": [3]}
    report = {"created_at_utc": datetime.now(timezone.utc).isoformat(), "pymupdf_version": pymupdf.__version__, "snapshot_id": "5da3bd4d5de54492", "status": "metadata_audit_not_accuracy_benchmark", "git_revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(), "script_sha256": sha256_file(Path(__file__)), "module_sha256": sha256_file(ROOT / "src/rag_hcmute/ingestion/page_artifacts.py"), "privacy": "Metadata only. Page renders are local review evidence and must be visually checked before report inclusion.", "documents": [], "review_figures": []}
    for doc_id, source, digest, url, in_g0 in sources:
        started = time.perf_counter()
        with pymupdf.open(source) as pdf:
            pages = [inspect_page(page, doc_id, digest).to_dict() for page in pdf]
            summaries = {
                "document_id": doc_id, "source_sha256": digest, "source_url": url, "in_g0": in_g0,
                "page_count": len(pages), "routing_counts": dict(Counter(p["routing_hint"] for p in pages)),
                "pages_with_raster": sum(bool(p["raster_images"]) for p in pages),
                "raster_occurrences": sum(len(p["raster_images"]) for p in pages),
                "pages_with_table_candidates": sum(bool(p["table_candidates"]) for p in pages),
                "table_candidates": sum(len(p["table_candidates"]) for p in pages),
                "table_detection_errors": sum(p["table_detection_error"] is not None for p in pages),
                "inspection_seconds": round(time.perf_counter() - started, 3), "pages": pages,
            }
            report["documents"].append(summaries)
            print(json.dumps({k:v for k,v in summaries.items() if k != "pages"}, ensure_ascii=True))
            if args.export_review_pages:
                for page_number in selected.get(doc_id, []):
                    page = pdf[page_number - 1]
                    path = output / "figures" / f"{doc_id}_p{page_number:03d}_source.png"
                    rendered = render_source_crop(page, list(page.rect), path)
                    report["review_figures"].append({**rendered, "document_id": doc_id, "source_sha256": digest, "source_url": url, "path": path.relative_to(output).as_posix(), "review_status": "requires_visual_pii_review"})
    with metrics_path.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
    print(f"Metadata output: {metrics_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
