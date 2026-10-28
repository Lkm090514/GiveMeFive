import importlib.util,json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from backend.app import create_app

ROOT=Path(__file__).resolve().parents[1]

def local(tmp_path,clock=lambda:1800000000):
 app=create_app(tmp_path,clock=clock,worker=False)
 return app,TestClient(app,base_url='http://localhost:4178',client=('127.0.0.1',55100))

def bearer(app):return {'Authorization':'Bearer '+next(iter(app.state.tokens))}
def grant(app,client):
 result=client.post('/api/v4/local-launch',headers=bearer(app));assert result.status_code==200
 return result.json()['login_path'].split('#launch=')[1]

def test_local_identity_required_and_one_use_launcher_ticket(tmp_path):
 app,c=local(tmp_path)
 assert c.get('/api/v4/health').json()['startup_protocol']==2
 for path in ['/api/v4/me','/api/v4/registry','/api/v4/questions','/api/v4/sets','/api/v4/papers/imports','/api/v4/sessions']:
  r=c.get(path);assert r.status_code==401;assert r.json()['detail']['code']=='auth_required'
 assert c.post('/api/v4/local-launch').status_code==401
 ticket=grant(app,c)
 assert ticket not in app.state.tokens
 r=c.post('/api/v4/login',json={'ticket':ticket});assert r.status_code==200
 cookie=r.headers['set-cookie'];assert 'HttpOnly' in cookie and 'Max-Age=1209600' in cookie and 'Path=/' in cookie and 'SameSite=strict' in cookie
 assert c.get('/api/v4/me').json()['owner_id']=='local-owner'
 for path in ['/api/v4/registry','/api/v4/questions','/api/v4/sets','/api/v4/papers/imports','/api/v4/sessions']:
  assert c.get(path).status_code==200
 assert c.post('/api/v4/local-launch',headers={'X-GMF-Request':'1'}).status_code==403
 assert c.post('/api/v4/login',json={'ticket':ticket}).status_code==401
 assert c.post('/api/v4/logout',headers={'X-GMF-Request':'1'}).status_code==200
 assert c.get('/api/v4/me').status_code==401

def test_expired_ticket_and_cookie_are_not_accepted(tmp_path):
 clock=[1800000000];app,c=local(tmp_path,lambda:clock[0]);ticket=grant(app,c);clock[0]+=301
 assert c.post('/api/v4/login',json={'ticket':ticket}).status_code==401
 c.cookies.set(app.state.auth_cookie_name,'invalid')
 result=c.get('/api/v4/me');assert result.status_code==401;assert result.json()['detail']['code']=='auth_expired'
 assert c.get('/local-login').status_code==200
 assert 'local-access' not in c.get('/local-login').text
 assert c.get('/local-login').headers['cache-control']=='no-store'
 assert c.get('/runtime/v4/local-access.json').status_code==404

def test_restart_preserves_identity_cookie_and_invalidates_unused_ticket(tmp_path):
 app,c=local(tmp_path);ticket=grant(app,c);unused=grant(app,c)
 assert c.post('/api/v4/login',json={'ticket':ticket}).status_code==200
 cookie=c.cookies.get(app.state.auth_cookie_name);before=(tmp_path/'local-access.json').read_bytes()
 restarted,other=local(tmp_path);other.cookies.set(restarted.state.auth_cookie_name,cookie)
 assert other.get('/api/v4/me').json()['owner_id']=='local-owner'
 assert (tmp_path/'local-access.json').read_bytes()==before
 assert other.post('/api/v4/login',json={'ticket':unused}).status_code==401
 assert other.post('/api/v4/login',json={'ticket':grant(restarted,other)}).status_code==200

def test_loopback_bootstrap_and_canonical_browser_host(tmp_path):
 app,c=local(tmp_path)
 external=TestClient(app,base_url='http://localhost:4178',client=('203.0.113.3',50000))
 assert external.post('/api/v4/local-launch',headers=bearer(app)).status_code==403
 ip=TestClient(app,base_url='http://127.0.0.1:4178',client=('127.0.0.1',55101))
 r=ip.get('/assessment/?course_id=x',follow_redirects=False)
 assert r.status_code==307 and r.headers['location']=='http://localhost:4178/assessment/?course_id=x'
 assert ip.get('/api/v4/me',headers=bearer(app)).status_code==200
 secure=TestClient(app,base_url='https://localhost',client=('127.0.0.1',55102))
 r=secure.post('/api/v4/login',json={'token':next(iter(app.state.tokens))});assert 'Secure' in r.headers['set-cookie']

