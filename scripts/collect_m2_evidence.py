"""Collect content-free metrics for review; never copy full contexts or source PDFs."""
from pathlib import Path
import argparse
import hashlib
import json
import sys

ROOT=Path(__file__).resolve().parents[1]

def main():
    print(f'Python executable: {sys.executable}')
    parser=argparse.ArgumentParser()
    parser.add_argument('--generation',type=Path,required=True)
    args=parser.parse_args()
    out=ROOT/'docs/evidence/m2/runs'
    out.mkdir(parents=True,exist_ok=True)
    sources={
        'corpus_snapshot.json':ROOT/'data/manifests/corpus_snapshot.json',
        'input_artifacts_summary.json':ROOT/'artifacts/results/m2_input/input_artifacts_metrics.json',
        'controlled_evaluation.json':ROOT/'artifacts/results/m2_eval/controlled_run_20261024T125011Z.json',
        'console_generation.json':args.generation.resolve(),
        'console_cold.json':ROOT/'artifacts/results/m2_console/cold.json',
        'console_warm.json':ROOT/'artifacts/results/m2_console/warm_interactive_20261025.json'}
    manifest=[]
    for name,path in sources.items():
        data=json.loads(path.read_text(encoding='utf-8'))
        if name=='input_artifacts_summary.json':
            data['documents']=[{k:v for k,v in d.items() if k!='pages'} for d in data['documents']]
            # Local figure pixels stay outside version control; count/source hashes suffice here.
            data.pop('review_figures',None)
        if name=='console_generation.json':
            if not data.get('completed'): raise ValueError('Incomplete generation experiment.')
            data.pop('private_content_directory',None)
        target=out/name
        content=json.dumps(data,ensure_ascii=False,indent=2)+'\n'
        if target.exists() and target.read_text(encoding='utf-8') != content:
            raise FileExistsError(target)
        # Canonical UTF-8/LF exports keep checksums stable across Git checkouts.
        target.write_text(content,encoding='utf-8',newline='\n')
        manifest.append({'file':name,'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),
                         'local_source':str(path.relative_to(ROOT)),
                         'source_sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(out)

if __name__=='__main__': main()
