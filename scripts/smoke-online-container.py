"""Exercise the real deployed container in CI; no shared admin, mock API or textbook.

Also usable against HTTPS after deployment. Bootstrap invitations are read from an
operator-owned container, never printed. HTTP cookie forwarding is permitted only
for a loopback CI origin; it is not an HTTPS/browser acceptance claim.
"""
import hashlib,json,os,secrets,subprocess,time
from pathlib import Path
import httpx

origin=os.environ['GMF_SMOKE_ORIGIN'].rstrip('/')
container=os.environ['GMF_SMOKE_CONTAINER'];key=os.environ['GMF_GATEWAY_KEY']
assert origin in ('http://127.0.0.1:18080',) or origin.startswith('https://')
front=os.environ['GMF_PUBLIC_ORIGIN'];password=secrets.token_urlsafe(24)
headers={'Origin':front,'X-GMF-Request':'1','X-GMF-Gateway-Key':key}

def ready():
 for _ in range(90):
  try:
   if httpx.get(origin+'/api/v4/ready',timeout=2).status_code==200:return
  except httpx.HTTPError:pass
  time.sleep(1)
 raise AssertionError('Container did not become ready')

def seed(email):
 code="import os,json;from backend.bank import Bank;from backend.identity import Identity; print(Identity(Bank(os.environ['GMF_DATA_DIR']).store).invite("+repr(email)+"))"
 return subprocess.check_output(['docker','exec',container,'python','-c',code],text=True).strip()

class Student:
 def __init__(self,email):
  self.email=email;self.client=httpx.Client(base_url=origin,headers=headers,timeout=120);self.cookie=None
 def call(self,method,path,**kwargs):
  extra={}
  if self.cookie and origin.startswith('http://127.0.0.1:'):extra['Cookie']=self.cookie
  result=self.client.request(method,'/api/v4'+path,headers=extra,**kwargs)
  cookie=result.headers.get('set-cookie','')
  if cookie.startswith('__Host-gmf_cloud_session='):self.cookie=cookie.split(';')[0]
  return result
 def login(self):
  r=self.call('POST','/auth/login',json={'email':self.email,'password':password});assert r.status_code==200,r.text

ready();students=[]
for who in ('a','b'):
 s=Student('ci-'+who+'@example.test');invite=seed(s.email)
 assert s.call('POST','/auth/register',json={'email':s.email,'password':password,'invite':invite}).status_code==200
 s.login();students.append(s)
a,b=students;assert a.call('GET','/me').json()['owner_id']!=b.call('GET','/me').json()['owner_id']
assert a.call('GET','/registry').json()['course_id']=='ap-physics-c-mechanics-2026-27'
assert a.call('GET','/sets').json()==[]
assert a.call('GET','/admin/questions').status_code==403
assert httpx.get(origin+'/data/course.json').status_code==404

for filename in ('v4-no-key.pdf','v4-mixed.docx'):
 path=Path('tests/fixtures')/filename
 r=a.call('POST','/papers/import',data={'request_key':secrets.token_hex(8),'duration_minutes':1},files={'file':(filename,path.read_bytes())});assert r.status_code==200,r.text;bid=r.json()['batch_id']
 for _ in range(90):
  rows=a.call('GET','/papers/imports').json();job=next(x for x in rows if x['batch_id']==bid)
  if job['status'] in ('completed','failed','partial'):break
  time.sleep(1)
 assert job['status']=='completed',job
 f=job['files'][0];pid=f['paper_id'];url=f"/papers/imports/{bid}/{f['job_id']}/original"
 assert hashlib.sha256(a.call('GET',url).content).digest()==hashlib.sha256(path.read_bytes()).digest()
 assert b.call('GET',url).status_code==404
 review=a.call('GET','/papers/'+pid+'/review').json()
 assert b.call('GET','/papers/'+pid+'/review').status_code==404
 assert a.call('POST','/sessions',json={'mode':'exam','set_id':pid,'request_id':secrets.token_hex(8)}).status_code==422
 r=a.call('POST','/papers/'+pid+'/confirm',json={'expected_revision':review['revision'],'reviewed_versions':{q['question_id']:q['version_id'] for q in review['questions']}});assert r.status_code==200,r.text
 q=review['questions'][0]
 for aid in q['assets']:assert b.call('GET','/assets/'+aid).status_code==404
 r=a.call('POST','/sessions',json={'mode':'exam','set_id':pid,'request_id':secrets.token_hex(8)});assert r.status_code==200,r.text;s=r.json()
 assert b.call('GET','/sessions/'+s['id']).status_code==404
 r=a.call('POST','/sessions/'+s['id']+'/commands',json={'type':'answer','question_id':q['question_id'],'option':q['options'][0]['label']});assert r.status_code==200,r.text
 result=a.call('POST','/sessions/'+s['id']+'/commands',json={'type':'submit'}).json()
 assert result['status']=='submitted'
 if filename=='v4-no-key.pdf':assert result['grade']['records'][0]['status']=='ungraded'
 assert a.call('POST','/sessions/'+s['id']+'/commands',json={'type':'submit'}).json()['grade_id']==result['grade_id']
 last=s['id'];last_grade=result['grade_id']
assert a.call('POST','/logout').status_code==200
assert a.call('GET','/me').status_code==401
subprocess.run(['docker','restart',container],check=True,stdout=subprocess.DEVNULL);ready();a.login()
assert a.call('GET','/sessions/'+last).json()['grade_id']==last_grade
assert b.call('GET','/sessions/'+last).status_code==404
print(json.dumps({'real_http':True,'pdf':True,'docx':True,'background_queue':True,'private_review':True,'exam_submit':True,'ungraded_without_key':True,'restart_persistence':True,'relogin':True,'two_students_isolated':True,'tls_browser_acceptance':False}))
