"""Durable local import queue. SQLite leases allow restart/retry without exam data."""
from __future__ import annotations
import json
import shutil
import threading
import time
import traceback
from pathlib import Path

from .contracts import ImportBatch,uid
from .store import ConflictError


class ImportQueue:
    def __init__(self,modules,*,clock=time.time,lease_seconds=120):
        self.modules=modules;self.store=modules.store;self.clock=clock;self.lease_seconds=lease_seconds

    def enqueue(self,paths,*,scope,owner_id,on_commit=None,**options):
        paths=list(paths)
        if not 1<=len(paths)<=20:raise ValueError("batch requires 1 to 20 PDFs")
        b=ImportBatch(batch_id=uid("batch"),scope=scope,owner_id=owner_id,status="queued")
        jobs=[]
        for ordinal,path in enumerate(paths):
            path=Path(path);job_id=uid("job")
            staged=self.modules.root/"inbox"/job_id/path.name
            result=None
            try:
                if path.stat().st_size>self.modules.pdf.max_bytes:raise ValueError("PDF exceeds byte limit")
                staged.parent.mkdir(parents=True,exist_ok=True)
                shutil.copyfile(path,staged)
                if staged.stat().st_size>self.modules.pdf.max_bytes:raise ValueError("PDF exceeds byte limit")
            except Exception as exc:
                result={"filename":path.name,"status":"failed","error_type":type(exc).__name__,"error":str(exc)[:200]}
            payload={"relative_path":staged.relative_to(self.modules.root).as_posix(),"filename":path.name,"options":options}
            jobs.append((job_id,ordinal,payload,result))
        with self.store.connect(write=True) as c:
            c.execute("INSERT INTO import_batches VALUES(?,?,?,?)",(b.batch_id,scope,owner_id,b.model_dump_json()))
            for job_id,ordinal,payload,result in jobs:
                c.execute("INSERT INTO import_jobs(job_id,batch_id,ordinal,status,payload,result) VALUES(?,?,?,?,?,?)",
                    (job_id,b.batch_id,ordinal,"failed" if result else "queued",json.dumps(payload),json.dumps(result) if result else None))
            if on_commit:on_commit(c,b)
            return self._refresh(c,b.batch_id)

    def _refresh(self,c,bid):
        row=c.execute("SELECT payload FROM import_batches WHERE batch_id=?",(bid,)).fetchone()
        if not row:raise KeyError(bid)
        b=ImportBatch.model_validate_json(row[0]);rows=c.execute("SELECT * FROM import_jobs WHERE batch_id=? ORDER BY ordinal",(bid,)).fetchall()
        if not rows:return b
        files=[]
        for row in rows:
            payload=json.loads(row["payload"])
            result=json.loads(row["result"]) if row["result"] else {"filename":payload["filename"],"status":row["status"]}
            files.append({**result,"job_id":row["job_id"],"attempts":row["attempts"]})
            segments=[dict(s) for s in c.execute("SELECT first_page,last_page,status,attempts,error FROM import_segments WHERE job_id=? AND cache_key=(SELECT cache_key FROM import_segment_heads WHERE job_id=?) ORDER BY first_page",(row['job_id'],row['job_id']))]
            if segments:
                files[-1]['segments']=segments
                files[-1]['progress']={'completed_pages':sum(s['last_page']-s['first_page']+1 for s in segments if s['status']=='completed'),
                                       'total_pages':sum(s['last_page']-s['first_page']+1 for s in segments)}
        states=[r["status"] for r in rows]
        if "running" in states:status="running"
        elif "queued" in states:status="running" if any(s in {"imported","failed","needs_review"} for s in states) else "queued"
        else:status="completed" if all(s=="imported" for s in states) else "partial" if "imported" in states else "failed"
        b=b.model_copy(update={"status":status,"files":files})
        c.execute("UPDATE import_batches SET payload=? WHERE batch_id=?",(b.model_dump_json(),bid))
        return b

    def claim(self,*,batch_id=None):
        timestamp=self.clock();token=uid("lease")
        with self.store.connect(write=True) as c:
            # An expired final attempt is made visible as failed instead of staying running forever.
            expired=c.execute("SELECT * FROM import_jobs WHERE status='running' AND lease_until<=? AND attempts>=max_attempts",(timestamp,)).fetchall()
            for row in expired:
                data=json.loads(row["payload"])
                result={"filename":data["filename"],"status":"failed","error_type":"LeaseExpired","error":"attempt limit reached; explicit retry available"}
                c.execute("UPDATE import_jobs SET status='failed',lease_owner=NULL,lease_until=NULL,result=? WHERE job_id=?",(json.dumps(result),row["job_id"]))
                self._refresh(c,row["batch_id"])
            sql="SELECT * FROM import_jobs WHERE (status='queued' OR (status='running' AND lease_until<=?)) AND attempts<max_attempts"
            args=[timestamp]
            if batch_id:sql+=" AND batch_id=?";args.append(batch_id)
            sql+=" ORDER BY batch_id,ordinal LIMIT 1"
            row=c.execute(sql,args).fetchone()
            if not row:return None
            c.execute("UPDATE import_jobs SET status='running',attempts=attempts+1,lease_owner=?,lease_until=? WHERE job_id=?",(token,timestamp+self.lease_seconds,row["job_id"]))
            self._refresh(c,row["batch_id"])
            return {**dict(row),"attempts":row["attempts"]+1,"lease_owner":token,"payload":json.loads(row["payload"])}

    def heartbeat(self,job):
        with self.store.connect(write=True) as c:
            return c.execute("UPDATE import_jobs SET lease_until=? WHERE job_id=? AND lease_owner=? AND status='running'",(self.clock()+self.lease_seconds,job["job_id"],job["lease_owner"])).rowcount==1

    def finish(self,job,result):
        if result["status"] not in {"imported","needs_review","failed"}:raise ValueError("invalid import result")
        with self.store.connect(write=True) as c:
            count=c.execute("UPDATE import_jobs SET status=?,result=?,lease_owner=NULL,lease_until=NULL WHERE job_id=? AND status='running' AND lease_owner=?",
                (result["status"],json.dumps(result),job["job_id"],job["lease_owner"])).rowcount
            if not count:raise ConflictError("job lease changed; stale worker result rejected")
            return self._refresh(c,job["batch_id"])

    def run_one(self,*,batch_id=None):
        job=self.claim(batch_id=batch_id)
        if not job:return None
        stop=threading.Event()
        def renew():
            while not stop.wait(max(.25,self.lease_seconds/3)):
                if not self.heartbeat(job):return
        thread=threading.Thread(target=renew,daemon=True);thread.start()
        diagnostics={'stage':'upload','upload':{'persisted':False}}
        try:
            b=self.store.batch(job["batch_id"])
            p=(self.modules.root/job["payload"]["relative_path"]).resolve()
            if not p.is_relative_to(self.modules.root):raise ValueError("invalid staged PDF path")
            diagnostics['upload']={'persisted':p.is_file(),'bytes':p.stat().st_size,'relative_path':job['payload']['relative_path']}
            from .import_checkpoint import ImportCheckpoint
            options={**job["payload"]["options"]}
            # V3 callers retain their original signature; V4 supplies stage diagnostics.
            if hasattr(self.modules,'exam_issues'):options['diagnostics']=diagnostics
            result=self.modules._process_import(p,scope=b.scope,owner_id=b.owner_id,parse_checkpoint=ImportCheckpoint(self,job),**options)
        except Exception as exc:
            diagnostics['exception']={'stage':diagnostics['stage'],'type':type(exc).__name__,'message':str(exc),'traceback':traceback.format_exc()}
            result={"filename":job["payload"]["filename"],"status":"failed","error_type":type(exc).__name__,"error":str(exc)[:500],"diagnostics":diagnostics}
        finally:
            stop.set();thread.join(timeout=5)
        # BaseException (process cancellation/KeyboardInterrupt) leaves the durable lease for recovery.
        diagnostics['task_status']=result['status']
        folder=self.modules.root/'import-diagnostics';folder.mkdir(exist_ok=True)
        report=folder/(job['job_id']+'-attempt-'+str(job['attempts'])+'.json')
        result['diagnostic_report']=report.relative_to(self.modules.root).as_posix()
        report.write_text(json.dumps(diagnostics,ensure_ascii=False,indent=2),encoding='utf-8')
        try:
            self.finish(job,result)
            diagnostics['task_update']={'success':True,'status':result['status']}
            report.write_text(json.dumps(diagnostics,ensure_ascii=False,indent=2),encoding='utf-8')
        except Exception as exc:
            diagnostics['exception']={'stage':'task_status_update','type':type(exc).__name__,'message':str(exc),'traceback':traceback.format_exc()}
            report.write_text(json.dumps(diagnostics,ensure_ascii=False,indent=2),encoding='utf-8')
            raise
        return {"job_id":job["job_id"],"batch_id":job["batch_id"],"status":result["status"]}

    def work(self,*,limit=20,batch_id=None):
        results=[]
        for _ in range(max(0,limit)):
            result=self.run_one(batch_id=batch_id)
            if result is None:break
            results.append(result)
        return results

    def retry(self,bid):
        with self.store.connect(write=True) as c:
            if not c.execute("SELECT 1 FROM import_batches WHERE batch_id=?",(bid,)).fetchone():raise KeyError(bid)
            c.execute("UPDATE import_jobs SET status='queued',result=NULL,lease_owner=NULL,lease_until=NULL,max_attempts=attempts+3 WHERE batch_id=? AND status IN ('failed','needs_review')",(bid,))
            return self._refresh(c,bid)
