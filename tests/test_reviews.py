import io
import json

from PIL import Image

from test_v4 import env,headers,targeted_bank,practice,command,exam,TOKENS
from backend.app import create_app
from fastapi.testclient import TestClient


def origin(env,correct=False):
    ids=targeted_bank(env);s=practice(env,[ids[0]],1)
    command(env,s,'answer',question_id=ids[0],option='B' if correct else 'A')
    s=command(env,s,'check',question_id=ids[0]).json()
    return ids,s,s['records'][0]


def note(env,qid,previous=None,ready=True,**extra):
    return env[1].post('/api/v4/learning/'+qid+'/notes',headers=headers(),json={'cause':'受力关系','reasoning':'先建立方程','text':'修正记录','expected_note_id':previous,'ready_for_check':ready,**extra})


def review(env,qid,phase='independent',count=1,key='review'):
    return env[1].post('/api/v4/sessions',headers=headers(),json={'mode':'practice','request_id':key,'review_question':qid,'review_phase':phase,'count':count})


def finish(env,s,option='B'):
    for q in s['questions']:command(env,s,'answer',question_id=q['question_id'],option=option)
    return command(env,s,'submit').json()


def test_optional_notes_images_history_conflict_and_owner_isolation(env):
    ids,s,r=origin(env);c=env[1]
    image=io.BytesIO();Image.new('RGB',(20,10),'white').save(image,format='PNG')
    upload=c.post('/api/v4/learning/'+ids[0]+'/images',headers=headers(),files={'file':('steps.png',image.getvalue(),'image/png')});assert upload.status_code==200
    aid=upload.json()['asset_id'];first=note(env,ids[0],assets=[aid]);assert first.status_code==200,first.text
    n=first.json()['notes'][0];assert n['version_id']==r['version_id']
    assert c.get('/api/v4/learning/images/'+aid,headers=headers()).status_code==200
    assert c.get('/api/v4/learning/images/'+aid,headers=headers('other')).status_code==404
    assert note(env,ids[0]).status_code==409
    second=note(env,ids[0],previous=n['id'],text='新增更正');assert second.status_code==200
    assert len(second.json()['notes'])==2 and second.json()['notes'][1]['supersedes']==n['id']
    assert c.post('/api/v4/learning/'+ids[0]+'/notes',headers=headers('other'),json={'text':'bad'}).status_code==404
    reopened=TestClient(create_app(env[0].state.bank.root,TOKENS,clock=lambda:env[2][0],worker=False))
    case=reopened.get('/api/v4/mistakes',headers=headers()).json()[0];assert len(case['review']['notes'])==2
    assert case['records'][0]==r


def test_correction_can_be_declared_without_forcing_a_written_note(env):
    ids,s,r=origin(env)
    response=env[1].post('/api/v4/learning/'+ids[0]+'/notes',headers=headers(),json={'ready_for_check':True})
    assert response.status_code==200,response.text
    assert response.json()['notes']==[] and response.json()['state']=='independent'
    assert review(env,ids[0]).status_code==200


def test_guessed_correct_uses_bookmark_without_error_or_score_change(env):
    ids,s,r=origin(env,True);c=env[1]
    for _ in range(2):assert c.post('/api/v4/learning/uncertain',headers=headers(),json={'record_id':r['record_id']}).status_code==200
    rows=c.get('/api/v4/mistakes',headers=headers()).json();assert len(rows)==1 and rows[0]['last_status']=='uncertain'
    assert rows[0]['record_ids']==[] and rows[0]['records'][0]['status']=='correct'
    with env[0].state.bank.store.connect() as db:
        assert db.execute('SELECT count(*) FROM v4_wrong').fetchone()[0]==0
        assert db.execute('SELECT count(*) FROM v4_bookmarks').fetchone()[0]==1
    assert c.post('/api/v4/learning/uncertain',headers=headers('other'),json={'record_id':r['record_id']}).status_code==404
    report=c.get('/api/v4/analysis',headers=headers()).json();topic=next(t for t in report['topics'] if t['topic_id']=='2.5')
    assert topic['first_correct']==1 and topic['first_incorrect']==0 and topic['certain_independent']==0 and not topic['priority']
    assert c.delete('/api/v4/mistakes/'+ids[0],headers=headers()).status_code==200
    assert c.get('/api/v4/mistakes',headers=headers()).json()==[]


def test_independent_delayed_pass_and_case_is_retained(env):
    ids,s,r=origin(env);assert note(env,ids[0]).status_code==200
    active=review(env,ids[0]);assert active.status_code==200,active.text;s=active.json()
    assert s['review']['type_match']=='exact-shared-type' and s['questions'][0]['question_id']!=ids[0]
    assert command(env,s,'check',question_id=s['questions'][0]['question_id']).status_code==422
    assert review(env,ids[0],key='parallel').status_code==422
    done=finish(env,s);assert done['review_outcome']['state']=='delayed'
    assert review(env,ids[0],'delayed',key='early').status_code==422
    env[2][0]+=24*3600
    m=env[1].get('/api/v4/mistakes',headers=headers()).json()[0];assert m['review']['display_state']=='due'
    next_run=review(env,ids[0],'delayed',key='due');assert next_run.status_code==200,next_run.text
    assert next_run.json()['questions'][0]['question_id'] not in [ids[0],s['questions'][0]['question_id']]
    done=finish(env,next_run.json());assert done['review_outcome']['state']=='passed'
    assert len(env[1].get('/api/v4/mistakes',headers=headers()).json())==1
    assert command(env,next_run.json(),'submit').json()['review_outcome']==done['review_outcome']


