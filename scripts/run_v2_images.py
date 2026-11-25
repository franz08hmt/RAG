"""Local-only OCR and VLM description experiment on visually reviewed crops."""
import argparse
import base64
import hashlib
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

ROOT=Path(__file__).resolve().parents[1]
QUESTIONS={
 'I01':[('Theo bảng, cử nhân chính quy học thiết kế bao nhiêu năm?','4,0 năm'),
        ('Cử nhân vừa làm vừa học có số tín chỉ tối thiểu là bao nhiêu?','120')],
 'I02':[('Điểm 8,5 đến 8,9 quy đổi thành điểm chữ nào?','A'),
        ('Điểm 6,5 đến 6,9 quy đổi sang thang điểm 4 là bao nhiêu?','2,5')],
 'I03':[('Điểm từ 3,2 đến cận 3,6 xếp loại gì?','Giỏi'),
        ('Điểm từ 2,0 đến cận 2,5 xếp loại gì?','Trung bình')],
 'I04':[('Điểm từ 6,5 đến cận 7,9 xếp loại gì?','Khá'),
        ('Điểm từ 9 đến 10 xếp loại gì?','Xuất sắc')],
 'I05':[('Năm thứ ba có bao nhiêu tín chỉ tích lũy?','72 – 107'),
        ('Năm thứ nhất có dưới bao nhiêu tín chỉ tích lũy?','36')],
 'I06':[('Mục thứ hai nói về chủ đề gì?','Sức khỏe tâm thần của sinh viên'),
        ('Mục thứ ba có tiêu đề gì?','Bạn có gặp vấn đề về sức khỏe tâm thần?')],
}
def call(model, messages):
 data={'model':model,'messages':messages,'stream':False,'think':False,'keep_alive':'5m',
       'options':{'temperature':0,'num_ctx':4096,'num_predict':384}}
 request=Request('http://127.0.0.1:11434/api/chat',data=json.dumps(data).encode(),
                 headers={'Content-Type':'application/json'})
 with urlopen(request,timeout=240) as response:return json.load(response)['message']['content']

def main():
 print('Python executable:',sys.executable,flush=True)
 ap=argparse.ArgumentParser()
 ap.add_argument('--private',type=Path,required=True)
 ap.add_argument('--out',type=Path,required=True)
 ap.add_argument('--metrics',type=Path,required=True)
 args=ap.parse_args()
 if args.out.resolve().is_relative_to(ROOT) or args.out.exists() or args.metrics.exists():
  raise ValueError('Use a fresh output directory outside the repository')
 manifest=json.loads((args.private/'manifest.json').read_text(encoding='utf-8'))
 args.out.mkdir(parents=True)
 result={'run_id':datetime.now(timezone.utc).strftime('image_%Y%m%dT%H%M%SZ'),
   'snapshot_id':'5da3bd4d5de54492','model':'ahmadwaqar/smolvlm2-256m-video:q8_0',
   'generator':'qwen3:4b','limitations':['Five image crops are tables; one is a numbered infographic. No arrow diagram is included.',
   'VLM description is inference, not an exact quotation.',
   'Keyword occurrence is a diagnostic; semantic correctness and directional hallucination require review.'],
   'images':[],'completed':False}
 with urlopen('http://127.0.0.1:11434/api/tags',timeout=10) as response:
  available={entry['name']:entry['digest'] for entry in json.load(response)['models']}
 result['model_digest']=available[result['model']]
 result['generator_digest']=available[result['generator']]
 texts={}
 exe=Path(sys.prefix)/'Library/bin/tesseract.exe'
 tess=Path('D:/RAG/models/tesseract/tessdata')
 result['tesseract_version']=subprocess.check_output([str(exe),'--version'],text=True).splitlines()[0]
 result['script_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
 args.metrics.parent.mkdir(parents=True,exist_ok=True)
 def save():
  args.metrics.write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
 save()
 for item in manifest['items']:
  path=args.private/(item['id']+'.png')
  if hashlib.sha256(path.read_bytes()).hexdigest()!=item['sha256']:
   raise ValueError('Image hash mismatch')
  ocr=subprocess.run([str(exe),str(path),'stdout','--tessdata-dir',str(tess),'-l','vie','--psm','6'],
                     capture_output=True,check=True,timeout=120).stdout.decode('utf8')
  image=base64.b64encode(path.read_bytes()).decode('ascii')
  started=time.perf_counter()
  vision=call(result['model'],[{'role':'user','content':
    'Describe this image and preserve table rows, columns, numbers, and ordering. Do not invent unreadable details.',
    'images':[image]}])
  texts[item['id']]={'ocr':ocr,'vlm_inference':vision}
  result['images'].append({'id':item['id'],'sha256':item['sha256'],'pdf_page':item['pdf_page'],
     'ocr_characters':len(ocr),'vlm_characters':len(vision),'vlm_seconds':time.perf_counter()-started})
  print(item['id'],'OCR + vision done',flush=True)
  (args.out/'extracted.json').write_text(json.dumps(texts,ensure_ascii=False,indent=2),encoding='utf8')
  save()
 for row in result['images']:
  image_id=row['id']; row['questions']=[]
  for index,(question,expected) in enumerate(QUESTIONS[image_id],1):
   for modality in ('ocr','vlm_inference'):
    context=texts[image_id][modality]
    answer=call('qwen3:4b',[{'role':'system','content':'Only answer from the provided text. If insufficient, say UNKNOWN.'},
      {'role':'user','content':f'Text: {context}\nQuestion: {question}'}])
    record={'question_id':f'{image_id}-Q{index}','modality':modality,'answer':answer,'expected':expected}
    texts.setdefault('answers',[]).append(record)
    # No keyword score for single-letter answers or OCR variants.
    row['questions'].append({'question_id':record['question_id'],'modality':modality,'review_status':'pending'})
    (args.out/'extracted.json').write_text(json.dumps(texts,ensure_ascii=False,indent=2),encoding='utf8')
   print(image_id,'question',index,flush=True)
   save()
 result['completed']=True
 save()
 print(args.metrics)
if __name__=='__main__': main()
