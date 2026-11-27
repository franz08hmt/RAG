"""Export non-sensitive metadata from the five locally retained console logs."""
import argparse,hashlib,json,subprocess,sys
from datetime import datetime,timezone
from pathlib import Path
print('Python executable:',sys.executable,flush=True)
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--private',type=Path,required=True);p.add_argument('--out',type=Path,required=True);args=p.parse_args()
if args.out.exists():raise FileExistsError(args.out)
rows=[]
for i in range(1,6):
 path=args.private/f'demo_{i:02}.json';raw=path.read_bytes();data=json.loads(raw);q=data['query']
 rows.append({'id':f'demo_{i:02}','success':data['success'],'status':q['status'],'abstained':q['abstained'],
              'citation_count':q['citation_count'],'total_seconds':data['total_seconds'],
              'retrieved_chunk_ids':q['retrieved_chunk_ids'],'log_sha256':hashlib.sha256(raw).hexdigest()})
result={'run_id':datetime.now(timezone.utc).strftime('console_rrf_%Y%m%dT%H%M%SZ'),
 'revision_before_summary':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
 'runner_sha256_at_summary':hashlib.sha256((ROOT/'scripts/demo_v4_rrf.ps1').read_bytes()).hexdigest(),
 'runner_note':'Case 05 was resumed separately after case 04 exit 3; script error handling was adjusted after the first four cases.',
 'console_sha256':hashlib.sha256((ROOT/'src/rag_hcmute/console_app.py').read_bytes()).hexdigest(),
 'method':'hybrid_rrf','rank_constant':60,'branch_depth':50,'reranker':False,'model':'qwen3:4b',
 'context_window':8192,'prompt':'scope_schema','cases':rows,'private_content_published':False}
args.out.parent.mkdir(parents=True,exist_ok=True);args.out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
print('run_id:',result['run_id'])
for row in rows:print(row['id'],row['status'],'success:',row['success'],'seconds:',round(row['total_seconds'],1))
