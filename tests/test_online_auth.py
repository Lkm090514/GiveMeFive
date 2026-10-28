import json,os
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from reportlab.pdfgen import canvas
from backend.app import create_app
from backend.identity import Identity

ORIGIN='https://gmf.example'
HEAD={'Origin':ORIGIN,'X-GMF-Request':'1'}
PASSWORD='Independent-user-Password-1234'
@pytest.fixture
def online(tmp_path,monkeypatch):
 monkeypatch.setenv('GMF_AUTH_MODE','password');monkeypatch.setenv('GMF_ENV','testing');monkeypatch.setenv('GMF_PUBLIC_ORIGIN',ORIGIN)
 app=create_app(tmp_path/'data',worker=False);identity=Identity(app.state.bank.store);clients={}
 for who,role in [('admin','admin'),('a','student'),('b','student')]:
  invite=identity.invite(who+'@example.test',role);c=TestClient(app,base_url=ORIGIN,headers=HEAD)
  assert c.post('/api/v4/auth/register',json={'email':who+'@example.test','password':PASSWORD,'invite':invite}).status_code==200
  assert c.post('/api/v4/auth/login',json={'email':who+'@example.test','password':PASSWORD}).status_code==200
  clients[who]=c
 return app,clients,tmp_path

def paper(online,client='a',extension='pdf'):
 app,clients,tmp=online;p=tmp/('private.'+extension)
 if extension=='pdf':
  c=canvas.Canvas(str(p));c.drawString(40,750,'1. Which direction is positive?');c.drawString(40,710,'(A) Left');c.drawString(40,680,'(B) Right');c.save()
 else:
  from docx import Document
  d=Document()
  for line in ['1. Which direction is positive?','(A) Left','(B) Right']:d.add_paragraph(line)
  d.save(p)
 r=clients[client].post('/api/v4/papers/import',data={'request_key':'private-'+extension,'duration_minutes':.1},files={'file':(p.name,p.read_bytes())});assert r.status_code==200,r.text
 app.state.bank.jobs.work(limit=1);batch=app.state.bank.store.batch(r.json()['batch_id']);assert batch.status=='completed',batch
 return batch,batch.files[0]['paper_id'],p

def confirm(client,pid):
 data=client.get('/api/v4/papers/'+pid+'/review').json();r=client.post('/api/v4/papers/'+pid+'/confirm',json={'expected_revision':data['revision'],'reviewed_versions':{q['question_id']:q['version_id'] for q in data['questions']}});assert r.status_code==200,r.text
 return data

def test_independent_accounts_roles_private_files_and_restart(online):
 app,clients,tmp=online;a,b=clients['a'],clients['b'];batch,pid,original=paper(online)
 assert a.get('/api/v4/me').json()['owner_id']!=b.get('/api/v4/me').json()['owner_id']
 assert b.get('/api/v4/papers/'+pid+'/review').status_code==404
 url=f"/api/v4/papers/imports/{batch.batch_id}/{batch.files[0]['job_id']}/original"
 assert a.get(url).content==original.read_bytes();assert b.get(url).status_code==404
 assert b.get('/api/v4/sets').json()==[]
 assert a.get('/api/v4/admin/questions').status_code==403
 assert a.post('/api/v4/admin/invites',json={'email':'attacker@example.test','role':'admin'}).status_code==403
 data=confirm(a,pid);qid=data['questions'][0]['question_id'];asset=data['questions'][0]['assets'][0]
 assert a.get('/api/v4/assets/'+asset).status_code==200
 assert b.get('/api/v4/assets/'+asset).status_code==404
 s=a.post('/api/v4/sessions',json={'mode':'exam','set_id':pid,'request_id':'real-exam'});assert s.status_code==200,s.text;s=s.json()
 r=a.post('/api/v4/sessions/'+s['id']+'/commands',json={'type':'answer','question_id':qid,'option':'A'});assert r.status_code==200,r.text
 assert b.get('/api/v4/sessions/'+s['id']).status_code==404
 result=a.post('/api/v4/sessions/'+s['id']+'/commands',json={'type':'submit'}).json()
 assert result['grade']['records'][0]['status']=='ungraded';assert result['grade']['records'][0]['selected']=='A'
 assert a.post('/api/v4/sessions/'+s['id']+'/commands',json={'type':'submit'}).json()['grade_id']==result['grade_id']
 old_cookie=a.cookies.get(app.state.auth_cookie_name);assert a.post('/api/v4/logout').status_code==200
 assert a.get('/api/v4/me').status_code==401
 restarted=create_app(app.state.bank.root,worker=False);new=TestClient(restarted,base_url=ORIGIN,headers=HEAD)
 new.cookies.set(restarted.state.auth_cookie_name,old_cookie);assert new.get('/api/v4/me').status_code==401
 assert new.post('/api/v4/auth/login',json={'email':'a@example.test','password':PASSWORD}).status_code==200
 assert new.get('/api/v4/sessions/'+s['id']).json()['grade_id']==result['grade_id']
 with app.state.bank.store.connect() as c:
  rows=c.execute('SELECT password_hash FROM v43_users').fetchall();assert all(PASSWORD not in r[0] for r in rows)
  assert c.execute('SELECT count(*) FROM v43_users').fetchone()[0]==3

