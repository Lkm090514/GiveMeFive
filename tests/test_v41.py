"""V4.1 source-key-only grading and original-visual exam admission."""
import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from reportlab.pdfgen import canvas
from backend.app import create_app
from backend.bank import Bank
from gmf_v3.answers import UnconfiguredProvider
from gmf_v3.contracts import AnswerStatus
from test_v4 import env, headers, command, setup_bank, exam


def own_import(env,path,key='private'):
 app,client,*_=env
 with path.open('rb') as f:
  result=client.post('/api/v4/papers/import',headers=headers(),files={'file':(path.name,f)},data={'request_key':key,'duration_minutes':1})
 assert result.status_code==200,result.text
 app.state.bank.jobs.work(limit=1)
 batch=app.state.bank.store.batch(result.json()['batch_id'])
 assert batch.status=='completed',batch
 return batch.files[0]


def private_exam(env,paper,request_id='private-exam'):
 result=env[1].post('/api/v4/sessions',headers=headers(),json={'mode':'exam','set_id':paper['paper_id'],'request_id':request_id})
 assert result.status_code==200,result.text
 return result.json()


def visual_pdf(path):
 """Authored QA fixture; two visual questions (one cross-page), one blank option."""
 c=canvas.Canvas(str(path),pagesize=(612,792));c.setFont('Helvetica',12)
 c.drawString(40,760,'GMF authored QA fixture - not an official physics paper')
 c.drawString(40,710,'1. Select the corresponding diagram for the acceleration.')
 for i,label in enumerate('ABCD'):
  y=650-i*75;c.drawString(40,y,f'({label})');c.rect(100,y-25,30+i*10,60)
 c.drawString(40,240,'2. Select the correct expression; this question continues.')
 c.drawString(40,200,'(A) x = v t');c.drawString(40,170,'(B) x = a t')
 c.showPage();c.setFont('Helvetica',12)
 c.drawString(40,740,'(C) x = a t^2 / 2');c.drawString(40,710,'(D) x = v / t')
 c.drawString(40,620,'3. This malformed question has a missing last option.')
 for i,label in enumerate('ABC'):c.drawString(40,580-i*35,f'({label}) value {i+1}')
 c.drawString(40,475,'(D)');c.save();return path


def test_no_ai_even_when_credentials_or_queued_auto_solve_are_present(env,monkeypatch):
 app,client,clock,temp=env
 monkeypatch.setenv('GMF_LLM_API_KEY','dummy-never-use');monkeypatch.setenv('GMF_LLM_MODEL','dummy')
 assert isinstance(Bank(temp/'other').answers.provider,UnconfiguredProvider)
 calls=[]
 monkeypatch.setattr(app.state.bank.answers,'solve',lambda *a,**kw:calls.append('solve'))
 monkeypatch.setattr(app.state.bank,'model_tags',lambda *a,**kw:calls.append('classify'))
 paper=own_import(env,Path(__file__).parent/'fixtures/v4-mixed.pdf')
 # Older persisted import jobs may still carry auto_solve=True after an upgrade.
 queued=app.state.bank.enqueue_import([Path(__file__).parent/'fixtures/v4-no-key.pdf'],scope='exam_private',owner_id='student',auto_solve=True)
 app.state.bank.jobs.work(limit=1,batch_id=queued.batch_id)
 assert app.state.bank.store.batch(queued.batch_id).status=='completed'
 assert not calls
 assert all(a=='Verified' for a in paper['answer_states'].values())


def test_original_visual_options_cross_page_admission_and_blank_option_block(env):
 app,client,clock,temp=env;paper=own_import(env,visual_pdf(temp/'visual.pdf'))
 assert paper['summary']['mcq']==3
 with app.state.bank.store.connect() as c:
  saved=json.loads(c.execute('SELECT payload FROM v4_sets WHERE set_id=?',(paper['paper_id'],)).fetchone()[0])
 assert len(saved['question_ids'])==2
 rows=[app.state.bank.store.version(app.state.bank.store.question(q).current_version_id) for q in paper['question_ids']]
 assert len(rows[1].spans)==2
 assert app.state.bank.exam_issues(rows[2])==['missing_options']
 s=private_exam(env,paper)
 assert len(s['questions'])==2 and s['questions'][0]['display_mode']=='original'
 assert len(s['questions'][1]['assets'])==2
 for q in s['questions']:
  for asset in q['assets']:assert client.get('/api/v4/assets/'+asset,headers=headers()).status_code==200
 # Admission rechecks stored versions rather than trusting the paper's old snapshot.
 q=s['questions'][0];asset=app.state.bank.store.asset(q['assets'][0])
 (app.state.bank.assets/asset.relative_path).write_bytes(b'damaged')
 command(env,s,'submit')
 r=client.post('/api/v4/sessions',headers=headers(),json={'mode':'exam','set_id':paper['paper_id'],'request_id':'damaged'})
 assert r.status_code==422


