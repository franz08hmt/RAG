from __future__ import annotations

import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_ROOT))

from rag_hcmute.ingestion.chunk import DEFAULT_CHUNK_TOKENS, DEFAULT_OVERLAP_TOKENS  # noqa: E402
from rag_hcmute.ingestion.pipeline import build_snapshot  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Trich xuat PDF theo trang, lam sach, chia chunk va dong snapshot corpus tu manifest."
    )
    parser.add_argument("--manifest", type=Path, default=PROJECT_ROOT / "data/manifests/corpus_manifest.csv")
    parser.add_argument("--project-root", type=Path, default=PROJECT_ROOT)
    parser.add_argument("--pages-output-dir", type=Path, default=PROJECT_ROOT / "data/processed/pages")
    parser.add_argument("--chunks-output-dir", type=Path, default=PROJECT_ROOT / "data/processed/chunks")
    parser.add_argument("--snapshot-manifest", type=Path, default=PROJECT_ROOT / "data/manifests/corpus_snapshot.json")
    parser.add_argument("--build-log", type=Path, default=PROJECT_ROOT / "artifacts/logs/build_corpus.log")
    parser.add_argument("--chunk-tokens", type=int, default=DEFAULT_CHUNK_TOKENS)
    parser.add_argument("--overlap-tokens", type=int, default=DEFAULT_OVERLAP_TOKENS)
    return parser


def main() -> int:
    args = build_parser().parse_args()

    snapshot = build_snapshot(
        manifest_path=args.manifest,
        project_root=args.project_root,
        pages_output_dir=args.pages_output_dir,
        chunks_output_dir=args.chunks_output_dir,
        snapshot_manifest_path=args.snapshot_manifest,
        build_log_path=args.build_log,
        chunk_tokens=args.chunk_tokens,
        overlap_tokens=args.overlap_tokens,
    )

    totals = snapshot["totals"]
    print(f"Snapshot ID: {snapshot['snapshot_id']}")
    print(
        f"Documents: {totals['document_count']} (skipped: {totals['skipped_document_count']}) | "
        f"Pages: {totals['page_count']} | Chunks: {totals['chunk_count']} | "
        f"Probable-scan pages: {totals['probable_scan_page_count']}"
    )
    if totals["document_count"] == 0:
        print("CANH BAO: khong co tai lieu nao duoc xu ly. Kiem tra manifest va data/raw/.")
        return 1
    print(f"Chunks file: {snapshot['chunks_file']}")
    print(f"Snapshot manifest: {args.snapshot_manifest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
