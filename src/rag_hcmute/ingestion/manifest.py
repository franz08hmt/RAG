from __future__ import annotations

import argparse
import csv
import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


REQUIRED_COLUMNS = {
    "document_id",
    "document_title",
    "document_number",
    "document_type",
    "issued_date",
    "effective_date",
    "source_url",
    "local_path",
    "file_sha256",
    "page_count",
    "language",
    "status",
    "notes",
}

REQUIRED_VALUES = {
    "document_id",
    "document_title",
    "document_type",
    "source_url",
    "local_path",
    "file_sha256",
    "page_count",
    "language",
    "status",
}


@dataclass(frozen=True)
class AuditIssue:
    row_number: int
    field: str
    message: str

    def format(self) -> str:
        return f"row={self.row_number} field={self.field}: {self.message}"


def sha256_file(path: Path, block_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(block_size):
            digest.update(block)
    return digest.hexdigest()


def read_manifest(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        columns = reader.fieldnames or []
        rows = [dict(row) for row in reader]
    return columns, rows


def audit_manifest(manifest_path: Path, project_root: Path) -> list[AuditIssue]:
    columns, rows = read_manifest(manifest_path)
    issues: list[AuditIssue] = []

    missing_columns = sorted(REQUIRED_COLUMNS.difference(columns))
    for column in missing_columns:
        issues.append(AuditIssue(1, column, "missing required column"))
    if missing_columns:
        return issues

    seen_ids: set[str] = set()
    seen_hashes: set[str] = set()

    for row_number, row in enumerate(rows, start=2):
        normalized = {key: (value or "").strip() for key, value in row.items()}

        for field in sorted(REQUIRED_VALUES):
            if not normalized[field]:
                issues.append(AuditIssue(row_number, field, "required value is empty"))

        document_id = normalized["document_id"]
        if document_id in seen_ids:
            issues.append(AuditIssue(row_number, "document_id", "duplicate document_id"))
        elif document_id:
            seen_ids.add(document_id)

        expected_hash = normalized["file_sha256"].lower()
        if expected_hash in seen_hashes and expected_hash:
            issues.append(AuditIssue(row_number, "file_sha256", "duplicate file hash"))
        elif expected_hash:
            seen_hashes.add(expected_hash)

        local_path = project_root / normalized["local_path"]
        if not normalized["local_path"]:
            continue
        if local_path.suffix.lower() != ".pdf":
            issues.append(AuditIssue(row_number, "local_path", "only PDF files are accepted"))
            continue
        if not local_path.is_file():
            issues.append(AuditIssue(row_number, "local_path", f"file not found: {local_path}"))
            continue

        actual_hash = sha256_file(local_path)
        if expected_hash and actual_hash != expected_hash:
            issues.append(AuditIssue(row_number, "file_sha256", "SHA-256 does not match the file"))

        try:
            page_count = int(normalized["page_count"])
            if page_count <= 0:
                raise ValueError
        except ValueError:
            issues.append(AuditIssue(row_number, "page_count", "must be a positive integer"))

    return issues


def format_report(rows: Iterable[dict[str, str]], issues: list[AuditIssue]) -> str:
    row_count = sum(1 for _ in rows)
    if issues:
        details = "\n".join(f"- {issue.format()}" for issue in issues)
        return f"Manifest audit FAILED: documents={row_count}, issues={len(issues)}\n{details}"
    return f"Manifest audit PASSED: documents={row_count}, issues=0"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Audit the RAG corpus manifest.")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    return parser


def main() -> int:
    args = build_parser().parse_args()
    _, rows = read_manifest(args.manifest)
    issues = audit_manifest(args.manifest, args.project_root.resolve())
    print(format_report(rows, issues))
    return 1 if issues else 0


if __name__ == "__main__":
    raise SystemExit(main())

