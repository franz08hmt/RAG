"""Rebuild machine-local registries from pinned revisions already on disk."""
import argparse
import json
import sys
from pathlib import Path


def main():
    print(f"Python executable: {sys.executable}")
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-cache", type=Path, default=Path("D:/RAG/models/huggingface/hub"))
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    registry = json.loads((root/"configs/m3_model_revisions.json").read_text(encoding="utf-8-sig"))
    directory = root/"artifacts/results/m3"
    directory.mkdir(parents=True, exist_ok=True)
    for role, models in registry.items():
        entries = []
        for model in models:
            snapshot = args.model_cache / ("models--"+model["model_id"].replace("/", "--")) / "snapshots" / model["revision"]
            if not (snapshot/"model.safetensors").is_file():
                raise FileNotFoundError(f"Missing local weights for {model['model_id']} at {model['revision']}")
            entries.append({**model, "path": str(snapshot)})
        output = directory/f"downloaded_{role}.json"
        if output.exists():
            existing = json.loads(output.read_text(encoding="utf-8-sig"))
            same = [(e["model_id"],e["revision"],Path(e["path"]).resolve()) for e in existing] == [
                (e["model_id"],e["revision"],Path(e["path"]).resolve()) for e in entries]
            if not same:
                raise FileExistsError(f"Existing registry differs: {output}")
        else:
            output.write_text(json.dumps(entries, indent=2)+"\n",encoding="utf-8")
        print(f"{role}: {len(entries)} local snapshots verified")


if __name__ == "__main__":
    main()
