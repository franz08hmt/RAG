"""Summarize local AI judge labels, stability, and comparable pre-existing Codex labels."""
import argparse,csv,hashlib,json,sys
from collections import Counter,defaultdict
from datetime import datetime,timezone
from pathlib import Path
print('Python executable:',sys.executable,flush=True)
ap=argparse.ArgumentParser();ap.add_argument('--judge',type=Path,required=True);ap.add_argument('--text-judge',type=Path,required=True);ap.add_argument('--codex',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);args=ap.parse_args()
if args.output.exists():raise FileExistsError(args.output)
b=json.loads(args.judge.read_text(encoding='utf8'))
if not b['completed'] or len(b['results'])!=b['planned_calls']:raise ValueError('Incomplete judge run')
t=json.loads(args.text_judge.read_text(encoding='utf8'))
if not t['completed'] or len(t['results'])!=34 or t['model_digest']!=b['model_digest']:raise ValueError('Incomplete or incompatible text rerun')
b['results']=[x for x in b['results'] if x['group'] not in ('qa12','demo5')]+t['results']
with args.codex.open(encoding='utf-8-sig',newline='') as f:a=list(csv.DictReader(f))
if len(a)!=24:raise ValueError('Expected 24 original image labels')
first=[x for x in b['results'] if x['repeat']==1];second={x['item_id']:x for x in b['results'] if x['repeat']==2}
if len(first)!=59 or len(second)!=59:raise ValueError('Expected two judgments per item')
groups={}
for group in sorted({x['group'] for x in first}):
 items=[x for x in first if x['group']==group];valid=[x for x in items if x['valid']]
 groups[group]={'item_count':len(items),'valid_count':len(valid),'labels':dict(Counter(x['label'] for x in valid)),
                'support':dict(Counter(x['support'] for x in valid))}
paired=[(x,second[x['item_id']]) for x in first if x['valid'] and second[x['item_id']]['valid']]
stable=sum(x['label']==y['label'] for x,y in paired)
support_stable=sum(x['support']==y['support'] for x,y in paired)
by_id={x['item_id']:x for x in first};comparable=[];excluded=Counter()
for row in a:
 label=row['ai_label'];item_id=f"image_{row['question_id']}_{row['modality']}"
 if label not in ('correct','partial','incorrect'):
  excluded[label or 'missing']+=1;continue
 if item_id not in by_id or not by_id[item_id]['valid']:
  excluded['judge_b_invalid_or_missing']+=1;continue
 comparable.append({'id':item_id,'judge_a':label,'judge_b':by_id[item_id]['label']})
labels=sorted(set(x['judge_a'] for x in comparable)|set(x['judge_b'] for x in comparable));n=len(comparable)
observed=sum(x['judge_a']==x['judge_b'] for x in comparable)/n if n else None
ca=Counter(x['judge_a'] for x in comparable);cb=Counter(x['judge_b'] for x in comparable)
expected=sum(ca[k]*cb[k] for k in labels)/(n*n) if n else None
kappa=(observed-expected)/(1-expected) if n and expected!=1 else None
summary={'run_id':datetime.now(timezone.utc).strftime('judge_summary_'+ '%Y%m%dT%H%M%SZ'),
 'judge_b_run_id':b['run_id'],'judge_b_text_run_id':t['run_id'],'judge_b_model':b['model'],'judge_b_digest':b['model_digest'],
 'private_run_sha256':hashlib.sha256(args.judge.read_bytes()).hexdigest(),
 'private_text_run_sha256':hashlib.sha256(args.text_judge.read_bytes()).hexdigest(),
 'judge_a_run_id':'image_review_20261125T060820Z','judge_a':'Codex',
 'judge_a_source_sha256':hashlib.sha256(args.codex.read_bytes()).hexdigest(),
 'rubric':['correct','partial','incorrect','correct_refusal','should_refuse'],
 'groups':groups,'judge_b_status':{'selected_calls':len(b['results']),'actual_calls_including_discarded_initial_text':b['planned_calls']+t['planned_calls'],
  'valid_calls':sum(x['valid'] for x in b['results'])},
 'judge_b_repeat_stability':{'paired_valid':len(paired),'label_agree':stable,'support_agree':support_stable,
  'label_agreement':stable/len(paired) if paired else None,'support_agreement':support_stable/len(paired) if paired else None},
 'judge_a_vs_b':{'a_original_count':len(a),'comparable_count':n,'excluded':dict(excluded),
  'observed_agreement':observed,'chance_agreement':expected,'cohen_kappa':kappa,
  'contingency':{f'{a_label}|{b_label}':sum(x['judge_a']==a_label and x['judge_b']==b_label for x in comparable) for a_label in labels for b_label in labels},
  'disagreements':[x for x in comparable if x['judge_a']!=x['judge_b']]},
 'limitations':['Codex A has pre-existing labels only for OCR/SmolVLM2; no A labels for new QA, demo, Qwen-VL or arrow outputs.',
  'A model_abstained records model behavior, not a correctness judgment; excluded from kappa.',
  'AI-drafted references and AI judges have no independent human adjudication.',
  'The two judges use shared source material and are not independent observations of ground truth.']}
args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(summary,indent=2)+'\n',encoding='utf8')
print('summary run:',summary['run_id']);print('B groups:',groups);print('repeat:',summary['judge_b_repeat_stability']);print('A vs B:',summary['judge_a_vs_b'])
