"""Explicit isolated QA adapter for the managed preview daemon, never the local launcher."""
import argparse,json,os,secrets,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'as-v3-reference')]
p=argparse.ArgumentParser();p.add_argument('--host',default='127.0.0.1');p.add_argument('--port',type=int,default=4173);p.add_argument('--strictPort',action='store_true');args=p.parse_args()
if os.environ.get('SITES_MANAGED_LINUX_CONTAINER')!='1':raise SystemExit('Managed preview only. Use npm start for local development.')
root=ROOT/'runtime/managed-preview';root.mkdir(parents=True,exist_ok=True);identity=root/'preview-access.json'
if identity.exists():token=json.loads(identity.read_text())['token']
else:token=secrets.token_urlsafe(32);identity.write_text(json.dumps({'token':token}));identity.chmod(0o600)
os.environ['GMF_AUTH_MODE']='token'
from backend.app import create_app
from fastapi import Request
from fastapi.responses import HTMLResponse,RedirectResponse
import uvicorn
app=create_app(root,tokens={token:{'owner_id':'managed-qa','role':'admin'}})
# Explicit fixture identity; neither these routes nor its token exist in backend.app.
@app.get('/qa-preview')
def qa_entry():return HTMLResponse('<!doctype html><meta charset="utf-8"><title>GiveMeFive 隔离验收</title><h1>GiveMeFive 隔离验收</h1><p>只使用独立 QA 数据，不访问正式学习数据。</p><form method="post"><button>进入隔离验收环境</button></form>')
@app.post('/qa-preview')
def qa_login(request:Request):
 response=RedirectResponse('/',status_code=303);response.set_cookie(app.state.auth_cookie_name,token,httponly=True,samesite='strict',secure=request.url.scheme=='https',max_age=3600,path='/');return response
app.router.routes=app.router.routes[-2:]+app.router.routes[:-2]
uvicorn.run(app,host=args.host,port=args.port)
