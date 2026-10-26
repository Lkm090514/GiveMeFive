"""Optional V2 repair/review rules on V4 answers and PracticeSessions; no second ledger."""
from __future__ import annotations

import io
import json
from pathlib import Path

from gmf_v3.contracts import AnswerStatus, uid
from gmf_v3.store import ConflictError


class Reviews:
    DELAY_MS = 24 * 3600 * 1000  # V2 emptyState().settings.delayHours baseline.

    def __init__(self, sessions):
        self.sessions = sessions
        self.bank, self.store = sessions.bank, sessions.store

    def unlocked(self, c, owner):
        if self.sessions._lock(c, owner):
            raise ValueError('正式考试期间不开放学习记录和复查')

    def load(self, c, owner, qid):
        row=c.execute('SELECT payload FROM v4_review_cases WHERE owner_id=? AND question_id=?',(owner,qid)).fetchone()
        return json.loads(row[0]) if row else None

    def save(self, c, owner, case):
        c.execute('INSERT INTO v4_review_cases VALUES(?,?,?) ON CONFLICT(owner_id,question_id) DO UPDATE SET payload=excluded.payload',
                  (owner,case['question_id'],json.dumps(case)))

    def event(self, case, kind, **details):
        case.setdefault('events',[]).append({'id':uid('reviewevent'),'at':self.sessions.ms(),'kind':kind,**details})

    def on_error(self, c, owner, r):
        case=self.load(c,owner,r['question_id']) or {'question_id':r['question_id'],'notes':[],'events':[]}
        case.update(version_id=r['version_id'],source_record_id=r['record_id'],state='repair',due_at=None,active_review=None,removed=False)
        self.event(case,'error',record_id=r['record_id']);self.save(c,owner,case)

    def record(self, c, owner, rid):
        row=c.execute('SELECT payload FROM v4_answers WHERE owner_id=? AND record_id=?',(owner,rid)).fetchone()
        if not row:raise KeyError('Answer not found')
        return json.loads(row[0])

    def uncertain(self, owner, rid):
        with self.store.connect(write=True) as c:
            self.unlocked(c,owner);r=self.record(c,owner,rid)
            session=self.sessions._load(c,r['session_id'],owner);effective=r
            if session.get('grade_id'):
                grade=c.execute('SELECT payload FROM v4_grades WHERE grade_id=?',(session['grade_id'],)).fetchone()
                if grade:effective=next((x for x in json.loads(grade[0])['records'] if x.get('record_id')==rid),r)
            key=self.sessions._key(c,r['version_id'])
            if effective['status']!='correct' or not key or key['status']!='Verified' or key['answer_key_id']!=effective.get('answer_key_id'):
                raise ValueError('仅对当前可靠评分为正确的作答标记“猜对但不确定”')
            c.execute('INSERT OR IGNORE INTO v4_bookmarks VALUES(?,?)',(owner,r['question_id']))
            case=self.load(c,owner,r['question_id'])
            if not case:
                case={'question_id':r['question_id'],'version_id':r['version_id'],'source_record_id':rid,'state':'repair','due_at':None,'notes':[],'events':[]}
            new_mark=rid not in case.get('uncertain_records',[])
            if new_mark:
                case.setdefault('uncertain_records',[]).append(rid);self.event(case,'uncertain',record_id=rid)
            case['removed']=False;self.save(c,owner,case)
            if new_mark and session.get('review'):
                target=self.load(c,owner,session['review']['source_question_id'])
                passes=[e for e in (target or {}).get('events',[]) if e['kind']=='review_passed']
                if target and passes and passes[-1].get('session_id')==session['id'] and not target.get('active_review'):
                    target.update(state='independent',due_at=None)
                    self.event(target,'review_uncertain',session_id=session['id'],record_id=rid);self.save(c,owner,target)
                    session['review_outcome_revision']={'reason':'提交后标记了猜对但不确定','state':'independent','record_id':rid}
                    self.sessions._save(c,session)
            return case

    def require_case(self, c, owner, qid):
        case=self.load(c,owner,qid)
        if not case:
            wrong=c.execute('SELECT payload FROM v4_wrong WHERE owner_id=? AND question_id=?',(owner,qid)).fetchone()
            if not wrong:raise KeyError('Case not found')
            m=json.loads(wrong[0])
            if m.get('removed'):raise ValueError('此题已移出待复查记录')
            case={'question_id':qid,'version_id':m['version_id'],'source_record_id':m['record_ids'][-1],'state':'repair','due_at':None,'notes':[],'events':[]}
        if case.get('removed'):raise ValueError('此题已移出待复查记录')
        return case

    def note(self, owner, qid, data):
        cause=data.get('cause','');reasoning=data.get('reasoning','');text=data.get('text','');assets=data.get('assets',[])
        if any(not isinstance(x,str) or len(x)>12000 for x in [cause,reasoning,text]) or not isinstance(assets,list) or len(assets)>8:
            raise ValueError('笔记内容或图片数量超出范围')
        has_note=any(x.strip() for x in [cause,reasoning,text]) or bool(assets)
        if not has_note and data.get('ready_for_check') is not True:raise ValueError('请写笔记、添加步骤图片，或主动标记已完成修正')
        with self.store.connect(write=True) as c:
            self.unlocked(c,owner);case=self.require_case(c,owner,qid)
            if case.get('active_review'):raise ValueError('请先完成或退出当前复查，再修改修正记录')
            previous=case['notes'][-1]['id'] if case['notes'] else None
            if data.get('expected_note_id')!=previous:raise ConflictError('笔记已更新，请刷新后再保存；原历史已保留')
            for aid in assets:
                row=c.execute('SELECT version_id FROM v4_note_assets WHERE asset_id=? AND owner_id=?',(aid,owner)).fetchone()
                if not row or row[0]!=case['version_id']:raise ValueError('步骤图片不属于本用户和此题版本')
            note={'id':uid('note'),'version_id':case['version_id'],'at':self.sessions.ms(),'cause':cause.strip(),'reasoning':reasoning.strip(),'text':text.strip(),'assets':list(dict.fromkeys(assets)),'supersedes':previous} if has_note else None
            if note:case['notes'].append(note)
            if data.get('ready_for_check') is True:case.update(state='independent',due_at=None)
            self.event(case,'correction' if data.get('ready_for_check') else 'note',note_id=note['id'] if note else None);self.save(c,owner,case)
            return case

    def image(self, owner, qid, data):
        if len(data)>4*1024*1024:raise ValueError('步骤图片须小于 4 MiB')
        from PIL import Image,UnidentifiedImageError
        try:
            with Image.open(io.BytesIO(data)) as image:
                if image.format not in ['PNG','JPEG','WEBP'] or image.width*image.height>20_000_000:raise ValueError('请选择 PNG、JPEG 或 WebP 图片，最多 2000 万像素')
                out=io.BytesIO();image.convert('RGB').save(out,format='PNG');encoded=out.getvalue()
                if len(encoded)>12*1024*1024:raise ValueError('图片展开后过大，请缩小后重试')
        except (UnidentifiedImageError,OSError,Image.DecompressionBombError) as exc:raise ValueError('无效图片') from exc
        with self.store.connect(write=True) as c:
            self.unlocked(c,owner);case=self.require_case(c,owner,qid);aid=uid('noteasset')
            path=self.bank.root/'learning-assets'/(aid+'.png');path.parent.mkdir(exist_ok=True)
            path.write_bytes(encoded)
            payload={'relative_path':path.relative_to(self.bank.root).as_posix(),'media_type':'image/png'}
            c.execute('INSERT INTO v4_note_assets VALUES(?,?,?,?)',(aid,owner,case['version_id'],json.dumps(payload)))
            return {'asset_id':aid,'version_id':case['version_id']}

    def image_path(self, owner, aid):
        with self.store.connect(write=True) as c:
            self.unlocked(c,owner)
            row=c.execute('SELECT payload FROM v4_note_assets WHERE owner_id=? AND asset_id=?',(owner,aid)).fetchone()
            if not row:raise KeyError('Image not found')
            path=(self.bank.root/json.loads(row[0])['relative_path']).resolve()
            if not path.is_relative_to(self.bank.root):raise KeyError('Image not found')
            return path

    def seen(self, c, owner):
        ids=set();fingerprints=set()
        for row in c.execute('SELECT payload FROM v4_sessions WHERE owner_id=?',(owner,)):
            for item in json.loads(row[0])['items']:
                ids.add(item['question_id'])
                fingerprints.add(item.get('fingerprint') or self.store.version(item['version_id']).fingerprint)
        return ids,fingerprints

    def select(self, c, owner, req, sid):
        qid=req.get('review_question');phase=req.get('review_phase');case=self.require_case(c,owner,qid)
        if any(req.get(k) for k in ['paper_id','question_ids','related_to','continue_from','repeat_seen','random']):raise ValueError('复查不可覆盖选题范围')
        if case.get('active_review'):raise ValueError('已有未完成的复查，请继续原会话')
        if phase not in ['independent','delayed']:raise ValueError('无效复查阶段')
        if phase=='independent' and case['state']!='independent':raise ValueError('请先主动保存修正并准备独立检查')
        if phase=='delayed' and (case['state']!='delayed' or self.sessions.ms()<(case.get('due_at') or 0)):raise ValueError('延迟复查尚未到期')
        v=self.store.version(case['version_id']);m=self.bank.meta(v.version_id);types=self.bank.types(v.version_id)
        source=self.record(c,owner,case['source_record_id'])
        if 'course_id' in source:
            m={**m,'course_id':source['course_id'],'core':source.get('topic_ids',[])}
            types={**types,'methods':source.get('question_types',[]),'structures':source.get('question_structures',[])}
        if len(m['core'])!=1:raise ValueError('独立复查需要已确认的单一核心 Topic；综合题可继续自由专项练习')
        ids,fps=self.seen(c,owner);ids.add(qid);fps.add(v.fingerprint)
        refs=self.bank.candidates(m['course_id'],None,m['core'],False,ids)
        refs=[row for row in refs if row[1].fingerprint not in fps and row[2] and row[2].status==AnswerStatus.VERIFIED]
        typed=bool(types['methods'] or types['structures'])
        if typed:
            refs=[row for row in refs if set(types['methods'])&set(self.bank.types(row[1].version_id)['methods']) or set(types['structures'])&set(self.bank.types(row[1].version_id)['structures'])]
        count=int(req.get('count',3))
        if not 1<=count<=20:raise ValueError('复查题量应在 1–20 之间')
        if not refs:raise ValueError('公共题库缺少符合范围、尚未见过且答案可靠的题；暂不能进行独立复查，可继续自由练习')
        review={'source_question_id':qid,'source_version_id':v.version_id,'phase':phase,'topic_id':m['core'][0],'type_match':'exact-shared-type' if typed else 'topic-only-type-unconfirmed','requested_count':count,'actual_count':min(count,len(refs))}
        case['active_review']=sid;self.event(case,'review_started',session_id=sid,phase=phase);self.save(c,owner,case)
        return refs[:count],review

    def finish(self, c, s, records):
        review=s.get('review')
        if not review:return
        case=self.load(c,s['owner_id'],review['source_question_id'])
        if not case or case.get('active_review')!=s['id']:return
        passed=all(r['status']=='correct' and r.get('independent') and not r.get('assisted') and (key:=self.sessions._key(c,r['version_id'])) and key['status']=='Verified' and key['answer_key_id']==r['answer_key_id'] for r in records)
        failed=any(r['status'] in ['incorrect','unanswered'] for r in records)
        if failed:case.update(state='repair',due_at=None)
        elif passed and review['phase']=='independent':case.update(state='delayed',due_at=self.sessions.ms()+self.DELAY_MS)
        elif passed and review['phase']=='delayed':case.update(state='passed',due_at=None)
        outcome='failed' if failed else 'passed' if passed else 'inconclusive'
        case['active_review']=None;self.event(case,'review_'+outcome,session_id=s['id'],phase=review['phase']);self.save(c,s['owner_id'],case)
        s['review_outcome']={'outcome':outcome,'state':case['state'],'due_at':case['due_at']}

    def enrich(self, c, owner, rows):
        indexed={m['question_id']:m for m in rows}
        for row in c.execute('SELECT question_id FROM v4_bookmarks WHERE owner_id=?',(owner,)):
            qid=row[0];case=self.load(c,owner,qid)
            if not case or case.get('removed'):continue
            if qid not in indexed:
                indexed[qid]={'question_id':qid,'version_id':case['version_id'],'record_ids':[],'last_status':'uncertain','question':self.bank.public(qid,case['version_id']),'records':[json.loads(r[0]) for r in c.execute('SELECT payload FROM v4_answers WHERE owner_id=? AND question_id=? ORDER BY rowid',(owner,qid))]}
            indexed[qid]['uncertain']=True
        for m in indexed.values():
            case=self.load(c,owner,m['question_id']);m['review']=case or {'state':'repair','notes':[],'events':[],'due_at':None}
            m['review']['display_state']='due' if case and case['state']=='delayed' and (case.get('due_at') or 0)<=self.sessions.ms() else m['review']['state']
        return list(indexed.values())
