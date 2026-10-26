import json,sys,concurrent.futures
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from backend.app import create_app
from gmf_v3.contracts import AnswerStatus
from make_v4_fixtures import mixed_pdf,docx_file
TOKENS={'admin-token':{'owner_id':'owner','role':'admin'},'student-token':{'owner_id':'student','role':'student'},'other-token':{'owner_id':'other','role':'student'}}
@pytest.fixture
def env(tmp_path):
 clock=[1800000000.0];app=create_app(tmp_path/'data',TOKENS,clock=lambda:clock[0],worker=False);client=TestClient(app);return app,client,clock,tmp_path

def headers(which='student'):return {'Authorization':'Bearer '+which+'-token'}
def upload(env,path,key='fixture'):
 app,c,clock,temp=env
 with path.open('rb') as f:r=c.post('/api/v4/admin/imports',headers=headers('admin'),files={'file':(path.name,f)},data={'request_key':key,'reuse_confirmed':'true','license_name':'CC0 GMF authored test'})
 assert r.status_code==200,r.text
 app.state.bank.jobs.work(limit=20);return app.state.bank.store.batch(r.json()['batch_id'])
def setup_bank(env):
 app,c,clock,temp=env;b=upload(env,mixed_pdf(temp/'mixed.pdf'));ids=b.files[0]['question_ids'];assert len(ids)==2,b
 for qid in ids:
  assert c.put('/api/v4/admin/questions/'+qid+'/tags',headers=headers('admin'),json={'course_id':app.state.bank.catalog['course_id'],'core':['2.5'],'related':['3.3']}).status_code==200
  assert c.post('/api/v4/admin/questions/'+qid+'/publish',headers=headers('admin'),json={}).status_code==200
 return ids,b

def practice(env,ids=None,count=10):
 app,c,*_=env;data={'mode':'practice','request_id':'p'+str(len(app.state.sessions.list('student'))),'course_id':app.state.bank.catalog['course_id'],'topics':['2.5'],'count':count,'comprehensive':True}
 if ids:data['question_ids']=ids
 r=c.post('/api/v4/sessions',headers=headers(),json=data);assert r.status_code==200,r.text;return r.json()
def command(env,s,typ,**kw):return env[1].post('/api/v4/sessions/'+s['id']+'/commands',headers=headers(),json={'type':typ,**kw})
def exam(env,ids,request_id='exam'):
 app,c,*_=env;r=c.post('/api/v4/admin/sets',headers=headers('admin'),json={'title':'QA MCQ','source_year':'2026','duration_minutes':1,'question_ids':ids,'course_id':app.state.bank.catalog['course_id'],'section':'MCQ'});assert r.status_code==200,r.text
 r=c.post('/api/v4/sessions',headers=headers(),json={'mode':'exam','set_id':r.json()['set_id'],'request_id':request_id});assert r.status_code==200,r.text;return r.json()

def test_pdf_two_mcq_shared_images_and_frq_exclusion(env):
 app,c,clock,temp=env;b=upload(env,mixed_pdf(temp/'mixed.pdf'));assert len(b.files[0]['question_ids'])==2
 summary=b.files[0]['summary'];assert summary['frq_excluded']==1;assert summary['mcq']==2
 for qid in b.files[0]['question_ids']:
  q=app.state.bank.public(qid);assert len(q['options'])==3;assert q['shared_ref'];assert q['shared_assets'];assert q['assets'];assert q['spans']
  a=app.state.bank.store.latest_answer(q['version_id']);assert a.status==AnswerStatus.VERIFIED;assert a.label=='B'

def test_docx_answers_not_in_options(env):
 app,c,clock,temp=env;b=upload(env,docx_file(temp/'mixed.docx'));assert b.status=='completed',b
 assert len(b.files[0]['question_ids'])==2
 for qid in b.files[0]['question_ids']:
  q=app.state.bank.public(qid);assert all('Answer' not in o['text'] for o in q['options']);assert len(q['options'])==2

