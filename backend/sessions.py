"""Server-owned practice/exam sessions. Stable V3 versions and immutable response records."""
from __future__ import annotations
import json,random,time
from gmf_v3.contracts import AnswerStatus,uid

class Sessions:
 def __init__(self,bank,clock=time.time):
  self.bank=bank;self.store=bank.store;self.clock=clock
  from .reviews import Reviews
  self.reviews=Reviews(self)
 def ms(self):return int(self.clock()*1000)
 def expire_due(self):
  with self.store.connect(write=True) as c:
   rows=c.execute("SELECT payload FROM v4_sessions WHERE mode='exam' AND status='active'").fetchall()
   for row in rows:
    s=json.loads(row[0]);self._expire(c,s);self._save(c,s)
 def _save(self,c,s):c.execute('INSERT INTO v4_sessions VALUES(?,?,?,?,?) ON CONFLICT(session_id) DO UPDATE SET status=excluded.status,payload=excluded.payload',(s['id'],s['owner_id'],s['mode'],s['status'],json.dumps(s)))
 def _load(self,c,sid,owner):
  row=c.execute('SELECT payload FROM v4_sessions WHERE session_id=? AND owner_id=?',(sid,owner)).fetchone()
  if not row:raise KeyError('Session not found')
  return json.loads(row[0])
 def _lock(self,c,owner):
  rows=c.execute("SELECT payload FROM v4_sessions WHERE owner_id=? AND mode='exam' AND status='active'",(owner,)).fetchall()
  for r in rows:
   s=json.loads(r[0]);self._expire(c,s)
   if s['status']=='active':return s
  return None
 def _expire(self,c,s):
  current=max(self.ms(),s['last_clock']);s['last_clock']=current
  if s['status']=='active' and s['mode']=='exam' and current>=s['deadline']:self._submit(c,s,reason='timeout',at=s['deadline'])
  return s
 def _key(self,c,vid,key_id=None):
  sql='SELECT payload FROM answer_keys WHERE '+('answer_key_id=?' if key_id else 'version_id=? ORDER BY revision DESC LIMIT 1')
  row=c.execute(sql,(key_id or vid,)).fetchone();key=json.loads(row[0]) if row else None
  return key if key and key['version_id']==vid else None
 def _grade(self,selected,key):
  if not key or key['status']!='Verified' or not key['label']:return 'ungraded'
  return 'unanswered' if selected is None else 'correct' if selected==key['label'] else 'incorrect'
 def _record(self,c,s,item,selected,*,trial=0,key_override=None,record_id=None):
  record_id=record_id or f"{s['id']}:{item['question_id']}:{trial}"
  row=c.execute('SELECT payload FROM v4_answers WHERE record_id=?',(record_id,)).fetchone()
  if row:return json.loads(row[0])
  key=self._key(c,item['version_id'],key_override or item['answer_key_id']) if key_override or item.get('answer_key_id') else None;status=self._grade(selected,key)
  types=item.get('types_snapshot') or self.bank.types(item['version_id'])
  r={'record_id':record_id,'session_id':s['id'],'question_id':item['question_id'],'version_id':item['version_id'],'selected':selected,'status':status,'answer_key_id':key['answer_key_id'] if key else None,'correct_answer':key['label'] if key and key['status']=='Verified' else None,'explanation':(self.bank.meta(item['version_id'],c).get('explanation','') if key.get('confirmed_by')=='source-key-audit/4' else key.get('explanation','')) if key and key['status']=='Verified' else '', 'answer_source':key.get('confirmed_by') if key and key['status']=='Verified' else None,'reference_answer':None,'topic_ids':self.bank.meta(item['version_id'],c).get('core',[]),'related_topics':self.bank.meta(item['version_id'],c).get('related',[]),'question_types':self.bank.types(item['version_id'])['methods'],'at':self.ms(),'trial':trial}
  r.update({'question_types':types['methods'],'question_structures':types['structures']})
  tags=item.get('topics_snapshot') or self.bank.meta(item['version_id'],c)
  r.update({'topic_ids':tags.get('core',[]),'related_topics':tags.get('related',[]),'course_id':tags.get('course_id'),'unit_ids':tags.get('unit_ids',[]),
   'independent':bool(item.get('independent_snapshot')) and trial==0 and item['question_id'] not in s.get('assisted',[]),
   'assisted':trial>0 or item['question_id'] in s.get('assisted',[]),'purpose':s.get('review',{}).get('phase','practice' if s['mode']=='practice' else 'exam')})
  c.execute('INSERT INTO v4_answers VALUES(?,?,?,?,?,?)',(record_id,s['owner_id'],s['id'],item['question_id'],item['version_id'],json.dumps(r)))
  include=status=='incorrect' or s['mode']=='exam' and status=='unanswered'
  if include:
   row=c.execute('SELECT payload FROM v4_wrong WHERE owner_id=? AND question_id=?',(s['owner_id'],item['question_id'])).fetchone()
   wrong=json.loads(row[0]) if row else {'question_id':item['question_id'],'record_ids':[]}
   if record_id not in wrong['record_ids']:wrong['record_ids'].append(record_id)
   wrong.update({'removed':False,'last_status':status,'last_at':r['at'],'version_id':item['version_id']})
   c.execute('INSERT OR REPLACE INTO v4_wrong VALUES(?,?,?)',(s['owner_id'],item['question_id'],json.dumps(wrong)))
   self.reviews.on_error(c,s['owner_id'],r)
  return r
 def _submit(self,c,s,reason='manual',at=None):
  if s['status']=='submitted':return s
  s['status']='submitted';s['submitted_at']=at if at is not None else max(self.ms(),s['last_clock']);s['reason']=reason;s['revision']+=1
  records=[]
  for item in s['items']:
   qid=item['question_id'];prior=s['checks'].get(qid,[])
   record=self._record(c,s,item,s['answers'].get(qid),trial=s['trials'].get(qid,0));records.append(record)
   if not prior or prior[-1]!=record['record_id']:s['checks'].setdefault(qid,[]).append(record['record_id'])
  grade={'grade_id':s['id']+':grade:1','session_id':s['id'],'revision':1,'source':'original-snapshot','records':records,'at':s['submitted_at']}
  grade['summary']=self.summary(s,records)
  c.execute('INSERT OR IGNORE INTO v4_grades VALUES(?,?,?)',(grade['grade_id'],s['id'],json.dumps(grade)))
  self.reviews.finish(c,s,records)
  s['grade_id']=grade['grade_id'];self._save(c,s);return s
 def _related_candidates(self,c,owner,req):
  if req.get('paper_id') or req.get('question_ids'):raise ValueError('专项练习不能同时指定其他试卷或题目')
  if req.get('continue_from'):
   previous=self._load(c,req['continue_from'],owner)
   if previous['mode']!='practice' or previous['status']!='submitted' or not previous.get('related_scope'):
    raise ValueError('请先完成当前专项练习，再继续下一组')
   scope=previous['related_scope']
   if req.get('repeat_seen') is True:scope={**scope,'seen_ids':[]}
  else:
   q=self.bank.store.question(req['related_to'])
   if q.scope=='exam_private' and q.owner_id!=owner:raise KeyError('Question not found')
   if q.scope=='bank' and q.publication!='approved':raise KeyError('Question not available')
   v=self.bank.store.version(q.current_version_id);m=self.bank.meta(v.version_id);types=self.bank.types(v.version_id)
   if not m['core']:raise ValueError('此题尚无已确认核心 Topic')
   if req.get('same_type') and not types['methods'] and not types['structures']:
    raise ValueError('此题的解题类型尚未确认，可改为按知识点练习')
   exclude=[q.question_id]
   if q.scope=='exam_private':
    exclude.extend(other.question_id for other,ov,_,_ in self.bank.store.list_questions(scope='bank',limit=None) if ov.fingerprint==v.fingerprint)
   scope={'source_question_id':q.question_id,'source_version_id':v.version_id,'source_fingerprint':v.fingerprint,'course_id':m['course_id'],
    'topics':list(dict.fromkeys([*m['core'],*(m['related'] if req.get('expand_related') else [])])),
    'methods':types['methods'],'structures':types['structures'],'same_type':bool(req.get('same_type')),
    'comprehensive':bool(req.get('comprehensive')),'exclude_ids':exclude,'seen_ids':[]}
  refs=self.bank.candidates(scope['course_id'],None,scope['topics'],scope['comprehensive'],[*scope['exclude_ids'],*scope['seen_ids']],owner_id=owner)
  if scope.get('source_fingerprint'):refs=[row for row in refs if row[1].fingerprint!=scope['source_fingerprint']]
  if scope['same_type']:
   methods=set(scope['methods']);structures=set(scope['structures'])
   refs=[row for row in refs if methods & set(self.bank.types(row[1].version_id)['methods']) or structures & set(self.bank.types(row[1].version_id)['structures'])]
  if not refs:
   raise ValueError('当前专项范围没有更多未练题目；可勾选允许重做，或等待公共题库补充题目' if req.get('continue_from') else '公共题库中暂无匹配题目，可扩大知识点范围或稍后再试')
  return refs,scope
 def create(self,owner,req):
  mode=req.get('mode','practice');current=self.ms()
  if mode not in ['practice','exam']:raise ValueError('MCQ practice or exam only')
  with self.store.connect(write=True) as c:
   key=req.get('request_id')
   if not isinstance(key,str) or not 1<=len(key)<=100:raise ValueError('request_id required')
   sid='session_'+owner+'_'+key
   if c.execute('SELECT 1 FROM v4_sessions WHERE session_id=?',(sid,)).fetchone():return self._load(c,sid,owner)
   if self._lock(c,owner):raise ValueError('正式考试进行中，请先完成考试')
   context=req.get('context') or {};items=[];title='自由练习';set_info=None;related_scope=None;practice_progress=None;review=None
   seen_ids,seen_fingerprints=self.reviews.seen(c,owner)
   if mode=='exam' and req.get('review_question'):raise ValueError('复查使用自由练习会话')
   if mode=='exam' and req.get('continue_from'):raise ValueError('连续专项练习仅用于自由练习')
   if mode=='exam':
    row=c.execute('SELECT payload FROM v4_sets WHERE set_id=?',(req.get('set_id'),)).fetchone()
    if not row:raise ValueError('请选择已发布 MCQ 试卷')
    set_info=json.loads(row[0]);title=set_info['title']
    if not set_info.get('published'):raise ValueError('试卷未发布')
    if set_info.get('owner_id') and set_info['owner_id']!=owner:raise KeyError('Paper not found')
    candidates=[self.bank.store.question(qid) for qid in set_info['question_ids']]
    if any(q.publication!='approved' and not(q.scope=='exam_private' and q.owner_id==owner) for q in candidates):raise ValueError('试卷含已撤回题目')
    refs=[(q,self.bank.store.version(vid),None) for q,vid in zip(candidates,set_info['version_ids'])]
   else:
    topics=req.get('topics',[]);count=int(req.get('count',10))
    if not 1<=count<=200:raise ValueError('题数应在 1–200 之间')
    if req.get('review_question'):
     refs,review=self.reviews.select(c,owner,req,sid);title='独立检查' if review['phase']=='independent' else '延迟复查'
    elif req.get('related_to') or req.get('continue_from'):
     refs,related_scope=self._related_candidates(c,owner,req)
     title='同类型专项练习' if related_scope['same_type'] else '相关知识点练习'
    else:refs=self.bank.candidates(req.get('course_id'),req.get('unit_id'),topics,bool(req.get('comprehensive')),owner_id=owner)
    if req.get('question_ids'):
     chosen=list(dict.fromkeys(req['question_ids']));available={q.question_id:(q,v,a) for q,v,a in refs}
     for qid in chosen:
      try:private=self.bank.store.question(qid)
      except KeyError:continue
      if private.scope=='exam_private' and private.owner_id==owner:
       version=self.bank.store.version(private.current_version_id)
       if not self.bank.meta(version.version_id).get('issues'):available[qid]=(private,version,None)
     refs=[available[qid] for qid in chosen if qid in available]
    if req.get('paper_id'):
     paper_row=c.execute('SELECT payload FROM v4_sets WHERE set_id=?',(req['paper_id'],)).fetchone()
     if not paper_row:raise KeyError('Paper not found')
     private_paper=json.loads(paper_row[0])
     if private_paper.get('owner_id')!=owner:raise KeyError('Paper not found')
     refs=[(self.bank.store.question(qid),self.bank.store.version(vid),None) for qid,vid in zip(private_paper['question_ids'],private_paper['version_ids'])];title=private_paper['title']
    if req.get('random'):random.SystemRandom().shuffle(refs)
    available=len(refs)
    refs=refs[:count]
    if related_scope:
     related_scope={**related_scope,'seen_ids':list(dict.fromkeys([*related_scope['seen_ids'],*(q.question_id for q,_,_ in refs)]))}
     practice_progress={'selected':len(refs),'remaining':available-len(refs),'seen':len(related_scope['seen_ids'])}
   if not refs:raise ValueError('当前范围没有可用题目，请选择其他 Topic')
   if mode=='exam' and any(self.bank.exam_issues(v) for _,v,_ in refs):raise ValueError('试卷存在题目显示或选项结构异常，请先复核原题')
   for q,v,_ in refs:
    key_data=self._key(c,v.version_id)
    items.append({'question_id':q.question_id,'version_id':v.version_id,'answer_key_id':key_data['answer_key_id'] if key_data else None,'types_snapshot':self.bank.types(v.version_id),
     'topics_snapshot':self.bank.meta(v.version_id),'fingerprint':v.fingerprint,'independent_snapshot':q.question_id not in seen_ids and v.fingerprint not in seen_fingerprints})
   duration=set_info['duration_minutes']*60000 if set_info else None
   s={'id':sid,'owner_id':owner,'mode':mode,'title':title,'set_info':set_info,'status':'active','started_at':current,'deadline':current+duration if duration else None,'last_clock':current,'items':items,'answers':{},'checks':{},'trials':{},'flags':[],'index':0,'revision':0,'active_ms':0,'context':context}
   if related_scope:s.update({'related_scope':related_scope,'practice_progress':practice_progress})
   if review:s['review']=review
   self._save(c,s);return s
 def mutate(self,owner,sid,req):
  with self.store.connect(write=True) as c:
   s=self._load(c,sid,owner);self._expire(c,s);typ=req.get('type');item=next((i for i in s['items'] if i['question_id']==req.get('question_id')),None)
   if s['status']!='active':
    return s  # Late inputs cannot roll back a just-committed timeout.
   if s['mode']=='practice' and self._lock(c,owner):raise ValueError('正式考试期间暂停自由练习')
   qid=item['question_id'] if item else None;checked=s['checks'].get(qid,[]);trial=s['trials'].get(qid,0);rid=f'{s["id"]}:{qid}:{trial}'
   locked=bool(checked and checked[-1]==rid)
   if s.get('review') and typ in ['check','retry','assistance']:raise ValueError('独立复查整组提交后才开放答案，不能重试覆盖')
   if typ=='answer':
    if not item or locked:raise ValueError('已检查作答不可修改；请使用重新尝试')
    v=self.bank.store.version(item['version_id'])
    if req.get('option') not in [o.label for o in v.options]:raise ValueError('无效选项')
    s['answers'][qid]=req['option']
   elif typ=='check':
    if s['mode']!='practice' or not item or not s['answers'].get(qid):raise ValueError('先作答，再检查答案')
    record=self._record(c,s,item,s['answers'][qid],trial=trial)
    if record['record_id'] not in checked:s['checks'].setdefault(qid,[]).append(record['record_id'])
   elif typ=='retry':
    if s['mode']!='practice' or not item or not locked:raise ValueError('请先检查本次作答')
    s['trials'][qid]=trial+1;s['answers'].pop(qid,None)
   elif typ=='navigate':
    index=req.get('index');
    if not isinstance(index,int) or not 0<=index<len(s['items']):raise ValueError('无效题号')
    s['index']=index
   elif typ=='flag':
    if not item:raise ValueError('无效题目')
    s['flags']= [x for x in s['flags'] if x!=qid] if qid in s['flags'] else [*s['flags'],qid]
   elif typ=='assistance':
    if s['mode']!='practice' or not item or locked:raise ValueError('仅能在自由练习检查前标记辅助作答')
    s['assisted']=[x for x in s.get('assisted',[]) if x!=qid]
    if req.get('assisted') is True:s['assisted'].append(qid)
   elif typ=='tick':
    # Active time is observational, never used for the authoritative deadline.
    elapsed=req.get('elapsed_ms',0)
    if isinstance(elapsed,(int,float)) and req.get('visible'):s['active_ms']+=min(5000,max(0,elapsed))
   elif typ=='submit':return self._submit(c,s)
   else:raise ValueError('无效操作')
   s['revision']+=1;self._save(c,s);return s
 def get(self,owner,sid):
  with self.store.connect(write=True) as c:s=self._load(c,sid,owner);self._expire(c,s);self._save(c,s);return s
 def list(self,owner):
  with self.store.connect(write=True) as c:
   self._lock(c,owner)
   return [json.loads(r[0]) for r in c.execute('SELECT payload FROM v4_sessions WHERE owner_id=? ORDER BY rowid DESC',(owner,))]
 def public(self,s):
  with self.store.connect(write=True) as c:
   lock=self._lock(c,s['owner_id'])
   if lock and lock['id']!=s['id']:raise ValueError('正式考试期间不开放其他作答回看')
   questions=[self.bank.public(i['question_id'],i['version_id']) for i in s['items']]
   for question,item in zip(questions,s['items']):
    if item.get('types_snapshot'):question['types']=item['types_snapshot']
    if item.get('topics_snapshot'):question['topics']={k:item['topics_snapshot'].get(k) for k in ['course_id','core','related','unit_ids','tag_source']}
   records=[]
   if s['mode']=='practice' or s['status']=='submitted':records=[json.loads(r[0]) for r in c.execute('SELECT payload FROM v4_answers WHERE session_id=? ORDER BY rowid',(s['id'],))]
   grade=None
   if s.get('grade_id'):
    row=c.execute('SELECT payload FROM v4_grades WHERE grade_id=?',(s['grade_id'],)).fetchone();grade=json.loads(row[0]) if row else None
  result={k:v for k,v in s.items() if k not in ['items','owner_id','last_clock','set_info']}
  if s.get('set_info'):result['set_info']={k:s['set_info'][k] for k in ['title','source_year','section','duration_minutes']}
  # Legacy stored model candidates remain in history, but never surface as an answer.
  records=[{**r,'reference_answer':None} for r in records]
  if grade:grade={**grade,'records':[{**r,'reference_answer':None} for r in grade['records']]}
  result.update({'questions':questions,'records':records,'grade':grade,'summary':self.summary(s,grade['records']) if grade else None,'server_now':self.ms()});return result
 def summary(self,s,records):
  total=len(s['items']);answered=sum(s['answers'].get(i['question_id']) is not None for i in s['items'])
  known=[r for r in records if r['status'] in ['correct','incorrect','unanswered']]
  correct=sum(r['status']=='correct' for r in known);graded=len(known)
  return {'total':total,'answered':answered,'unanswered':total-answered,'graded':graded,'ungraded':total-graded,
   'correct':correct,'incorrect':sum(r['status']=='incorrect' for r in known),'graded_unanswered':sum(r['status']=='unanswered' for r in known),
   'scoring_mode':'ungraded' if not graded else 'graded' if graded==total else 'partial',
   'accuracy':correct/total if graded==total and total else None,'graded_accuracy':correct/graded if graded else None,
   'coverage':graded/total if total else 0,'elapsed_ms':max(0,s['submitted_at']-s['started_at'])}
 def mistakes(self,owner):
  with self.store.connect(write=True) as c:
   if self._lock(c,owner):raise ValueError('正式考试期间不开放错题回看')
   out=[]
   for row in c.execute('SELECT payload FROM v4_wrong WHERE owner_id=?',(owner,)):
    m=json.loads(row[0])
    if m.get('removed'):continue
    records=[json.loads(r[0]) for r in c.execute('SELECT payload FROM v4_answers WHERE owner_id=? AND question_id=? ORDER BY rowid',(owner,m['question_id']))]
    out.append({**m,'question':self.bank.public(m['question_id'],m['version_id']),'records':records})
   return self.reviews.enrich(c,owner,out)
 def remove_wrong(self,owner,qid):
  with self.store.connect(write=True) as c:
   if self._lock(c,owner):raise ValueError('正式考试期间不能操作错题集')
   row=c.execute('SELECT payload FROM v4_wrong WHERE owner_id=? AND question_id=?',(owner,qid)).fetchone()
   bookmarked=c.execute('SELECT 1 FROM v4_bookmarks WHERE owner_id=? AND question_id=?',(owner,qid)).fetchone()
   if not row and not bookmarked:raise KeyError('Wrong question not found')
   if row:
    m=json.loads(row[0]);m['removed']=True;c.execute('UPDATE v4_wrong SET payload=? WHERE owner_id=? AND question_id=?',(json.dumps(m),owner,qid))
   c.execute('DELETE FROM v4_bookmarks WHERE owner_id=? AND question_id=?',(owner,qid))
   case=self.reviews.load(c,owner,qid)
   if case:
    case.update(removed=True,active_review=None);self.reviews.event(case,'manually_removed');self.reviews.save(c,owner,case)
 def regrade(self,sid,reviewer,reason):
  if not reason.strip():raise ValueError('修订理由必填')
  with self.store.connect(write=True) as c:
   row=c.execute('SELECT payload FROM v4_sessions WHERE session_id=?',(sid,)).fetchone()
   if not row:raise KeyError('Session not found')
   s=json.loads(row[0]);self._expire(c,s)
   if s['status']!='submitted':raise ValueError('只能修订已提交成绩')
   revision=c.execute('SELECT count(*) FROM v4_grades WHERE session_id=?',(sid,)).fetchone()[0]+1
   records=[]
   for item in s['items']:
    row=c.execute('SELECT payload FROM v4_answers WHERE owner_id=? AND session_id=? AND question_id=? ORDER BY rowid DESC LIMIT 1',(s['owner_id'],sid,item['question_id'])).fetchone()
    original=json.loads(row[0]) if row else {}
    key=self._key(c,item['version_id']);records.append({**original,'question_id':item['question_id'],'version_id':item['version_id'],'selected':s['answers'].get(item['question_id']),'status':self._grade(s['answers'].get(item['question_id']),key),'correct_answer':key['label'] if key and key['status']=='Verified' else None,'answer_key_id':key['answer_key_id'] if key else None,'explanation':key.get('explanation','') if key else '', 'answer_source':key.get('confirmed_by') if key else None})
   grade={'grade_id':uid('grade'),'session_id':sid,'revision':revision,'source':'admin:'+reviewer,'reason':reason,'records':records,'at':self.ms()}
   grade['summary']=self.summary(s,records)
   c.execute('INSERT INTO v4_grades VALUES(?,?,?)',(grade['grade_id'],sid,json.dumps(grade)));s['grade_id']=grade['grade_id'];self._save(c,s);return grade
