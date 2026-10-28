"""Backend-only module API, not an exam UI. No credentials are sent to a browser."""
from __future__ import annotations
import hmac
import json
import os
import tempfile
from pathlib import Path
from typing import Annotated, Literal

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import Field
from .contracts import Contract, Option, QuestionClassification
from .service import Modules
from .store import ConflictError


class Principal(Contract):
    owner_id:str
    role:Literal["admin","student","integration"]


class ReviewRequest(Contract):
    label:str=Field(pattern=r"^[A-H]$")
    reason:str=Field(min_length=1,max_length=4000)
    expected_revision:int=Field(ge=0)


class EditRequest(Contract):
    expected_version:str
    stem:str=Field(min_length=1)
    options:list[Option]


class RightsRequest(Contract):
    license_name:str=Field(min_length=1)
    reuse_confirmed:bool


class WorkRequest(Contract):
    limit:int=Field(default=20,ge=1,le=20)


def create_app(modules=None,tokens=None):
    modules=modules or Modules(os.getenv("GMF_V3_DATA_DIR","runtime/v3"))
    tokens=tokens if tokens is not None else json.loads(os.getenv("GMF_API_TOKENS","{}"))
    principals={k:Principal.model_validate(v) for k,v in tokens.items()}
    app=FastAPI(title="GiveMeFive V3 integration modules",version="0.2.0",
        description="Backend module workbench. No exam/session/ledger database is opened.")
    app.state.modules=modules

    def auth(authorization:Annotated[str|None,Header()]=None):
        if not principals: raise HTTPException(503,"API tokens are not configured")
        token=(authorization or "").removeprefix("Bearer ")
        if not token: raise HTTPException(401,"Bearer token required")
        for secret,p in principals.items():
            if hmac.compare_digest(secret,token): return p
        raise HTTPException(401,"Invalid token")

    def admin(p=Depends(auth)):
        if p.role!="admin": raise HTTPException(403,"Administrator required")
        return p

    def backend(p=Depends(auth)):
        if p.role not in {"admin","integration"}: raise HTTPException(403,"Backend integration authorization required")
        return p

    def allowed(qid,p):
        try: q=modules.store.question(qid)
        except KeyError: raise HTTPException(404,"Question not found")
        if q.scope=="exam_private" and q.owner_id!=p.owner_id: raise HTTPException(404,"Question not found")
        if q.scope=="bank" and q.publication!="approved" and p.role!="admin": raise HTTPException(404,"Question not found")
        return q

    @app.exception_handler(ConflictError)
    async def conflict(request,exc):
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=409,content={"detail":str(exc)})

    @app.exception_handler(ValueError)
    async def value_error(request,exc):
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=422,content={"detail":str(exc)[:200]})

    @app.get("/health")
    def health(): return {"status":"ok","module_version":"0.2.0","integration":"pending-AS-V2-source"}

    async def import_files(files,scope,p,license_name=None,reuse_confirmed=False,defer=False):
        if len(files)>20: raise HTTPException(413,"Maximum 20 PDFs per batch")
        with tempfile.TemporaryDirectory() as temp:
            paths=[]
            for i,f in enumerate(files):
                name=Path(f.filename or "input.pdf").name
                dest=Path(temp)/str(i)/name
                dest.parent.mkdir()
                count=0
                with dest.open("wb") as out:
                    while block:=await f.read(1024*1024):
                        count+=len(block)
                        if count>50*1024*1024: raise HTTPException(413,"PDF exceeds 50 MiB")
                        out.write(block)
                paths.append(dest)
            # CPU-heavy extraction runs off the event loop; synchronous result is durable before response.
            from starlette.concurrency import run_in_threadpool
            method=modules.enqueue_import if defer else modules.import_pdfs
            return await run_in_threadpool(method,paths,scope=scope,owner_id=p.owner_id,
                license_name=license_name,reuse_confirmed=reuse_confirmed)

    @app.post("/v1/imports/exam")
    async def import_exam(files:list[UploadFile]=File(...),defer:bool=Form(False),p=Depends(auth)):
        b=await import_files(files,"exam_private",p,defer=defer)
        # Never return labels, raw source text or solution evidence through the student endpoint.
        return {"batch_id":b.batch_id,"status":b.status,"files":[{k:v for k,v in f.items() if k!="answer_states"} for f in b.files]}

    @app.post("/v1/imports/bank")
    async def import_bank(files:list[UploadFile]=File(...),license_name:str|None=Form(None),reuse_confirmed:bool=Form(False),defer:bool=Form(False),p=Depends(admin)):
        return await import_files(files,"bank",p,license_name,reuse_confirmed,defer)

    @app.get("/v1/batches/{bid}")
    def batch(bid:str,p=Depends(auth)):
        try: b=modules.store.batch(bid)
        except KeyError: raise HTTPException(404,"Batch not found")
        if b.owner_id!=p.owner_id or (b.scope=="bank" and p.role!="admin"): raise HTTPException(404,"Batch not found")
        result=b.model_dump()
        if p.role=="student":
            result["files"]=[{k:v for k,v in f.items() if k!="answer_states"} for f in result["files"]]
        return result

    @app.post("/v1/batches/{bid}/retry")
    def retry_batch(bid:str,p=Depends(auth)):
        try:b=modules.store.batch(bid)
        except KeyError:raise HTTPException(404,"Batch not found")
        if b.owner_id!=p.owner_id or (b.scope=="bank" and p.role!="admin"):raise HTTPException(404,"Batch not found")
        result=modules.jobs.retry(bid).model_dump()
        if p.role=="student":result["files"]=[{k:v for k,v in f.items() if k!="answer_states"} for f in result["files"]]
        return result

    @app.post("/v1/jobs/work")
    def work(req:WorkRequest,p=Depends(admin)):
        results=modules.jobs.work(limit=req.limit)
        return {"processed":len(results),"status_counts":{s:sum(r["status"]==s for r in results) for s in {r["status"] for r in results}}}

    @app.get("/v1/answers/changes")
    def answer_changes(p=Depends(backend)):
        return modules.store.answer_changes(owner_id=p.owner_id,include_bank=p.role=="admin")

    @app.post("/v1/answers/changes/{change_id}/ack")
    def ack_change(change_id:str,p=Depends(backend)):
        try:modules.store.acknowledge_change(change_id,owner_id=p.owner_id,include_bank=p.role=="admin")
        except KeyError:raise HTTPException(404,"Change not found")
        return {"acknowledged":True}

    @app.get("/v1/questions")
    def questions(scope:Literal["bank","exam_private"]="bank",text:str="",knowledge:str|None=None,method:str|None=None,answer_status:str|None=None,limit:int=100,offset:int=0,p=Depends(auth)):
        rows=modules.store.list_questions(scope=scope,owner_id=p.owner_id,include_drafts=p.role=="admin",text=text,knowledge=knowledge,method=method,answer_status=answer_status,limit=max(1,min(limit,500)),offset=max(0,offset))
        return [modules.public_question(q.question_id) for q,v,c,a in rows]

    @app.get("/v1/questions/{qid}")
    def question(qid:str,p=Depends(auth)):
        allowed(qid,p)
        return modules.public_question(qid)

    @app.get("/v1/questions/{qid}/similar")
    def similar(qid:str,seen:str="",p=Depends(auth)):
        q=allowed(qid,p)
        return modules.store.similar(q.current_version_id,seen_ids=seen.split(",") if seen else ())

    @app.patch("/v1/questions/{qid}")
    def edit(qid:str,req:EditRequest,p=Depends(admin)):
        allowed(qid,p)
        return modules.store.revise(qid,expected_version=req.expected_version,stem=req.stem,options=req.options)

    @app.put("/v1/questions/{qid}/classification")
    def classification(qid:str,req:QuestionClassification,p=Depends(admin)):
        q=allowed(qid,p)
        if req.version_id!=q.current_version_id: raise ConflictError("classification version changed")
        if req.external.confirmed: raise ValueError("canonical linkage requires an AS registry adapter")
        # Server controls provenance and reviewed status; never trusts the submitted producer.
        cls=req.model_copy(update={"producer":"human:"+p.owner_id,"reviewed":True})
        modules.store.save_classification(cls)
        return cls

    @app.post("/v1/questions/{qid}/classify")
    def model_classification(qid:str,p=Depends(admin)):
        q=allowed(qid,p)
        try: return modules.classify_with_model(q.current_version_id)
        except RuntimeError: raise HTTPException(503,"Model classification is not configured or unavailable")

    @app.put("/v1/documents/{did}/rights")
    def rights(did:str,req:RightsRequest,p=Depends(admin)):
        return modules.store.review_source(did,reviewer=p.owner_id,**req.model_dump())

    @app.post("/v1/documents/{did}/docling")
    def docling(did:str,p=Depends(admin)):
        try:source=modules.store.source(did)
        except KeyError:raise HTTPException(404,"Document not found")
        if source.scope=="exam_private" and source.owner_id!=p.owner_id:raise HTTPException(404,"Document not found")
        try:return modules.enrich_docling(did)
        except RuntimeError:raise HTTPException(503,"Docling is optional and not available in this runtime")

    @app.post("/v1/questions/{qid}/solve")
    def solve(qid:str,p=Depends(backend)):
        q=allowed(qid,p)
        return modules.answers.solve(q.current_version_id)

    @app.get("/v1/questions/{qid}/answers")
    def answers(qid:str,p=Depends(backend)):
        q=allowed(qid,p)
        return {"history":modules.store.answer_history(q.current_version_id),"evidence":modules.store.evidence(q.current_version_id)}

    @app.post("/v1/questions/{qid}/confirm-answer")
    def confirm(qid:str,req:ReviewRequest,p=Depends(admin)):
        q=allowed(qid,p)
        return modules.answers.confirm(q.current_version_id,reviewer=p.owner_id,**req.model_dump())

    @app.post("/v1/questions/{qid}/approve")
    def approve(qid:str,expected_version:str,p=Depends(admin)):
        allowed(qid,p)
        return modules.store.approve(qid,reviewer=p.owner_id,expected_version=expected_version)

    @app.get("/v1/assets/{aid}")
    def asset(aid:str,p=Depends(backend)):
        try: a=modules.store.asset(aid);s=modules.store.source(a.document_id)
        except KeyError: raise HTTPException(404,"Asset not found")
        if s.scope=="exam_private" and s.owner_id!=p.owner_id: raise HTTPException(404,"Asset not found")
        file=(modules.assets/a.relative_path).resolve()
        if not file.is_relative_to(modules.assets.resolve()): raise HTTPException(404,"Asset not found")
        return FileResponse(file,media_type=a.media_type,headers={"Cache-Control":"private, no-store"})

    return app

