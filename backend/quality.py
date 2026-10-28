"""Read-only quality evidence and explicit immutable display-asset repair."""
import hashlib,json
from PIL import Image,ImageChops

def inspect_display(bank,q,v):
    m=bank.meta(v.version_id);assets=[];faults=[]
    for aid in m.get('safe_assets',[]):
        a=bank.store.asset(aid);p=bank.assets/a.relative_path
        row={'asset_id':aid,'page':a.page,'bbox':a.bbox,'sha256':a.sha256,'relative_path':a.relative_path}
        if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest()!=a.sha256:faults.append('missing_or_changed_asset')
        else:
            with Image.open(p) as im:
                im.load();row['pixels']=list(im.size)
                ink=ImageChops.difference(im.convert('RGB'),Image.new('RGB',im.size,'white')).convert('L')
                row['nonwhite_bbox']=ink.point(lambda p:255 if p>50 else 0).getbbox()
                if not row['nonwhite_bbox']:faults.append('blank_crop')
                if min(im.size)<16:faults.append('tiny_crop')
        assets.append(row)
    pages=[s.page for s in v.spans]
    if not assets or {a['page'] for a in assets}!=set(pages):faults.append('page_coverage')
    if [o.label for o in v.options]!=list('ABCD'):faults.append('option_labels')
    if any(b!=a+1 for a,b in zip(pages,pages[1:])):faults.append('nonconsecutive_pages')
    return {'question_id':q.question_id,'version_id':v.version_id,'unit':v.source_section,'source_number':q.source_number,'pages':pages,'assets':assets,'automated_faults':sorted(set(faults)),'parser_warnings':v.warnings,'visual_review':None,'quality_state':'confirmed_error' if faults else 'automatic_check_passed' if not v.warnings and not m.get('issues') else 'needs_visual_review'}

def attach_visual_review(record,evidence):
    if evidence.get('version_id')!=record['version_id'] or evidence.get('asset_sha256')!=[a['sha256'] for a in record['assets']]:raise ValueError('Review version/assets changed')
    if evidence.get('reviewer_kind') not in {'human','ai_visual'}:raise ValueError('Explicit visual reviewer kind required')
    if not evidence.get('notes') or evidence.get('outcome') not in {'pass','error','unresolved'}:raise ValueError('Visual findings required')
    state='confirmed_error' if record['automated_faults'] or evidence['outcome']=='error' else 'visual_review_passed' if evidence['outcome']=='pass' else 'needs_manual_review'
    return {**record,'visual_review':evidence,'quality_state':state}

def repair_display_rasters(bank,document_id):
    """Repaint audited boxes; retain old assets, identities, answer and student history."""
    import io,pdfplumber
    from gmf_v3.pdf_core import visual_top
    from gmf_v3.contracts import now
    source=bank.store.source(document_id);original=bank.assets/document_id/'original.pdf'
    if hashlib.sha256(original.read_bytes()).hexdigest()!=source.sha256:raise ValueError('Original PDF hash mismatch')
    with bank.store.connect() as c:raw=c.execute("SELECT payload FROM assets WHERE document_id=? AND json_extract(payload,'$.kind')='layout_json'",(document_id,)).fetchone()
    layouts={p['page']:p for p in json.loads((bank.assets/json.loads(raw[0])['relative_path']).read_text())} if raw else {}
    rows=[(q,v,bank.meta(v.version_id)) for q,v,_,_ in bank.store.list_questions(scope=source.scope,include_drafts=True,limit=None) if q.document_id==document_id]
    by_page={};replacements={};created=0
    for q,v,m in rows:
        if not m.get('audited'):raise ValueError('Existing bank audit required')
        for aid in m.get('safe_assets',[]):
            a=bank.store.asset(aid)
            if a.kind!='question_crop' or not a.bbox:raise ValueError('Audited display crop required')
            anchor=next((s.bbox[1] for s in v.spans if s.page==a.page),a.bbox[1])
            top=min(a.bbox[1],visual_top(layouts[a.page],a.bbox[0],anchor,a.bbox[2])) if a.page in layouts else a.bbox[1]
            by_page.setdefault(a.page,[]).append((a,top))
    with pdfplumber.open(original) as pdf:
        for pn,group in sorted(by_page.items()):
            page=pdf.pages[pn-1];im=page.to_image(resolution=144,antialias=True).original.convert('RGB')
            for a,top in group:
                x0,_,x1,y1=a.bbox;bbox=(x0,top,x1,y1)
                crop=im.crop((round(x0*im.width/page.width),round(top*im.height/page.height),round(x1*im.width/page.width),round(y1*im.height/page.height)))
                out=io.BytesIO();crop.save(out,format='PNG');data=out.getvalue();sha=hashlib.sha256(data).hexdigest()
                path=bank.assets/document_id/f'display-aa-{sha}.png'
                if not path.exists():path.write_bytes(data);created+=1
                identity=json.dumps([document_id,pn,bbox,'aa144',sha]);aid='asset_'+hashlib.sha256(identity.encode()).hexdigest()[:32]
                new=a.model_copy(update={'asset_id':aid,'relative_path':path.relative_to(bank.assets).as_posix(),'sha256':sha,'bbox':bbox})
                with bank.store.connect(write=True) as c:c.execute('INSERT OR IGNORE INTO assets VALUES(?,?,?)',(aid,document_id,new.model_dump_json()))
                replacements[a.asset_id]=aid
            im.close();page.close()
    with bank.store.connect(write=True) as c:
        for q,v,m in rows:
            after=[replacements[a] for a in m['safe_assets']]
            if after==m['safe_assets']:continue
            m.setdefault('display_asset_history',[]).append({'at':now(),'reason':'pdfplumber antialias144/1','source_sha256':source.sha256,'before':m['safe_assets'],'after':after})
            m['safe_assets']=after;bank.save_meta(v.version_id,m,c)
    return {'questions':len(rows),'pages':len(by_page),'new_assets':created,'source_sha256':source.sha256,'dpi':144,'antialias':True}