def test_group_failure_and_delayed_failure_return_to_repair(env):
    ids,s,r=origin(env);note(env,ids[0]);s=review(env,ids[0],count=2).json()
    command(env,s,'answer',question_id=s['questions'][0]['question_id'],option='A')
    command(env,s,'answer',question_id=s['questions'][1]['question_id'],option='B')
    done=command(env,s,'submit').json();assert done['review_outcome']['state']=='repair'
    original=next(m for m in env[1].get('/api/v4/mistakes',headers=headers()).json() if m['question_id']==ids[0]);assert original['records'][0]==r
    n=original['review']['notes'][-1]['id'];note(env,ids[0],previous=n)
    s=review(env,ids[0],key='after-repair').json();finish(env,s)
    env[2][0]+=24*3600
    result=review(env,ids[0],'delayed',key='exhausted')
    assert result.status_code==422 and '公共题库缺少' in result.text


def test_delayed_failure_is_not_hidden_by_later_correctness(env):
    ids,s,r=origin(env);note(env,ids[0]);finish(env,review(env,ids[0]).json());env[2][0]+=24*3600
    done=finish(env,review(env,ids[0],'delayed',key='fail-delayed').json(),'A')
    assert done['review_outcome']['outcome']=='failed' and done['review_outcome']['state']=='repair'


def test_review_rejects_scope_override_and_seen_retries(env):
    ids,s,r=origin(env);note(env,ids[0]);c=env[1]
    bad=c.post('/api/v4/sessions',headers=headers(),json={'mode':'practice','request_id':'bad','review_question':ids[0],'review_phase':'independent','question_ids':[ids[0]]})
    assert bad.status_code==422
    # All other public items have already appeared in a normal practice session.
    practice(env,ids[1:]);assert review(env,ids[0]).status_code==422


def test_diagnosis_deduplicates_retries_tracks_assistance_and_snapshots_topics(env):
    ids,s,r=origin(env);c=env[1]
    command(env,s,'retry',question_id=ids[0]);command(env,s,'answer',question_id=ids[0],option='B');command(env,s,'check',question_id=ids[0]);done=command(env,s,'submit').json()
    a=c.get('/api/v4/analysis',headers=headers()).json();t=next(x for x in a['topics'] if x['topic_id']=='2.5')
    assert t['independent_scored']==1 and t['first_incorrect']==1 and t['retries']['correct']==1
    assert next(x for x in a['topics'] if x['topic_id']=='7.5')['evidence']=='未评估'
    c.put('/api/v4/admin/questions/'+ids[0]+'/tags',headers=headers('admin'),json={'course_id':env[0].state.bank.catalog['course_id'],'core':['3.3'],'related':[]})
    still=c.get('/api/v4/sessions/'+s['id'],headers=headers()).json();assert still['questions'][0]['topics']['core']==['2.5']
    a=c.get('/api/v4/sessions/'+s['id']+'/analysis',headers=headers()).json();assert next(x for x in a['topics'] if x['topic_id']=='2.5')['first_incorrect']==1
    s2=practice(env,[ids[1]],1);command(env,s2,'assistance',question_id=ids[1],assisted=True);command(env,s2,'answer',question_id=ids[1],option='B');r2=command(env,s2,'check',question_id=ids[1]).json()['records'][0]
    assert r2['assisted'] and not r2['independent']


def test_multitopic_records_only_associated_and_exam_lock_covers_new_apis(env):
    ids,s,r=origin(env);c=env[1]
    c.put('/api/v4/admin/questions/'+ids[1]+'/tags',headers=headers('admin'),json={'course_id':env[0].state.bank.catalog['course_id'],'core':['2.5','3.3'],'related':['5.4']})
    s2=practice(env,[ids[1]],1);finish(env,s2,'A')
    a=c.get('/api/v4/analysis',headers=headers()).json()
    assert next(x for x in a['topics'] if x['topic_id']=='3.3')['independent_scored']==0
    assert next(x for x in a['topics'] if x['topic_id']=='3.3')['associated_only']==1
    assert c.get('/api/v4/sessions/'+s['id']+'/analysis',headers=headers('other')).status_code==404
    ex=exam(env,ids)
    assert c.get('/api/v4/analysis',headers=headers()).status_code==422
    assert note(env,ids[0]).status_code==422
    assert c.get('/api/v4/analysis',headers=headers('other')).status_code==200
    command(env,ex,'submit')


