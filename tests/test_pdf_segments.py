"""Recovery and boundary tests for real ImportQueue-backed page extraction."""
from pathlib import Path

import pdfplumber.page
import pytest
from reportlab.pdfgen.canvas import Canvas

from backend.bank import Bank
from gmf_v3.jobs import ImportQueue
from gmf_v3.import_checkpoint import ImportCheckpoint
from gmf_v3.store import ConflictError


def segmented_pdf(path, blank_pages=0):
    c=Canvas(str(path),pagesize=(612,792))
    pages=[
        ['Unit 1: Kinematics','1. First complete MCQ','(A) one','(B) two','(C) three','(D) four'],
        ['Unit 1: Kinematics','2. Cross-page question','(A) first','(B) second'],
        ['Unit 1: Kinematics','(C) third','(D) fourth','3. Next MCQ','(A) yes','(B) no','(C) maybe','(D) neither'],
        ['Unit 2: Dynamics','1. A different Unit restarts numbering','(A) up','(B) down','(C) left','(D) right']]
    for lines in pages:
        for i,line in enumerate(lines):c.drawString(40,740-i*26,line)
        c.showPage()
    for _ in range(blank_pages):c.showPage()
    c.save();return path


def test_segment_failure_restart_reuses_completed_pages_and_stitches_boundary(tmp_path,monkeypatch):
    m=Bank(tmp_path/'runtime');m.pdf.segment_pages=2
    batch=m.enqueue_import([segmented_pdf(tmp_path/'split.pdf')],scope='bank',owner_id='admin',auto_solve=False,ocr=False)
    render=pdfplumber.page.Page.to_image;seen=[]
    def cancel(page,*a,**kw):
        seen.append(page.page_number)
        if page.page_number==3:raise KeyboardInterrupt('simulated service termination')
        return render(page,*a,**kw)
    monkeypatch.setattr(pdfplumber.page.Page,'to_image',cancel)
    clock=[100.];m.jobs=ImportQueue(m,clock=lambda:clock[0],lease_seconds=10)
    with pytest.raises(KeyboardInterrupt):m.jobs.run_one(batch_id=batch.batch_id)
    f=m.store.batch(batch.batch_id).files[0]
    assert f['progress']=={'completed_pages':2,'total_pages':4}
    assert [s['status'] for s in f['segments']]==['completed','running']
    # A new process/model instance uses the same staged original and checkpoint DB.
    reopened=Bank(m.root);reopened.pdf.segment_pages=2;clock[0]=111.
    reopened.jobs=ImportQueue(reopened,clock=lambda:clock[0],lease_seconds=10)
    resumed=[]
    def record(page,*a,**kw):resumed.append(page.page_number);return render(page,*a,**kw)
    monkeypatch.setattr(pdfplumber.page.Page,'to_image',record)
    assert reopened.jobs.run_one(batch_id=batch.batch_id)['status']=='imported'
    assert resumed==[3,4]
    f=reopened.store.batch(batch.batch_id).files[0];assert f['progress']['completed_pages']==4
    assert [s['attempts'] for s in f['segments']]==[1,2]
    ids=f['question_ids'];assert len(ids)==len(set(ids))==4
    vs=[reopened.store.version(reopened.store.question(q).current_version_id) for q in ids]
    assert [o.label for o in vs[1].options]==list('ABCD')
    assert [s.page for s in vs[1].spans]==[2,3]
    assert [v.source_section for v in vs]==['1','1','1','2']
    assert not any('duplicate_source_number' in v.warnings for v in vs)
    # Repeated delivery creates no duplicate questions/versions and cannot publish them.
    reopened.jobs.retry(batch.batch_id);assert reopened.jobs.run_one(batch_id=batch.batch_id) is None
    assert reopened.store.list_questions(scope='bank',include_drafts=True,limit=None)
    with reopened.store.connect() as c:
        assert c.execute('SELECT count(*) FROM questions').fetchone()[0]==4
        assert c.execute("SELECT count(*) FROM questions WHERE publication='approved'").fetchone()[0]==0


def test_completed_checkpoint_asset_corruption_reextracts_only_affected_segment(tmp_path,monkeypatch):
    m=Bank(tmp_path/'runtime');m.pdf.segment_pages=2
    b=m.enqueue_import([segmented_pdf(tmp_path/'split.pdf')],scope='bank',owner_id='admin',auto_solve=False,ocr=False)
    m.jobs.work(limit=1,batch_id=b.batch_id)
    with m.store.connect(write=True) as c:
        c.execute("UPDATE import_jobs SET status='queued',max_attempts=5 WHERE batch_id=?",(b.batch_id,))
        row=c.execute('SELECT relative_path FROM import_segments WHERE first_page=1').fetchone()
    import json
    e=json.loads((m.root/row[0]).read_text())[0];(m.assets/e['asset']['relative_path']).unlink()
    render=pdfplumber.page.Page.to_image;seen=[]
    def record(page,*a,**kw):seen.append(page.page_number);return render(page,*a,**kw)
    monkeypatch.setattr(pdfplumber.page.Page,'to_image',record)
    m.jobs.work(limit=1,batch_id=b.batch_id)
    assert seen==[1,2]
    assert len(m.store.batch(b.batch_id).files[0]['question_ids'])==4
    with m.store.connect() as c:assert c.execute('SELECT count(*) FROM questions').fetchone()[0]==4