def test_student_no_admin_or_spoofed_headers(env):
 app,c,*_=env
 for path in ['/admin/questions','/admin/imports']:
  assert c.get('/api/v4'+path,headers=headers()).status_code==403
 assert c.post('/api/v4/admin/imports',headers=headers(),files={'file':('x.pdf',b'%PDF-x')},data={'request_key':'x'}).status_code==403
 assert c.get('/api/v4/admin/questions',headers={'oai-authenticated-user-id':'owner'}).status_code==401

def test_import_idempotence_and_reparse(env):
 app,c,clock,temp=env;p=mixed_pdf(temp/'mixed.pdf');b=upload(env,p);again=upload(env,p);assert b.batch_id==again.batch_id
 assert c.post('/api/v4/admin/imports/'+b.batch_id+'/reparse',headers=headers('admin')).status_code==200
 app.state.bank.jobs.work(limit=1);assert len(app.state.bank.store.list_questions(scope='bank',include_drafts=True,limit=None))==2
 assert app.state.bank.store.batch(b.batch_id).files[0]['summary']['publishable']==2

def test_failed_queue_retry_after_restart(env):
 app,c,clock,temp=env;p=temp/'bad.pdf';p.write_bytes(b'bad');b=upload(env,p);assert b.status=='failed'
 # Preserve staged original and retry from a new service instance, as after a stopped process.
 with app.state.bank.store.connect() as conn:job=conn.execute('SELECT payload FROM import_jobs WHERE batch_id=?',(b.batch_id,)).fetchone()
 staged=app.state.bank.root/json.loads(job[0])['relative_path'];mixed_pdf(staged)
 restarted=create_app(app.state.bank.root,TOKENS,clock=lambda:clock[0],worker=False);restarted.state.bank.jobs.retry(b.batch_id);restarted.state.bank.jobs.work(limit=1);assert restarted.state.bank.store.batch(b.batch_id).status=='completed'

def test_multi_topic_registry_and_no_keyword_guess(env):
 ids,b=setup_bank(env);app,c,*_=env
 qid=ids[0];r=c.put('/api/v4/admin/questions/'+qid+'/tags',headers=headers('admin'),json={'course_id':app.state.bank.catalog['course_id'],'core':['2.5','3.3'],'related':['5.4']});assert r.status_code==200
 assert app.state.bank.meta(app.state.bank.store.question(qid).current_version_id)['core']==['2.5','3.3']
 assert c.put('/api/v4/admin/questions/'+qid+'/tags',headers=headers('admin'),json={'course_id':app.state.bank.catalog['course_id'],'core':['FAKE']}).status_code==422
 assert len(app.state.bank.candidates(app.state.bank.catalog['course_id'],topics=['2.5'],comprehensive=True))==2

def test_practice_fixed_order_check_wrong_retry_history(env):
 ids,_=setup_bank(env);s=practice(env);qid=s['questions'][0]['question_id'];ids0=[q['version_id'] for q in s['questions']]
 assert command(env,s,'answer',question_id=qid,option='A').status_code==200
 s=command(env,s,'navigate',index=1).json();r=env[1].get('/api/v4/sessions/'+s['id'],headers=headers()).json();assert r['index']==1;assert r['answers'][qid]=='A';assert [q['version_id'] for q in r['questions']]==ids0
 r=command(env,s,'check',question_id=qid).json();assert r['records'][0]['status']=='incorrect'
 assert command(env,s,'answer',question_id=qid,option='B').status_code==422
 assert command(env,s,'retry',question_id=qid).status_code==200
 command(env,s,'answer',question_id=qid,option='B');r=command(env,s,'check',question_id=qid).json();assert [x['status'] for x in r['records']]==['incorrect','correct']
 wrong=env[1].get('/api/v4/mistakes',headers=headers()).json();assert len(wrong)==1;assert len(wrong[0]['records'])==2
 assert env[1].delete('/api/v4/mistakes/'+qid,headers=headers()).status_code==200
 assert env[1].get('/api/v4/mistakes',headers=headers()).json()==[]

