"""Private student DOCX parity, source-only grading, original fidelity and isolation."""
from docx import Document
from test_v4 import env,headers,command
from test_v41 import own_import,private_exam

def test_student_docx_preserves_original_and_ungraded_answers(env):
 app,client,clock,temp=env;path=temp/'private.docx';doc=Document()
 for line in ['1. Which direction is positive?','(A) Left','(B) Right']:doc.add_paragraph(line)
 doc.save(path);paper=own_import(env,path,'docx-v42');assert paper['summary']['mcq']==1;assert paper['summary']['unconfirmed_answers']==1
 job=client.get('/api/v4/papers/imports',headers=headers()).json()[0];url=f"/api/v4/papers/imports/{job['batch_id']}/{job['files'][0]['job_id']}/original"
 r=client.get(url,headers=headers());assert r.content==path.read_bytes();assert r.headers['content-type']=='application/vnd.openxmlformats-officedocument.wordprocessingml.document';assert client.get(url,headers=headers('other')).status_code==404
 s=private_exam(env,paper);qid=s['questions'][0]['question_id'];assert command(env,s,'answer',question_id=qid,option='A').status_code==200
 first=command(env,s,'submit').json();again=command(env,s,'submit').json();assert first['grade_id']==again['grade_id'];assert first['grade']['records'][0]['status']=='ungraded';assert first['grade']['records'][0]['selected']=='A';assert first['grade']['records'][0]['correct_answer'] is None

def test_private_import_rejects_unsupported_extension(env):
 r=env[1].post('/api/v4/papers/import',headers=headers(),files={'file':('bad.exe',b'test')},data={'request_key':'invalid'});assert r.status_code==422