def test_configured_auth_has_no_generated_local_admin_or_bootstrap(tmp_path,monkeypatch):
 monkeypatch.setenv('GMF_AUTH_MODE','token')
 tokens={'student-key':{'owner_id':'separate-student','role':'student'}}
 app=create_app(tmp_path,tokens=tokens,worker=False);c=TestClient(app,base_url='http://localhost',client=('127.0.0.1',1))
 assert not (tmp_path/'local-access.json').exists()
 assert c.get('/api/v4/health').json()['auth_mode']=='token'
 assert c.post('/api/v4/local-launch',headers={'Authorization':'Bearer student-key'}).status_code==403
 assert c.get('/api/v4/admin/questions',headers={'Authorization':'Bearer student-key'}).status_code==403
 monkeypatch.setenv('GMF_AUTH_MODE','production')
 with pytest.raises(RuntimeError,match='邮箱账号'):create_app(tmp_path/'production',worker=False)

def test_launcher_reuses_only_the_expected_ready_service(tmp_path,monkeypatch):
 spec=importlib.util.spec_from_file_location('local_launcher',ROOT/'scripts/run-v4.py');runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(runner)
 app,c=local(tmp_path);health=c.get('/api/v4/health').json()
 monkeypatch.setattr(runner,'call',lambda origin,path,token=None:health)
 assert runner.running_service('http://localhost:4178',tmp_path)
 with pytest.raises(RuntimeError,match='另一份项目'):runner.running_service('http://localhost:4178',tmp_path/'other')
 monkeypatch.setattr(runner,'call',lambda origin,path,token=None:{'version':'4.1.0'})
 with pytest.raises(RuntimeError,match='旧版服务'):runner.running_service('http://localhost:4178',tmp_path)

def test_launcher_printed_link_is_distinct_from_auto_opened_link(tmp_path,monkeypatch,capsys):
 spec=importlib.util.spec_from_file_location('local_launcher',ROOT/'scripts/run-v4.py');runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(runner)
 app,c=local(tmp_path);opened=[]
 monkeypatch.setattr(runner,'call',lambda origin,path,token=None:c.post(path,headers={'Authorization':'Bearer '+token}).json())
 monkeypatch.setattr(runner.webbrowser,'open',lambda url:opened.append(url))
 url=runner.initialize_browser('http://localhost:4178',tmp_path,True)
 assert url!=opened[0]
 assert next(iter(app.state.tokens)) not in capsys.readouterr().out
 for target in [url,opened[0]]:assert c.post('/api/v4/login',json={'ticket':target.split('#launch=')[1]}).status_code==200
 assert json.loads((tmp_path/'last-launch.json').read_text())['url']==url

def test_two_local_projects_do_not_overwrite_each_others_browser_cookies(tmp_path):
 first,a=local(tmp_path/'main');second,b=local(tmp_path/'qa')
 assert first.state.auth_cookie_name!=second.state.auth_cookie_name
 assert a.post('/api/v4/login',json={'ticket':grant(first,a)}).status_code==200
 b.cookies.update(a.cookies)
 assert b.get('/api/v4/me').status_code==401
 assert b.post('/api/v4/login',json={'ticket':grant(second,b)}).status_code==200
 a.cookies.update(b.cookies)
 assert a.get('/api/v4/me').status_code==200
 assert b.get('/api/v4/me').status_code==200
 # Valid legacy cookies migrate once; foreign legacy cookies cannot authorize this database.
 legacy=TestClient(first,base_url='http://localhost:4178',client=('127.0.0.1',1));legacy.cookies.set('gmf_session',next(iter(first.state.tokens)))
 assert legacy.get('/api/v4/me').status_code==200
 assert legacy.cookies.get(first.state.auth_cookie_name)
 foreign=TestClient(first,base_url='http://localhost:4178',client=('127.0.0.1',1));foreign.cookies.set('gmf_session',next(iter(second.state.tokens)))
 assert foreign.get('/api/v4/me').status_code==401
