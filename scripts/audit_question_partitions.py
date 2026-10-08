from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from rag_hcmute.evaluation.question_partitions import (  # noqa: E402
    validate_question_partition_manifest,
)


def main() -> int:
    print(f"Python executable: {sys.executable}", file=sys.stderr)
    report = validate_question_partition_manifest()
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
