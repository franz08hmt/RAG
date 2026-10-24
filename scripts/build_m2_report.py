"""New M2 report from retained M1 cover; all measured tables load saved runs."""
from __future__ import annotations
import argparse
from collections import Counter
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
import statistics
import subprocess
import sys

from docx import Document
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
from build_m1_report_v3 import add_p, add_heading, add_data_table, add_flow_diagram, set_run_font

TEMPLATE = ROOT/'reports/22110068_RAG_Bao_Cao_Tien_Do_Dot_1_v6.docx'
TEMPLATE_SHA = '8e06f4bf57dc4dcabc810b296ce5438bc04bb435ea21f1d073aaaa8f0b39654b'
EVAL = ROOT/'artifacts/results/m2_eval/controlled_run_20261024T125011Z.json'
INPUT = ROOT/'artifacts/results/m2_input/input_artifacts_metrics.json'

def load(path):
    return json.loads(path.read_text(encoding='utf-8'))

def num(value, digits=3):
    return f'{value:.{digits}f}'.replace('.', ',')

def p(doc,text):
    paragraph=add_p(doc,text)
    paragraph.paragraph_format.keep_together=True
    return paragraph

def table(doc,caption,headers,rows,widths,note):
    result=add_data_table(doc,caption,headers,[[str(v) for v in r] for r in rows],widths,note)
    # Small comparison tables and their source note stay together on one page.
    for row in result.rows:
        for cell in row.cells:
            for para in cell.paragraphs:
                para.paragraph_format.keep_with_next=True
    return result

