"""Compare three local output contracts using identical saved M2 retrieval contexts.

This isolates generation from retrieval changes; it is NOT an end-to-end rerun.
Full text remains outside Git. No human semantic labels are synthesized.
"""
from __future__ import annotations
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path
from datetime import datetime, timezone
from dataclasses import asdict
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from rag_hcmute.generation.ollama import GroundingSource, generate_grounded_answer
from rag_hcmute.evaluation.run_pilot import load_pilot_questions
from rag_hcmute.evaluation.generation_pilot import summarize_generation_pilot


def main():
    print(f'Python executable: {sys.executable}',flush=True)
    source = Path('D:/RAG/private_eval/m2_console/20261024T130313Z')
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    output = ROOT/f'artifacts/results/m3/generation_{stamp}.json'
    private = Path('D:/RAG/private_eval/m3_generation')/stamp
    private.mkdir(parents=True,exist_ok=False)
    output.parent.mkdir(parents=True,exist_ok=True)
    tags = json.load(urlopen('http://127.0.0.1:11434/api/tags',timeout=10))
    model_meta = next(m for m in tags['models'] if m['name']=='qwen3:4b')
    questions = load_pilot_questions(ROOT/'data/question_sets/pilot_questions.csv',partition='development',
                                    project_root=ROOT,snapshot_path=ROOT/'data/manifests/corpus_snapshot.json')
    contexts = {}
    report = {'run_id':f'generation_{stamp}','snapshot_id':'5da3bd4d5de54492',
        'partition':'development','holdout_used':False,'human_semantic_review':'pending',
        'model':'qwen3:4b','model_digest':model_meta['digest'],'temperature':0,'think':False,
        'max_output_tokens':1024,'api_cost_usd':0,'reused_retrieval_run':'m2_console_20261024T130313Z',
        'context_sha256':{},'completed':False,'cases':[],
        'revision_before_run':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        'source_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in
            [Path(__file__),ROOT/'src/rag_hcmute/generation/ollama.py',ROOT/'src/rag_hcmute/evaluation/generation_pilot.py']},
        'limitations':['Fixed saved retrieval contexts; generation-only experiment, not new retrieval/end-to-end timing.',
            'Prompt variants run in sequence on ten reused dev questions; no holdout.',
            'evidence_first changes prompt, schema and validator; not a single-variable schema ablation.',
            'Matching a quoted string verifies location only, not claim entailment or answer correctness.',
            'Model refusal labels must still be checked by a human; technical withheld outputs are separate.']}
    for q in questions:
        raw = json.loads((source/f'standard_{q.question_id}.json').read_text(encoding='utf-8'))
        if raw['question'] != q.question:
            raise ValueError('Question text differs from stored retrieval run.')
        contexts[q.question_id] = [GroundingSource(**s) for s in raw['sources']]
        report['context_sha256'][q.question_id] = hashlib.sha256(
            json.dumps(raw['sources'],ensure_ascii=False,sort_keys=True).encode()).hexdigest()
    def save():
        output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    save()
    for variant in ('standard','schema','evidence_first'):
        for q in questions:
            print(f'{variant}: {q.question_id}',flush=True)
            started = time.perf_counter()
            try:
                sources = contexts[q.question_id]
                result = generate_grounded_answer(q.question,sources,prompt_variant=variant,
                    max_output_tokens=1024,timeout_seconds=240,keep_alive='5m')
                row = {'question_id':q.question_id,'answerability':q.answerability,'variant':variant,
                    'status':result.status,'abstained':result.abstained,'generation_ms':result.latency_ms,
                    'citation_ids_valid': all(s.source_id in {x.source_id for x in sources} for s in result.citations) if result.citations else None,
                    'cited_expected_document':any(s.document_id==q.expected_document for s in result.citations),
                    'citation_ids':[s.source_id for s in result.citations]}
                payload = {'question':q.question,'sources':[asdict(s) for s in sources], 'result':asdict(result)}
            except RuntimeError as exc:
                row = {'question_id':q.question_id,'answerability':q.answerability,'variant':variant,
                    'status':'transport_error','abstained':True,'generation_ms':(time.perf_counter()-started)*1000,
                    'citation_ids_valid':None,'cited_expected_document':False,'citation_ids':[]}
                payload = {'error_type':type(exc).__name__}
            (private/f'{variant}_{q.question_id}.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
            report['cases'].append(row)
            save()
    report['summary'] = {v:summarize_generation_pilot([r for r in report['cases'] if r['variant']==v])
                         for v in ('standard','schema','evidence_first')}
    report['private_directory'] = str(private)
    report['completed'] = True
    save()
    print(output,flush=True)


if __name__=='__main__':
    main()
