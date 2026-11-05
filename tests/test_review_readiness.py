import json
from rag_hcmute.evaluation.review_readiness import audit_review_rows


def row(qid='Q1'):
    return {'question_id':qid,'question':'Nơi nộp?','snapshot_id':'G','review_status':'human_verified',
            'verified_by':'test_reviewer','verified_at':'2026-11-04','created_by':'human',
            'reference_answer':'Văn phòng khoa','leakage_group':'place','split':'development',
            'answerability':'answerable','evidence_json':json.dumps([{'document_id':'D','pdf_page':1,'quote':'Văn phòng khoa'}])}


def test_pending_cannot_become_test_evidence_automatically():
    r=row(); r['review_status']='pending'
    result=audit_review_rows([r],snapshot_id='G')
    assert result['pending_rows']==1
    assert not result['ready_for_freeze']
    assert result['minimum_deficits']['reviewed']==80


def test_false_quote_is_rejected_despite_human_verified_label():
    result=audit_review_rows([row()],snapshot_id='G',source_pages={('D',1):'Một nội dung khác.'})
    assert any(e['reason']=='evidence_not_found_in_snapshot' for e in result['errors'])


def test_pilot_and_group_leakage_are_detected():
    a,b=row('P007'),row('NEW')
    a['split']='holdout'; b['question']='Cần đến đâu để nộp?'
    result=audit_review_rows([a,b],snapshot_id='G',source_pages={('D',1):'Văn phòng khoa'})
    reasons={e['reason'] for e in result['errors']}
    assert 'pilot_cannot_be_holdout' in reasons
    assert 'group_leakage_across_splits' in reasons


def test_normalized_duplicate_and_snapshot_mismatch_are_detected():
    a,b=row(),row('Q2'); b['question']='  NƠI NỘP? '; b['snapshot_id']='other'
    result=audit_review_rows([a,b],snapshot_id='G',source_pages={('D',1):'Văn phòng khoa'})
    assert {'duplicate_question','snapshot_mismatch'} <= {e['reason'] for e in result['errors']}


def test_valid_small_sample_still_cannot_freeze_large_test():
    result=audit_review_rows([row()],snapshot_id='G',source_pages={('D',1):'Văn phòng khoa'})
    assert result['counts']['reviewed']==1
    assert not result['ready_for_freeze']


def test_duplicate_spans_do_not_qualify_for_multi_span_quota():
    item = row()
    item['tags'] = 'multi_span'
    item['evidence_json'] = json.dumps(json.loads(item['evidence_json']) * 2)
    result = audit_review_rows([item], snapshot_id='G', source_pages={('D',1):'Văn phòng khoa'})
    assert 'multi_span_requires_distinct_evidence' in {e['reason'] for e in result['errors']}


def test_pending_holdout_cannot_be_included_in_freeze():
    item = row('NEW')
    item.update(review_status='pending', split='holdout')
    result = audit_review_rows([item], snapshot_id='G')
    assert result['minimum_deficits']['human_authored'] == 24
    assert 'holdout_requires_human_verification' in {e['reason'] for e in result['errors']}
