from __future__ import annotations
import hashlib,hmac,json,os,secrets,tempfile,threading,time
from pathlib import Path
from typing import Annotated
from fastapi import Depends,FastAPI,File,Form,Header,HTTPException,Request,Response,UploadFile
from fastapi.responses import FileResponse,HTMLResponse,JSONResponse,RedirectResponse
from fastapi.staticfiles import StaticFiles
from gmf_v3.contracts import Option,Question,uid,now
from gmf_v3.store import ConflictError
from .bank import Bank,ROOT
from .sessions import Sessions
from .local_auth import load_local_tokens,LaunchTickets,COOKIE_SECONDS,data_instance,loopback_request

def create_app(root=None,tokens=None,clock=time.time,worker=True):
 root=Path(root or os.getenv('GMF_DATA_DIR',ROOT/'runtime/v4')).resolve();bank=Bank(root);sessions=Sessions(bank,clock)
 mode=os.getenv('GMF_AUTH_MODE','local')
 if mode not in ('local','token','qa'):raise RuntimeError('此版本尚未接入正式邮箱账号认证；不能将本地开发登录用于正式部署。')
 qa=os.getenv('GMF_QA_FIXTURE')=='1'
 if qa and mode!='qa':raise RuntimeError('固定 QA 身份只能在 GMF_AUTH_MODE=qa 的独立验收环境中启用。')
 local_bootstrap=tokens is None and not os.getenv('GMF_API_TOKENS') and mode=='local' and not qa
 if qa and tokens is None:tokens={'preview-fixture-admin':{'owner_id':'qa-admin','role':'admin'},'preview-fixture-student':{'owner_id':'qa-student','role':'student'}}
 if tokens is None:
  if os.getenv('GMF_API_TOKENS'):tokens=json.loads(os.environ['GMF_API_TOKENS'])
  elif local_bootstrap:tokens=load_local_tokens(root)
  else:raise RuntimeError('独立认证模式需要明确配置身份提供方；不会自动生成本机管理员身份。')
 cookie_name="gmf_session_"+data_instance(root)
 tickets=LaunchTickets(clock)
 app=FastAPI(title='GiveMeFive Fusion + Assessment V4.1',version='4.1.0');app.state.bank=bank;app.state.sessions=sessions;app.state.tokens=tokens;app.state.auth_cookie_name=cookie_name
 running=threading.Event();running.set();import_lock=threading.Lock()
 def auth(request:Request,authorization:Annotated[str|None,Header()]=None):
  token=(authorization or '').removeprefix('Bearer ') or request.cookies.get(cookie_name) or request.cookies.get('gmf_session','')
  principal=next((p for k,p in tokens.items() if token and hmac.compare_digest(token,k)),None)
  if not principal:raise HTTPException(401,{'code':'auth_expired' if authorization or request.cookies.get(cookie_name) else 'auth_required','message':'登录状态已失效。请重新运行统一启动器。' if authorization or request.cookies.get(cookie_name) else '尚未登录。请双击项目根目录 Start-GiveMeFive.cmd，再使用它提供的登录入口。'})
  if request.method not in ['GET','HEAD','OPTIONS'] and not authorization and request.headers.get('x-gmf-request')!='1':raise HTTPException(403,'Missing same-origin request header')
  if not authorization and not request.cookies.get(cookie_name):request.state.migrate_local_cookie=token
  return principal
 def admin(p=Depends(auth)):
  if p['role']!='admin':raise HTTPException(403,'Administrator required')
  return p
 @app.middleware('http')
 async def security(request,call_next):
  if local_bootstrap and request.method=='GET' and not request.url.path.startswith('/api/') and request.url.hostname in ('127.0.0.1','::1'):
   return RedirectResponse(str(request.url.replace(netloc='localhost'+(':'+str(request.url.port) if request.url.port else ''))),status_code=307)
  response=await call_next(request)
  if getattr(request.state,'migrate_local_cookie',None):response.set_cookie(cookie_name,request.state.migrate_local_cookie,httponly=True,samesite='strict',secure=request.url.scheme=='https',max_age=COOKIE_SECONDS,path='/')
  if request.url.path.endswith(('.js','.mjs','.html')):response.headers['Cache-Control']='no-cache'
  if request.url.path=='/local-login':response.headers['Cache-Control']='no-store';response.headers['Referrer-Policy']='no-referrer'
  if request.url.path.startswith('/api/'):
   response.headers['Cache-Control']='private, no-store';response.headers['X-Content-Type-Options']='nosniff'
  return response
 @app.exception_handler(ValueError)
 async def bad(request,exc):return JSONResponse(status_code=422,content={'detail':str(exc)[:300]})
 @app.exception_handler(ConflictError)
 async def conflict(request,exc):return JSONResponse(status_code=409,content={'detail':str(exc)[:300]})
 @app.exception_handler(KeyError)
 async def missing(request,exc):return JSONResponse(status_code=404,content={'detail':'Record not found'})
 @app.get('/api/v4/health')
 def health():return {'service':'givemefive-python','startup_protocol':2,'data_instance':data_instance(root),'auth_mode':'local' if local_bootstrap else ('qa' if qa else 'token'),'version':'4.1.0','persistence':'sqlite-v3+v4','time':sessions.ms(),'auth':'local-token-development' if local_bootstrap else 'configured-token','cloud_sync':False,'ai_enabled':False}
 @app.post('/api/v4/local-launch')
 def local_launch(request:Request,p=Depends(auth)):
  if not local_bootstrap or not loopback_request(request):raise HTTPException(403,'Local launcher is disabled for this environment')
  token=request.headers.get('authorization','').removeprefix('Bearer ')
  if token not in tokens:raise HTTPException(403,'The launcher requires its local credential file')
  return {'login_path':'/local-login#launch='+tickets.issue(token),'expires_in':300}
 @app.post('/api/v4/login')
 async def login(request:Request,response:Response):
  data=await request.json();token=data.get('token','')
  if 'ticket' in data:
   token=tickets.consume(data['ticket']) if local_bootstrap and loopback_request(request) else None
  principal=next((p for k,p in tokens.items() if isinstance(token,str) and hmac.compare_digest(token,k)),None)
  if not principal:raise HTTPException(401,{'code':'auth_expired','message':'登录链接已失效或已使用。请重新运行 Start-GiveMeFive.cmd 获取新入口。'})
  response.set_cookie(cookie_name,token,httponly=True,samesite='strict',secure=request.url.scheme=='https',max_age=COOKIE_SECONDS,path='/');return {'role':principal['role'],'owner_id':principal['owner_id']}
 @app.post('/api/v4/logout')
 def logout(response:Response,p=Depends(auth)):response.delete_cookie(cookie_name,path='/');response.delete_cookie('gmf_session',path='/');return {'ok':True}
 @app.get('/api/v4/me')
 def me(p=Depends(auth)):return {**p,'server_now':sessions.ms()}
 @app.get('/api/v4/registry')
 def registry(p=Depends(auth)):return bank.registry()
 @app.get('/api/v4/library')
 def library(p=Depends(auth)):
  from .library import inventory
  return inventory(bank,p['owner_id'])
 @app.get('/api/v4/library/{did}/original')
 def library_original(did:str,p=Depends(auth)):
  from .library import private_document
  source=private_document(bank,p['owner_id'],did)
  path=bank.assets/did/'original.pdf'
  if not path.is_file():raise HTTPException(404)
  return FileResponse(path,media_type='application/pdf',filename=source.filename)
 @app.get('/api/v4/questions')
 def questions(course_id:str|None=None,unit_id:str|None=None,topics:str='',comprehensive:bool=False,p=Depends(auth)):
  rows=bank.candidates(course_id,unit_id,[x for x in topics.split(',') if x],comprehensive,owner_id=p['owner_id'] if (topics.strip() or unit_id is not None) else None)
  return [{'question_id':q.question_id,'source_number':q.source_number,'topics':bank.public(q.question_id)['topics']} for q,v,a in rows]
 @app.get('/api/v4/sets')
 def sets(p=Depends(auth)):
  with bank.store.connect() as c:rows=[json.loads(r[0]) for r in c.execute('SELECT payload FROM v4_sets')]
  return [{k:v for k,v in s.items() if k not in ['version_ids','answer_ids','question_ids']}|{'question_count':len(s['question_ids'])} for s in rows if s.get('published') and (not s.get('owner_id') or s['owner_id']==p['owner_id'])]
 @app.get('/api/v4/papers/imports')
 def own_imports(p=Depends(auth)):
  with bank.store.connect() as c:ids=[r[0] for r in c.execute("SELECT b.batch_id FROM import_batches b WHERE b.scope='exam_private' AND b.owner_id=? AND NOT EXISTS (SELECT 1 FROM v4_import_archives a WHERE a.batch_id=b.batch_id AND a.owner_id=b.owner_id) ORDER BY b.rowid DESC",(p['owner_id'],))]
  return [{'batch_id':b.batch_id,'status':b.status,'files':[{k:v for k,v in f.items() if k not in ['answer_states','solve_errors']} for f in b.files]} for b in [bank.store.batch(i) for i in ids]]
 @app.post('/api/v4/papers/import')
 async def own_import(file:UploadFile=File(...),request_key:str=Form(...),title:str=Form('我的试卷'),duration_minutes:float=Form(45),course_id:str=Form('ap-physics-c-mechanics-2026-27'),p=Depends(auth)):
  if any(s['mode']=='exam' and s['status']=='active' for s in sessions.list(p['owner_id'])):raise ValueError('请先完成当前考试')
  name=Path(file.filename or '').name
  if Path(name).suffix.lower()!='.pdf':raise ValueError('请上传 PDF 试卷')
  if course_id!=bank.catalog['course_id']:raise ValueError('请选择现有课程')
  if not 0<duration_minutes<=600 or not title.strip():raise ValueError('请填写试卷名称和考试时长')
  content=await file.read(50*1024*1024+1)
  if len(content)>50*1024*1024:raise HTTPException(413,'PDF 超过 50 MiB')
  if not 1<=len(request_key)<=100:raise ValueError('request_key required')
  sha=hashlib.sha256(content).hexdigest();key='student:'+request_key
  with import_lock:
   with bank.store.connect() as c:old=c.execute('SELECT * FROM v4_imports WHERE owner_id=? AND request_key=?',(p['owner_id'],key)).fetchone()
   if old:
    if old['file_sha']!=sha:raise ConflictError('请求 ID 已用于其他试卷')
    return {'batch_id':old['batch_id'],'status':bank.store.batch(old['batch_id']).status}
   with tempfile.TemporaryDirectory() as temp:
    path=Path(temp)/name;path.write_bytes(content)
    batch=bank.jobs.enqueue([path],scope='exam_private',owner_id=p['owner_id'],auto_solve=False,paper_title=title,duration_minutes=duration_minutes,course_id=course_id,on_commit=lambda c,b:c.execute('INSERT INTO v4_imports VALUES(?,?,?,?,?)',(p['owner_id'],key,sha,b.batch_id,json.dumps({'filename':name}))))
  return {'batch_id':batch.batch_id,'status':batch.status}
 @app.post('/api/v4/papers/imports/{bid}/retry')
 def retry_own(bid:str,p=Depends(auth)):
  b=bank.store.batch(bid)
  if b.scope!='exam_private' or b.owner_id!=p['owner_id']:raise HTTPException(404)
  bank.jobs.retry(bid);return {'batch_id':bid,'status':'queued'}
 @app.delete('/api/v4/papers/imports/{bid}')
 def archive_own(bid:str,p=Depends(auth)):
  b=bank.store.batch(bid)
  if b.scope!='exam_private' or b.owner_id!=p['owner_id']:raise HTTPException(404)
  if b.status not in ['failed','partial']:raise HTTPException(409,'只能删除已失败的解析任务')
  with bank.store.connect(write=True) as c:c.execute('INSERT OR IGNORE INTO v4_import_archives VALUES(?,?,?)',(p['owner_id'],bid,now()))
  return {'batch_id':bid,'removed_from_list':True,'original_preserved':True}
 @app.get('/api/v4/papers/imports/{bid}/{job_id}/original')
 def own_original(bid:str,job_id:str,p=Depends(auth)):
  b=bank.store.batch(bid)
  if b.scope!='exam_private' or b.owner_id!=p['owner_id']:raise HTTPException(404)
  with bank.store.connect() as c:row=c.execute('SELECT payload FROM import_jobs WHERE batch_id=? AND job_id=?',(bid,job_id)).fetchone()
  if not row:raise HTTPException(404)
  payload=json.loads(row[0]);path=(bank.root/payload['relative_path']).resolve()
  if not path.is_relative_to(bank.root) or not path.is_file():raise HTTPException(404)
  return FileResponse(path,media_type='application/pdf',filename=payload['filename'],content_disposition_type='inline')
 @app.post('/api/v4/sessions')
 def create_session(data:dict,p=Depends(auth)):return sessions.public(sessions.create(p['owner_id'],data))
 @app.get('/api/v4/sessions')
 def list_sessions(p=Depends(auth)):
  rows=sessions.list(p['owner_id']);lock=next((s for s in rows if s['mode']=='exam' and s['status']=='active'),None)
  return {'sessions':[{k:s.get(k) for k in ['id','title','mode','status','started_at','deadline']} for s in rows],'exam_lock':lock['id'] if lock else None,'server_now':sessions.ms()}
 @app.get('/api/v4/sessions/{sid}')
 def session(sid:str,p=Depends(auth)):return sessions.public(sessions.get(p['owner_id'],sid))
 @app.post('/api/v4/sessions/{sid}/commands')
 def command(sid:str,data:dict,p=Depends(auth)):return sessions.public(sessions.mutate(p['owner_id'],sid,data))
 @app.get('/api/v4/mistakes')
 def mistakes(p=Depends(auth)):return sessions.mistakes(p['owner_id'])
 @app.delete('/api/v4/mistakes/{qid}')
 def remove(qid:str,p=Depends(auth)):sessions.remove_wrong(p['owner_id'],qid);return {'removed':True}
 @app.post('/api/v4/learning/uncertain')
 def uncertain(data:dict,p=Depends(auth)):return sessions.reviews.uncertain(p['owner_id'],data.get('record_id'))
 @app.post('/api/v4/learning/{qid}/notes')
 def note(qid:str,data:dict,p=Depends(auth)):return sessions.reviews.note(p['owner_id'],qid,data)
 @app.post('/api/v4/learning/{qid}/images')
 async def note_image(qid:str,file:UploadFile=File(...),p=Depends(auth)):
  return sessions.reviews.image(p['owner_id'],qid,await file.read(4*1024*1024+1))
 @app.get('/api/v4/learning/images/{aid}')
 def learning_image(aid:str,p=Depends(auth)):return FileResponse(sessions.reviews.image_path(p['owner_id'],aid),media_type='image/png')
 @app.get('/api/v4/analysis')
 def analysis(p=Depends(auth)):
  from .topic_analysis import analyze
  return analyze(sessions,p['owner_id'])
 @app.get('/api/v4/sessions/{sid}/analysis')
 def session_analysis(sid:str,p=Depends(auth)):
  from .topic_analysis import analyze
  return analyze(sessions,p['owner_id'],session_id=sid)
 @app.get('/api/v4/sessions/{sid}/ledger')
 def ledger(sid:str,p=Depends(auth)):
  s=sessions.get(p['owner_id'],sid)
  if s['status']!='submitted':return {'events':[],'sessions':[]}
  public=sessions.public(s);at=s['submitted_at'];items=[];course_ids=[];topic_ids=[];unit_ids=[];grading_revision=public['grade']['revision'];suffix=':grading:'+str(grading_revision) if grading_revision>1 else ''
  for r in public['grade']['records']:
   m=bank.meta(r['version_id']);m={**m,'core':r.get('topic_ids',m['core']),'unit_ids':r.get('unit_ids',m['unit_ids']),'course_id':r.get('course_id',m['course_id'])};tid=m['core'][0] if len(m['core'])==1 else None;unit=m['unit_ids'][0] if len(m['unit_ids'])==1 else None;course_ids.append(m['course_id']);topic_ids.append(tid);unit_ids.append(unit)
   items.append({'schema_version':4,'event_id':s['id']+':item:'+r['question_id']+suffix,'session_id':s['id'],'course_id':m['course_id'],'unit_id':unit,'topic_id':tid,'exercise_id':r['question_id'],'source':'Assessment','type':'ASSESSMENT_ITEM_RESULT','occurred_at':now(),'payload':{**r,'grading_revision':grading_revision,'topic_ids':m['core'],'mode':s['mode'],'launch_context':s['context']}})
  one=lambda values:values[0] if values and len(set(values))==1 else None
  summary={'schema_version':4,'event_id':s['id']+':result'+suffix,'session_id':s['id'],'course_id':one(course_ids),'unit_id':one(unit_ids),'topic_id':one(topic_ids),'exercise_id':None,'source':'Assessment','type':'ASSESSMENT','occurred_at':now(),'payload':{'grading_revision':grading_revision,'mode':s['mode'],'answers':public['grade']['records'],'launch_context':s['context'],'active_seconds':s['active_ms']/1000}}
  study={'session_id':s['id'],'course_id':summary['course_id'],'unit_id':summary['unit_id'],'topic_id':summary['topic_id'],'source':'Assessment','mode':'assessment','started_at':__import__('datetime').datetime.fromtimestamp(s['started_at']/1000,__import__('datetime').timezone.utc).isoformat(),'ended_at':__import__('datetime').datetime.fromtimestamp(at/1000,__import__('datetime').timezone.utc).isoformat(),'active_seconds':s['active_ms']/1000,'daily_seconds':{}}
  return {'events':[summary,*items],'sessions':[study]}
 @app.get('/api/v4/assets/{aid}')
 def asset(aid:str,p=Depends(auth)):
  a=bank.store.asset(aid)
  if p['role']!='admin':
   with bank.store.connect() as c:
    metas=[json.loads(r[0]) for r in c.execute("SELECT m.payload FROM v4_meta m JOIN question_versions v ON m.version_id=v.version_id JOIN questions q ON q.question_id=v.question_id WHERE q.scope='bank' AND q.publication='approved'")]
    for row in c.execute("SELECT v.current_version_id FROM questions v WHERE v.scope='exam_private' AND v.owner_id=?",(p['owner_id'],)):metas.append(bank.meta(row[0],c))
    # Historical snapshots retain access even when the current question is withdrawn.
    for r in c.execute('SELECT payload FROM v4_sessions WHERE owner_id=?',(p['owner_id'],)):
     s=json.loads(r[0]);metas.extend(bank.meta(i['version_id'],c) for i in s['items'])
   if a.kind!='question_crop' or not any(aid in [*m.get('safe_assets',[]),*m.get('shared_assets',[])] for m in metas):raise HTTPException(404,'Asset not available')
  file=(bank.assets/a.relative_path).resolve()
  if not file.is_relative_to(bank.assets.resolve()):raise HTTPException(404)
  return FileResponse(file,media_type=a.media_type,headers={'Cache-Control':'private, no-store'})
 @app.get('/api/v4/admin/imports')
 def imports(p=Depends(admin)):
  with bank.store.connect() as c:rows=c.execute("SELECT batch_id FROM import_batches WHERE scope='bank' ORDER BY rowid DESC").fetchall()
  return [bank.store.batch(r[0]).model_dump() for r in rows]
 @app.post('/api/v4/admin/imports')
 async def import_file(request:Request,file:UploadFile=File(...),request_key:str=Form(...),license_name:str=Form('User-supplied'),reuse_confirmed:bool=Form(False),p=Depends(admin)):
  name=Path(file.filename or '').name
  if Path(name).suffix.lower() not in ['.pdf','.docx']:raise ValueError('仅支持 PDF / DOCX')
  if not 1<=len(request_key)<=100:raise ValueError('request_key required')
  data=await file.read(50*1024*1024+1)
  if len(data)>50*1024*1024:raise HTTPException(413,'文件超过 50 MiB')
  sha=hashlib.sha256(data).hexdigest()
  # Serialize request-key reservation with queue creation; persistent idempotency survives restart.
  with import_lock:
   with bank.store.connect() as c:r=c.execute('SELECT * FROM v4_imports WHERE owner_id=? AND request_key=?',(p['owner_id'],request_key)).fetchone()
   if r:
    if r['file_sha']!=sha:raise ConflictError('同一请求 ID 对应不同文件')
    return bank.store.batch(r['batch_id']).model_dump()
   with tempfile.TemporaryDirectory() as temp:
    path=Path(temp)/name;path.write_bytes(data);batch=bank.jobs.enqueue([path],scope='bank',owner_id=p['owner_id'],license_name=license_name,reuse_confirmed=reuse_confirmed,auto_solve=False,on_commit=lambda c,b:c.execute('INSERT INTO v4_imports VALUES(?,?,?,?,?)',(p['owner_id'],request_key,sha,b.batch_id,json.dumps({'filename':name}))))
  return batch.model_dump()
 @app.post('/api/v4/admin/imports/batch')
 async def import_batch(files:list[UploadFile]=File(...),request_key:str=Form(...),license_name:str=Form('User-supplied'),reuse_confirmed:bool=Form(False),p=Depends(admin)):
  if not 1<=len(files)<=20:raise ValueError('每批可上传 1–20 份试卷，可继续添加下一批')
  if not 1<=len(request_key)<=100:raise ValueError('request_key required')
  staged=[];hashes=[];total=0
  with tempfile.TemporaryDirectory() as temp:
   for i,f in enumerate(files):
    name=Path(f.filename or '').name
    if Path(name).suffix.lower() not in ['.pdf','.docx']:raise ValueError('仅支持 PDF / DOCX')
    content=await f.read(50*1024*1024+1);total+=len(content)
    if len(content)>50*1024*1024 or total>300*1024*1024:raise HTTPException(413,'单文件上限 50 MiB，每批上限 300 MiB')
    dest=Path(temp)/str(i)/name;dest.parent.mkdir();dest.write_bytes(content);staged.append(dest);hashes.append(hashlib.sha256(content).hexdigest())
   sha=hashlib.sha256(json.dumps(hashes).encode()).hexdigest()
   with import_lock:
    with bank.store.connect() as c:old=c.execute('SELECT * FROM v4_imports WHERE owner_id=? AND request_key=?',(p['owner_id'],request_key)).fetchone()
    if old:
     if old['file_sha']!=sha:raise ConflictError('请求 ID 已用于其他文件')
     return bank.store.batch(old['batch_id']).model_dump()
    batch=bank.jobs.enqueue(staged,scope='bank',owner_id=p['owner_id'],license_name=license_name,reuse_confirmed=reuse_confirmed,auto_solve=False,on_commit=lambda c,b:c.execute('INSERT INTO v4_imports VALUES(?,?,?,?,?)',(p['owner_id'],request_key,sha,b.batch_id,json.dumps({'file_count':len(staged)}))))
  return batch.model_dump()
 @app.post('/api/v4/admin/imports/{bid}/retry')
 def retry(bid:str,p=Depends(admin)):return bank.jobs.retry(bid)
 @app.post('/api/v4/admin/imports/{bid}/reparse')
 def reparse(bid:str,p=Depends(admin)):
  # Same immutable document/version IDs; does not fork the bank.
  with bank.store.connect(write=True) as c:
   c.execute("UPDATE import_jobs SET status='queued',result=NULL,lease_owner=NULL,lease_until=NULL,max_attempts=attempts+3 WHERE batch_id=? AND status!='running'",(bid,));return bank.jobs._refresh(c,bid)
 @app.post('/api/v4/admin/work')
 def work(p=Depends(admin)):return bank.jobs.work(limit=20)
 @app.get('/api/v4/admin/questions')
 def admin_questions(p=Depends(admin)):
  return [{**bank.public(q.question_id),'publication':q.publication,'document_id':q.document_id,'meta':bank.meta(v.version_id),'answer':a.model_dump() if a else None} for q,v,cls,a in bank.store.list_questions(scope='bank',include_drafts=True,limit=None)]
 @app.get('/api/v4/admin/bank')
 def bank_page(offset:int=0,limit:int=30,course_id:str|None=None,unit_id:str|None=None,topic_id:str|None=None,method:str|None=None,structure:str|None=None,publication:str|None=None,answer:str|None=None,issue:str|None=None,document_id:str|None=None,text:str='',p=Depends(admin)):
  return bank.bank_page(offset=offset,limit=limit,course_id=course_id,unit_id=unit_id,topic_id=topic_id,method=method,structure=structure,publication=publication,answer=answer,issue=issue,document_id=document_id,text=text)
 @app.put('/api/v4/admin/questions/{qid}/types')
 def review_types(qid:str,data:dict,p=Depends(admin)):return bank.review_types(qid,data,p['owner_id'])
 @app.get('/api/v4/admin/questions/{qid}/types')
 def type_history(qid:str,p=Depends(admin)):
  q=bank.store.question(qid)
  if q.scope!='bank':raise HTTPException(404)
  with bank.store.connect() as c:
   return [json.loads(r[0]) for r in c.execute('SELECT r.payload FROM v4_type_reviews r JOIN question_versions v ON r.version_id=v.version_id WHERE v.question_id=? ORDER BY r.rowid',(qid,))]
 @app.put('/api/v4/admin/questions/{qid}/tags')
 def tags(qid:str,data:dict,p=Depends(admin)):
  q=bank.store.question(qid);m=bank.meta(q.current_version_id);valid=bank.validate_tags(data.get('course_id'),data.get('core',[]),data.get('related',[]));bank.save_meta(q.current_version_id,{**m,**valid,'tag_source':'admin:'+p['owner_id']});return {'saved':True}
 @app.post('/api/v4/admin/questions/{qid}/answer')
 def answer(qid:str,data:dict,p=Depends(admin)):
  q=bank.store.question(qid)
  return bank.answers.confirm(q.current_version_id,label=data['label'],reviewer=p['owner_id'],reason=data['reason'],expected_revision=data['expected_revision'])
 @app.patch('/api/v4/admin/questions/{qid}')
 def edit(qid:str,data:dict,p=Depends(admin)):
  old=bank.store.question(qid);meta=bank.meta(old.current_version_id);new=bank.store.revise(qid,expected_version=data['expected_version'],stem=data['stem'],options=[Option.model_validate(o) for o in data['options']]);bank.save_meta(new.version_id,{**meta,'issues_reviewed':False,'issues':list(set(meta.get('issues',[])+['edited_content_visuals_require_review']))});return new
 @app.post('/api/v4/admin/questions/{qid}/publish')
 def publish(qid:str,data:dict,p=Depends(admin)):return bank.publish(qid,p['owner_id'],acknowledge_issues=bool(data.get('acknowledge_issues')))
 @app.post('/api/v4/admin/questions/{qid}/withdraw')
 def withdraw(qid:str,p=Depends(admin)):
  q=bank.store.question(qid).model_copy(update={'publication':'draft'})
  with bank.store.connect(write=True) as c:c.execute("UPDATE questions SET publication='draft',payload=? WHERE question_id=?",(q.model_dump_json(),qid))
  return {'withdrawn':True}
 @app.post('/api/v4/admin/publish-batch/{bid}')
 def publish_batch(bid:str,p=Depends(admin)):
  b=bank.store.batch(bid);published=[];skipped=[]
  for f in b.files:
   for qid in f.get('question_ids',[]):
    try:bank.publish(qid,p['owner_id']);published.append(qid)
    except ValueError as e:skipped.append({'question_id':qid,'reason':str(e)})
  return {'published':published,'skipped':skipped}
 @app.post('/api/v4/admin/sets')
 def create_set(data:dict,p=Depends(admin)):
  ids=data.get('question_ids',[])
  if not ids and data.get('document_id'):
   refs=[q for q,_,_,_ in bank.store.list_questions(scope='bank',limit=None) if q.document_id==data['document_id']]
   refs.sort(key=lambda q:(int(q.source_number) if q.source_number.isdigit() else 99999,q.question_id));ids=[q.question_id for q in refs]
  if not ids or len(ids)>1000 or len(set(ids))!=len(ids):raise ValueError('请选择不重复的已发布 MCQ')
  duration=data.get('duration_minutes');title=data.get('title','').strip()
  if not title or not isinstance(duration,(int,float)) or not 0<duration<=600:raise ValueError('试卷名称和考试时间必填')
  if data.get('section','MCQ')!='MCQ':raise ValueError('Only MCQ sections are supported')
  if data.get('course_id')!=bank.catalog['course_id']:raise ValueError('请选择现有课程')
  questions=[bank.store.question(qid) for qid in ids]
  if any(q.scope!='bank' or q.publication!='approved' for q in questions):raise ValueError('Only published public-bank questions may enter a paper')
  if data.get('document_id') and any(q.document_id!=data['document_id'] for q in questions):raise ValueError('试卷题目必须来自选定的原始试卷')
  s={**data,'source_year':data.get('source_year') or None,'set_id':uid('set'),'question_ids':ids,'version_ids':[q.current_version_id for q in questions],'section':'MCQ','created_by':p['owner_id'],'published':True}
  with bank.store.connect(write=True) as c:c.execute('INSERT INTO v4_sets VALUES(?,?,?)',(s['set_id'],data.get('document_id'),json.dumps(s)))
  return s
 @app.post('/api/v4/admin/sessions/{sid}/regrade')
 def regrade(sid:str,data:dict,p=Depends(admin)):return sessions.regrade(sid,p['owner_id'],data.get('reason',''))
 @app.get('/local-login')
 def local_login():return HTMLResponse('''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>GiveMeFive · 本地登录</title><main style="font:16px/1.8 system-ui;max-width:660px;margin:12vh auto;padding:24px"><h1>GiveMeFive 本地登录</h1><p id="status" role="status">正在验证启动入口…</p><p>请双击项目根目录的 Start-GiveMeFive.cmd。入口仅在本机使用，有效期五分钟；不同浏览器需使用新的入口。</p><a href="/">返回学习路径</a></main><script src="/local-login.js?v=4.1-auth2"></script></html>''')
 @app.get('/local-login.js')
 def local_login_script():return FileResponse(ROOT/'dist/local-login.js',media_type='text/javascript',headers={'Cache-Control':'no-store','Referrer-Policy':'no-referrer'})
 def process():
  while running.is_set():
   try:bank.jobs.work(limit=1)
   except Exception:pass
   running.wait(.2) if not running.is_set() else time.sleep(.2)
 def deadlines():
  while running.is_set():
   try:sessions.expire_due()
   except Exception:pass
   time.sleep(.5)
 if worker:
  threading.Thread(target=process,daemon=True).start()
  threading.Thread(target=deadlines,daemon=True).start()
 @app.on_event('shutdown')
 def shutdown():running.clear()
 if qa:
  @app.get('/qa-preview/{role}')
  def qa_fixture(role:str):
   if role not in ['admin','student']:raise HTTPException(404)
   response=HTMLResponse('<!doctype html><meta charset="utf-8"><p>正在打开隔离的 QA 验收环境…</p><script>location.replace("/assessment/")</script>');response.set_cookie(cookie_name,'preview-fixture-'+role,httponly=True,samesite='strict',path='/');return response
 app.mount('/',StaticFiles(directory=ROOT/'dist',html=True),name='fusion')
 return app
