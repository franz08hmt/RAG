"""Replay image extraction text with a constrained local answer schema."""
import sys,json,hashlib
from pathlib import Path
from datetime import datetime,timezone
from urllib.request import Request,urlopen
print('Python executable:',sys.executable,flush=True)
source=Path('D:/RAG/private_eval/final_20261115/image_v2_run_20261125b/extracted.json')
out=Path('D:/RAG/private_eval/final_20261115/image_v2_run_20261125b/structured_answers.json')
metric=Path('artifacts/results/v2/image_qa_schema.json')
if out.exists() or metric.exists():raise FileExistsError('Choose a fresh output')
data=json.loads(source.read_text(encoding='utf8'))
schema={'type':'object','properties':{'answer':{'type':'string'},'abstain':{'type':'boolean'}},'required':['answer','abstain']}
old=data['answers']
image_run=json.loads(Path('artifacts/results/v2/image_20261125b.json').read_text(encoding='utf8'))
if not image_run['completed']:raise ValueError('Image extraction run is incomplete')
result={'run_id':datetime.now(timezone.utc).strftime('image_qa_%Y%m%dT%H%M%SZ'),'image_run':image_run['run_id'],
        'model':'qwen3:4b','settings':{'temperature':0,'num_ctx':4096,'num_predict':384,'format':'json_schema'},
        'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'rows':[],'completed':False}
answers=[]
for r in old:
 image=r['question_id'].split('-')[0]
 index=int(r['question_id'].split('Q')[1])-1
 from run_v2_images import QUESTIONS
 question,expected=QUESTIONS[image][index]
 prompt=f'Tư liệu:\\n{data[image][r["modality"]]}\\nCâu hỏi: {question}\\nChỉ dùng tư liệu để trả lời ngắn. Nếu không đủ, abstain=true.'
 payload={'model':'qwen3:4b','messages':[{'role':'system','content':'Trả lời bằng tiếng Việt. Chỉ dùng thông tin được cung cấp. Không suy đoán.'},{'role':'user','content':prompt}],
          'stream':False,'think':False,'format':schema,'keep_alive':'5m','options':result['settings']|{'format':None}}
 payload['options'].pop('format',None)
 request=Request('http://127.0.0.1:11434/api/chat',data=json.dumps(payload,ensure_ascii=False).encode('utf8'),headers={'Content-Type':'application/json'})
 with urlopen(request,timeout=240) as response:response=json.load(response)
 content=response['message']['content']
 try:
  value=json.loads(content)
  valid=isinstance(value.get('answer'),str) and isinstance(value.get('abstain'),bool)
 except (ValueError,TypeError,AttributeError):
  value={'raw':content};valid=False
 answers.append({'id':r['question_id'],'modality':r['modality'],'question':question,'expected':expected,'output':value})
 result['rows'].append({'id':r['question_id'],'modality':r['modality'],'valid_json':valid,'review_status':'pending'})
 out.write_text(json.dumps(answers,ensure_ascii=False,indent=2),encoding='utf8')
 metric.write_text(json.dumps(result,indent=2),encoding='utf8')
 print(r['question_id'],r['modality'],valid,flush=True)
result['completed']=True
metric.write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