def test_related_excludes_current_deduplicated_actual_count(env):
 ids,_=setup_bank(env);app,c,*_=env;r=c.post('/api/v4/sessions',headers=headers(),json={'mode':'practice','request_id':'related','related_to':ids[0],'count':10,'comprehensive':True});assert r.status_code==200,r.text
 assert [q['question_id'] for q in r.json()['questions']]==[ids[1]]

def test_exam_server_deadline_close_resume_expiry_idempotent(env):
 ids,_=setup_bank(env);s=exam(env,ids);qid=s['questions'][0]['question_id'];command(env,s,'answer',question_id=qid,option='A');command(env,s,'flag',question_id=qid);clock=env[2];clock[0]+=30
 resumed=env[1].get('/api/v4/sessions/'+s['id'],headers=headers()).json();assert resumed['deadline']==s['deadline'];assert resumed['answers'][qid]=='A';assert resumed['flags']==[qid];assert 'correct_answer' not in json.dumps(resumed)
 clock[0]+=31;r=command(env,s,'answer',question_id=qid,option='B').json();assert r['status']=='submitted';assert r['answers'][qid]=='A';assert r['reason']=='timeout';assert r['submitted_at']==s['deadline']
 assert sorted(x['status'] for x in r['grade']['records'])==['incorrect','unanswered']
 command(env,s,'submit');command(env,s,'submit')
 with env[0].state.bank.store.connect() as c:assert c.execute('SELECT count(*) FROM v4_grades').fetchone()[0]==1
 assert env[1].get('/api/v4/sessions').status_code==401

def test_exam_lock_blocks_other_practice_and_result_access(env):
 ids,_=setup_bank(env);p=practice(env);s=exam(env,ids)
 assert command(env,p,'check',question_id=ids[0]).status_code==422
 assert env[1].get('/api/v4/mistakes',headers=headers()).status_code==422
 assert env[1].get('/api/v4/sessions/'+p['id'],headers=headers()).status_code==422
 # No answer labels or source originals through public question/assets endpoints.
 public=env[1].get('/api/v4/questions',headers=headers()).json();assert 'answer' not in json.dumps(public).lower()
 v=env[0].state.bank.store.version(env[0].state.bank.store.question(ids[0]).current_version_id);original=next(a for a in v.asset_ids if env[0].state.bank.store.asset(a).kind=='original_pdf')
 assert env[1].get('/api/v4/assets/'+original,headers=headers()).status_code==404
 assert command(env,s,'submit').status_code==200

def test_user_isolation(env):
 ids,_=setup_bank(env);s=practice(env);assert env[1].get('/api/v4/sessions/'+s['id'],headers=headers('other')).status_code==404
 assert env[1].get('/api/v4/mistakes',headers=headers('other')).json()==[]

def test_unknown_answer_ungraded_not_wrong_and_revision_retains_original(env):
 ids,_=setup_bank(env);app,c,*_=env;q=app.state.bank.store.question(ids[0]);old=app.state.bank.store.latest_answer(q.current_version_id)
 app.state.bank.store.append_answer(q.current_version_id,label=None,status=AnswerStatus.UNRESOLVED,evidence=[],expected_revision=old.revision)
 app.state.bank.publish(ids[0],'admin');s=practice(env,ids);s=command(env,s,'submit').json();assert {r['status'] for r in s['grade']['records']}=={'ungraded','unanswered'}
 wrong=c.get('/api/v4/mistakes',headers=headers()).json();assert wrong==[] # Practice unanswered is not an exam mistake.
 original_grade=s['grade'];answer=app.state.bank.store.latest_answer(q.current_version_id);app.state.bank.answers.confirm(q.current_version_id,label='A',reviewer='admin',reason='Reviewed correction',expected_revision=answer.revision)
 r=c.post('/api/v4/admin/sessions/'+s['id']+'/regrade',headers=headers('admin'),json={'reason':'Source key corrected'});assert r.status_code==200;assert r.json()['revision']==2
 with app.state.bank.store.connect() as conn:
  grades=[json.loads(x[0]) for x in conn.execute('SELECT payload FROM v4_grades ORDER BY rowid')];assert grades[0]==original_grade;assert len(grades)==2

