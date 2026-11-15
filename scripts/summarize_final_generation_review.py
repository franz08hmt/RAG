"""Summarize explicit case reviews, keeping reviewer provenance and errors separate."""
import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path

RUNS = {"scope_check": "extended_a", "scope_schema": "scope_schema", "scope_8192": "scope_8192"}
ANSWERS = {"correct_supported", "partial_supported", "incorrect_or_unsupported", "ambiguous_prompt"}


def main():
    print(f"Python executable: {sys.executable}")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reviews", type=Path, required=True)
    parser.add_argument("--runs-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    with args.reviews.open(encoding="utf-8-sig", newline="") as stream:
        reviews = {}
        for row in csv.DictReader(stream):
            key = (row["run"], row["configuration"], row["question_id"])
            if key in reviews or row["label"] not in ANSWERS:
                raise ValueError("Duplicate or unsupported semantic review.")
            reviews[key] = row["label"]
    all_keys = set()
    output = {"reviewer": "ai_assistant_source_comparison_not_human_verified", "results": {}}
    for variant, filename in RUNS.items():
        measured = json.loads((args.runs_dir / f"{filename}.json").read_text(encoding="utf-8"))
        if not measured["completed"]:
            raise ValueError(f"Incomplete run: {variant}")
        summaries = {}
        for row in measured["generation"]:
            config, qid, status = row["configuration"], row["question_id"], row["status"]
            group = summaries.setdefault(config, {"answerable": Counter(), "unanswerable": Counter()})
            counts = group["answerable" if row["answerable"] else "unanswerable"]
            counts["total"] += 1
            key = (variant, config, qid)
            if status.startswith("generated_"):
                counts["answer_emitted"] += 1
                if row["answerable"]:
                    if key not in reviews:
                        raise ValueError(f"Review missing: {key}")
                    all_keys.add(key)
                    counts[reviews[key]] += 1
                else:
                    counts["answer_despite_missing_evidence"] += 1
            elif status == "model_abstained":
                counts["model_abstained"] += 1
            else:
                counts["technical_block"] += 1
            # F39 omits the input scale. Keep its operational status, but exclude
            # it from the denominator of the strict semantic correctness rate.
            if row["answerable"] and qid != "F39":
                counts["unambiguous_total"] += 1
        output["results"][variant] = summaries
    if all_keys != set(reviews):
        raise ValueError("Review contains rows outside emitted answerable cases.")
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(output, stream, indent=2)


if __name__ == "__main__":
    main()

