import argparse,json,os
from pathlib import Path
from .service import Modules


def main():
    p=argparse.ArgumentParser(description="GiveMeFive pre-integration modules; never opens the existing exam database")
    p.add_argument("--data",default=os.getenv("GMF_V3_DATA_DIR","runtime/v3"))
    sub=p.add_subparsers(dest="cmd",required=True)
    i=sub.add_parser("import");i.add_argument("pdf",nargs="+");i.add_argument("--scope",choices=["bank","exam_private"],required=True)
    i.add_argument("--owner",required=True);i.add_argument("--license");i.add_argument("--reuse-confirmed",action="store_true")
    i.add_argument("--no-solve",action="store_true");i.add_argument("--layout",choices=["auto","single","two-column"],default="auto")
    i.add_argument("--pages",help="1-based inclusive, e.g. 100:105")
    i.add_argument("--enqueue",action="store_true",help="Persist input and defer processing to work")
    w=sub.add_parser("work");w.add_argument("--limit",type=int,default=20);w.add_argument("--batch")
    b=sub.add_parser("batch");b.add_argument("batch_id")
    b=sub.add_parser("retry-batch");b.add_argument("batch_id")
    q=sub.add_parser("search");q.add_argument("--text",default="");q.add_argument("--scope",choices=["bank","exam_private"],default="bank");q.add_argument("--owner");q.add_argument("--drafts",action="store_true");q.add_argument("--knowledge");q.add_argument("--method")
    s=sub.add_parser("solve");s.add_argument("question_id");s.add_argument("--force",action="store_true")
    s=sub.add_parser("similar");s.add_argument("question_id");s.add_argument("--drafts",action="store_true")
    c=sub.add_parser("confirm");c.add_argument("question_id");c.add_argument("label");c.add_argument("--reviewer",required=True);c.add_argument("--reason",required=True);c.add_argument("--revision",required=True,type=int)
    c=sub.add_parser("approve");c.add_argument("question_id");c.add_argument("--reviewer",required=True)
    sub.add_parser("serve")
    a=p.parse_args()
    m=Modules(a.data)
    if a.cmd=="import":
        pages=tuple(map(int,a.pages.split(":"))) if a.pages else None
        method=m.enqueue_import if a.enqueue else m.import_pdfs
        result=method(a.pdf,scope=a.scope,owner_id=a.owner,license_name=a.license,reuse_confirmed=a.reuse_confirmed,
            auto_solve=not a.no_solve,layout=a.layout,page_range=pages).model_dump()
    elif a.cmd=="work":result=m.jobs.work(limit=a.limit,batch_id=a.batch)
    elif a.cmd=="batch":result=m.store.batch(a.batch_id).model_dump()
    elif a.cmd=="retry-batch":result=m.jobs.retry(a.batch_id).model_dump()
    elif a.cmd=="search":
        result=[{"question":q.model_dump(),"content":v.model_dump(),"classification":c.model_dump(),"answer":ans.model_dump() if ans else None}
            for q,v,c,ans in m.store.list_questions(scope=a.scope,owner_id=a.owner,include_drafts=a.drafts,text=a.text,knowledge=a.knowledge,method=a.method)]
    elif a.cmd in {"solve","similar","confirm","approve"}:
        q=m.store.question(a.question_id)
        if a.cmd=="solve": result=m.answers.solve(q.current_version_id,force=a.force).model_dump()
        elif a.cmd=="similar": result=m.store.similar(q.current_version_id,include_drafts=a.drafts)
        elif a.cmd=="confirm": result=m.answers.confirm(q.current_version_id,label=a.label,reviewer=a.reviewer,reason=a.reason,expected_revision=a.revision).model_dump()
        else: result=m.store.approve(q.question_id,reviewer=a.reviewer,expected_version=q.current_version_id).model_dump()
    elif a.cmd=="serve":
        import uvicorn
        from .api import create_app
        uvicorn.run(create_app(m),host="127.0.0.1",port=8765)
        return
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=="__main__": main()