def test_server_persistence_and_concurrent_submission(env):
 ids,_=setup_bank(env);s=exam(env,ids);app,c,clock,temp=env
 restarted=create_app(app.state.bank.root,TOKENS,clock=lambda:clock[0],worker=False);assert restarted.state.sessions.get('student',s['id'])['deadline']==s['deadline']
 with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:list(pool.map(lambda _:app.state.sessions.mutate('student',s['id'],{'type':'submit'}),range(8)))
 with app.state.bank.store.connect() as conn:assert conn.execute('SELECT count(*) FROM v4_grades WHERE session_id=?',(s['id'],)).fetchone()[0]==1;assert conn.execute('SELECT count(*) FROM v4_answers WHERE session_id=?',(s['id'],)).fetchone()[0]==2

def test_question_revision_preserves_snapshot(env):
 ids,_=setup_bank(env);s=practice(env);app,c,*_=env;q=s['questions'][0]
 r=c.patch('/api/v4/admin/questions/'+q['question_id'],headers=headers('admin'),json={'expected_version':q['version_id'],'stem':'Changed question','options':q['options']});assert r.status_code==200
 restored=c.get('/api/v4/sessions/'+s['id'],headers=headers()).json();assert restored['questions'][0]['stem']==q['stem'];assert restored['questions'][0]['version_id']==q['version_id']

def test_admin_many_papers_batch_reuses_queue_and_is_idempotent(env):
 app,c,clock,temp=env;p=mixed_pdf(temp/'a.pdf');d=docx_file(temp/'b.docx')
 def send():
  with p.open('rb') as f,d.open('rb') as g:return c.post('/api/v4/admin/imports/batch',headers=headers('admin'),files=[('files',('a.pdf',f)),('files',('b.docx',g))],data={'request_key':'many','reuse_confirmed':'true','license_name':'CC0'})
 r=send();assert r.status_code==200,r.text;bid=r.json()['batch_id'];assert send().json()['batch_id']==bid
 app.state.bank.jobs.work(limit=20);b=app.state.bank.store.batch(bid);assert len(b.files)==2;assert all(f['status']=='imported' for f in b.files)

def test_closed_exam_deadline_sweep_without_browser_request(env):
 ids,_=setup_bank(env);s=exam(env,ids);app,c,clock,*_=env;clock[0]+=61;app.state.sessions.expire_due()
 with app.state.bank.store.connect() as conn:
  stored=json.loads(conn.execute('SELECT payload FROM v4_sessions WHERE session_id=?',(s['id'],)).fetchone()[0]);assert stored['status']=='submitted';assert stored['submitted_at']==s['deadline']

def test_student_pdf_automatically_becomes_private_exam_without_answer_editor(env):
 app,c,clock,temp=env;p=mixed_pdf(temp/'student.pdf')
 with p.open('rb') as f:r=c.post('/api/v4/papers/import',headers=headers(),files={'file':('student.pdf',f)},data={'request_key':'my-pdf','title':'我的 PDF 模考','duration_minutes':'2','course_id':app.state.bank.catalog['course_id']})
 assert r.status_code==200,r.text;bid=r.json()['batch_id'];app.state.bank.jobs.work(limit=1)
 tasks=c.get('/api/v4/papers/imports',headers=headers()).json();assert len(tasks)==1;paper_id=tasks[0]['files'][0]['paper_id'];assert paper_id
 assert c.get('/api/v4/papers/imports',headers=headers('other')).json()==[]
 # Public question discovery must not list private PDFs, even for their owner.
 for identity in ['student','other','admin']:
  assert c.get('/api/v4/questions',headers=headers(identity)).json()==[]
 public=c.get('/api/v4/questions',headers=headers()).json();assert public==[]
 papers=c.get('/api/v4/sets',headers=headers()).json();assert papers[0]['source_kind']=='student-upload'
 started=c.post('/api/v4/sessions',headers=headers(),json={'mode':'exam','request_id':'pdf-exam','set_id':paper_id});assert started.status_code==200,started.text;s=started.json();assert len(s['questions'])==2;assert 'correct_answer' not in json.dumps(s)
 qid=s['questions'][0]['question_id'];command(env,s,'answer',question_id=qid,option='A');s=command(env,s,'submit').json();assert s['grade']['records'][0]['status']=='incorrect';assert s['grade']['records'][0]['correct_answer']=='B'
 assert len(c.get('/api/v4/mistakes',headers=headers()).json())==2
 ownpractice=c.post('/api/v4/sessions',headers=headers(),json={'mode':'practice','request_id':'pdf-practice','paper_id':paper_id,'count':10});assert ownpractice.status_code==200;assert len(ownpractice.json()['questions'])==2

