"""Reclassify judge presentation using fixed draft scope labels and observed status.

No model is called; no old labels or evaluation results are modified.
"""
import argparse,hashlib,json,sys
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path
print('Python executable:',sys.executable,flush=True)
ROOT=Path(__file__).resolve().parents[1]
ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True);args=ap.parse_args()
if args.output.exists():raise FileExistsError(args.output)
paths={'qa':ROOT/'docs/evidence/v5/scope_rrf12.json','demo':ROOT/'docs/evidence/v5/demo_rrf.json','judge':ROOT/'docs/evidence/v6/judge_rows.json','summary':ROOT/'docs/evidence/v6/judge_summary.json','demo_spec':ROOT/'docs/DEMO.md'}
data={k:json.loads(p.read_text(encoding='utf8')) for k,p in paths.items() if k!='demo_spec'}
judges={r['item_id']:r for r in data['judge']['rows'] if r['repeat']==1}
demo_scope={'demo_01':True,'demo_02':True,'demo_03':True,'demo_04':False,'demo_05':True}
def build(name,records):
 have=[x for x in records if x['answerable_draft']];missing=[x for x in records if not x['answerable_draft']]
 refused=[x for x in missing if x['status']=='model_abstained']
 answered=[x for x in missing if x['status']=='generated_citations_unverified']
 errors=[x for x in missing if x not in refused and x not in answered]
 labels=Counter(judges[x['judge_id']]['label'] for x in have if judges[x['judge_id']]['valid'])
 conflict=[{'id':x['judge_id'],'judge_label':judges[x['judge_id']]['label']} for x in answered if judges[x['judge_id']]['label']=='correct']
 return {'group':name,'total':len(records),'answerable_draft':len(have),'unanswerable_draft':len(missing),
         'unanswerable_model_abstained':len(refused),'unanswerable_answered_should_refuse':len(answered),
         'unanswerable_technical_error':len(errors),'judge_labels_on_answerable':dict(labels),'judge_conflicts':conflict}
qa=[{'answerable_draft':x['answerable_draft'],'status':x['status'],'judge_id':'qa_'+x['question_id']} for x in data['qa']['rows']]
demo=[{'answerable_draft':demo_scope[x['id']],'status':x['status'],'judge_id':x['id']} for x in data['demo']['cases']]
qa_result=build('qa12',qa);demo_result=build('demo5',demo)
assert (qa_result['total'],qa_result['unanswerable_draft'],qa_result['unanswerable_model_abstained'],qa_result['unanswerable_answered_should_refuse'])==(12,6,1,5)
assert (demo_result['total'],demo_result['unanswerable_draft'],demo_result['unanswerable_model_abstained'],demo_result['unanswerable_answered_should_refuse'])==(5,1,1,0)
result={'run_id':datetime.now(timezone.utc).strftime('scope_presentation_%Y%m%dT%H%M%SZ'),
 'description':'Deterministic presentation from existing draft answerability and model status; not human-verified and no model calls.',
 'source_runs':{'qa':data['qa']['run_id'],'demo':data['demo']['run_id'],'judge_summary':data['summary']['run_id']},
 'source_sha256':{k:hashlib.sha256(p.read_bytes()).hexdigest() for k,p in paths.items()},
 'demo_answerability_rule':'demo_04 is outside HCMUTE corpus; other four use source-linked questions; see docs/DEMO.md',
 'qa':qa_result,'demo':demo_result,'note':'Judge correct on unanswerable answered questions is excluded; labels on answerable remain unverified AI judgments.'}
args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
print('run_id:',result['run_id']);print(json.dumps({'qa':qa_result,'demo':demo_result},indent=2))
