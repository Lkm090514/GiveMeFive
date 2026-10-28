import pytest
from backend.quality import attach_visual_review

def test_review_requires_exact_version_assets_and_explicit_visual_reviewer():
    row={'version_id':'v1','assets':[{'sha256':'a'}],'automated_faults':[]}
    e={'version_id':'v1','asset_sha256':['a'],'reviewer_kind':'ai_visual','outcome':'pass','notes':'Compared full source/crops.'}
    assert attach_visual_review(row,e)['quality_state']=='visual_review_passed'
    assert 'visual_review' not in row
    for change in [{'version_id':'v2'},{'asset_sha256':['b']},{'reviewer_kind':'auto'},{'notes':''}]:
        with pytest.raises(ValueError):attach_visual_review(row,{**e,**change})
    assert attach_visual_review({**row,'automated_faults':['blank_crop']},e)['quality_state']=='confirmed_error'

def test_fraction_top_includes_numerator_but_not_previous_question():
    from gmf_v3.pdf_core import visual_top
    layout={'lines':[{'x0':60,'x1':140,'top':53,'bottom':65}],'geometry':[{'x0':95,'x1':130,'top':81.36,'bottom':89.44},{'x0':95,'x1':130,'top':40,'bottom':48}]}
    assert visual_top(layout,0,85.73,612)==pytest.approx(78.36)
    layout['lines'].append({'x0':60,'x1':140,'top':75,'bottom':83})
    assert visual_top(layout,0,85.73,612)==85.73

def test_footer_tightening_preserves_bottom_physics_and_original(tmp_path):
    from backend.bank import Bank
    from gmf_v3.contracts import QuestionAsset
    from gmf_v3.pdf_core import digest
    from PIL import Image,ImageDraw
    b=Bank(tmp_path/'bank');folder=b.assets/'doc_test';folder.mkdir()
    with b.store.connect(write=True) as c:c.execute('INSERT INTO documents VALUES(?,?,?,?)',('doc_test','bank','test','{}'))
    path=folder/'original.png';im=Image.new('RGB',(612,792),'white');d=ImageDraw.Draw(im);d.rectangle((100,700,350,730),fill='black');d.line((36,756,576,756),fill='black');im.save(path)
    a=QuestionAsset(asset_id='a',document_id='doc_test',kind='question_crop',relative_path='doc_test/original.png',sha256=digest(path.read_bytes()),page=1,bbox=(0,0,612,792),media_type='image/png')
    layout={'width':612,'height':792,'lines':[{'text':'(D) final option','x0':100,'top':700,'bottom':730},{'text':'AP Physics C: Mechanics Page 1 of 18','x0':36,'top':770,'bottom':780}],'geometry':[{'x0':100,'x1':350,'top':700,'bottom':730},{'x0':36,'x1':576,'top':756,'bottom':756}]}
    result=b.store.asset(b.display_crop(a,layout,None));assert result.bbox[3]==738;assert digest(path.read_bytes())==a.sha256
    with Image.open(b.assets/result.relative_path) as image:assert image.getpixel((120,720))==(0,0,0)

def test_aa_repair_idempotent_preserves_versions_and_answer_history(tmp_path,monkeypatch):
    from pathlib import Path
    import pdfplumber.page
    from backend.bank import Bank
    from backend.quality import repair_display_rasters
    seen=[];old=pdfplumber.page.Page.to_image
    def render(page,*a,**kw):seen.append(kw);return old(page,*a,**kw)
    monkeypatch.setattr(pdfplumber.page.Page,'to_image',render)
    b=Bank(tmp_path/'bank');batch=b.enqueue_import([Path(__file__).parent/'fixtures/v4-mixed.pdf'],scope='bank',owner_id='test',auto_solve=False,ocr=False);b.jobs.work(limit=1,batch_id=batch.batch_id)
    did=b.store.batch(batch.batch_id).files[0]['document_id'];rows=b.store.list_questions(scope='bank',include_drafts=True,limit=None)
    before=[(q.question_id,v.model_dump_json(),a.model_dump_json() if a else None) for q,v,_,a in rows]
    repair_display_rasters(b,did);meta=[b.meta(v.version_id) for _,v,_,_ in rows];assert repair_display_rasters(b,did)['new_assets']==0
    assert meta==[b.meta(v.version_id) for _,v,_,_ in rows]
    assert before==[(q.question_id,v.model_dump_json(),a.model_dump_json() if a else None) for q,v,_,a in b.store.list_questions(scope='bank',include_drafts=True,limit=None)]
    assert seen and all(kw['antialias'] is True for kw in seen)