def test_student_no_key_saves_selected_option_ungraded_no_forced_answer(env):
 from reportlab.pdfgen import canvas
 app,c,clock,temp=env;p=temp/'no-key.pdf';pdf=canvas.Canvas(str(p));pdf.setFont('Helvetica',12)
 for y,text in [(760,'1. Use net F = ma to find acceleration for a 3 kg block under 9 N.'),(730,'(A) 1 m/s^2'),(710,'(B) 3 m/s^2')]:pdf.drawString(40,y,text)
 pdf.save()
 with p.open('rb') as f:r=c.post('/api/v4/papers/import',headers=headers(),files={'file':('no-key.pdf',f)},data={'request_key':'no-key','title':'无答案试卷','duration_minutes':'1'})
 assert r.status_code==200,r.text;app.state.bank.jobs.work(limit=1);task=c.get('/api/v4/papers/imports',headers=headers()).json()[0];pid=task['files'][0]['paper_id']
 s=c.post('/api/v4/sessions',headers=headers(),json={'mode':'practice','request_id':'unknown-practice','paper_id':pid,'count':10}).json();qid=s['questions'][0]['question_id'];command(env,s,'answer',question_id=qid,option='A');r=command(env,s,'check',question_id=qid).json();assert r['records'][0]['selected']=='A';assert r['records'][0]['status']=='ungraded';assert r['records'][0]['correct_answer'] is None
 assert c.get('/api/v4/mistakes',headers=headers()).json()==[]
 assert c.post('/api/v4/admin/questions/'+qid+'/answer',headers=headers(),json={'label':'A','reason':'student guess','expected_revision':0}).status_code==403

def test_private_error_matches_same_type_in_admin_public_bank(env):
 ids,_=setup_bank(env);app,c,clock,temp=env;p=mixed_pdf(temp/'private-mixed.pdf')
 with p.open('rb') as f:r=c.post('/api/v4/papers/import',headers=headers(),files={'file':('private.pdf',f)},data={'request_key':'private-related','title':'学生试卷','duration_minutes':'1'})
 app.state.bank.jobs.work(limit=1);b=app.state.bank.store.batch(r.json()['batch_id']);private_id=b.files[0]['question_ids'][0]
 assert app.state.bank.store.question(private_id).scope=='exam_private';assert private_id not in ids
 r=c.post('/api/v4/sessions',headers=headers(),json={'mode':'practice','request_id':'same-type','related_to':private_id,'same_type':True,'comprehensive':True,'count':20});assert r.status_code==200,r.text
 assert r.json()['questions'];assert all(q['question_id'] in ids for q in r.json()['questions']);assert private_id not in [q['question_id'] for q in r.json()['questions']]

def targeted_bank(env):
 from reportlab.pdfgen import canvas
 app,c,clock,temp=env;p=temp/'targeted.pdf';pdf=canvas.Canvas(str(p),pagesize=(612,792));pdf.setFont('Helvetica',11)
 pdf.drawString(40,765,'Section I: Multiple Choice')
 for n in range(1,5):
  y=720-(n-1)*150
  for offset,text in [(0,f'{n}. A {n+2} kg cart receives {3*(n+2)} N. Use net F = ma to find acceleration.'),(25,'(A) 1 m/s^2'),(45,'(B) 3 m/s^2')]:pdf.drawString(40,y-offset,text)
 pdf.drawString(40,90,'Answer Key');pdf.drawString(40,65,'1 B   2 B   3 B   4 B');pdf.save()
 ids=upload(env,p,'targeted').files[0]['question_ids'];assert len(ids)==4
 for qid in ids:assert c.post('/api/v4/admin/questions/'+qid+'/publish',headers=headers('admin'),json={}).status_code==200
 return ids

