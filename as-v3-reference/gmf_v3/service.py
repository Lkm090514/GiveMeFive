"""Application facade for the future AS adapter, CLI and authenticated API."""
from pathlib import Path
from .answers import AnswerEngine
from .contracts import ImportBatch, uid
from .pdf_core import PDFProcessingCore
from .store import Store


class Modules:
    def __init__(self,root="runtime/v3",provider=None,review_provider=None):
        self.root=Path(root).resolve()
        self.root.mkdir(parents=True,exist_ok=True)
        self.assets=self.root/"assets"
        self.store=Store(self.root/"modules.sqlite3")
        self.pdf=PDFProcessingCore(self.assets)
        self.answers=AnswerEngine(self.store,self.assets,provider,review_provider)
        from .jobs import ImportQueue
        self.jobs=ImportQueue(self)

    def enrich_docling(self,did):
        a=self.pdf.enrich_docling(did)
        with self.store.connect(write=True) as c:
            c.execute("INSERT OR IGNORE INTO assets VALUES(?,?,?)",(a.asset_id,a.document_id,a.model_dump_json()))
        return a

    def import_pdfs(self,paths,*,scope,owner_id,source_url=None,license_name=None,reuse_confirmed=False,
                    auto_solve=True,layout="auto",ocr=True,page_range=None):
        batch=self.enqueue_import(paths,scope=scope,owner_id=owner_id,source_url=source_url,license_name=license_name,
            reuse_confirmed=reuse_confirmed,auto_solve=auto_solve,layout=layout,ocr=ocr,page_range=page_range)
        self.jobs.work(limit=20,batch_id=batch.batch_id)
        return self.store.batch(batch.batch_id)

    def enqueue_import(self,paths,*,scope,owner_id,**options):
        return self.jobs.enqueue(paths,scope=scope,owner_id=owner_id,**options)

    def _process_import(self,path,*,scope,owner_id,source_url=None,license_name=None,reuse_confirmed=False,
                        auto_solve=True,layout="auto",ocr=True,page_range=None,parse_checkpoint=None):
        result=self.pdf.parse(path,scope=scope,owner_id=owner_id,source_url=source_url,
            license_name=license_name,reuse_confirmed=reuse_confirmed,layout=layout,ocr=ocr,page_range=page_range,checkpoint=parse_checkpoint)
        ids=self.store.import_parsed(result)
        answer_states={};solve_errors=[]
        if auto_solve:
            for qid in ids:
                v=self.store.version(self.store.question(qid).current_version_id)
                try:answer_states[qid]=self.answers.solve(v.version_id).status.value
                except Exception as exc:solve_errors.append({"question_id":qid,"error_type":type(exc).__name__})
        return {"filename":Path(path).name,"document_id":result.source.document_id,"question_ids":ids,
            "status":"imported" if ids else "needs_review","warnings":result.warnings,"answer_states":answer_states,"solve_errors":solve_errors}

    def classify_with_model(self,vid):
        provider=self.answers.provider
        if not hasattr(provider,"classify"):
            raise RuntimeError("configured model does not support classification")
        cls=provider.classify(self.answers.solver_input(vid))
        self.store.save_classification(cls)
        return cls

    def public_question(self,qid):
        q=self.store.question(qid);v=self.store.version(q.current_version_id)
        return {"question_id":qid,"version_id":v.version_id,"stem":v.stem,
            "options":[o.model_dump() for o in v.options],"warnings":v.warnings,
            "spans":[s.model_dump() for s in v.spans],"classification":self.store.classification(v.version_id).model_dump()}

