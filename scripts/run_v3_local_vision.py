"""Compare a local VLM on previously privacy-reviewed image crops, without publishing text."""
import base64, csv, hashlib, json, sys, time
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
print('Python executable:', sys.executable, flush=True)
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from run_v2_images import QUESTIONS
src=Path('D:/RAG/private_eval/final_20261115/image_v2')
manifest=json.loads((src/'manifest.json').read_text(encoding='utf8'))
stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
out=Path('D:/RAG/private_eval/final_20261115')/('image_v3_'+stamp)
out.mkdir(parents=True,exist_ok=False)
metrics=ROOT/'artifacts/results/v3'/('vision_'+stamp+'.json')
metrics.parent.mkdir(parents=True,exist_ok=True)
model='qwen2.5vl:3b'; generator='qwen3:4b'
with urlopen('http://127.0.0.1:11434/api/tags',timeout=10) as response:
    available={entry['name']:entry['digest'] for entry in json.load(response)['models']}
report={'run_id':'vision_'+stamp,'model':model,'model_digest':available[model],
        'generator':generator,'generator_digest':available[generator],
        'runner_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'source_run':json.loads((ROOT/'docs/evidence/v2/image_run.json').read_text(encoding='utf8'))['run_id'],'description_is_inference':True,
        'questions':[],'images':[],'completed':False}
def save():metrics.write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
def call(payload, timeout=300):
    req=Request('http://127.0.0.1:11434/api/chat', data=json.dumps(payload,ensure_ascii=False).encode('utf8'),headers={'Content-Type':'application/json'})
    with urlopen(req,timeout=timeout) as response:return json.load(response)
descriptions={}
for item in manifest['items']:
    path=src/(item['id']+'.png'); raw=path.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=item['sha256']:raise ValueError('Crop hash mismatch')
    t=time.perf_counter()
    response=call({'model':model,'messages':[{'role':'user','content':'Describe this image and preserve table rows, columns, numbers, and ordering. Do not invent unreadable details.','images':[base64.b64encode(raw).decode('ascii')]}],
                   'stream':False,'keep_alive':0,'options':{'temperature':0,'num_ctx':4096,'num_predict':384}})
    descriptions[item['id']]=response['message']['content']
    report['images'].append({'id':item['id'],'sha256':item['sha256'],'seconds':time.perf_counter()-t})
    (out/'descriptions.json').write_text(json.dumps(descriptions,ensure_ascii=False,indent=2),encoding='utf8');save()
    print('Vision',item['id'],flush=True)
schema={'type':'object','properties':{'answer':{'type':'string'},'abstain':{'type':'boolean'}},'required':['answer','abstain']}
rows=[]
for image_id,pairs in QUESTIONS.items():
    for i,(question,expected) in enumerate(pairs,1):
        response=call({'model':generator,'messages':[{'role':'system','content':'Trả lời bằng tiếng Việt. Chỉ dùng thông tin được cung cấp. Không suy đoán.'},
          {'role':'user','content':f'Tư liệu:\n{descriptions[image_id]}\nCâu hỏi: {question}\nChỉ dùng tư liệu để trả lời ngắn. Nếu không đủ, abstain=true.'}],
          'stream':False,'think':False,'format':schema,'keep_alive':'5m','options':{'temperature':0,'num_ctx':4096,'num_predict':384}})
        try:
            value=json.loads(response['message']['content']); valid=isinstance(value.get('answer'),str) and isinstance(value.get('abstain'),bool)
        except (ValueError,TypeError,AttributeError):value={};valid=False
        qid=f'{image_id}-Q{i}'
        rows.append({'id':qid,'image_path':str(src/(image_id+'.png')),'question':question,'expected_reference':expected,
                     'vlm_description':descriptions[image_id],'answer':value.get('answer',''),'abstain':value.get('abstain',''),
                     'student_label':'','student_notes':''})
        report['questions'].append({'id':qid,'valid_json':valid,'abstain':value.get('abstain') if valid else None,'review_status':'pending'})
        with (out/'student_review.csv').open('w',encoding='utf-8-sig',newline='') as stream:
            writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
        save();print(qid,flush=True)
report['completed']=True;save();print('PRIVATE_REVIEW',out/'student_review.csv',flush=True);print('METRICS',metrics,flush=True)