def test_private_mistake_continuous_same_type_batches_survive_restart(env):
 app,c,clock,temp=env;ids=targeted_bank(env);p=mixed_pdf(temp/'own.pdf')
 with p.open('rb') as f:r=c.post('/api/v4/papers/import',headers=headers(),files={'file':('own.pdf',f)},data={'request_key':'own-chain'})
 app.state.bank.jobs.work(limit=1);task=app.state.bank.store.batch(r.json()['batch_id']);paper=task.files[0]['paper_id'];original=task.files[0]['question_ids'][0]
 s=c.post('/api/v4/sessions',headers=headers(),json={'mode':'practice','request_id':'origin','paper_id':paper,'count':10}).json()
 command(env,s,'answer',question_id=original,option='A');checked=command(env,s,'check',question_id=original).json()
 assert checked['records'][0]['correct_answer']=='B';assert checked['records'][0]['question_types']==['newton_second_law']
 wrong=c.get('/api/v4/mistakes',headers=headers()).json();assert wrong[0]['question']['topics']['core']==['2.5']
 def start(body,client=c):return client.post('/api/v4/sessions',headers=headers(),json={'mode':'practice','count':2,**body})
 first=start({'request_id':'batch-one','related_to':original,'same_type':True,'comprehensive':True}).json()
 assert first['practice_progress']=={'selected':2,'remaining':2,'seen':2};assert all(q['origin']=='public-bank' for q in first['questions'])
 assert start({'request_id':'too-soon','continue_from':first['id']}).status_code==422
 command(env,first,'submit')
 # Later reclassification of the original must not redirect an existing practice series.
 m=app.state.bank.meta(first['related_scope']['source_version_id']);m['core']=['3.3'];app.state.bank.save_meta(first['related_scope']['source_version_id'],m)
 restarted=create_app(app.state.bank.root,TOKENS,clock=lambda:clock[0],worker=False);client=TestClient(restarted)
 request={'request_id':'batch-two','continue_from':first['id'],'topics':['3.3'],'same_type':False}
 r=start(request,client);assert r.status_code==200,r.text;second=r.json()
 assert second['related_scope']['topics']==['2.5'];assert second['related_scope']['same_type'] is True
 assert second['practice_progress']=={'selected':2,'remaining':0,'seen':4}
 assert {q['question_id'] for q in first['questions']}.isdisjoint(q['question_id'] for q in second['questions'])
 assert start(request,client).json()['id']==second['id']
 assert client.post('/api/v4/sessions/'+second['id']+'/commands',headers=headers(),json={'type':'submit'}).status_code==200
 exhausted=start({'request_id':'exhausted','continue_from':second['id']},client);assert exhausted.status_code==422;assert '没有更多未练题目' in exhausted.json()['detail']
 repeated=start({'request_id':'repeat','continue_from':second['id'],'repeat_seen':True},client);assert repeated.status_code==200;assert repeated.json()['practice_progress']['seen']==2
 assert original not in [q['question_id'] for q in repeated.json()['questions']]
 assert len(client.get('/api/v4/mistakes',headers=headers()).json())==1

def test_continuation_enforces_owner_and_scope_and_exam_lock(env):
 ids=targeted_bank(env);app,c,*_=env
 first=c.post('/api/v4/sessions',headers=headers(),json={'mode':'practice','request_id':'special','related_to':ids[0],'same_type':True,'comprehensive':True,'count':1}).json();command(env,first,'submit')
 body={'mode':'practice','request_id':'next','continue_from':first['id']}
 assert c.post('/api/v4/sessions',headers=headers('other'),json=body).status_code==404
 assert c.post('/api/v4/sessions',headers=headers(),json={**body,'question_ids':[ids[0]]}).status_code==422
 assert c.post('/api/v4/sessions',headers=headers(),json={**body,'mode':'exam'}).status_code==422
 active=exam(env,ids)
 assert c.post('/api/v4/sessions',headers=headers(),json=body).status_code==422
 command(env,active,'submit');r=c.post('/api/v4/sessions',headers=headers(),json=body);assert r.status_code==200,r.text

