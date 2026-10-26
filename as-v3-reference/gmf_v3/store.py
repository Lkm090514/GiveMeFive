"""Independent SQLite persistence. Does not open GMF's exam DB or Learning Ledger."""
from __future__ import annotations
import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from .classification import classify, similarity
from .contracts import (AnswerEvidence, AnswerKey, AnswerStatus, ImportBatch, Question,
                        QuestionAsset, QuestionClassification, QuestionRelation, QuestionVersion,
                        SourceRecord, now, uid)
from .pdf_core import fingerprints


class ConflictError(ValueError):
    pass


class Store:
    def __init__(self, path: Path | str):
        self.path = Path(path).resolve()
        self.path.parent.mkdir(parents=True,exist_ok=True)
        with self.connect() as c:
            c.execute("PRAGMA journal_mode=WAL")
            c.executescript((Path(__file__).parent/"migrations/001_initial.sql").read_text())
            c.execute("INSERT OR IGNORE INTO schema_migrations VALUES(1,?)",(now(),))
            if not c.execute("SELECT 1 FROM schema_migrations WHERE version=2").fetchone():
                c.executescript((Path(__file__).parent/"migrations/002_reliability.sql").read_text())
                c.execute("INSERT OR IGNORE INTO schema_migrations VALUES(2,?)",(now(),))
            c.executescript((Path(__file__).parent/"migrations/003_import_segments.sql").read_text())
            c.execute("INSERT OR IGNORE INTO schema_migrations VALUES(3,?)",(now(),))

    @contextmanager
    def connect(self, write=False):
        c = sqlite3.connect(self.path,timeout=30)
        c.row_factory=sqlite3.Row
        c.execute("PRAGMA foreign_keys=ON")
        try:
            if write:
                c.execute("BEGIN IMMEDIATE")
            yield c
            c.commit()
        except BaseException:
            c.rollback()
            raise
        finally:
            c.close()

    def import_parsed(self, result):
        s = result.source
        ids = []
        with self.connect(write=True) as c:
            c.execute("INSERT OR IGNORE INTO documents VALUES(?,?,?,?)",(s.document_id,s.scope,s.owner_id,s.model_dump_json()))
            for a in result.assets:
                c.execute("INSERT OR IGNORE INTO assets VALUES(?,?,?)",(a.asset_id,a.document_id,a.model_dump_json()))
            # Older parsers used the count of preceding accepted questions in the ID.
            # Reuse an unambiguous original-page anchor; never overwrite edits or old versions.
            anchors={}
            for row in c.execute('SELECT q.question_id,q.payload,v.payload version FROM questions q JOIN question_versions v ON q.current_version_id=v.version_id WHERE q.document_id=?',(s.document_id,)):
                old=QuestionVersion.model_validate_json(row['version']);q=Question.model_validate_json(row['payload'])
                anchors.setdefault((q.source_number,old.spans[0].page),[]).append((q,old))
            for item in result.questions:
                v = item.version
                matches=[q for q,old in anchors.get((item.number,v.spans[0].page),[]) if abs(old.spans[0].bbox[1]-v.spans[0].bbox[1])<5 and (not old.source_section or old.source_section==v.source_section)]
                if not matches:
                    matches=[q for q,old in anchors.get((item.number,v.spans[0].page),[]) if not old.source_section]
                if len(matches)==1:
                    ids.append(matches[0].question_id);continue
                if len(matches)>1:raise ConflictError('Reimport question anchor is ambiguous; originals preserved')
                ids.append(v.question_id)
                if c.execute("SELECT 1 FROM questions WHERE question_id=?",(v.question_id,)).fetchone():
                    continue  # Idempotent reimport never overwrites edits or answer revisions.
                q = Question(question_id=v.question_id,scope=s.scope,owner_id=s.owner_id,document_id=s.document_id,
                    source_number=item.number,current_version_id=v.version_id)
                c.execute("INSERT INTO questions VALUES(?,?,?,?,?,?,?)",(q.question_id,q.document_id,q.scope,q.owner_id,q.publication,q.current_version_id,q.model_dump_json()))
                self._insert_version(c,v)
                self._insert_classification(c,classify(v))
                labels = list(dict.fromkeys(item.source_answers))
                if labels:
                    ev=AnswerEvidence(version_id=v.version_id,kind="source_key",producer="pdf-native-parser/1",
                        details={"labels":labels,"document_id":s.document_id,"question_number":item.number,"confirmed":False})
                    c.execute("INSERT INTO answer_evidence VALUES(?,?,?)",(ev.evidence_id,ev.version_id,ev.model_dump_json()))
                    valid = len(labels)==1 and labels[0] in {o.label for o in v.options}
                    ans=AnswerKey(version_id=v.version_id,revision=1,label=labels[0] if valid else None,
                        status=AnswerStatus.PROVISIONAL if valid else AnswerStatus.DISPUTED,
                        evidence_ids=[ev.evidence_id],explanation="Extracted source key; requires source/mapping confirmation.")
                    c.execute("INSERT INTO answer_keys(answer_key_id,version_id,revision,payload) VALUES(?,?,?,?)",(ans.answer_key_id,ans.version_id,ans.revision,ans.model_dump_json()))
        self.refresh_duplicates(ids)
        return ids

    @staticmethod
    def _insert_version(c,v):
        c.execute("INSERT INTO question_versions VALUES(?,?,?,?,?,?)",(v.version_id,v.question_id,v.version,v.text_fingerprint,v.fingerprint,v.model_dump_json()))

    @staticmethod
    def _insert_classification(c,cls):
        c.execute("INSERT INTO classifications(classification_id,version_id,payload) VALUES(?,?,?)",(cls.classification_id,cls.version_id,cls.model_dump_json()))

    def question(self,qid) -> Question:
        with self.connect() as c:
            row=c.execute("SELECT payload FROM questions WHERE question_id=?",(qid,)).fetchone()
        if not row:
            raise KeyError(qid)
        return Question.model_validate_json(row[0])

    def version(self,vid) -> QuestionVersion:
        with self.connect() as c:
            row=c.execute("SELECT payload FROM question_versions WHERE version_id=?",(vid,)).fetchone()
        if not row:
            raise KeyError(vid)
        return QuestionVersion.model_validate_json(row[0])

    def source(self,did) -> SourceRecord:
        with self.connect() as c:
            row=c.execute("SELECT payload FROM documents WHERE document_id=?",(did,)).fetchone()
        if not row: raise KeyError(did)
        return SourceRecord.model_validate_json(row[0])

    def review_source(self,did,*,license_name,reuse_confirmed,reviewer):
        if not reviewer or not license_name.strip():raise ValueError("license and reviewer required")
        source=self.source(did)
        if source.scope!="bank":raise ValueError("personal papers cannot be promoted into the bank")
        source=source.model_copy(update={"license_name":license_name,"reuse_confirmed":reuse_confirmed,
            "warnings":source.warnings+["rights_reviewed_by:"+reviewer]})
        with self.connect(write=True) as c:
            c.execute("UPDATE documents SET payload=? WHERE document_id=?",(source.model_dump_json(),did))
            if not reuse_confirmed:
                rows=c.execute("SELECT payload FROM questions WHERE document_id=?",(did,)).fetchall()
                for row in rows:
                    q=Question.model_validate_json(row[0]).model_copy(update={"publication":"draft"})
                    c.execute("UPDATE questions SET publication='draft',payload=? WHERE question_id=?",(q.model_dump_json(),q.question_id))
        return source

    def asset(self,aid) -> QuestionAsset:
        with self.connect() as c:
            row=c.execute("SELECT payload FROM assets WHERE asset_id=?",(aid,)).fetchone()
        if not row: raise KeyError(aid)
        return QuestionAsset.model_validate_json(row[0])

    def latest_answer(self,vid) -> AnswerKey | None:
        with self.connect() as c:
            row=c.execute("SELECT payload FROM answer_keys WHERE version_id=? ORDER BY revision DESC LIMIT 1",(vid,)).fetchone()
        return AnswerKey.model_validate_json(row[0]) if row else None

    def answer_history(self,vid):
        with self.connect() as c:
            return [AnswerKey.model_validate_json(r[0]) for r in c.execute("SELECT payload FROM answer_keys WHERE version_id=? ORDER BY revision",(vid,))]

    def evidence(self,vid):
        with self.connect() as c:
            return [AnswerEvidence.model_validate_json(r[0]) for r in c.execute("SELECT payload FROM answer_evidence WHERE version_id=?",(vid,))]

    def append_answer(self,vid,*,label,status,evidence,explanation="",confirmed_by=None,expected_revision=None):
        v=self.version(vid)
        if label is not None and label not in {o.label for o in v.options}:
            raise ValueError("answer label is not an option")
        with self.connect(write=True) as c:
            ans=self._write_answer(c,vid,label=label,status=status,evidence=evidence,explanation=explanation,
                confirmed_by=confirmed_by,expected_revision=expected_revision)
            pending=[ans]
            while pending:
                changed=pending.pop(0)
                rows=c.execute("SELECT DISTINCT derived.payload FROM answer_dependencies d JOIN answer_keys src ON src.answer_key_id=d.source_answer_key_id JOIN answer_keys derived ON derived.answer_key_id=d.derived_answer_key_id WHERE src.version_id=?",(changed.version_id,)).fetchall()
                for row in rows:
                    derived=AnswerKey.model_validate_json(row[0])
                    current=self._latest_answer(c,derived.version_id)
                    if not current or current.answer_key_id!=derived.answer_key_id or current.status!=AnswerStatus.VERIFIED:
                        continue  # A later independent human confirmation must be retained.
                    if changed.status==AnswerStatus.VERIFIED and changed.label==current.label:
                        continue
                    ev=AnswerEvidence(version_id=current.version_id,kind="dependency_invalidated",producer="answer-dependency-tracker/1",
                        details={"source_version_id":changed.version_id,"source_answer_key_id":changed.answer_key_id,"root_answer_key_id":ans.answer_key_id})
                    invalid=self._write_answer(c,current.version_id,label=current.label,status=AnswerStatus.DISPUTED,
                        evidence=[ev],explanation="Upstream trusted answer changed; independent review required.",root=ans.answer_key_id)
                    pending.append(invalid)
        return ans

    @staticmethod
    def _latest_answer(c,vid):
        row=c.execute("SELECT payload FROM answer_keys WHERE version_id=? ORDER BY revision DESC LIMIT 1",(vid,)).fetchone()
        return AnswerKey.model_validate_json(row[0]) if row else None

    def _write_answer(self,c,vid,*,label,status,evidence,explanation="",confirmed_by=None,expected_revision=None,root=None):
        old=self._latest_answer(c,vid)
        revision=old.revision if old else 0
        if expected_revision is not None and revision!=expected_revision:
            raise ConflictError("answer changed; reload before confirming")
        dependencies=[]
        for ev in evidence:
            if ev.version_id!=vid:raise ValueError("evidence version mismatch")
            if ev.kind=="trusted_match":
                source_id=ev.details.get("matched_answer_key_id")
                row=c.execute("SELECT a.payload,q.publication,q.scope,v.fingerprint FROM answer_keys a JOIN question_versions v ON v.version_id=a.version_id JOIN questions q ON q.current_version_id=v.version_id WHERE a.answer_key_id=?",(source_id,)).fetchone()
                source=AnswerKey.model_validate_json(row[0]) if row else None
                target_fp=c.execute("SELECT fingerprint FROM question_versions WHERE version_id=?",(vid,)).fetchone()[0]
                if not source or row[1]!="approved" or row[2]!="bank" or row[3]!=target_fp or source.version_id==vid or source.status!=AnswerStatus.VERIFIED or source.label!=label or self._latest_answer(c,source.version_id).answer_key_id!=source_id:
                    raise ConflictError("trusted source changed or is no longer eligible")
                dependencies.append(source_id)
            c.execute("INSERT INTO answer_evidence VALUES(?,?,?)",(ev.evidence_id,vid,ev.model_dump_json()))
        ans=AnswerKey(version_id=vid,revision=revision+1,label=label,status=status,evidence_ids=[e.evidence_id for e in evidence],
            explanation=explanation,supersedes=old.answer_key_id if old else None,confirmed_by=confirmed_by)
        c.execute("INSERT INTO answer_keys(answer_key_id,version_id,revision,payload) VALUES(?,?,?,?)",(ans.answer_key_id,vid,ans.revision,ans.model_dump_json()))
        for source_id in dependencies:c.execute("INSERT INTO answer_dependencies VALUES(?,?)",(ans.answer_key_id,source_id))
        if ans.status!=AnswerStatus.VERIFIED:
            row=c.execute("SELECT payload FROM questions WHERE current_version_id=? AND publication='approved'",(vid,)).fetchone()
            if row:
                q=Question.model_validate_json(row[0]).model_copy(update={"publication":"draft"})
                c.execute("UPDATE questions SET publication='draft',payload=? WHERE question_id=?",(q.model_dump_json(),q.question_id))
        if old and (old.label!=ans.label or old.status!=ans.status):
            payload={"old_status":old.status.value,"new_status":ans.status.value,"reason":"upstream_changed" if root else "answer_revised"}
            c.execute("INSERT INTO answer_changes VALUES(?,?,?,?,?,?,?,?)",(uid("change"),vid,old.answer_key_id,ans.answer_key_id,root or ans.answer_key_id,now(),None,json.dumps(payload)))
        return ans

    def answer_changes(self,*,owner_id,include_bank=False,include_acknowledged=False):
        sql="SELECT ch.* FROM answer_changes ch JOIN question_versions v ON v.version_id=ch.version_id JOIN questions q ON q.question_id=v.question_id WHERE ((q.scope='exam_private' AND q.owner_id=?)"
        args=[owner_id]
        sql+=(" OR q.scope='bank')" if include_bank else ")")
        if not include_acknowledged:sql+=" AND ch.acknowledged_by IS NULL"
        sql+=" ORDER BY ch.created_at,ch.change_id"
        with self.connect() as c:return [dict(r) for r in c.execute(sql,args)]

    def acknowledge_change(self,change_id,*,owner_id,include_bank=False):
        allowed={r["change_id"] for r in self.answer_changes(owner_id=owner_id,include_bank=include_bank,include_acknowledged=True)}
        if change_id not in allowed:raise KeyError(change_id)
        with self.connect(write=True) as c:c.execute("UPDATE answer_changes SET acknowledged_by=? WHERE change_id=? AND acknowledged_by IS NULL",(owner_id,change_id))

    def classification(self,vid):
        with self.connect() as c:
            row=c.execute("SELECT payload FROM classifications WHERE version_id=? ORDER BY seq DESC LIMIT 1",(vid,)).fetchone()
        return QuestionClassification.model_validate_json(row[0]) if row else classify(self.version(vid))

    def save_classification(self,cls):
        self.version(cls.version_id)
        with self.connect(write=True) as c:
            self._insert_classification(c,cls)

    def approve(self,qid,*,reviewer,expected_version):
        q=self.question(qid)
        if q.scope!="bank": raise ValueError("personal papers cannot be published through approval")
        if q.current_version_id!=expected_version: raise ConflictError("question changed")
        if not reviewer: raise ValueError("reviewer required")
        source=self.source(q.document_id)
        if not source.reuse_confirmed or not source.license_name:
            raise ValueError("explicit source reuse confirmation and license required")
        a=self.latest_answer(q.current_version_id)
        if not a or a.status!=AnswerStatus.VERIFIED: raise ValueError("verified answer required")
        new=q.model_copy(update={"publication":"approved"})
        with self.connect(write=True) as c:
            latest=self._latest_answer(c,expected_version)
            source_row=c.execute("SELECT payload FROM documents WHERE document_id=?",(q.document_id,)).fetchone()
            source=SourceRecord.model_validate_json(source_row[0])
            if not latest or latest.status!=AnswerStatus.VERIFIED or not source.reuse_confirmed or not source.license_name:
                raise ConflictError("answer or source rights changed during review")
            r=c.execute("UPDATE questions SET publication='approved',payload=? WHERE question_id=? AND current_version_id=?",(new.model_dump_json(),qid,expected_version))
            if r.rowcount!=1: raise ConflictError("question changed")
        return new

    def revise(self,qid,*,expected_version,stem,options):
        q=self.question(qid)
        old=self.version(q.current_version_id)
        if old.version_id!=expected_version: raise ConflictError("question changed")
        # Retained original crops can no longer be asserted to match edited text.
        tf,fp=fingerprints(stem,options,[old.fingerprint] if old.has_visual else [])
        new=QuestionVersion(**{**old.model_dump(),"version_id":uid("qv"),"version":old.version+1,
            "stem":stem,"options":options,"fingerprint":fp,"text_fingerprint":tf,"created_at":now(),
            "warnings":list(dict.fromkeys(old.warnings+["edited_content_visuals_require_review"])),
            "external":{}})
        updated=q.model_copy(update={"current_version_id":new.version_id,"publication":"draft"})
        with self.connect(write=True) as c:
            r=c.execute("UPDATE questions SET current_version_id=?,publication='draft',payload=? WHERE question_id=? AND current_version_id=?",(new.version_id,updated.model_dump_json(),qid,expected_version))
            if r.rowcount!=1: raise ConflictError("question changed")
            self._insert_version(c,new)
            self._insert_classification(c,classify(new))
        return new

    def list_questions(self,*,scope,owner_id=None,include_drafts=False,text="",knowledge=None,method=None,answer_status=None,limit=100,offset=0):
        if scope not in {"bank","exam_private"}: raise ValueError("explicit scope required")
        if scope=="exam_private" and not owner_id: raise ValueError("private owner required")
        sql="SELECT payload FROM questions WHERE scope=?"
        args=[scope]
        if scope=="exam_private": sql+=" AND owner_id=?";args.append(owner_id)
        if scope=="bank" and not include_drafts: sql+=" AND publication='approved'"
        sql+=" ORDER BY question_id"
        result=[]
        matched=0
        with self.connect() as c:
            rows=c.execute(sql,args).fetchall()
        for row in rows:
            q=Question.model_validate_json(row[0]);v=self.version(q.current_version_id)
            cls=self.classification(v.version_id);a=self.latest_answer(v.version_id)
            if text and text.casefold() not in (v.stem+" "+" ".join(o.text for o in v.options)).casefold(): continue
            if knowledge and knowledge not in cls.knowledge: continue
            if method and method not in cls.methods: continue
            if answer_status and (a.status.value if a else "Unresolved")!=answer_status: continue
            if matched>=offset:result.append((q,v,cls,a))
            matched+=1
            if limit is not None and len(result)>=limit: break
        return result

    def trusted_match(self,v):
        q=self.question(v.question_id)
        for other,ov,cls,ans in self.list_questions(scope="bank",limit=None):
            if ov.version_id!=v.version_id and ov.fingerprint==v.fingerprint and ans and ans.status==AnswerStatus.VERIFIED:
                return ov,ans
        return None

    def refresh_duplicates(self,qids):
        for qid in qids:
            q=self.question(qid);v=self.version(q.current_version_id)
            with self.connect() as c:
                rows=c.execute("SELECT v.payload FROM question_versions v JOIN questions q ON q.current_version_id=v.version_id WHERE v.text_fingerprint=? AND q.scope=? AND q.owner_id=? AND q.question_id!=?",(v.text_fingerprint,q.scope,q.owner_id,qid)).fetchall()
            for row in rows:
                other=QuestionVersion.model_validate_json(row[0])
                exact=other.fingerprint==v.fingerprint
                rel=QuestionRelation(from_version_id=v.version_id,to_version_id=other.version_id,
                    kind="exact_duplicate" if exact else "possible_duplicate",score=1 if exact else .6,
                    reasons=["same_text_and_visual_fingerprint" if exact else "same_text_visuals_differ"])
                with self.connect(write=True) as c:
                    c.execute("INSERT OR IGNORE INTO relations VALUES(?,?,?,?,?)",(rel.relation_id,rel.from_version_id,rel.to_version_id,rel.kind,rel.model_dump_json()))

    def similar(self,vid,*,exclude_ids=(),seen_ids=(),limit=10,include_drafts=False):
        v=self.version(vid);a=self.classification(vid)
        output=[]
        for q,ov,b,answer in self.list_questions(scope="bank",include_drafts=include_drafts,limit=None):
            if q.question_id in {*exclude_ids,v.question_id} or ov.fingerprint==v.fingerprint: continue
            score,reasons=similarity(a,b)
            if not (set(a.knowledge)&set(b.knowledge) or set(a.methods)&set(b.methods)): continue
            if q.question_id in seen_ids: score*=.5;reasons.append("seen_before_penalty")
            if not answer or answer.status!=AnswerStatus.VERIFIED: score*=.5;reasons.append("unverified_answer_penalty")
            kind="transfer" if set(a.methods)&set(b.methods) and not set(a.structures)&set(b.structures) else "consolidation"
            output.append({"question_id":q.question_id,"version_id":ov.version_id,"score":round(score,4),"kind":kind,"reasons":reasons})
        return sorted(output,key=lambda x:(-x["score"],x["question_id"]))[:limit]

    def save_batch(self,batch:ImportBatch):
        with self.connect(write=True) as c:
            c.execute("INSERT INTO import_batches VALUES(?,?,?,?) ON CONFLICT(batch_id) DO UPDATE SET payload=excluded.payload",(batch.batch_id,batch.scope,batch.owner_id,batch.model_dump_json()))

    def batch(self,bid):
        with self.connect() as c: row=c.execute("SELECT payload FROM import_batches WHERE batch_id=?",(bid,)).fetchone()
        if not row: raise KeyError(bid)
        return ImportBatch.model_validate_json(row[0])
