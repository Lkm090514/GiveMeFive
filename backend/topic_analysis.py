"""Explainable projections of existing answer evidence, never a mastery model or new ledger."""
from __future__ import annotations

from collections import defaultdict
import json


def analyze(sessions, owner, *, session_id=None):
    bank=sessions.bank
    with bank.store.connect(write=True) as c:
        sessions.reviews.unlocked(c,owner)
        if session_id:
            s=sessions._load(c,session_id,owner)
            if s['status']!='submitted':raise ValueError('提交后才生成本次知识点分析')
        records=[json.loads(r[0]) for r in c.execute('SELECT payload FROM v4_answers WHERE owner_id=? ORDER BY rowid',(owner,))]
        uncertain=set()
        for row in c.execute('SELECT payload FROM v4_review_cases WHERE owner_id=?',(owner,)):
            uncertain.update(json.loads(row[0]).get('uncertain_records',[]))
        # Score revisions project onto final responses only; original facts are never updated.
        final={}
        for r in records:final[(r['session_id'],r['question_id'])]=r['record_id']
        revisions={}
        for row in c.execute("SELECT s.payload session,g.payload grade FROM v4_sessions s JOIN v4_grades g ON g.grade_id=json_extract(s.payload,'$.grade_id') WHERE s.owner_id=?",(owner,)):
            s=json.loads(row['session']);g=json.loads(row['grade'])
            if g['revision']>1:
                for r in g['records']:
                    rid=final.get((s['id'],r['question_id']))
                    if rid:revisions[rid]={**r,'scoring_revision':g['revision'],'scoring_source':g['source']}
        keys={}
        for r in records:
            r.update(revisions.get(r['record_id'],{}));r['uncertain']=r['record_id'] in uncertain
            vid=r['version_id']
            if vid not in keys:keys[vid]=sessions._key(c,vid)
            key=keys[vid]
            r['reliable']=bool(key and key['status']=='Verified' and key['answer_key_id']==r.get('answer_key_id'))
    if session_id:records=[r for r in records if r['session_id']==session_id]
    topics={t['topic_id']:{'topic_id':t['topic_id'],'title':t['title'],'rows':[]} for t in bank.catalog['topics']}
    unmapped=0;multi=0;related=0
    for r in records:
        core=list(dict.fromkeys(r.get('topic_ids',[])))
        if not core:unmapped+=1
        if len(core)>1:multi+=1
        for tid in set(core+r.get('related_topics',[])):
            if tid in topics:
                topics[tid]['rows'].append({**r,'attribution':'single-core' if len(core)==1 and tid in core else 'associated-only'})
    now=sessions.ms();result=[]
    for topic in topics.values():
        rows=topic.pop('rows');direct=[r for r in rows if r['attribution']=='single-core']
        scored=[r for r in direct if r['reliable'] and r['status'] in ['correct','incorrect']]
        first={}
        for r in scored:
            if r.get('independent') and not r.get('assisted'):first.setdefault(r['question_id'],r)
        independent=list(first.values());recent=[r for r in independent if r['at']>=now-30*86400000]
        certain=[r for r in independent if not r['uncertain']]
        repeated=[r for r in scored if not r.get('independent') or r.get('assisted')]
        wrong=[r for r in independent if r['status']=='incorrect']
        types=defaultdict(dict);timeline=defaultdict(list)
        for r in independent:
            for kind in set(r.get('question_types',[])):types[kind][r['question_id']]=r
            from datetime import datetime,timezone
            timeline[datetime.fromtimestamp(r['at']/1000,timezone.utc).date().isoformat()].append(r)
        enough=len(certain)>=5
        topic.update(independent_scored=len(independent),certain_independent=len(certain),first_correct=sum(r['status']=='correct' for r in independent),first_incorrect=len(wrong),
                     recent={'days':30,'unique_questions':len(recent),'correct':sum(r['status']=='correct' for r in recent)},
                     retries={'attempts':len(repeated),'unique_questions':len({r['question_id'] for r in repeated}),'correct':sum(r['status']=='correct' for r in repeated)},
                     uncertain=sum(r['uncertain'] for r in direct),unanswered=sum(r['status']=='unanswered' for r in direct),ungraded=sum(r['status']=='ungraded' or not r['reliable'] for r in direct),
                     associated_only=sum(r['attribution']=='associated-only' for r in rows),legacy_independence_unknown=sum('independent' not in r for r in direct),
                     evidence='未评估' if not rows else '数据充分（仅描述表现）' if enough else '数据不足',
                     priority=bool(enough and len(wrong)>=2 and len(wrong)/max(1,len(independent))>.3),
                     question_types=[{'type':kind,'unique_questions':len(values),'correct':sum(r['status']=='correct' for r in values.values())} for kind,values in sorted(types.items())],
                     timeline=[{'date':day,'unique_questions':len(items),'correct':sum(r['status']=='correct' for r in items)} for day,items in sorted(timeline.items())])
        result.append(topic)
    return {'algorithm':'topic-evidence/1','session_id':session_id,'topics':result,'unmapped_records':unmapped,'multi_core_records':multi,
            'rules':{'independent_unit':'stable Question ID, first unassisted unseen attempt; retries never add independent samples','attribution':'only single core Topic contributes correctness; multi-core and related Topics are association counts only','reliability':'latest verified answer must equal effective grading snapshot; otherwise excluded pending review','sufficiency':'at least 5 distinct independent, unassisted, non-uncertain questions; descriptive threshold, not calibrated mastery','priority':'sufficient evidence, at least 2 first errors, first-error fraction above 0.30; optional practice suggestion','recent_window_days':30},'server_now':now}