def test_stale_worker_cannot_commit_segment(tmp_path):
    m=Bank(tmp_path/'runtime');b=m.enqueue_import([segmented_pdf(tmp_path/'split.pdf')],scope='bank',owner_id='admin')
    clock=[100.];queue=ImportQueue(m,clock=lambda:clock[0],lease_seconds=5)
    stale=queue.claim(batch_id=b.batch_id);cp=ImportCheckpoint(queue,stale);cp.prepare('test',[(1,2)])
    clock[0]=106.;assert queue.claim(batch_id=b.batch_id)
    with pytest.raises(ConflictError):cp.begin('test',1,2)
    with pytest.raises(ConflictError):cp.complete('test',1,2,[])


def test_more_than_100_pages_complete_and_unknown_answers_remain_ungraded(tmp_path):
    m=Bank(tmp_path/'runtime');p=segmented_pdf(tmp_path/'long.pdf',blank_pages=99)
    b=m.enqueue_import([p],scope='bank',owner_id='admin',auto_solve=False,ocr=False)
    assert m.jobs.work(limit=1,batch_id=b.batch_id)[0]['status']=='imported'
    f=m.store.batch(b.batch_id).files[0]
    assert f['progress']=={'completed_pages':103,'total_pages':103}
    assert len(f['segments'])==9 and len(f['question_ids'])==4
    assert all(v!='Verified' for v in f['answer_states'].values())


def test_old_database_migration_preserves_rows_and_is_repeatable(tmp_path):
    m=Bank(tmp_path/'runtime');b=m.enqueue_import([segmented_pdf(tmp_path/'old.pdf')],scope='bank',owner_id='admin',auto_solve=False,ocr=False)
    m.jobs.work(limit=1,batch_id=b.batch_id)
    with m.store.connect(write=True) as c:
        before=[tuple(x) for x in c.execute('SELECT question_id,payload FROM questions')]
        c.execute('DROP TABLE import_segments');c.execute('DELETE FROM schema_migrations WHERE version=3')
    for _ in range(2):m=Bank(m.root)
    with m.store.connect() as c:
        assert [tuple(x) for x in c.execute('SELECT question_id,payload FROM questions')]==before
        assert c.execute('SELECT count(*) FROM schema_migrations WHERE version=3').fetchone()[0]==1


def test_question_identity_is_stable_across_page_ranges_and_legacy_ids(tmp_path):
    m=Bank(tmp_path/'runtime');p=segmented_pdf(tmp_path/'source.pdf')
    options={'scope':'bank','owner_id':'admin','ocr':False}
    full=m.pdf.parse(p,**options);partial=m.pdf.parse(p,page_range=(3,4),**options)
    assert full.questions[2].version.question_id==partial.questions[0].version.question_id
    # Simulate old ordinal-based IDs already referenced by student histories.
    from gmf_v3.pdf_core import digest
    old=[]
    for i,item in enumerate(full.questions):
        qid='q_'+digest(f'{full.source.document_id}|{item.number}|{i}'.encode())[:32]
        version=item.version.model_copy(update={'question_id':qid,'version_id':qid.replace('q_','qv_',1)+'_1','source_section':None})
        old.append(item.model_copy(update={'version':version}))
    legacy=full.model_copy(update={'questions':old});expected=m.store.import_parsed(legacy)
    assert m.store.import_parsed(full)==expected
    with m.store.connect() as c:
        assert c.execute('SELECT count(*) FROM questions').fetchone()[0]==4
        assert c.execute('SELECT count(*) FROM question_versions').fetchone()[0]==4


def test_contents_question_ranges_are_not_shared_stems(tmp_path):
    c=Canvas(str(tmp_path/'contents.pdf'),pagesize=(612,792))
    c.drawString(40,740,'1.1 Scalars and Vectors (questions 1-9) ............ 1');c.showPage()
    for i,line in enumerate(['Unit 1: Kinematics','1. Valid MCQ','(A) yes','(B) no','(C) up','(D) down']):c.drawString(40,740-i*26,line)
    c.save();m=Bank(tmp_path/'runtime');b=m.import_pdfs([tmp_path/'contents.pdf'],scope='bank',owner_id='admin',auto_solve=False,ocr=False)
    q=m.store.question(b.files[0]['question_ids'][0]);assert 'shared_stem_unresolved' not in m.meta(q.current_version_id)['issues']
