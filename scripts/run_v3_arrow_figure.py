"""Local OCR/VLM pilot on one visually checked, non-personal diagram crop."""
import base64,csv,hashlib,json,subprocess,sys,time
from datetime import datetime,timezone
from pathlib import Path
from urllib.request import Request,urlopen
from PIL import Image
print('Python executable:',sys.executable,flush=True)
ROOT=Path(__file__).resolve().parents[1]
stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
out=Path('D:/RAG/private_eval/final_20261115')/('arrow_v3_'+stamp);out.mkdir(parents=True,exist_ok=False)
crop=out/'I07.png';Image.open('D:/RAG/private_eval/final_20261115/page136_review.png').crop((150,675,455,980)).save(crop)
digest=hashlib.sha256(crop.read_bytes()).hexdigest()
metrics=ROOT/'artifacts/results/v3'/('arrow_'+stamp+'.json')
report={'run_id':'arrow_'+stamp,'source':'HCMUTE_SOTAYSV_2024','pdf_page':136,'crop_sha256':digest,
        'privacy_review':'visually inspected diagram crop; no names, phone numbers, emails or photographs',
        'models':['tesseract-vie','ahmadwaqar/smolvlm2-256m-video:q8_0','qwen2.5vl:3b'],
        'generator':'qwen3:4b','questions':[],'completed':False}
def save():metrics.write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
def call(payload):
    req=Request('http://127.0.0.1:11434/api/chat',data=json.dumps(payload,ensure_ascii=False).encode('utf8'),headers={'Content-Type':'application/json'})
    with urlopen(req,timeout=300) as r:return json.load(r)['message']['content']
exe=Path(sys.prefix)/'Library/bin/tesseract.exe'
contents={'ocr':subprocess.run([str(exe),str(crop),'stdout','--tessdata-dir','D:/RAG/models/tesseract/tessdata','-l','vie','--psm','6'],capture_output=True,check=True).stdout.decode('utf8')}
for name in report['models'][1:]:
    contents[name]=call({'model':name,'messages':[{'role':'user','content':'Describe all readable text and the direction and order of arrows. Do not invent unclear details.','images':[base64.b64encode(crop.read_bytes()).decode('ascii')]}],
       'stream':False,'keep_alive':0,'options':{'temperature':0,'num_ctx':4096,'num_predict':384}})
    print('Figure description',name,flush=True)
schema={'type':'object','properties':{'answer':{'type':'string'},'abstain':{'type':'boolean'}},'required':['answer','abstain']}
qs=[('Sau bước hít vào, theo mũi tên là bước nào?','Giữ hơi trong 4 giây'),('Sau bước thở ra, theo mũi tên là bước nào?','Ngừng hít thở trong 4 giây')]
rows=[]
for name,context in contents.items():
 for i,(question,expected) in enumerate(qs,1):
    result=call({'model':'qwen3:4b','messages':[{'role':'system','content':'Chỉ dùng tư liệu, không suy đoán. Nếu không đủ hãy từ chối.'},
      {'role':'user','content':f'Tư liệu:\n{context}\nCâu hỏi: {question}'}],
      'stream':False,'think':False,'format':schema,'options':{'temperature':0,'num_ctx':4096,'num_predict':384}})
    try: answer=json.loads(result); valid=isinstance(answer.get('answer'),str) and isinstance(answer.get('abstain'),bool)
    except (ValueError,TypeError,AttributeError):answer={};valid=False
    rows.append({'id':f'I07-Q{i}','image_path':str(crop),'method':name,'question':question,'expected_reference':expected,'extracted_text':context,'answer':answer.get('answer',''),'abstain':answer.get('abstain',''),'student_label':'','direction_error':'','notes':''})
    report['questions'].append({'id':f'I07-Q{i}','method':name,'valid_json':valid,'abstain':answer.get('abstain') if valid else None,'review_status':'pending'})
    with (out/'student_review.csv').open('w',encoding='utf-8-sig',newline='') as stream:
      writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    save();print('I07-Q',i,name,flush=True)
report['completed']=True;save();print('PRIVATE_REVIEW',out/'student_review.csv',flush=True);print('METRICS',metrics,flush=True)
