"""Run/review a real workbook in an isolated bank and emit metadata-only quality evidence.

The supplied index is an expectation, never extraction ground truth. No question text,
private database, page images or answer guesses are included in the report.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'as-v3-reference')]
from backend.bank import Bank


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('pdf',type=Path);parser.add_argument('--index',required=True,type=Path)
    parser.add_argument('--runtime',required=True,type=Path);parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--batch-id');parser.add_argument('--import-document',action='store_true')
    args=parser.parse_args();pdf=args.pdf.resolve();index=json.loads(args.index.read_text());sha=hashlib.sha256(pdf.read_bytes()).hexdigest()
    if sha!=index['document']['sha256']:raise ValueError('Index/PDF SHA mismatch; do not reuse expected counts from a different file')
    if args.runtime.resolve().is_relative_to(ROOT/'runtime'):raise ValueError('Use a separate audit runtime, outside the normal student/public bank')
    bank=Bank(args.runtime)
    if args.import_document:
        start=time.monotonic();batch=bank.enqueue_import([pdf],scope='bank',owner_id='isolated-workbook-audit',reuse_confirmed=False,auto_solve=False,ocr=False)
        bank.jobs.work(limit=1,batch_id=batch.batch_id);elapsed=round(time.monotonic()-start,3)
    else:
        if not args.batch_id:raise ValueError('--batch-id or --import-document required')
        batch=bank.store.batch(args.batch_id);elapsed=None
    batch=bank.store.batch(batch.batch_id);f=batch.files[0]
    if f['status']!='imported':raise ValueError('Import incomplete: '+json.dumps(f,ensure_ascii=False)[:500])
    did=f['document_id'];source=bank.store.source(did)
    if source.reuse_confirmed or source.owner_id!='isolated-workbook-audit':raise ValueError('Expected an isolated, unpublished audit source')
    rows=[(q,v,a,bank.meta(v.version_id)) for q,v,_,a in bank.store.list_questions(scope='bank',include_drafts=True,limit=None) if q.document_id==did]
    expectations={(str(q['unit']),str(q['question_number_in_unit'])):q for q in index['questions']}
    counts=Counter();units=[];details=[];assets_checked=set();missing_assets=[]
    from PIL import Image
    for u in index['unit_page_ranges']:
        section=str(u['unit']);group=[row for row in rows if row[1].source_section==section]
        stats=Counter();expected=[q for q in index['questions'] if q['unit']==u['unit']]
        for q,v,a,m in group:
            flags=[];pages=[s.page for s in v.spans];crops=[]
            for aid in m.get('safe_assets',[]):
                asset=bank.store.asset(aid);path=bank.assets/asset.relative_path
                if aid not in assets_checked:
                    assets_checked.add(aid)
                    if not path.exists() or hashlib.sha256(path.read_bytes()).hexdigest()!=asset.sha256:missing_assets.append(aid)
                    else:
                        with Image.open(path) as image:image.verify()
                crops.append(asset.page)
            expected_row=expectations.get((section,q.source_number));labels=[o.label for o in v.options]
            label_complete=labels==list('ABCD');visual_review='visual_and_formula_transcription_requires_review' in v.warnings
            option_review='visual_option_requires_review' in v.warnings
            crop_coverage=set(crops)==set(pages) and bool(crops)
            cross_anomaly=any(b!=a+1 for a,b in zip(pages,pages[1:])) or len(pages)!=len(set(pages))
            directory_match=bool(expected_row and expected_row['pdf_page_start']==pages[0])
            if not label_complete:flags.append('option_label_anomaly')
            if not crop_coverage:flags.append('crop_coverage_anomaly')
            if cross_anomaly:flags.append('cross_page_anomaly')
            if visual_review:flags.append('visual_formula_review_required')
            if option_review:flags.append('visual_option_review_required')
            verified=bool(a and a.status.value=='Verified')
            for name,condition in [('labels_and_crops_complete',label_complete and crop_coverage),('automated_structure_complete',label_complete and crop_coverage and not m['issues'] and not visual_review),('visual_formula_review',visual_review),('visual_option_review',option_review),('cross_page',len(pages)>1),('cross_page_anomalies',cross_anomaly),('directory_topic_candidates',directory_match),('confirmed_core_topics',bool(m['core'])),('verified_answers',verified),('unconfirmed_answers',not verified),('review_pending',bool(flags or not verified or not m['core']))]:stats[name]+=int(condition)
            details.append({'question_id':q.question_id,'version_id':v.version_id,'unit':u['unit'],'source_number':q.source_number,'pages':pages,'labels':labels,'candidate_topic_id':expected_row['pl_canonical_topic_id'] if directory_match else None,'confirmed_topics':m['core'],'answer_status':a.status.value if a else 'Unresolved','flags':flags,'publication':q.publication})
        row={'unit':u['unit'],'expected':len(expected),'recognized':len(group),'unique_question_ids':len({q.question_id for q,_,_,_ in group}),'unique_unit_numbers':len({q.source_number for q,_,_,_ in group}),**dict(stats)}
        units.append(row);counts.update(stats)
    original=bank.assets/did/'original.pdf'
    report={'document':{'filename':pdf.name,'sha256':sha,'pages':source.page_count,'bytes':pdf.stat().st_size,'original_retained_and_hash_verified':original.exists() and hashlib.sha256(original.read_bytes()).hexdigest()==sha},
            'expected_candidates':len(index['questions']),'recognized':len(rows),'unique_question_ids':len({q.question_id for q,_,_,_ in rows}),'total':dict(counts),'units':units,
            'published':sum(q.publication=='approved' for q,_,_,_ in rows),'reuse_confirmed':source.reuse_confirmed,'missing_assets':missing_assets,'verified_display_assets':len(assets_checked),
            'queue':{'batch_id':batch.batch_id,'job_id':f['job_id'],'status':batch.status,'segments':f.get('segments',[]),'progress':f.get('progress'),'this_import_seconds':elapsed},
            'limits':['A–D labels and valid crops do not prove complete semantic transcription.','Visual/formula review flags are automated review requirements, not confirmed content corruption.','Directory candidate Topics require reasoning/tag review and are not published core tags.','No reliable complete answer key was supplied; no automatic scoring or public publication.','Only representative crops have been manually viewed; 369-question visual acceptance is incomplete.'],
            'questions':details}
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps({k:v for k,v in report.items() if k not in ['questions','limits','queue']},ensure_ascii=False))


if __name__=='__main__':main()