def test_no_current_reliable_answer_cannot_drive_diagnosis_or_review_pass(env):
    ids,s,r=origin(env);note(env,ids[0]);review_session=review(env,ids[0]).json();qid=review_session['questions'][0]['question_id']
    bank=env[0].state.bank;vid=bank.store.question(qid).current_version_id
    from gmf_v3.contracts import AnswerStatus
    key=bank.store.latest_answer(vid);bank.store.append_answer(vid,label=None,status=AnswerStatus.DISPUTED,evidence=[],expected_revision=key.revision)
    done=finish(env,review_session)
    assert done['review_outcome']['outcome']=='inconclusive' and done['review_outcome']['state']=='independent'
    a=env[1].get('/api/v4/sessions/'+review_session['id']+'/analysis',headers=headers()).json()
    t=next(x for x in a['topics'] if x['topic_id']=='2.5');assert t['independent_scored']==0 and t['ungraded']==1


def test_marking_review_pass_as_guessed_restores_optional_check_without_changing_grade(env):
    ids,s,r=origin(env);note(env,ids[0]);s=finish(env,review(env,ids[0]).json())
    rid=s['grade']['records'][0]['record_id'];grade=s['grade']
    assert env[1].post('/api/v4/learning/uncertain',headers=headers(),json={'record_id':rid}).status_code==200
    refreshed=env[1].get('/api/v4/sessions/'+s['id'],headers=headers()).json()
    assert refreshed['grade']==grade and refreshed['review_outcome_revision']['state']=='independent'
    case=next(m for m in env[1].get('/api/v4/mistakes',headers=headers()).json() if m['question_id']==ids[0])
    assert case['review']['state']=='independent'


def test_sufficient_evidence_threshold_is_explicit_and_uncertainty_never_counts_as_wrong(env):
    from reportlab.pdfgen.canvas import Canvas
    from test_v4 import upload
    p=env[3]/'six.pdf';pdf=Canvas(str(p),pagesize=(612,792))
    for n in range(1,7):
        for i,text in enumerate([f'{n}. A {n+20} kg cart receives {3*(n+20)} N. Use net F = ma.','(A) 1','(B) 3']):pdf.drawString(40,720-i*25,text)
        pdf.showPage()
    pdf.drawString(40,740,'Answer Key');pdf.drawString(40,700,'1 B  2 B  3 B  4 B  5 B  6 B');pdf.save()
    ids=upload(env,p,'six').files[0]['question_ids']
    for qid in ids:env[0].state.bank.publish(qid,'admin')
    s=practice(env,ids,6)
    for i,q in enumerate(s['questions']):command(env,s,'answer',question_id=q['question_id'],option='A' if i<3 else 'B')
    s=command(env,s,'submit').json();c=env[1]
    def topic():return next(t for t in c.get('/api/v4/analysis',headers=headers()).json()['topics'] if t['topic_id']=='2.5')
    assert topic()['independent_scored']==6 and topic()['priority']
    for r in s['grade']['records'][3:]:assert c.post('/api/v4/learning/uncertain',headers=headers(),json={'record_id':r['record_id']}).status_code==200
    t=topic();assert t['first_incorrect']==3 and t['first_correct']==3 and t['certain_independent']==3 and t['evidence']=='数据不足' and not t['priority']


def test_regrading_projects_a_new_ledger_revision_and_retains_original_answer(env):
    ids,s,r=origin(env);s=command(env,s,'submit').json();c=env[1];bank=env[0].state.bank
    old=c.get('/api/v4/sessions/'+s['id']+'/ledger',headers=headers()).json()
    c.put('/api/v4/admin/questions/'+ids[0]+'/tags',headers=headers('admin'),json={'course_id':bank.catalog['course_id'],'core':['3.3'],'related':[]})
    vid=r['version_id'];key=bank.store.latest_answer(vid);bank.answers.confirm(vid,label='A',reviewer='admin',reason='Source revision',expected_revision=key.revision)
    assert c.post('/api/v4/admin/sessions/'+s['id']+'/regrade',headers=headers('admin'),json={'reason':'verified source correction'}).status_code==200
    new=c.get('/api/v4/sessions/'+s['id']+'/ledger',headers=headers()).json()
    assert not {e['event_id'] for e in old['events']}&{e['event_id'] for e in new['events']}
    assert all(e['payload']['grading_revision']==2 for e in new['events'])
    assert all(e['topic_id']=='2.5' for e in new['events'])
    a=c.get('/api/v4/analysis',headers=headers()).json();t=next(t for t in a['topics'] if t['topic_id']=='2.5');assert t['first_correct']==1 and t['first_incorrect']==0
    assert c.post('/api/v4/learning/uncertain',headers=headers(),json={'record_id':r['record_id']}).status_code==200
    with bank.store.connect() as db:assert json.loads(db.execute('SELECT payload FROM v4_answers WHERE record_id=?',(r['record_id'],)).fetchone()[0])['status']=='incorrect'
