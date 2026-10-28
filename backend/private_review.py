"""Student-owned proofreading before releasing a newly imported private paper."""
import json
from gmf_v3.contracts import Option
from gmf_v3.store import ConflictError

class PrivateReview:
 def __init__(self,bank):self.bank=bank
 def paper(self,owner,pid,c=None):
  if c is None:
   with self.bank.store.connect() as con:return self.paper(owner,pid,con)
  row=c.execute('SELECT payload FROM v4_sets WHERE set_id=?',(pid,)).fetchone();p=json.loads(row[0]) if row else None
  if not p or p.get('owner_id')!=owner:raise KeyError('Paper not found')
  return p
 def read(self,owner,pid):
  p=self.paper(owner,pid)
  return {'paper':{k:v for k,v in p.items() if k not in ('question_ids','version_ids')},'revision':p.get('review_revision',0),'questions':[self.bank.public(qid,vid) for qid,vid in zip(p['question_ids'],p['version_ids'])]}
 def edit(self,owner,pid,qid,data):
  p=self.paper(owner,pid)
  if p.get('published'):raise ConflictError('已确认的试卷已锁定；原题与考试记录保留')
  if qid not in p['question_ids']:raise KeyError('Question not in paper')
  if data.get('expected_revision')!=p.get('review_revision',0):raise ConflictError('校对页面已变化，请刷新')
  q=self.bank.store.question(qid)
  if q.owner_id!=owner or q.scope!='exam_private':raise KeyError('Private question not found')
  options=[Option.model_validate(o) for o in data.get('options',[])]
  if len(options)<2 or [o.label for o in options]!=list('ABCDEFGH')[:len(options)]:raise ValueError('请保留至少两个连续编号的完整选项')
  if not isinstance(data.get('stem'),str) or not data['stem'].strip() or len(data['stem'])>50000:raise ValueError('题干不可为空，最长 50000 字符')
  meta=self.bank.meta(q.current_version_id)
  new=self.bank.store.revise(qid,expected_version=data.get('expected_version'),stem=data['stem'].strip(),options=options)
  self.bank.save_meta(new.version_id,{**meta,'issues_reviewed':True,'display_mode':'structured-with-original','student_edited':True})
  p['version_ids'][p['question_ids'].index(qid)]=new.version_id;p['review_revision']=p.get('review_revision',0)+1
  with self.bank.store.connect(write=True) as c:
   fresh=self.paper(owner,pid,c)
   if fresh.get('review_revision',0)!=data['expected_revision']:raise ConflictError('试卷校对已变化，请重新读取')
   c.execute('UPDATE v4_sets SET payload=? WHERE set_id=?',(json.dumps(p),pid))
  return self.read(owner,pid)
 def confirm(self,owner,pid,data):
  with self.bank.store.connect(write=True) as c:
   p=self.paper(owner,pid,c)
   if p.get('published'):return {'confirmed':True,'paper_id':pid}
   if p.get('review_revision',0)!=data.get('expected_revision'):raise ConflictError('校对页面已变化，请重新确认')
   expected=dict(zip(p['question_ids'],p['version_ids']))
   if data.get('reviewed_versions')!=expected:raise ValueError('请逐题对照原题并确认当前版本')
   for qid,vid in expected.items():
    row=c.execute('SELECT current_version_id FROM questions WHERE question_id=?',(qid,)).fetchone()
    if not row or row[0]!=vid:raise ConflictError('题目版本已变化，请重新校对')
    if self.bank.exam_issues(self.bank.store.version(vid)):raise ValueError('题目仍有结构异常，不能确认：'+qid)
   p.update({'published':True,'review_confirmed':True,'review_revision':p.get('review_revision',0)+1})
   c.execute('UPDATE v4_sets SET payload=? WHERE set_id=?',(json.dumps(p),pid))
   c.execute('INSERT OR REPLACE INTO v43_paper_reviews VALUES(?,?,?,?)',(pid,owner,p['review_revision'],json.dumps(expected)))
  return {'confirmed':True,'paper_id':pid}
