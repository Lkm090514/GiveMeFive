from pathlib import Path
from reportlab.pdfgen.canvas import Canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from gmf_v3.pdf_core import QUESTION
from backend.bank import Bank
from test_v4 import env, headers

def import_result(bank,path):
    batch=bank.jobs.enqueue([path],scope='exam_private',owner_id='qa-student',auto_solve=False)
    bank.jobs.work(batch_id=batch.batch_id)
    return bank.store.batch(batch.batch_id).files[0]


def test_chinese_numbered_mcq_preserves_original_visual_and_unknown_answer(tmp_path):
    pdfmetrics.registerFont(UnicodeCIDFont('STSong-Light'))
    path = tmp_path / 'chinese-number.pdf'
    c = Canvas(str(path))
    c.setFont('STSong-Light', 14)
    for i, text in enumerate(['QA 测试夹具，非真实试卷', '第 1 题', '选择正确方向。', 'A. 向左', 'B. 向右', 'C. 向上', 'D. 向下']):
        c.drawString(50, 780-i*28, text)
    c.save()
    bank = Bank(tmp_path / 'bank')
    result = import_result(bank,path)
    assert result['status'] == 'imported', result
    assert result['paper_id']
    assert result['summary']['mcq'] == 1
    assert result['summary']['unconfirmed_answers'] == 1
    assert QUESTION.match('1.2 speed') is None
    assert QUESTION.match('2026 年') is None


def test_zero_question_pdf_gives_actionable_feedback_without_creating_paper(tmp_path):
    path = tmp_path / 'not-an-exam.pdf'
    c = Canvas(str(path)); c.drawString(50, 700, 'QA plain document without numbered questions'); c.save()
    result = import_result(Bank(tmp_path / 'bank'),path)
    assert result['status'] == 'needs_review'
    assert result['paper_id'] is None
    assert '未识别出完整' in result['error']


def plain_pdf(path):
    c=Canvas(str(path))
    for i,text in enumerate(['1. A particle moves at constant speed. Select the direction.', '(A) Left', '(B) Right', '(C) Up', '(D) Down']):c.drawString(40,740-24*i,text)
    c.save();return path


def test_one_page_one_ordinary_question_is_interactive_and_ungraded(env):
    app,client,clock,temp=env
    path=plain_pdf(temp/'one-question.pdf')
    with path.open('rb') as stream:r=client.post('/api/v4/papers/import',headers=headers(),files={'file':(path.name,stream)},data={'request_key':'one'})
    assert r.status_code==200,r.text
    app.state.bank.jobs.work(batch_id=r.json()['batch_id'])
    f=app.state.bank.store.batch(r.json()['batch_id']).files[0]
    assert f['summary']['mcq']==f['summary']['structure_ready']==1
    s=client.post('/api/v4/sessions',headers=headers(),json={'mode':'exam','set_id':f['paper_id'],'request_id':'one-exam'}).json()
    q=s['questions'][0]['question_id']
    command=lambda kind,**kw:client.post('/api/v4/sessions/'+s['id']+'/commands',headers=headers(),json={'type':kind,**kw})
    assert command('answer',question_id=q,option='B').status_code==200
    final=command('submit').json()
    assert final['summary']['answered']==1 and final['summary']['accuracy'] is None
    assert client.get('/api/v4/mistakes',headers=headers()).json()==[]


def test_failed_task_retry_delete_and_original_are_owner_checked(env):
    app,client,clock,temp=env
    path=temp/'no-questions.pdf';c=Canvas(str(path));c.drawString(40,700,'A plain QA document without numbered questions');c.save()
    batch=app.state.bank.jobs.enqueue([path],scope='exam_private',owner_id='student',auto_solve=False)
    app.state.bank.jobs.work(batch_id=batch.batch_id)
    row=app.state.bank.store.batch(batch.batch_id).files[0];bid=batch.batch_id
    original=f'/api/v4/papers/imports/{bid}/{row["job_id"]}/original'
    assert client.get(original,headers=headers('other')).status_code==404
    assert client.delete('/api/v4/papers/imports/'+bid,headers=headers('other')).status_code==404
    assert client.post('/api/v4/papers/imports/'+bid+'/retry',headers=headers('other')).status_code==404
    assert client.post('/api/v4/papers/imports/'+bid+'/retry',headers=headers()).status_code==200
    assert app.state.bank.store.batch(bid).files[0]['status']=='queued'
    app.state.bank.jobs.work(batch_id=bid)
    assert app.state.bank.store.batch(bid).files[0]['attempts']==2
    assert client.delete('/api/v4/papers/imports/'+bid,headers=headers()).status_code==200
    assert client.get('/api/v4/papers/imports',headers=headers()).json()==[]
    assert client.get(original,headers=headers()).content==path.read_bytes()
    assert app.state.bank.store.batch(bid).files[0]['diagnostics']['failure_stage']=='question_detection'