def figure(doc,source,page,clip,output,caption,width=6.0):
    subprocess.run([r'C:\Users\Dell\anaconda3\envs\rag-hcmute\python.exe',
                    str(ROOT/'scripts/render_pdf_evidence.py'),str(source),str(output),
                    '--page',str(page),'--clip',*[str(v) for v in clip]],check=True)
    para=doc.add_paragraph()
    para.alignment=WD_ALIGN_PARAGRAPH.CENTER
    para.paragraph_format.keep_with_next=True
    para.add_run().add_picture(str(output),width=Inches(width))
    borders=OxmlElement('w:pBdr')
    for side in ('top','left','bottom','right'):
        edge=OxmlElement('w:'+side)
        for key,value in [('val','single'),('sz','6'),('space','4'),('color','000000')]: edge.set(qn('w:'+key),value)
        borders.append(edge)
    para._p.get_or_add_pPr().append(borders)
    add_p(doc,caption,italic=True,align=WD_ALIGN_PARAGRAPH.CENTER,first_line=False)

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--generation',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists(): raise FileExistsError(args.output)
    if hashlib.sha256(TEMPLATE.read_bytes()).hexdigest()!=TEMPLATE_SHA: raise ValueError('Template changed.')
    e,i,g=load(EVAL),load(INPUT),load(args.generation)
    if not e.get('completed') or not g.get('completed'): raise ValueError('Incomplete experimental run.')
    doc=Document(TEMPLATE)
    body=doc._element.body
    past=False
    for child in list(body):
        if past and child.tag!=qn('w:sectPr'): body.remove(child)
        elif child.tag==qn('w:p') and child.find('w:pPr/w:sectPr',doc._element.nsmap) is not None: past=True
    if not past: raise ValueError('Missing cover section.')
    for para in doc.paragraphs:
        if para.text.strip()=='Tìm hiểu Retrieval Augmented Generation (RAG)':
            para.style=doc.styles['Title']
            para.paragraph_format.space_before=Pt(8)
            para.paragraph_format.space_after=Pt(8)
            para.alignment=WD_ALIGN_PARAGRAPH.CENTER
            for run in para.runs: set_run_font(run,14,bold=True)
    # Preserve the user's no-page-number layout; all new headings use real styles.
    for name,size in [('Title',14),('Heading 1',14),('Heading 2',13)]:
        style=doc.styles[name]
        style.font.name='Times New Roman'
        style.font.size=Pt(size)
        from docx.shared import RGBColor
        style.font.color.rgb=RGBColor(0,0,0)
    assets=ROOT/'artifacts/results/m2_report/figures'
    assets.mkdir(parents=True,exist_ok=True)
    macro=lambda key:e['retrieval'][key]['character_coverage']['macro']
    short={'bm25':'BM25','dense_bge-m3':'Dense BGE-M3','rrf_bge-m3':'RRF với BGE-M3',
           'dense_multilingual-e5-small':'Dense E5-small','rrf_multilingual-e5-small':'RRF với E5-small'}
    def slot(name):
        if name=='summary':
            p(doc,'Kết quả đáng chú ý là chênh lệch giữa hai embedding giảm khi cùng nhận đầu vào không bị cắt; reranker tăng độ phủ nguồn nhưng không cải thiện mọi chỉ số thứ hạng; và câu trả lời có nguồn vẫn cần kiểm tra nội dung. Các bảng ở phần sau chỉ rõ mẫu số, cấu hình và giới hạn của từng kết quả.')
        elif name=='pipeline':
            add_flow_diagram(doc,'Hình 1 Luồng dữ liệu trong PoC',[
                ('Chuẩn bị nguồn','PDF → kiểm mã băm → trích chữ và khảo sát bố cục → Page và vùng nguồn'),
                ('Chuẩn bị chỉ mục','Chunk và metadata → BM25 hoặc embedding → chỉ mục vector'),
                ('Tìm bằng chứng','Câu hỏi → truy xuất → hợp thứ hạng nếu bật → reranker → các đoạn được chọn'),
                ('Trả lời và kiểm tra','Câu hỏi + nguồn → Qwen3 → JSON → kiểm citation ID → hiển thị trang nguồn')],
                'Vùng bảng và hình đang được khảo sát riêng; không mặc định mọi vùng đã được chuyển thành nội dung tra cứu.')
        elif name=='corpus':
            snapshot=load(ROOT/'data/manifests/corpus_snapshot.json')
            names=['Quy chế đào tạo QĐ 1727/2021','Hướng dẫn thực tập tốt nghiệp 2022','Sổ tay sinh viên 2024']
            table(doc,'Bảng 1 Corpus dùng để đối chiếu',['Tài liệu','Trang PDF','Chunk G0'],
                  [[n,d['page_count'],d['chunk_count']] for n,d in zip(names,snapshot['documents'])],[4.3,1,1],
                  'Nguồn M2-D0. G0 là snapshot lịch sử; số chunk thay đổi trong từng phép thử chunking.')
        elif name=='data_contract':
            table(doc,'Bảng 2 Dữ liệu được giữ để truy nguyên',['Thành phần','Dữ liệu chính','Dùng để kiểm tra'],[
                ['Manifest tài liệu','ID, tên, SHA-256, nguồn','Đúng tệp và phiên bản'],
                ['PageArtifacts','Trang, bbox, loại vùng, hash','Mở lại vùng chữ, bảng hoặc ảnh'],
                ['Chunk','Nội dung, ID, khoảng nguồn','Ánh xạ kết quả về đoạn gốc'],
                ['RetrievalHit','Hạng, điểm, ID chunk','So sánh trước và sau xếp hạng'],
                ['GroundingSource','S1/S2, chunk, trang, nội dung','Giới hạn nguồn LLM được dẫn']],[1.4,2.6,2.3],
                'Manifest lưu record tài liệu; các dòng còn lại là dataclass đang có. Bảng chỉ liệt kê các trường chính.')
        elif name=='input_audit':
            table(doc,'Bảng 3 Khảo sát bố cục trang bằng PyMuPDF',['Tài liệu','Trang','Trang có ảnh','Bảng ứng viên'],[
                [label,d['page_count'],d['pages_with_raster'],d['table_candidates']]
                for label,d in zip(['QĐ 1727','Hướng dẫn TTTN','Sổ tay 2024','QĐ 3116 khảo sát riêng'],i['documents'])],[2.7,.8,1.4,1.4],
                'Nguồn M2-D1. Đếm vùng phát hiện, chưa đo precision/recall của bộ nhận dạng bảng.')
        elif name=='table_crop':
            figure(doc,ROOT/'data/raw/HCMUTE_QCDT_1727_2021.pdf',20,(75,104,540,218),assets/'table_source.png',
                   'Hình 2 Vùng Bảng 5 trên trang PDF 20 của QĐ 1727 — ảnh cắt trực tiếp từ nguồn',6.1)
        elif name=='figure_crop':
            figure(doc,ROOT/'data/raw/HCMUTE_SOTAYSV_2024.pdf',136,(95,445,310,660),assets/'diagram_source.png',
                   'Hình 3 Vùng sơ đồ trong Sổ tay 2024 trang PDF 136 — ví dụ quan hệ không gian mà OCR chữ có thể bỏ sót',3.2)
        elif name=='chunk_control':
            table(doc,'Bảng 4 Kiểm soát đầu vào embedding',['Cấu hình','Số chunk','BGE vượt giới hạn','E5 vượt giới hạn'],[
                ['G0 500/80',e['baseline_chunk_count'],e['baseline_input_lengths']['bge-m3']['over_original_limit'],e['baseline_input_lengths']['multilingual-e5-small']['over_original_limit']],
                ['Cửa sổ chung ≤512',e['shared_chunk_count'],e['shared_input_lengths']['bge-m3']['over_512'],e['shared_input_lengths']['multilingual-e5-small']['over_512']]],[2.3,.8,1.6,1.6],
                'Nguồn M2-E1. Hàng G0: giới hạn BGE 1024, E5 512. Hàng mới: cả hai 512. Corpus nguồn không đổi.')
        elif name=='embedding':
            rows=[]
            for model in e['embedding_models']:
                m=macro('dense_'+model['key'])
                rows.append([model['key'],num(m['character_recall_at_5']),num(m['mrr_at_10_threshold_05']),num(model['corpus_encode_seconds_after_one_warmup'],2),num(model['query_encode_latency']['p50_ms'],2)])
            table(doc,'Bảng 5 Hai embedding trên cùng đoạn không bị cắt',['Model','Recall ký tự @5','MRR @10','Nhúng corpus s','Nhúng query p50 ms'],rows,[1.9,1.1,1,1.1,1.2],
                'Nguồn M2-E1. Chất lượng: 7 câu có bằng chứng. Thời gian query: 3 lượt/câu sau warm-up, không gồm tìm chỉ mục.')
        elif name=='embedding_interpretation':
            b=e['paired_comparison_e5_minus_bge']['character_recall_at_5']
            p(doc,f"Recall ký tự trung bình là {num(macro('dense_bge-m3')['character_recall_at_5']*100,2)}% với BGE-M3 và {num(macro('dense_multilingual-e5-small')['character_recall_at_5']*100,2)}% với E5-small. Chênh E5 trừ BGE là {num(b['mean_right_minus_left']*100,2)} điểm phần trăm; khoảng bootstrap 95% từ {num(b['ci95_percentile'][0]*100,2)} đến {num(b['ci95_percentile'][1]*100,2)}. Có {b['wins_ties_losses_right'][1]} câu hòa và {b['wins_ties_losses_right'][2]} câu E5 thấp hơn về độ phủ. Không thể dùng phép thử cũ có nhiều đoạn E5 bị cắt để quy toàn bộ khác biệt cho chất lượng ngôn ngữ của model.")
        elif name=='vector_indexes':
            table(doc,'Bảng 6 Tìm láng giềng trên cùng vector BGE-M3',['Chỉ mục','Neighbor Recall@10','p50 ms','p95 ms','Kích thước KiB'],[
                [r['name'],num(r['mean_neighbor_recall_at_10_vs_flat']),num(r['search_latency']['p50_ms']),num(r['search_latency']['p95_nearest_rank_ms']),num(r['serialized_index_bytes']/1024,1)] for r in e['vector_indexes']],[2.1,1.3,.85,.85,1.2],
                'Nguồn M2-E1. Một luồng CPU, 50 lượt × 7 truy vấn. HNSW M=16; IVF nlist=4; vector chuẩn hóa L2.')
        elif name=='retrieval':
            table(doc,'Bảng 7 Truy xuất trên cửa sổ chung',['Phương pháp','Recall ký tự @5','Hit@5','MRR@10','nDCG@5'],[
                [short[key],num(macro(key)['character_recall_at_5']),num(macro(key)['hit_at_5_threshold_05']),num(macro(key)['mrr_at_10_threshold_05']),num(macro(key)['ndcg_at_5_linear_span_coverage'])] for key in short],[2.1,1.2,1,1,1],
                'Nguồn M2-E1. Hit/MRR dùng ngưỡng phủ 50% một span; định nghĩa đầy đủ ở Mục 11.')
        elif name=='reranking':
            rows=[]
            for key,r in e['reranking'].items():
                before=r['before']['character_coverage']['macro']; after=r['after']['character_coverage']['macro']
                rows.append([short[key],num(before['character_recall_at_5'])+' → '+num(after['character_recall_at_5']),num(before['mrr_at_10_threshold_05'])+' → '+num(after['mrr_at_10_threshold_05']),num(r['latency']['p50_ms'],1)])
            table(doc,'Bảng 8 Tác động của reranker trên Top-20',['Nguồn ứng viên','Recall ký tự trước → sau','MRR trước → sau','Rerank p50 ms'],rows,[1.6,1.7,1.8,1.2],
                'Nguồn M2-E1. Cùng một cross-encoder, max_length=1024; hai lượt/câu sau warm-up, gồm kiểm độ dài đầu vào.')
        elif name=='reranking_interpretation':
            a=e['reranking']['dense_bge-m3']['after']['character_coverage']['macro']
            p(doc,f"Với ứng viên Dense, Recall ký tự tăng từ {num(macro('dense_bge-m3')['character_recall_at_5']*100,2)}% lên {num(a['character_recall_at_5']*100,2)}%, nhưng MRR giảm từ {num(macro('dense_bge-m3')['mrr_at_10_threshold_05'])} xuống {num(a['mrr_at_10_threshold_05'])}. Reranker đưa thêm bằng chứng vào Top-5 nhưng không đặt chunk đạt ngưỡng đầu tiên cao hơn ở mọi câu. Kết quả này không phù hợp với một kết luận đơn giản rằng reranking luôn cải thiện toàn bộ chất lượng.")
        elif name=='generation':
            rows=[]
            for variant in ('standard','scope_check'):
                cases=[r for r in g['cases'] if r['prompt_variant']==variant]
                pos=[r for r in cases if r['answerability']=='answerable']; neg=[r for r in cases if r['answerability']!='answerable']
                rows.append([variant,f"{sum(r['status']=='generated_citations_unverified' for r in pos)}/{len(pos)}",
                    f"{sum(r['status']=='model_abstained' for r in neg)}/{len(neg)}",
                    sum(r['status'].startswith('invalid_') or r['status']=='transport_error' for r in cases),
                    num(statistics.median(r['generation_ms'] for r in cases if 'generation_ms' in r)/1000,2)])
            table(doc,'Bảng 9 Hành vi sinh trên cùng mười câu development',['Prompt','Sinh ở câu có đáp án','Từ chối ở câu thiếu căn cứ','Lỗi đầu ra','Sinh p50 s'],rows,[1.6,1.3,1.4,.9,1.1],
                'Nguồn M2-G1. Số lần sinh không phải số câu đúng. Từ chối chỉ đếm model_abstained; JSON lỗi được tách riêng.')
        elif name=='generation_interpretation':
            for variant in ('standard','scope_check'):
                rows=[r for r in g['cases'] if r['prompt_variant']==variant]
                bad=[r['qid'] for r in rows if r['answerability']!='answerable' and r['status']=='generated_citations_unverified']
                false_ref=[r['qid'] for r in rows if r['answerability']=='answerable' and r['status']=='model_abstained']
                errors=[r['qid']+' ('+r['status']+')' for r in rows if r['status'].startswith('invalid_')]
                p(doc,f"Prompt {variant}: câu thiếu căn cứ nhưng vẫn trả lời là {', '.join(bad) if bad else 'không có'}; lỗi đầu ra gặp ở {', '.join(errors) if errors else 'không có'}. Số câu có bằng chứng bị model từ chối: {len(false_ref)}.")
            p(doc,'Yêu cầu kiểm tra phạm vi trong prompt chưa khắc phục được lỗi trên tập này. Hai biến thể chạy nối tiếp trên cùng development, chưa cân bằng thứ tự hoặc đo độ ổn định qua nhiều lần sinh. Cần xem nguồn và nội dung từng câu trước khi đề xuất thêm cơ chế từ chối.')
        elif name=='cases':
            b={r['question_id']:r for r in e['retrieval']['dense_bge-m3']['character_coverage']['per_question']}
            f={r['question_id']:r for r in e['retrieval']['dense_multilingual-e5-small']['character_coverage']['per_question']}
            table(doc,'Bảng 10 Độ phủ theo từng câu',['Câu','BGE Recall ký tự','E5 Recall ký tự','BGE MRR','E5 MRR'],[
                [qid,num(b[qid]['character_recall_at_5']),num(f[qid]['character_recall_at_5']),num(b[qid]['mrr_at_10_threshold_05']),num(f[qid]['mrr_at_10_threshold_05'])] for qid in b],[.7,1.5,1.5,1.3,1.3],
                'Nguồn M2-E1. Giữ kết quả từng câu để nhận ra hòa/thắng/thua thay vì chỉ nhìn trung bình.')
        elif name=='console':
            cold=load(ROOT/'artifacts/results/m2_console/cold.json')
            warm=load(ROOT/'artifacts/results/m2_console/warm_interactive_20261025.json')
            table(doc,'Bảng 11 Kiểm tra khởi tạo console',['Lượt chạy','Cache vector','Tổng khởi tạo s','Nhúng corpus s'],[
                ['Lượt không có cache','Miss',num(cold['startup']['total_seconds'],2),num(cold['startup']['dense']['corpus_encode_and_cache_write_seconds'],2)],
                ['Lượt console có cache','Hit' if warm['startup']['dense']['cache_hit'] else 'Miss',num(warm['startup']['total_seconds'],2),'< 0,001']],[2.4,1.1,1.4,1.4],
                'Nguồn M2-C0 và M2-C1. Hai lượt đơn; reranker lần sau dùng giới hạn 1024 thay vì 512. Không xem đây là benchmark tăng tốc có kiểm soát.')
            p(doc,'Trích kết quả console ở câu P007: nguồn hạng 1 là HCMUTE_QCDT_1727_2021__c0038, Chương IV, Điều 17, trang PDF 23–24. Lượt đầu đã sinh câu trả lời và trả S1. Log gốc được lưu cục bộ để đối chiếu; đoạn trình bày này là bản trích log, không phải ảnh chụp màn hình hay bằng chứng chấm đúng ngữ nghĩa.')
            p(doc,f"Lượt console kiểm tra lại ngày 25/10 đã hoàn thành trong {num(warm['total_seconds'],2)} giây, gồm khởi tạo {num(warm['startup']['total_seconds'],2)} giây và sinh {num(warm['query']['generation_ms']/1000,2)} giây. Top-20 không có cặp bị cắt ở max_length=1024. Chương trình trả S1 hợp lệ về ID; phần nội dung vẫn chờ đối chiếu ngữ nghĩa.")
        elif name=='evidence_manifest':
            table(doc,'Bảng 12 Danh mục minh chứng chính',['Mã','Nội dung','Tệp số liệu trong docs/evidence/m2/runs'],[
                ['M2-D0','Snapshot G0','corpus_snapshot.json'],['M2-D1','Khảo sát trang nguồn','input_artifacts_summary.json'],
                ['M2-E1','Embedding và ANN có kiểm soát','controlled_evaluation.json'],['M2-G1','Hai prompt local','console_generation.json'],
                ['M2-C0','Console lần chưa có cache','console_cold.json'],['M2-C1','Console kiểm tra lại 25/10','console_warm.json']],[.8,2.3,3.2],
                'Mỗi tệp giữ run_id hoặc thời điểm chạy, cấu hình và liên kết nguồn. Không công bố toàn văn PDF hoặc nguồn chứa dữ liệu cá nhân.')
        elif name=='code_revision':
            p(doc,'Mã revision trước khi thực nghiệm: '+e['git_revision_before_run']+'. Mã SHA-256 của script và dữ liệu được lưu trong artifact vì lượt chạy bao gồm thay đổi chưa commit. Nhật ký bàn giao ghi commit cuối chứa mã và báo cáo của đợt này.')
        elif name=='reproduction':
            for line in ['Mở PowerShell tại D:\\RAG\\rag-hcmute-dot2 và dùng Python của env rag-hcmute, không dùng env base.',
                         'Console tối giản: .\\scripts\\demo_m2.ps1 -Method bm25 -NoAnswer -Question "Thủ tục xin nghỉ học tạm thời được quy định ra sao?"',
                         'Console đầy đủ: dùng scripts/demo_m2.ps1 để chọn câu hỏi và bật sinh cục bộ. Mô hình phải có sẵn trên máy; script không tải trọng số.',
                         'Đánh giá kiểm soát: scripts/run_m2_controlled_evaluation.py; đánh giá prompt: scripts/run_m2_console_demo.py. Chi tiết tham số và thư mục ở docs/MOC2_HUONG_DAN.md.']:
                para=p(doc,line)
                para.alignment=WD_ALIGN_PARAGRAPH.LEFT
        elif name=='traceability':
            rows=[['YC1','Tên đề tài đúng yêu cầu','Bìa'],['YC2','Luồng đầy đủ, phân biệt từng khâu','1'],['YC3','Chunk và vùng nguồn có provenance','3'],['YC4','Audit ảnh/bảng; OCR còn giới hạn','4'],['YC5','So ranh giới và độ dài đầu vào','5'],['YC6','Hai model; chưa đủ sáu','6'],['YC7','Flat/HNSW/IVF; Qdrant từ Mốc 1','7'],['YC8','BM25/dense/RRF có số đo','8'],['YC9','Một reranker, trước và sau','9'],['YC10','Hai prompt, citation, từ chối còn lỗi','10'],['YC11','Chỉ số retrieval; thiếu chấm người và test','11'],['YC12','Console chạy local đầu–cuối','12'],['YC13','Giải thích cơ chế và lỗi; tiếp tục mở rộng','Toàn báo cáo']]
            table(doc,'Bảng 13 Trạng thái theo YC1 đến YC13',['YC','Minh chứng và giới hạn','Mục'],rows,[.7,4.6,1],
                'Có minh chứng ở một phần không đồng nghĩa đã hoàn tất toàn bộ kế hoạch của YC đó.')
        elif name=='references':
            refs=[
              '[1] P. Lewis và cộng sự (2020). Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks. NeurIPS. https://arxiv.org/abs/2005.11401',
              '[2] BAAI. BGE-M3 model card. https://huggingface.co/BAAI/bge-m3',
              '[3] Intfloat. Multilingual-E5-small model card. https://huggingface.co/intfloat/multilingual-e5-small',
              '[4] FAISS contributors. Faiss indexes. https://github.com/facebookresearch/faiss/wiki/Faiss-indexes',
              '[5] PyMuPDF contributors. Page API và find_tables. https://pymupdf.readthedocs.io/en/latest/page.html',
              '[6] Tesseract contributors. Improving the quality of the output. https://tesseract-ocr.github.io/tessdoc/ImproveQuality.html',
              '[7] G. V. Cormack, C. L. A. Clarke và S. Büttcher (2009). Reciprocal Rank Fusion outperforms Condorcet and individual Rank Learning Methods. SIGIR. https://cormack.uwaterloo.ca/cormacksigir09-rrf.pdf',
              '[8] BAAI. BGE-Reranker-v2-m3 model card. https://huggingface.co/BAAI/bge-reranker-v2-m3',
              '[9] Ollama. Generate a chat message. https://docs.ollama.com/api/chat']
            for ref in refs:
                para=add_p(doc,ref,align=WD_ALIGN_PARAGRAPH.LEFT,first_line=False)
                para.paragraph_format.keep_together=True
            p(doc,'Các nguồn kỹ thuật được mở kiểm tra ngày 24/10/2026. Nguồn PDF HCMUTE và mã băm nằm trong manifest dữ liệu của dự án.')
        else: raise ValueError('Unknown report slot '+name)
    for block in (ROOT/'docs/MOC2_REPORT_CONTENT.md').read_text(encoding='utf-8').split('\n\n'):
        block=block.strip()
        if not block: continue
        if block.startswith('{{') and block.endswith('}}'): slot(block[2:-2])
        elif block.startswith('### '): add_heading(doc,block[4:],2)
        elif block.startswith('## '): add_heading(doc,block[3:],1)
        elif block.startswith('# '):
            para=add_heading(doc,block[2:],1)
            para.alignment=WD_ALIGN_PARAGRAPH.CENTER
        else: p(doc,block.replace('\n',' '))
    doc.core_properties.title='Tìm hiểu Retrieval Augmented Generation (RAG)'
    doc.core_properties.subject='Báo cáo tiến độ Mốc 2'
    args.output.parent.mkdir(parents=True,exist_ok=True)
    doc.save(args.output)
    if hashlib.sha256(TEMPLATE.read_bytes()).hexdigest()!=TEMPLATE_SHA: raise RuntimeError('Source changed.')
    print(args.output)

if __name__=='__main__': main()
