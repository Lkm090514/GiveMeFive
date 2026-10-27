"""Password-protected isolated QA preview; never an ordinary local launcher."""
import argparse,json,os,secrets,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'as-v3-reference')]
from scripts.preview_auth import matches,require_password
p=argparse.ArgumentParser();p.add_argument('--host',default='127.0.0.1');p.add_argument('--port',type=int,default=4173);p.add_argument('--strictPort',action='store_true');args=p.parse_args()
if os.environ.get('SITES_MANAGED_LINUX_CONTAINER')!='1':raise SystemExit('Managed preview only. Use npm start for local development.')
password=require_password(os.environ.get('GMF_PREVIEW_PASSWORD'))
root=ROOT/'runtime/managed-preview';root.mkdir(parents=True,exist_ok=True);identity=root/'preview-access.json'
if identity.exists():token=json.loads(identity.read_text())['token']
else:token=secrets.token_urlsafe(32);identity.write_text(json.dumps({'token':token}))
identity.chmod(0o600)
os.environ['GMF_AUTH_MODE']='token'
from backend.app import create_app
from fastapi import Request
from fastapi.responses import HTMLResponse,RedirectResponse,JSONResponse
import uvicorn
app=create_app(root,tokens={token:{'owner_id':'managed-qa','role':'admin'}})
LOGIN_HTML='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>GiveMeFive 私人验收</title><body style="font:16px system-ui;max-width:400px;margin:15vh auto;padding:24px"><h1>GiveMeFive</h1><p>私人验收环境 · 请输入访问密码</p><form method="post" action="/qa-preview"><label>访问密码 <input name="password" type="password" autocomplete="current-password" required style="display:block;width:100%;padding:12px;box-sizing:border-box;margin:12px 0"></label><button style="padding:12px 20px">进入预览</button></form></body></html>'''

@app.middleware('http')
async def preview_gate(request:Request,call_next):
    # Protect *all* paths, including static textbook images/JSON. An API-only
    # login would leave Pathline assets publicly downloadable.
    path=request.url.path
    if path!='/qa-preview' or request.method not in ('GET','POST'):
        cookie=request.cookies.get(app.state.auth_cookie_name,'')
        if not cookie or not secrets.compare_digest(cookie,token):
            if request.method in ('GET','HEAD') and 'text/html' in request.headers.get('accept',''):
                return RedirectResponse('/qa-preview',status_code=303)
            return JSONResponse({'detail':'Preview login required'},status_code=401,headers={'Cache-Control':'no-store'})
    response=await call_next(request)
    response.headers['Cache-Control']='private, no-store'
    response.headers['Referrer-Policy']='no-referrer'
    response.headers['X-Content-Type-Options']='nosniff'
    return response

@app.get('/qa-preview')
def qa_entry():return HTMLResponse(LOGIN_HTML)

@app.post('/qa-preview')
async def qa_login(request:Request):
    form=await request.form()
    if not matches(form.get('password'),password):
        return HTMLResponse('<p>访问密码错误。<a href="/qa-preview">返回重试</a></p>',status_code=403,headers={'Cache-Control':'no-store'})
    response=RedirectResponse('/',status_code=303)
    response.set_cookie(app.state.auth_cookie_name,token,httponly=True,samesite='strict',secure=True,max_age=3600,path='/')
    return response

# Keep the QA login before the mounted StaticFiles catch-all route.
app.router.routes=app.router.routes[-2:]+app.router.routes[:-2]
uvicorn.run(app,host=args.host,port=args.port)