def admin_bank(env,**params):
 r=env[1].get('/api/v4/admin/bank',headers=headers('admin'),params=params);assert r.status_code==200,r.text;return r.json()

def review_types(env,qid,methods,structures=(),**overrides):
 app,c,*_=env;q=app.state.bank.store.question(qid);cls=app.state.bank.store.classification(q.current_version_id)
 return c.put('/api/v4/admin/questions/'+qid+'/types',headers=headers('admin'),json={'methods':methods,'structures':list(structures),'reason':'Reviewed necessary solution steps','expected_version':q.current_version_id,'expected_classification_id':cls.classification_id,**overrides})

def test_admin_bank_pagination_filters_and_honest_coverage_excludes_private(env):
 app,c,clock,temp=env;empty=admin_bank(env);assert empty['totals']['total']==0;assert len(empty['coverage'])==41;assert sum(t['published'] for t in empty['coverage'])==0
 ids,b=setup_bank(env)
 assert c.put('/api/v4/admin/questions/'+ids[0]+'/tags',headers=headers('admin'),json={'course_id':app.state.bank.catalog['course_id'],'core':['2.5','3.3'],'related':[]}).status_code==200
 p=mixed_pdf(temp/'private.pdf')
 with p.open('rb') as f:r=c.post('/api/v4/papers/import',headers=headers(),files={'file':('private.pdf',f)},data={'request_key':'private-coverage'})
 assert r.status_code==200;app.state.bank.jobs.work(limit=1)
 page=admin_bank(env,limit=1);second=admin_bank(env,offset=1,limit=1)
 assert page['total']==page['totals']['total']==2;assert page['items'][0]['question_id']!=second['items'][0]['question_id']
 assert page['sources'][0]['filename']=='mixed.pdf';assert len(page['sources'])==1
 coverage={t['topic_id']:t for t in page['coverage']};assert coverage['2.5']['published']==coverage['2.5']['verified']==2;assert coverage['3.3']['published']==1
 assert admin_bank(env,topic_id='3.3',method='newton_second_law')['total']==2 # Core or related Topic both match this filter.
 assert admin_bank(env,unit_id='1')['total']==0
 assert admin_bank(env,document_id=b.files[0]['document_id'],publication='approved',structure='force_acceleration')['total']==2
 assert c.get('/api/v4/admin/bank',headers=headers()).status_code==403
 assert c.get('/api/v4/admin/bank',headers=headers('admin'),params={'limit':101}).status_code==422
 assert c.get('/api/v4/admin/bank',headers=headers('admin'),params={'topic_id':'invented'}).status_code==422
 version=app.state.bank.store.question(ids[1]).current_version_id;key=app.state.bank.store.latest_answer(version)
 app.state.bank.store.append_answer(version,label=None,status=AnswerStatus.UNRESOLVED,evidence=[],expected_revision=key.revision)
 assert admin_bank(env,answer='unconfirmed')['total']==1;assert admin_bank(env)['totals']['verified']==1
 c.post('/api/v4/admin/questions/'+ids[0]+'/withdraw',headers=headers('admin'))
 assert admin_bank(env,publication='draft')['total']==2 # V3 also withdraws the question whose verified key was invalidated.
 assert next(t for t in admin_bank(env)['coverage'] if t['topic_id']=='3.3')['published']==0