def test_ungraded_exam_answers_restart_deadline_submit_and_no_mistakes(env):
 app,client,clock,temp=env
 paper=own_import(env,Path(__file__).parent/'fixtures/v4-no-key.pdf')
 s=private_exam(env,paper);qid=s['questions'][0]['question_id']
 assert command(env,s,'answer',question_id=qid,option='A').status_code==200
 command(env,s,'answer',question_id=qid,option='B');clock[0]+=15
 restarted=create_app(app.state.bank.root,app.state.tokens,clock=lambda:clock[0],worker=False);c=TestClient(restarted)
 resumed=c.get('/api/v4/sessions/'+s['id'],headers=headers()).json()
 assert resumed['answers'][qid]=='B' and resumed['deadline']==s['deadline']
 assert resumed['grade'] is None and resumed['summary'] is None
 clock[0]+=46
 done=c.get('/api/v4/sessions/'+s['id'],headers=headers()).json()
 assert done['status']=='submitted' and done['reason']=='timeout'
 summary=done['summary'];assert summary['scoring_mode']=='ungraded'
 assert summary['answered']==1 and summary['unanswered']==summary['total']-1
 assert summary['accuracy'] is None and summary['graded_accuracy'] is None
 assert summary['elapsed_ms']==60000 and summary['graded']==0
 assert all(r['status']=='ungraded' for r in done['grade']['records'])
 for typ in ['submit','submit','answer']:
  result=c.post('/api/v4/sessions/'+s['id']+'/commands',headers=headers(),json={'type':typ,'question_id':qid,'option':'A'}).json()
  assert result['answers'][qid]=='B'
 with app.state.bank.store.connect() as db:
  assert db.execute('SELECT count(*) FROM v4_grades').fetchone()[0]==1
 assert c.get('/api/v4/mistakes',headers=headers()).json()==[]
 assert c.get('/api/v4/sessions/'+s['id'],headers=headers('other')).status_code==404


def test_partial_scoring_has_explicit_coverage_and_never_marks_unknown_wrong(env):
 ids,_=setup_bank(env);app,client,*_=env
 q=app.state.bank.store.question(ids[1]);key=app.state.bank.store.latest_answer(q.current_version_id)
 app.state.bank.store.append_answer(q.current_version_id,label=None,status=AnswerStatus.UNRESOLVED,evidence=[],expected_revision=key.revision)
 app.state.bank.publish(ids[1],'admin');s=exam(env,ids)
 command(env,s,'answer',question_id=ids[0],option='B');command(env,s,'answer',question_id=ids[1],option='A')
 done=command(env,s,'submit').json();summary=done['summary']
 assert summary['scoring_mode']=='partial' and summary['coverage']==.5
 assert summary['graded']==1 and summary['ungraded']==1
 assert summary['accuracy'] is None and summary['graded_accuracy']==1
 assert summary['answered']==2 and summary['incorrect']==0
 assert client.get('/api/v4/mistakes',headers=headers()).json()==[]


def test_source_key_grading_and_answer_snapshots_are_preserved(env):
 paper=own_import(env,Path(__file__).parent/'fixtures/v4-mixed.pdf');s=private_exam(env,paper)
 for q in s['questions']:command(env,s,'answer',question_id=q['question_id'],option='B')
 done=command(env,s,'submit').json()
 assert done['summary']['scoring_mode']=='graded' and done['summary']['accuracy']==1
 assert done['summary']['graded']==2 and all(r['answer_source']=='source-key-audit/4' for r in done['grade']['records'])


def test_answer_added_after_exam_start_never_retroactively_scores_the_snapshot(env):
 app,client,*_=env;paper=own_import(env,Path(__file__).parent/'fixtures/v4-no-key.pdf');s=private_exam(env,paper)
 q=s['questions'][0];v=q['version_id'];old=app.state.bank.store.latest_answer(v)
 app.state.bank.answers.confirm(v,label='A',reviewer='source-reviewer',reason='Original key manually checked',expected_revision=old.revision if old else 0)
 command(env,s,'answer',question_id=q['question_id'],option='A')
 assert command(env,s,'submit').json()['summary']['scoring_mode']=='ungraded'


def test_page_range_boundary_is_blocked_instead_of_silently_truncating_an_exam(env):
 app,client,clock,temp=env
 batch=app.state.bank.enqueue_import([visual_pdf(temp/'partial.pdf')],scope='exam_private',owner_id='student',auto_solve=False,ocr=False,page_range=(1,1))
 app.state.bank.jobs.work(limit=1,batch_id=batch.batch_id);result=app.state.bank.store.batch(batch.batch_id).files[0]
 versions=[app.state.bank.store.version(app.state.bank.store.question(q).current_version_id) for q in result['question_ids']]
 assert 'page_range_boundary_requires_review' in versions[-1].warnings
 assert 'page_range_boundary_requires_review' in app.state.bank.exam_issues(versions[-1])
 s=private_exam(env,result)
 assert len(s['questions'])==1


def test_existing_explicit_display_review_still_allows_exam_but_not_missing_options(env):
 ids,_=setup_bank(env);bank=env[0].state.bank;q=bank.store.question(ids[0]);m=bank.meta(q.current_version_id)
 bank.save_meta(q.current_version_id,{**m,'issues':['ocr_requires_review']})
 bank.publish(q.question_id,'admin',acknowledge_issues=True)
 s=exam(env,ids);assert len(s['questions'])==2
 edited=env[1].patch('/api/v4/admin/questions/'+q.question_id,headers=headers('admin'),json={'expected_version':q.current_version_id,'stem':'Edited content requires a fresh display review','options':bank.public(q.question_id)['options']})
 assert edited.status_code==200
 assert bank.meta(edited.json()['version_id'])['issues_reviewed'] is False
 assert env[1].post('/api/v4/admin/questions/'+q.question_id+'/publish',headers=headers('admin'),json={}).status_code==422
 bank.save_meta(q.current_version_id,{**bank.meta(q.current_version_id),'issues':['missing_options']})
 assert 'missing_options' in bank.exam_issues(bank.store.version(q.current_version_id))
