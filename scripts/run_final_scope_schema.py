"""Replay the extended study's saved contexts with the scope prompt and JSON schema."""
import argparse
import hashlib
import json
import subprocess
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from rag_hcmute.generation.ollama import GroundingSource, generate_grounded_answer


def main():
    print(f"Python executable: {sys.executable}", flush=True)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--before", required=True, type=Path)
    parser.add_argument("--private-before", required=True, type=Path)
    parser.add_argument("--private-out", required=True, type=Path)
    parser.add_argument("--metrics", required=True, type=Path)
    parser.add_argument("--context-window", type=int)
    args = parser.parse_args()
    if args.metrics.exists() or args.private_out.resolve().is_relative_to(ROOT):
        raise ValueError("Use a new metrics file and a private output directory outside Git.")
    before = json.loads(args.before.read_text(encoding="utf-8"))
    if not before["completed"]:
        raise ValueError("The baseline run must be complete.")
    with urlopen("http://127.0.0.1:11434/api/tags", timeout=10) as response:
        tags = json.load(response)
    digest = next(row["digest"] for row in tags["models"] if row["name"] == "qwen3:4b")
    if digest != before["ollama_model_digest"]:
        raise ValueError("Ollama model digest changed.")
    args.private_out.mkdir(parents=True, exist_ok=False)
    report = {"run_id": datetime.now(timezone.utc).strftime("schema_%Y%m%dT%H%M%SZ"),
              "parent_run": before["config"]["run_id"],
              "parent_metrics_sha256": hashlib.sha256(args.before.read_bytes()).hexdigest(),
              "revision_before_run": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
              "model_digest": digest, "prompt_variant": "scope_schema",
              "generation_max_output_tokens": before["config"]["generation_max_output_tokens"],
              "context_window": args.context_window, "completed": False, "generation": []}
    for row in before["generation"]:
        qid, method = row["question_id"], row["configuration"]
        file = f"{qid}_{'bm25' if method == 'BM25' else 'rerank'}.json"
        raw = json.loads((args.private_before / file).read_text(encoding="utf-8"))
        sources = [GroundingSource(**value) for value in raw["sources"]]
        if [s.chunk_id for s in sources] != row["context_chunk_ids"]:
            raise ValueError(f"Stored context changed: {file}")
        print(file, flush=True)
        result = generate_grounded_answer(raw["case"]["question"], sources, prompt_variant="scope_schema",
                                          timeout_seconds=180, max_output_tokens=report["generation_max_output_tokens"],
                                          context_window=args.context_window)
        raw["result"] = asdict(result)
        raw.pop("error", None)
        (args.private_out / file).write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")
        report["generation"].append({
            "question_id": qid, "configuration": method, "answerable": row["answerable"],
            "same_ordered_context_chunk_ids": row["context_chunk_ids"], "status": result.status,
            "generation_ms": result.latency_ms, "cited_chunk_ids": [s.chunk_id for s in result.citations],
        })
        args.metrics.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    report["completed"] = True
    args.metrics.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()

