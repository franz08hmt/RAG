"""Export only content-free per-item labels from selected local judge runs."""
import argparse,json,sys
from pathlib import Path
print('Python executable:',sys.executable,flush=True)
p=argparse.ArgumentParser();p.add_argument('--image-run',type=Path,required=True);p.add_argument('--text-run',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
if a.output.exists():raise FileExistsError(a.output)
x=json.loads(a.image_run.read_text(encoding='utf8'));y=json.loads(a.text_run.read_text(encoding='utf8'))
if not x['completed'] or not y['completed'] or x['model_digest']!=y['model_digest']:raise ValueError('Incompatible runs')
rows=[r for r in x['results'] if r['group'] not in ('qa12','demo5')]+y['results']
if len(rows)!=118:raise ValueError('Expected two selected labels for 59 outputs')
keys=['item_id','group','repeat','valid','label','support','prompt_eval_count','eval_count']
data={'image_run_id':x['run_id'],'text_run_id':y['run_id'],'model':x['model'],'model_digest':x['model_digest'],
      'rows':[{k:r.get(k) for k in keys} for r in rows]}
a.output.write_text(json.dumps(data,indent=2)+'\n',encoding='utf8');print('Exported rows:',len(rows))
