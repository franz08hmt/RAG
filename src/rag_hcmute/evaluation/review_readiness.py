"""Readiness audit for expanded question drafts. Never approves or assigns labels."""
from __future__ import annotations
import json
import math
import re
import unicodedata
from collections import Counter


def normalize(text):
    return " ".join(unicodedata.normalize("NFC", text).casefold().split())


def audit_review_rows(rows, *, snapshot_id, source_pages=None):
    ids, question_keys, groups = set(), {}, {}
    errors, counts, split_counts = [], Counter(), Counter()
    pending = 0
    for row in rows:
        qid = row.get('question_id', '')
        if not qid or qid in ids:
            errors.append({'id':qid,'reason':'missing_or_duplicate_id'})
        ids.add(qid)
        if row.get('snapshot_id') != snapshot_id:
            errors.append({'id':qid,'reason':'snapshot_mismatch'})
        key = re.sub(r'[^\w\s]', '', normalize(row.get('question', '')))
        if not key:
            errors.append({'id':qid,'reason':'empty_question'})
        elif key in question_keys:
            errors.append({'id':qid,'reason':'duplicate_question','other_id':question_keys[key]})
        question_keys[key] = qid
        split = row.get('split','')
        group = row.get('leakage_group','')
        if split and split not in {'development','holdout'}:
            errors.append({'id':qid,'reason':'invalid_split'})
        if re.fullmatch(r'P\d+', qid) and split == 'holdout':
            errors.append({'id':qid,'reason':'pilot_cannot_be_holdout'})
        if split and not group:
            errors.append({'id':qid,'reason':'missing_leakage_group'})
        if group and split:
            groups.setdefault(group,set()).add(split)
        if row.get('review_status') != 'human_verified':
            pending += 1
            if split == 'holdout':
                errors.append({'id':qid,'reason':'holdout_requires_human_verification'})
            continue
        # A human identity is an audit field, not proof that the agent may sign it.
        valid = True
        for field in ('verified_by','verified_at','reference_answer','leakage_group','created_by'):
            if not row.get(field,'').strip():
                errors.append({'id':qid,'reason':f'missing_{field}'})
                valid = False
        answerability = row.get('answerability')
        if answerability not in {'answerable','unanswerable'}:
            errors.append({'id':qid,'reason':'invalid_answerability'})
            valid = False
        if not split:
            errors.append({'id':qid,'reason':'reviewed_without_split'})
            valid = False
        try:
            evidence = json.loads(row.get('evidence_json','[]'))
            if not isinstance(evidence,list):
                raise ValueError()
        except (ValueError,TypeError):
            evidence = []
            errors.append({'id':qid,'reason':'invalid_evidence_json'})
            valid = False
        if answerability=='answerable' and not evidence:
            errors.append({'id':qid,'reason':'missing_evidence'})
            valid = False
        if answerability=='unanswerable' and (evidence or not row.get('absence_review_note','').strip()):
            errors.append({'id':qid,'reason':'unanswerable_requires_scope_review_without_positive_evidence'})
            valid = False
        source_locations = set()
        for span in evidence:
            try:
                did, page, quote = span['document_id'], span['pdf_page'], span['quote']
                if not isinstance(page,int) or isinstance(page,bool) or not isinstance(quote,str) or not quote.strip():
                    raise ValueError()
                if source_pages is None or (did,page) not in source_pages:
                    raise ValueError()
                # NFC + whitespace only; preserve case and punctuation for quote check.
                canon = lambda s:' '.join(unicodedata.normalize('NFC',s).split())
                if canon(quote) not in canon(source_pages[(did,page)]):
                    raise ValueError()
                source_locations.add((did, page, canon(quote)))
            except (KeyError,TypeError,ValueError):
                errors.append({'id':qid,'reason':'evidence_not_found_in_snapshot'})
                valid = False
        tags = set(row.get('tags','').split('|'))
        if 'multi_span' in tags and len(source_locations) < 2:
            errors.append({'id':qid,'reason':'multi_span_requires_distinct_evidence'})
            valid = False
        if valid:
            counts['reviewed'] += 1
            counts[answerability] += 1
            counts['human_authored'] += row.get('created_by')=='human'
            for tag in ('requires_table_or_image','multi_span','lexical_gap'):
                counts[tag] += tag in tags
            split_counts[split] += 1
    for group,splits in groups.items():
        if len(splits)>1:
            errors.append({'group':group,'reason':'group_leakage_across_splits'})
    minima={'reviewed':80,'unanswerable':15,'requires_table_or_image':10,'multi_span':10,'lexical_gap':20}
    deficits={k:max(0,n-counts[k]) for k,n in minima.items()}
    deficits['human_authored']=max(0, math.ceil(.3*max(minima['reviewed'],counts['reviewed']))-counts['human_authored'])
    ready = not errors and not any(deficits.values()) and all(split_counts[s]>0 for s in ('development','holdout'))
    return {'snapshot_id':snapshot_id,'row_count':len(rows),'pending_rows':pending,'counts':dict(counts),
            'split_counts':dict(split_counts),'minimum_deficits':deficits,'target_question_count':100,
            'errors':errors,'ready_for_freeze':ready,
            'interpretation':'Checks recorded labels and exact source quotes; does not replace human correctness/answerability review. No labels or splits changed.'}
