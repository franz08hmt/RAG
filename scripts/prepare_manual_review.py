from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from rag_hcmute.evaluation.manual_review import prepare_review_sheets  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Tạo phiếu answer/claim đang chờ chấm từ bundle cục bộ; đầu ra chỉ chứa ID và nhãn."
    )
    parser.add_argument("--bundle", type=Path, required=True, help="Private JSONL review bundle.")
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path(r"D:\RAG\private_eval\manual_review"),
        help="Thư mục ngoài repository để lưu phiếu đánh giá.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")
    print(f"Python executable: {sys.executable}")
    args = build_parser().parse_args(argv)
    try:
        answers_path, claims_path, row_count = prepare_review_sheets(
            args.bundle,
            output_root=args.output_root,
            project_root=PROJECT_ROOT,
        )
    except (OSError, ValueError, FileExistsError) as exc:
        raise SystemExit(f"Manual review sheet preparation stopped: {exc}") from exc
    print(f"Created pending answer rows: {row_count}")
    print(f"Answer sheet: {answers_path}")
    print(f"Claim sheet: {claims_path}")
    print("Question/answer/source text was not copied into the sheets.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
