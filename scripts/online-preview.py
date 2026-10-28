"""Isolated managed browser QA of real online login, queue and persistence. Not deployment."""
import argparse,os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'as-v3-reference')]
p=argparse.ArgumentParser();p.add_argument('--port',type=int,default=4173);p.add_argument('--host',default='127.0.0.1');p.add_argument('--strictPort',action='store_true');args=p.parse_args()
if os.environ.get('SITES_MANAGED_LINUX_CONTAINER')!='1':raise SystemExit('Managed isolated QA only')
os.environ.update(GMF_AUTH_MODE='password',GMF_ENV='testing',GMF_PUBLIC_ORIGIN='http://terminal.local:'+str(args.port))
os.environ.pop('GMF_QA_FIXTURE',None);os.environ.pop('GMF_API_TOKENS',None)
from backend.app import create_app
from backend.identity import Identity
import uvicorn
app=create_app(ROOT/'runtime/v43-browser',worker=True);identity=Identity(app.state.bank.store)
for who,password in [('student-a','QA-Student-A-2026!'),('student-b','QA-Student-B-2026!')]:
 email=who+'@qa.invalid'
 with app.state.bank.store.connect() as c:exists=c.execute('SELECT 1 FROM v43_users WHERE email=?',(email,)).fetchone()
 if not exists:identity.register(email,password,identity.invite(email,'student'))
from fastapi.responses import HTMLResponse,RedirectResponse
from fastapi import HTTPException
@app.get('/qa-accounts')
def qa_accounts():
 return HTMLResponse('<h1>隔离后端验收</h1><p>仅内部 QA。两个独立学生账号，不是正式登录入口。</p><a href="/qa-signin/student-a">测试学生 A</a><br><a href="/qa-signin/student-b">测试学生 B</a>')
@app.get('/qa-signin/{who}')
def qa_signin(who:str):
 if who not in ('student-a','student-b'):raise HTTPException(404)
 password={'student-a':'QA-Student-A-2026!','student-b':'QA-Student-B-2026!'}[who]
 token=identity.login(who+'@qa.invalid',password,'managed-browser-fixture')
 response=RedirectResponse('/assessment/',status_code=303);response.set_cookie(app.state.auth_cookie_name,token,httponly=True,samesite='lax',path='/');return response
app.router.routes=app.router.routes[-2:]+app.router.routes[:-2]
uvicorn.run(app,host=args.host,port=args.port,access_log=False)
