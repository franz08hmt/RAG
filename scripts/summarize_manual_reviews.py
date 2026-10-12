from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from rag_hcmute.evaluation.manual_review import (  # noqa: E402
    load_answer_reviews,
    load_claim_reviews,
    summarize_manual_reviews,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Tổng hợp phiếu chấm thủ công; chỉ xuất nhãn và số liệu, không xuất văn bản câu hỏi/đáp án/nguồn."
    )
    parser.add_argument("--answers", type=Path, required=True, help="CSV đánh giá ở cấp câu trả lời.")
    parser.add_argument("--claims", type=Path, required=True, help="CSV đánh giá mức hỗ trợ cho từng claim.")
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "artifacts/results/manual_review/summary.json",
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
        answers = load_answer_reviews(args.answers)
        claims = load_claim_reviews(args.claims)
        summary = summarize_manual_reviews(answers, claims)
    except (OSError, ValueError) as exc:
        raise SystemExit(f"Manual review summary stopped: {exc}") from exc

    report = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "metrics": summary,
    }
    try:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(json.dumps(report, ensure_ascii=False, indent=2))
    except OSError as exc:
        raise SystemExit(f"Không thể tạo summary mới (file đã tồn tại hoặc không ghi được): {args.output}") from exc
    print(f"Reviewed answer rows: {summary['answer_review']['reviewed_count']}/{summary['answer_review']['row_count']}")
    print(f"Reviewed factual claims: {summary['claim_review']['reviewed_count']}/{summary['claim_review']['row_count']}")
    print(f"Summary (labels and aggregates only): {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
