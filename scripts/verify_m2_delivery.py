"""Read-only delivery checks. No model/API calls and no source text output."""
import hashlib
import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET
import zipfile

ROOT=Path(__file__).resolve().parents[1]
NS={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}

def main():
    print(f'Python executable: {sys.executable}')
    base=ROOT/'docs/evidence/m2/runs'
    entries=json.loads((base/'manifest.json').read_text(encoding='utf-8'))
    for row in entries:
        assert hashlib.sha256((base/row['file']).read_bytes()).hexdigest()==row['sha256'], row['file']
    evaluation=json.loads((base/'controlled_evaluation.json').read_text(encoding='utf-8'))
    generation=json.loads((base/'console_generation.json').read_text(encoding='utf-8'))
    assert evaluation['completed'] and generation['completed']
    assert evaluation['answerable_count']==7 and evaluation['shared_chunk_count']==289
    assert all(value['over_512']==0 for value in evaluation['shared_input_lengths'].values())
    assert len(generation['cases'])==20
    assert len({(r['prompt_variant'],r['qid']) for r in generation['cases']})==20
    assert not evaluation['holdout_used']
    # No question, answer, source text or context content may enter the JSON exports.
    forbidden={'question','answer','text','text_preview','sources','context','raw_response'}
    def walk(value):
        if isinstance(value,dict):
            assert not forbidden.intersection(value), 'Content-bearing key in evidence export'
            for item in value.values(): walk(item)
        elif isinstance(value,list):
            for item in value: walk(item)
    for row in entries: walk(json.loads((base/row['file']).read_text(encoding='utf-8')))
    report=ROOT/'reports/22110068_RAG_Bao_Cao_Tien_Do_Moc_2_v3.docx'
    with zipfile.ZipFile(report) as archive:
        root=ET.fromstring(archive.read('word/document.xml'))
        sizes={int(n.attrib['{'+NS['w']+'}val']) for n in root.findall('.//w:sz',NS)}
        assert sizes <= {24,26,28}, sizes
        text=' '.join(n.text or '' for n in root.findall('.//w:t',NS))
        assert '{{' not in text and 'Tìm hiểu Retrieval Augmented Generation (RAG)' in text
        assert 'BÁO CÁO TIẾN ĐỘ MỐC 2' in text
        assert root.findall('.//w:pStyle',NS)
        for node in root.findall('.//w:color',NS):
            assert node.attrib.get('{'+NS['w']+'}val') in {'000000','auto'}
        for field in root.findall('.//w:instrText',NS):
            assert not any(k in (field.text or '').upper().split() for k in ('PAGE','NUMPAGES'))
    result={'evidence_files':len(entries),'generation_cases':20,'report_sha256':hashlib.sha256(report.read_bytes()).hexdigest(),
            'font_sizes_pt':sorted(s/2 for s in sizes),'automated_delivery_checks':'passed'}
    print(json.dumps(result,indent=2))

if __name__=='__main__': main()