def test_confirmation_gate_stale_versions_and_private_edit(online):
 app,clients,_=online;a=clients['a'];_,pid,_=paper(online)
 assert a.get('/api/v4/sets').json()==[]
 assert a.post('/api/v4/sessions',json={'mode':'exam','set_id':pid,'request_id':'before-confirm'}).status_code==422
 data=a.get('/api/v4/papers/'+pid+'/review').json();q=data['questions'][0]
 assert a.post('/api/v4/sessions',json={'mode':'practice','question_ids':[q['question_id']],'request_id':'bypass'}).status_code==422
 assert a.post('/api/v4/papers/'+pid+'/confirm',json={'expected_revision':0,'reviewed_versions':{}}).status_code==422
 edited=a.patch('/api/v4/papers/'+pid+'/review/'+q['question_id'],json={'expected_revision':0,'expected_version':q['version_id'],'stem':'Reviewed: which direction is positive?','options':q['options']})
 assert edited.status_code==200,edited.text
 assert a.post('/api/v4/papers/'+pid+'/confirm',json={'expected_revision':0,'reviewed_versions':{q['question_id']:q['version_id']}}).status_code==409
 confirm(a,pid)
 assert a.get('/api/v4/sets').json()[0]['question_count']==1
 assert app.state.bank.store.latest_answer(edited.json()['questions'][0]['version_id']) is None
 assert clients['b'].patch('/api/v4/papers/'+pid+'/review/'+q['question_id'],json={}).status_code==404

def test_invites_csrf_and_password_rate_limit(online):
 app,clients,_=online;a=clients['a'];anonymous=TestClient(app,base_url=ORIGIN)
 assert anonymous.post('/api/v4/auth/login',json={'email':'a@example.test','password':PASSWORD}).status_code==403
 assert anonymous.post('/api/v4/auth/login',headers={'Origin':'https://evil.example','X-GMF-Request':'1'},json={}).status_code==403
 for _ in range(5):assert anonymous.post('/api/v4/auth/login',headers=HEAD,json={'email':'a@example.test','password':'invalid-password'}).status_code==401
 assert anonymous.post('/api/v4/auth/login',headers=HEAD,json={'email':'a@example.test','password':PASSWORD}).status_code==429
 identity=Identity(app.state.bank.store);invite=identity.invite('new@example.test')
 assert a.post('/api/v4/auth/register',json={'email':'other@example.test','password':PASSWORD,'invite':invite}).status_code==422
 assert a.post('/api/v4/auth/register',json={'email':'new@example.test','password':PASSWORD,'invite':invite}).status_code==200
 assert a.post('/api/v4/auth/register',json={'email':'new@example.test','password':PASSWORD,'invite':invite}).status_code==422

def test_student_docx_online_review_and_original_bytes(online):
 app,clients,_=online;a=clients['a'];batch,pid,path=paper(online,extension='docx');assert pid
 confirm(a,pid)
 url=f"/api/v4/papers/imports/{batch.batch_id}/{batch.files[0]['job_id']}/original"
 assert a.get(url).content==path.read_bytes()
 assert clients['b'].get(url).status_code==404

def test_production_requires_gateway_and_never_serves_static_textbook(tmp_path,monkeypatch):
 monkeypatch.setenv('GMF_AUTH_MODE','password');monkeypatch.setenv('GMF_ENV','production');monkeypatch.setenv('GMF_PUBLIC_ORIGIN',ORIGIN);monkeypatch.delenv('GMF_GATEWAY_KEY',raising=False)
 with pytest.raises(RuntimeError):create_app(tmp_path/'prod',worker=False)
 monkeypatch.setenv('GMF_GATEWAY_KEY','x'*40);app=create_app(tmp_path/'prod',worker=False);client=TestClient(app,base_url=ORIGIN)
 assert client.get('/api/v4/me').status_code==403
 assert client.get('/api/v4/me',headers={'X-GMF-Gateway-Key':'x'*40}).status_code==401
 assert client.get('/data/course.json').status_code==404
 assert client.get('/api/v4/health').json()['auth_mode']=='password'
