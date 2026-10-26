"""Reproduce text extraction, cutting and authenticated import on supplied PDFs.
Always uses an isolated database; never modifies the live site's records.
"""
from pathlib import Path
import argparse, ast, json, re, subprocess, sys

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'as-v3-reference')]
import pdfplumber
from fastapi.testclient import TestClient
from backend.app import create_app
from gmf_v3.pdf_core import PDFProcessingCore, _native_lines, digest


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--pdf',action='append',type=Path,required=True)
    parser.add_argument('--data',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    if args.data.exists():raise SystemExit('Use a new isolated --data directory to preserve prior audit results.')
    baseline=ast.parse(subprocess.check_output(['git','show','d3544b5:as-v3-reference/gmf_v3/pdf_core.py'],cwd=ROOT,text=True,encoding='utf-8'))
    rules={n.targets[0].id:re.compile(ast.literal_eval(n.value.args[0]),re.I) for n in baseline.body if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name) and n.targets[0].id in ['QUESTION','OPTION']}
    app=create_app(args.data/'api',tokens={'audit':{'owner_id':'pipeline-audit','role':'student'}},worker=False)
    client=TestClient(app);headers={'Authorization':'Bearer audit'};reports=[]
    for index,path in enumerate(args.pdf):
        row={'filename':path.name,'sha256':digest(path.read_bytes()),'bytes':path.stat().st_size}
        print('EXTRACT',path.name,flush=True)
        pages=[]
        with pdfplumber.open(path) as pdf:
            for number,page in enumerate(pdf.pages,1):
                lines,two=_native_lines(page,number,'auto')
                pages.append({'page':number,'characters':sum(len(l.text) for l in lines),'old_question_candidates':sum(bool(rules['QUESTION'].match(l.text)) for l in lines),'old_option_markers':sum(len(list(rules['OPTION'].finditer(l.text))) for l in lines)})
        row['native_extraction']=pages
        print('CUT',path.name,flush=True)
        core=PDFProcessingCore(args.data/f'core-{index}')
        cut=core.parse(path,scope='exam_private',owner_id='pipeline-audit')
        row['cut']={'questions':len(cut.questions),'diagnostics':cut.diagnostics,'warnings':cut.warnings}
        print('IMPORT',path.name,'cut=',len(cut.questions),flush=True)
        with path.open('rb') as stream:
            upload=client.post('/api/v4/papers/import',headers=headers,files={'file':(path.name,stream,'application/pdf')},data={'request_key':f'audit-{index}','title':'解析验收 '+path.name,'duration_minutes':30})
        upload.raise_for_status();bid=upload.json()['batch_id']
        app.state.bank.jobs.work(limit=1,batch_id=bid)
        batch=app.state.bank.store.batch(bid);file=batch.files[0]
        row['full_import']={'batch_id':bid,'batch_status':batch.status,**file}
        if file.get('paper_id'):
            session=client.post('/api/v4/sessions',headers=headers,json={'mode':'exam','set_id':file['paper_id'],'request_id':f'exam-{index}'})
            session.raise_for_status();session=session.json();endpoint='/api/v4/sessions/'+session['id']
            for question in session['questions']:
                command=client.post(endpoint+'/commands',headers=headers,json={'type':'answer','question_id':question['question_id'],'option':'A'});command.raise_for_status()
            restored=client.get(endpoint,headers=headers).json()
            assert restored['deadline']==session['deadline'] and len(restored['answers'])==len(session['questions'])
            final=client.post(endpoint+'/commands',headers=headers,json={'type':'submit'});final.raise_for_status();final=final.json()
            row['exam']={'session_id':session['id'],'answers_restored':len(restored['answers']),'deadline_preserved':True,'status':final['status'],'summary':final['summary'],'shared_questions':[q['source_number'] for q in session['questions'] if q['shared_assets']],'cross_page_questions':[q['source_number'] for q in session['questions'] if len(q['assets'])>1]}
        reports.append(row)
        args.out.parent.mkdir(parents=True,exist_ok=True);args.out.write_text(json.dumps({'files':reports},ensure_ascii=False,indent=2),encoding='utf-8')
        print('RESULT',path.name,file['status'],file.get('summary'),row.get('exam',{}).get('summary'),flush=True)


if __name__=='__main__':main()
