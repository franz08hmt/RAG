"""Paired bootstrap for retrieval metrics within each fixed-input embedding study."""
from pathlib import Path
import argparse
import hashlib
import json
import sys
from datetime import datetime,timezone

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from rag_hcmute.evaluation.interval_metrics import paired_bootstrap

def main():
 print('Python executable:',sys.executable)
 ap=argparse.ArgumentParser()
 ap.add_argument('inputs',nargs='+',type=Path)
 ap.add_argument('--output',required=True,type=Path)
 args=ap.parse_args()
 if args.output.exists():raise FileExistsError(args.output)
 output={'run_id':datetime.now(timezone.utc).strftime('paired_bootstrap_%Y%m%dT%H%M%SZ'),
         'repetitions':5000,'seed':22110068,'inputs':[]}
 for file in args.inputs:
  data=json.loads(file.read_text(encoding='utf8'))
  if not data['completed']:raise ValueError('Incomplete study')
  models=[m for m in data['models'] if m['variant']=='recommended_preprocessing']
  base=next(m for m in models if m['model_id']=='BAAI/bge-m3')
  base_rows=base['metrics']['per_question']
  comparisons=[]
  for model in models:
   rows=model['metrics']['per_question']
   if [r['question_id'] for r in rows]!=[r['question_id'] for r in base_rows]:raise ValueError('Different questions')
   metrics={}
   for key in ('character_recall_at_5','mrr_at_10_threshold_05','ndcg_at_5_linear_span_coverage'):
    metrics[key]=paired_bootstrap([r[key] for r in base_rows],[r[key] for r in rows],repetitions=5000)
   comparisons.append({'model_id':model['model_id'],'metrics':metrics})
  output['inputs'].append({'run_id':data['run_id'],'sha256':hashlib.sha256(file.read_bytes()).hexdigest(),'comparisons':comparisons})
 args.output.write_text(json.dumps(output,indent=2)+'\n',encoding='utf8')
 print(args.output)
if __name__=='__main__': main()