"""Combine the existing review queue and new source-linked drafts outside Git."""
import argparse
import csv
import html
import json
import sys
from collections import Counter
from pathlib import Path

OLD_GROUPS = {
    "P001": "art16", "P002": "art9", "P003": "art13", "P004": "art9",
    "P005": "internship", "P006": "thesis", "P007": "art17", "P008": "art13-14",
    "P009": "future_event", "P010": "future_event", "C001": "art2", "C002": "art3",
    "C003": "art10", "C004": "art11", "C005": "art11", "C006": "art12", "C007": "art15",
    "C008": "art18", "C009": "art20", "C010": "art22", "C011": "internship", "C012": "scholarship",
}
ROOT = Path(__file__).resolve().parents[1]


def main():
    print(f"Python executable: {sys.executable}")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prior", type=Path, required=True)
    parser.add_argument("--drafts", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.resolve().is_relative_to(ROOT):
        raise ValueError("Review data belongs outside the repository.")
    with args.prior.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        rows = list(reader)
        fields = reader.fieldnames
    for row in rows:
        qid = row["question_id"]
        if row["review_status"] == "pending":
            row["leakage_group"] = OLD_GROUPS.get(qid, "table5" if qid.startswith("TB") else row["leakage_group"])
    drafts = json.loads(args.drafts.read_text(encoding="utf-8"))
    for case in drafts.values():
        evidence = case["evidence"]
        rows.append({
            "question_id": case["id"], "question": case["question"], "snapshot_id": "5da3bd4d5de54492",
            "created_by": "ai_draft", "review_status": "pending", "verified_by": "", "verified_at": "",
            "answerability": "answerable" if evidence else "unanswerable",
            "reference_answer": case["reference"], "evidence_json": json.dumps(evidence, ensure_ascii=False),
            "absence_review_note": "" if evidence else case["reference"],
            "tags": case["tags"], "leakage_group": case["group"], "split": "",
            "source_document_hint": evidence[0]["document_id"] if evidence else "",
            "source_page_hint": str(evidence[0]["pdf_page"]) if evidence else "",
        })
    if len({row["question_id"] for row in rows}) != len(rows):
        raise ValueError("Duplicate question IDs.")
    args.output.mkdir(parents=True, exist_ok=False)
    with (args.output / "question_review.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    sections = []
    escape = html.escape
    for row in rows:
        quotes = []
        for source in json.loads(row["evidence_json"] or "[]"):
            if isinstance(source, dict):
                label = f"{source.get('document_id', '')} · PDF trang {source.get('pdf_page', '')}"
                quotes.append(f"<p><strong>{escape(label)}</strong> {escape(source.get('quote', ''))}</p>")
        sections.append(
            f"<details><summary>{escape(row['question_id'])} · {escape(row['question'])}</summary>"
            f"<p>{escape(row['reference_answer'] or 'Đáp án đang chờ duyệt.')}</p>"
            f"<p>Nhóm {escape(row['leakage_group'])} · {escape(row['review_status'])}</p>"
            + "".join(quotes) + "</details>"
        )
    title = f"Phiếu duyệt {len(rows)} mục hỏi đáp học vụ"
    page = f"""<!doctype html><html lang="vi"><meta charset="utf-8"><title>{title}</title>
<style>body{{max-width:54rem;margin:2rem auto;padding:0 1rem;font:1rem/1.5 system-ui;color:#171717}}
details{{border-top:1px solid #ddd;padding:.5rem 0}}summary{{cursor:pointer}}a{{color:#17467d}}</style>
<h1>{title}</h1>
<p>Snapshot G0. Câu hỏi và đáp án trong gói này là đề xuất cần đối chiếu với PDF.
Mười câu pilot tiếp tục thuộc development. Các câu F/U đã dùng cho thực nghiệm mở rộng
và cần được giữ ngoài tập test độc lập về sau.</p>
<p>Mở <a href="question_review.csv">phiếu CSV</a> để ghi kết quả. Giữ các câu gần nhau trong cùng nhóm.
Khi đối chiếu xong, điền người và thời gian duyệt. Phần câu hỏi sinh viên tự viết có thể đưa vào
bộ đánh giá riêng rồi tách nhóm trước khi chạy.</p>
{"".join(sections)}
</html>"""
    (args.output / "START_HERE.html").write_text(page, encoding="utf-8")
    print(dict(Counter(row["review_status"] for row in rows)))


if __name__ == "__main__":
    main()