def test_database_write_exception_retains_stack_and_original(tmp_path,monkeypatch):
    bank=Bank(tmp_path/'bank');path=plain_pdf(tmp_path/'one.pdf')
    def fail(result):raise RuntimeError('QA injected database write failure')
    monkeypatch.setattr(bank.store,'import_parsed',fail)
    result=import_result(bank,path)
    assert result['status']=='failed'
    error=result['diagnostics']['exception']
    assert error['stage']=='database_write' and 'RuntimeError' in error['traceback']
    assert result['diagnostics']['upload']['persisted']
    assert list((bank.root/'import-diagnostics').glob('*.json'))


def test_bare_numbers_two_column_and_visual_options_are_not_lost(tmp_path):
    path=tmp_path/'bare-choices.pdf';c=Canvas(str(path))
    c.drawString(40,780,'QA authored structural fixture, without an answer key')
    c.drawString(40,740,'01 Choose one of the following values.')
    for x,y,text in [(50,700,'A 1 m/s'),(300,700,'B 2 m/s'),(50,660,'C 3 m/s'),(300,660,'D 4 m/s')]:c.drawString(x,y,text)
    c.drawString(40,600,'02 Choose the corresponding diagram.')
    for x,y,label in [(50,550,'A'),(300,550,'B'),(50,350,'C'),(300,350,'D')]:
        c.drawString(x,y,label);c.rect(x,y-100,180,70);c.line(x+10,y-90,x+120,y-40)
    c.save()
    result=import_result(Bank(tmp_path/'bank'),path)
    assert result['summary']['mcq']==result['summary']['structure_ready']==2,result
    assert result['diagnostics']['question_detection']['candidates']==2
    assert all(q['labels']==['A','B','C','D'] for q in result['diagnostics']['candidates'])


def test_rejected_candidate_is_in_partial_paper_count(tmp_path):
    path=tmp_path/'partial.pdf';c=Canvas(str(path))
    for i,text in enumerate(['1. A complete question','(A) Left','(B) Right','2. An incomplete question','(A) Only one choice']):c.drawString(40,740-i*30,text)
    c.save();bank=Bank(tmp_path/'bank');result=import_result(bank,path)
    assert result['summary']['candidate_count']==2 and result['summary']['split_rejected']==1
    with bank.store.connect() as db:paper=__import__('json').loads(db.execute('SELECT payload FROM v4_sets WHERE set_id=?',(result['paper_id'],)).fetchone()[0])
    assert paper['source_question_count']==2 and paper['excluded_question_count']==1


def test_missing_ocr_component_preserves_actual_exception_and_original(tmp_path,monkeypatch):
    import gmf_v3.pdf_core as core
    def missing(*args,**kwargs):raise FileNotFoundError('QA missing OCR executable')
    monkeypatch.setattr(core,'_ocr_lines',missing)
    path=tmp_path/'scan.pdf';c=Canvas(str(path));c.rect(40,300,300,300);c.save()
    result=import_result(Bank(tmp_path/'bank'),path)
    assert result['status']=='needs_review' and result['paper_id'] is None
    report=result['diagnostics']
    assert report['failure_stage']=='text_extraction'
    assert report['ocr_errors'][0]['type']=='FileNotFoundError'
    assert 'QA missing OCR executable' in report['ocr_errors'][0]['traceback']
    assert report['upload']['persisted']