def test_admin_type_review_overrides_rules_and_preserves_existing_attempt(env):
 ids,_=setup_bank(env);app,c,*_=env;s=practice(env,ids);qid=ids[0];old_type=s['questions'][0]['types'];old_cls=app.state.bank.store.classification(s['questions'][0]['version_id']).classification_id
 r=review_types(env,qid,['free_body_diagram'],['force_balance']);assert r.status_code==200,r.text
 assert app.state.bank.types(s['questions'][0]['version_id'])['methods']==['free_body_diagram']
 assert admin_bank(env,method='free_body_diagram',structure='force_balance')['total']==1
 command(env,s,'answer',question_id=qid,option='A');checked=command(env,s,'check',question_id=qid).json()
 assert checked['records'][0]['question_types']==old_type['methods'];assert checked['records'][0]['question_structures']==old_type['structures'];assert checked['questions'][0]['types']==old_type
 stale=review_types(env,qid,['newton_second_law'],expected_classification_id=old_cls);assert stale.status_code==409
 assert review_types(env,qid,[],[]).status_code==200
 assert app.state.bank.types(s['questions'][0]['version_id'])['methods']==[];assert admin_bank(env,issue='untyped')['total']==1
 history=c.get('/api/v4/admin/questions/'+qid+'/types',headers=headers('admin')).json();assert len(history)==2;assert history[0]['methods']==['free_body_diagram'];assert history[1]['methods']==[]
 assert c.get('/api/v4/admin/questions/'+qid+'/types',headers=headers()).status_code==403
 assert review_types(env,qid,['invented']).status_code==422;assert review_types(env,qid,[],reason=' ').status_code==422
 wrong=c.get('/api/v4/mistakes',headers=headers()).json();assert wrong[0]['records'][0]['question_types']==old_type['methods']

def test_private_pdf_inherits_exact_reviewed_bank_types_and_matches_other_public_questions(env):
 ids,b=setup_bank(env);app,c,clock,temp=env
 for qid in ids:assert review_types(env,qid,['free_body_diagram'],[]).status_code==200
 p=mixed_pdf(temp/'exact-private.pdf')
 with p.open('rb') as f:r=c.post('/api/v4/papers/import',headers=headers(),files={'file':('own.pdf',f)},data={'request_key':'reviewed-private'})
 app.state.bank.jobs.work(limit=1);own=app.state.bank.store.batch(r.json()['batch_id']);qid=own.files[0]['question_ids'][0]
 types=app.state.bank.types(app.state.bank.store.question(qid).current_version_id);assert types['methods']==['free_body_diagram'];assert types['source'].startswith('verified-bank-types:')
 r=c.post('/api/v4/sessions',headers=headers(),json={'mode':'practice','request_id':'exact-type-related','related_to':qid,'same_type':True,'comprehensive':True,'count':20});assert r.status_code==200,r.text
 assert [q['question_id'] for q in r.json()['questions']]==[ids[1]]
 assert review_types(env,qid,['work_energy']).status_code==404
 assert admin_bank(env)['totals']['total']==2

def test_admin_cannot_acknowledge_unsafe_structural_questions_into_publication(env):
 ids,_=setup_bank(env);app,c,*_=env;qid=ids[0];q=app.state.bank.store.question(qid)
 c.post('/api/v4/admin/questions/'+qid+'/withdraw',headers=headers('admin'))
 for issue in ['missing_options','shared_answer_leak','shared_stem_unresolved']:
  meta=app.state.bank.meta(q.current_version_id);app.state.bank.save_meta(q.current_version_id,{**meta,'issues':[issue]})
  r=c.post('/api/v4/admin/questions/'+qid+'/publish',headers=headers('admin'),json={'acknowledge_issues':True});assert r.status_code==422,r.text
 assert app.state.bank.store.question(qid).publication=='draft'
 assert qid not in [q['question_id'] for q in c.get('/api/v4/questions',headers=headers()).json()]

def test_original_paper_creation_uses_full_source_not_admin_page(env):
 ids=targeted_bank(env);app,c,*_=env;first=admin_bank(env,limit=1);assert len(first['items'])==1
 r=c.post('/api/v4/admin/sets',headers=headers('admin'),json={'title':'Full original MCQ','course_id':app.state.bank.catalog['course_id'],'document_id':first['sources'][0]['document_id'],'section':'MCQ','duration_minutes':30})
 assert r.status_code==200,r.text;assert r.json()['question_ids']==ids
 started=c.post('/api/v4/sessions',headers=headers(),json={'mode':'exam','request_id':'original-paper','set_id':r.json()['set_id']});assert started.status_code==200,started.text;assert started.json()['set_info']['source_year'] is None
