"""Rebuild the local textbook dataset. No network calls, no textbook rewriting."""
import json,re,hashlib,shutil,sys
from pathlib import Path
import pypdfium2 as pdfium
import pdfplumber

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'source/university-physics-v1.pdf'
ORIGINAL=Path(r'C:\Users\wojia\Documents\WeChat Files\wxid_p0zhjzuxltsx22\FileStorage\File\2026-10\基础知识概论（力学）(1).pdf')
for folder in ['source','data','assets/pages']: (ROOT/folder).mkdir(parents=True,exist_ok=True)
if not SOURCE.exists(): shutil.copyfile(ORIGINAL,SOURCE)
doc=pdfium.PdfDocument(SOURCE)
pages=[]
for i in range(len(doc)):
    p=doc[i];t=p.get_textpage();header=t.get_text_bounded(0,750,612,792).strip()
    nums=[n for pair in re.findall(r'^([0-9]+)\s|\s([0-9]+)$',header) for n in pair if n]
    pages.append(dict(pdf_page=i+1,printed_page=int(nums[-1]) if nums else None,header=header,
        text=t.get_text_range().replace('\r\n','\n').replace('\r','\n'),
        mapping_method='printed_header' if nums else 'unnumbered_frontmatter'))
    t.close();p.close()
for i,p in enumerate(pages):
    if i>4 and i<len(pages)-1 and p['printed_page'] is None:
        a=pages[i-1]['printed_page'];b=pages[i+1]['printed_page']
        if a is not None and b==a+2:p.update(printed_page=a+1,mapping_method='chapter_opening_between_verified_neighbors')
byprint={p['printed_page']:p for p in pages if p['printed_page'] is not None}
def dump(name,obj): (ROOT/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf8')
dump('source/page-text.json',pages)
dump('data/page-map.json',[{k:v for k,v in p.items() if k!='text'} for p in pages])
ATTR={'book':'OpenStax University Physics Volume 1','publisher':'OpenStax / Rice University',
    'license':'CC BY-NC-SA 4.0','license_evidence':{'printed_page':1,'pdf_page':6},
    'license_text':pages[5]['text'][pages[5]['text'].find('University Physics is licensed'):pages[5]['text'].find('Because our books')],
    'source_file':'source/university-physics-v1.pdf','sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
    'figure_credit_policy':'Preserve individual caption credits; do not assume identical image licenses.',
    'omitted_printed_pages':list(range(863,875)),'unnumbered_pdf_pages':[1,2,3,4,5]}
dump('data/source-metadata.json',ATTR)
toc='\n'.join(p['text'] for p in pages[:5]);sections=[];chapters=[];ch=None
lines=[x.strip() for x in toc.splitlines() if x.strip()]
for i,line in enumerate(lines):
    m=re.fullmatch(r'CHAPTER (\d+)',line)
    if m:
        ch=int(m[1]);heading=lines[i+1];start=int(re.search(r'(\d+)$',heading)[1]);chapters.append({'chapter':ch,'title':re.sub(r'\s+\d+$','',heading),'printed_start':start})
    m=re.fullmatch(r'(\d+\.\d+) (.+) (\d+)',line)
    if m:sections.append({'source_id':'os-section-'+m[1],'section':m[1],'chapter':int(m[1].split('.')[0]),'title':m[2],'printed_start':int(m[3])})
    m=re.fullmatch(r'Chapter Review (\d+)',line)
    if m and ch: next(c for c in chapters if c['chapter']==ch)['review_start']=int(m[1])
for s in sections:
    later=[x['printed_start'] for x in sections if x['chapter']==s['chapter'] and x['printed_start']>s['printed_start']]
    end=min(later+[next(c for c in chapters if c['chapter']==s['chapter'])['review_start']])-1
    # Section starts often occur mid-page. Both boundary pages remain indexed.
    s['printed_end_exclusive_boundary']=end+1;s['start_pdf_page']=byprint[s['printed_start']]['pdf_page']
    s['status']='indexed';s['content_policy']='section_marker_to_next_section_marker; partial selectors are explicit in topic mapping'
dump('data/source-structure.json',{'chapters':chapters,'sections':sections})

# Frozen user decisions. Selectors describe a subset, never a new AP scope decision.
UNITS=[('Kinematics',[
('Scalars and Vectors','2.1;2.2;2.3','full; 2.4 is a reusable dot/cross-product math tool'),
('Displacement, Velocity, and Acceleration','3.1;3.2;3.3;3.4;3.5;3.6','full'),
('Representing Motion','3.1;3.2;3.3;3.4;3.5;3.6','position/velocity/acceleration graphs, slope, area, derivative/integral; reuse'),
('Reference Frames and Relative Motion','4.5','full'),('Motion in Two or Three Dimensions','4.1;4.2;4.3;4.4','full')]),
('Force and Translational Dynamics',[
('Systems and Center of Mass','5.3;9.6','5.3 system/internal/external force; 9.6 full'),
('Forces and Free-Body Diagrams','5.1;5.6;5.7;6.1','6.1 necessary FBD applications only'),
("Newton’s Third Law",'5.5','full'),("Newton’s First Law",'5.2;6.1','6.1 equilibrium only'),
("Newton’s Second Law",'5.3;6.1','full'),('Gravitational Force','5.4;13.1;13.2','retain uniform sphere/shell applications and figures; no added shell theorem derivation'),
('Kinetic and Static Friction','6.2','full'),('Spring Forces','5.6','Hooke law/spring force only; pure series and pure parallel supplement'),
('Resistive Forces','6.4','full'),('Circular Motion','4.4;6.3','full')]),
('Work, Energy, and Power',[
('Translational Kinetic Energy','7.2','full'),('Work','7.1;7.3','full'),('Potential Energy','8.1;8.2;8.4','full'),
('Conservation of Energy','8.3;8.4','full'),('Power','7.4','full')]),
('Linear Momentum',[
('Linear Momentum','9.1','full'),('Change in Momentum and Impulse','9.2','full'),
('Conservation of Linear Momentum','9.3;9.6','9.6 P_total = M v_cm only; main 9.6 belongs to 2.1'),
('Elastic and Inelastic Collisions','9.4;9.5','full')]),
('Torque and Rotational Dynamics',[
('Rotational Kinematics','10.1;10.2','full'),('Connecting Linear and Rotational Motion','10.3','full'),('Torque','10.6','full'),
('Rotational Inertia','10.4;10.5','10.4 moment-of-inertia content; 10.5 full'),
("Rotational Equilibrium and Newton’s First Law in Rotational Form",'12.1;12.2','full'),
("Newton’s Second Law in Rotational Form",'10.7','full')]),
('Energy and Momentum of Rotating Systems',[
('Rotational Kinetic Energy','10.4;11.1','10.4 rotational KE; 11.1 rolling energy'),('Torque and Work','10.8','full'),
('Angular Momentum and Angular Impulse','11.2','full'),('Conservation of Angular Momentum','11.3','full'),('Rolling','11.1','full'),
('Motion of Orbiting Satellites','13.3;13.4;13.5','gravitational PE, bound/unbound energy, circular/elliptical orbit, speed/period/energy, periapsis/apoapsis, Kepler II/III, angular momentum; omit advanced conic derivation/transfer orbits')]),
('Oscillations',[
('Defining Simple Harmonic Motion','15.1','full'),('Frequency and Period of SHM','15.1;15.4','mass-spring and simple-pendulum period/frequency only'),
('Representing and Analyzing SHM','15.1;15.3','15.1 x/v/a/phase/graphs; 15.3 full'),('Energy of Simple Harmonic Oscillators','15.2','full'),
('Simple and Physical Pendulums','15.4','simple and physical pendulums only; exclude torsional main content')])]
supplements=[
{'supplement_id':'ap-spring-combinations','ap_topic':'2.8','title':'AP Supplement · 纯串联与纯并联弹簧',
 'formulas':['纯串联：1/k_eq = Σ(1/k_i)','纯并联：k_eq = Σk_i'],'notes':['仅适用于纯串联或纯并联，不展开混合弹簧网络。']},
{'supplement_id':'ap-inertia-integrals','ap_topic':'5.4','title':'AP Supplement · 非均匀杆与圆盘/圆环',
 'formulas':['非均匀杆：dm = λ(x) dx','绕 x = a：I = ∫(x−a)² λ(x) dx','圆盘/圆环：dm = σ 2πr dr','I = ∫r² dm'],
 'notes':['积分上下限使用物体实际边界；圆盘从 0 到 R，圆环从 R_inner 到 R_outer。']},
{'supplement_id':'ap-rotational-work','ap_topic':'6.2','title':'AP Supplement · 转动功',
 'formulas':['W = ∫τ dθ'],'notes':['τ–θ 图的有符号面积等于转动功。']},
{'supplement_id':'ap-angular-impulse','ap_topic':'6.3','title':'AP Supplement · 角冲量',
 'formulas':['ΔL = ∫τ dt'],'notes':['τ–t 图的有符号面积等于角冲量，也等于 ΔL。']}]
topics=[];units=[]
for u,(title,items) in enumerate(UNITS,1):
    ids=[]
    for n,(name,refs,selector) in enumerate(items,1):
        tid=f'{u}.{n}';ids.append(tid)
        topics.append({'topic_id':tid,'ap_unit':u,'title':name,'source_refs':['os-section-'+s for s in refs.split(';')],
            'selection_rule':selector,'supplement_refs':[s['supplement_id'] for s in supplements if s['ap_topic']==tid],
            'status':'validated' if tid in ['2.5','5.4','7.5'] else 'mapped_pending_batch',
            'reading_refs':[],'exercise_refs':[]})
    units.append({'unit_id':u,'title':title,'topic_refs':ids,'exam_weighting':None,'exam_weighting_status':'not supplied in frozen request; not inferred'})
for s in sections:s['topic_refs']=[t['topic_id'] for t in topics if s['source_id'] in t['source_refs']]
dump('data/source-structure.json',{'chapters':chapters,'sections':sections})

pl=pdfplumber.open(SOURCE);assets={};readings=[];objects=[]
def pageasset(pp):
    p=byprint[pp];aid=f'os-pdf-page-{p["pdf_page"]:04d}'
    if aid not in assets:
        path=f'assets/pages/{p["pdf_page"]:04d}.png';pg=doc[p['pdf_page']-1]
        if not (ROOT/path).exists():pg.render(scale=2).to_pil().save(ROOT/path)
        pg.close()
        assets[aid]={'asset_id':aid,'path':path,'printed_page':pp,'pdf_page':p['pdf_page'],'width':612,'height':792,'source_ref':'source/university-physics-v1.pdf'}
    return aid
def marker(pp,phrase,last=False):
    page=pl.pages[byprint[pp]['pdf_page']-1]
    ls=[l for l in page.extract_text_lines() if l['top']>50 and phrase.lower() in l['text'].lower()]
    if not ls: raise ValueError(f'marker missing: {pp} {phrase}')
    return ls[-1 if last else 0]['top']-3
def segment(sid,section,pp,top=55,bottom=746):
    pg=pl.pages[byprint[pp]['pdf_page']-1];bb=[72,round(top,2),540,round(bottom,2)]
    text=pg.crop(tuple(bb)).extract_text() or ''
    item={'content_id':sid,'source_section':section,'asset_id':pageasset(pp),'bbox':bb,
          'printed_page':pp,'pdf_page':byprint[pp]['pdf_page'],'text_for_search':text,
          'authoritative_content':'original_page_region; math may not survive PDF text extraction','source_attribution':ATTR}
    readings.append(item)
    for l in pg.crop(tuple(bb)).extract_text_lines():
        m=re.search(r'\b(EXAMPLE|CHECK YOUR UNDERSTANDING)\s+(\d+\.\d+)',l['text'])
        if m:objects.append({'object_id':'os-'+m[1].lower().replace(' ','-')+'-'+m[2],'object_type':'example' if m[1]=='EXAMPLE' else 'check_your_understanding','number':m[2],'content_ref':sid,'printed_page':pp,'pdf_page':byprint[pp]['pdf_page'],'placement':'reading_flow'})
        elif l['text'].strip() in ['Strategy','Solution','Significance']:
            objects.append({'object_id':f'{sid}-'+l['text'].lower()+f'-{int(l["top"])}','object_type':l['text'].lower(),'content_ref':sid,'printed_page':pp,'pdf_page':byprint[pp]['pdf_page'],'placement':'reading_flow'})
    return sid
def add(tid,sid):next(t for t in topics if t['topic_id']==tid)['reading_refs'].append(sid)
for pp in range(202,212):
    sid=segment(f'os-reading-5.3-p{pp}','5.3',pp,marker(pp,"5.3 Newton's Second Law") if pp==202 else 55);add('2.5',sid)
for pp in range(249,265):
    sid=segment(f'os-reading-6.1-p{pp}','6.1',pp,marker(pp,'6.1 Solving Problems',last=True) if pp==249 else 55);add('2.5',sid)
# Shared section, with explicit content boundaries. Keep Example 10.8 intact, including its KE subpart.
for pp in [471,472,473,474]:
    top=marker(pp,'Moment of Inertia') if pp==471 else marker(pp,'EXAMPLE 10.8') if pp==472 else 55
    bottom=marker(pp,'Applying Rotational Kinetic Energy') if pp==474 else 746
    sid=segment(f'os-reading-10.4-inertia-p{pp}','10.4',pp,top,bottom);add('5.4',sid)
for pp in range(477,485):
    sid=segment(f'os-reading-10.5-p{pp}','10.5',pp,marker(pp,'10.5 Calculating') if pp==477 else 55);add('5.4',sid)
for pp in range(728,734):
    top=marker(pp,'15.4 Pendulums') if pp==728 else 55
    bottom=marker(pp,'Torsional Pendulum') if pp==733 else 746
    sid=segment(f'os-reading-15.4-simple-physical-p{pp}','15.4',pp,top,bottom);add('7.5',sid)

# Exercise crop parser: read left column then right column, preserve continuation and diagrams.
TYPES=['Conceptual Questions','Problems','Additional Problems','Challenge Problems']
exercises=[];category_starts={};section_starts={}
for ch in [5,6,10,15]:
    chapter=next(c for c in chapters if c['chapter']==ch)
    nextstart=next(c for c in chapters if c['chapter']==ch+1)['printed_start']
    current=None;etype=None;section=None
    for pp in range(chapter['review_start'],nextstart):
        pg=pl.pages[byprint[pp]['pdf_page']-1]
        columns=[(72,316.7),(316.8,600)]
        for col,(left,right) in enumerate(columns):
            bounds=[left,55,right,746];crop=pg.crop(tuple(bounds));ls=crop.extract_text_lines()
            events=[]
            for l in ls:
                txt=l['text'].strip();kind=None;value=None
                if txt in TYPES:kind='type';value=txt
                elif re.match(rf'^{ch}\.\d+\s',txt):kind='section';value=re.match(r'^(\d+\.\d+)',txt)[1]
                else:
                    m=re.match(r'^(\d+)\s*\.\s+(.+)',txt)
                    if etype and m and 0<=l['x0']-left<15:kind='exercise';value=int(m[1])
                if kind:events.append((l['top']-2,kind,value))
            # Detection of numbered entries must also work when the category first appears on this column.
            for l in ls:
                m=re.match(r'^(\d+)\s*\.\s+(.+)',l['text'].strip())
                if m and 0<=l['x0']-left<15 and not any(abs(e[0]-(l['top']-2))<.1 for e in events):events.append((l['top']-2,'exercise',int(m[1])))
            events.sort();cursor=55
            first_ex=next((v for y,k,v in events if k=='exercise'),None)
            # A column's leading continuation belongs to the preceding source number,
            # which may differ from the last object encountered in the other column.
            current=next((e for e in exercises if e['source_chapter']==ch and e['source_number']==first_ex-1),None) if first_ex else current
            for j,(y,k,v) in enumerate(events):
                if k=='type':
                    following=next((ev[2] for ev in events[j+1:] if ev[1]=='exercise'),None)
                    if following is not None:category_starts.setdefault(ch,{})[v]=following
                if k=='section':
                    following=events[j+1][2] if j+1<len(events) and events[j+1][1]=='exercise' else None
                    if following is not None:section_starts.setdefault(ch,[]).append((following,v))
            def append_region(end):
                if current is not None and end>cursor+1:
                    bb=[left,round(cursor,2),right,round(end,2)]
                    txt=pg.crop(tuple(bb)).extract_text() or ''
                    current['question_text']+='\n'+txt
                    current['render_refs'].append({'asset_id':pageasset(pp),'bbox':bb,'printed_page':pp,'pdf_page':byprint[pp]['pdf_page']})
            for y,kind,value in events:
                append_region(y)
                if kind=='type':etype=value;section=None;current=None
                elif kind=='section':section=value;current=None
                elif etype:
                    current={'exercise_id':f'os-ch{ch}-ex{value:03d}','source_chapter':ch,'source_section':section,'source_number':value,
                        'exercise_type':etype,'question_text':'','subparts':[],'image_refs':[],'render_refs':[],
                        'source_page':{'printed_page':pp,'pdf_page':byprint[pp]['pdf_page']},'ap_unit':None,'ap_topic':[],
                        'answer_ref':None,'source_attribution':{'book':ATTR['book'],'license':ATTR['license']},
                        'visibility':'hidden_pending_scope_review','text_status':'search transcription; original render is authoritative for formulas'}
                    exercises.append(current)
                cursor=y
            append_region(746)
    print('chapter',ch,'exercises',len([e for e in exercises if e['source_chapter']==ch]),flush=True)
for e in exercises:
    boundaries=category_starts.get(e['source_chapter'],{})
    eligible=[(n,kind) for kind,n in boundaries.items() if n<=e['source_number']]
    if eligible:e['exercise_type']=max(eligible)[1]
    # Section headings also apply by source-number interval within each review category.
    starts=section_starts.get(e['source_chapter'],[])
    category_min=boundaries.get(e['exercise_type'],0)
    next_categories=[n for n in boundaries.values() if n>category_min]
    category_end=min(next_categories) if next_categories else float('inf')
    matches=[(n,s) for n,s in starts if category_min<=n<category_end and n<=e['source_number']]
    e['source_section']=max(matches)[1] if matches else None
    if e['source_chapter']==6 and e['source_number']==24:
        for r in e['render_refs']:r['bbox'][3]=274
    if e['source_chapter']==6 and e['source_number']==27:
        e['render_refs'].append({'asset_id':pageasset(296),'bbox':[316.8,275,600,320],'printed_page':296,'pdf_page':byprint[296]['pdf_page']})
    # A Prince PDF float on printed p513 places the illustration for 123 below 120.
    if e['source_chapter']==10 and e['source_number']==120:
        for r in e['render_refs']:
            if r['printed_page']==513:r['bbox'][3]=449
    if e['source_chapter']==10 and e['source_number']==123:
        e['render_refs'].append({'asset_id':pageasset(513),'bbox':[316.8,450,552,637],'printed_page':513,'pdf_page':byprint[513]['pdf_page']})
    e['question_text']='\n'.join(pl.pages[r['pdf_page']-1].crop(tuple(r['bbox'])).extract_text() or '' for r in e['render_refs']).strip()
    e['subparts']=list(dict.fromkeys(re.findall(r'\(([a-z])\)',e['question_text'])))
    # Every cropped source region contains its dependent drawings, including unnumbered ones.
    e['image_refs']=[{'kind':'embedded_original_question_region','render_index':i} for i,r in enumerate(e['render_refs'])]
    nums=e['source_number'];ch=e['source_chapter'];sec=e['source_section'];topicids=[]
    if ch==5 and sec=='5.3':topicids=['2.5']
    if ch==6 and sec=='6.1':topicids=['2.5']
    if ch==10 and sec=='10.5':topicids=['5.4']
    if ch==10 and sec=='10.4' and nums in [12,54]:topicids=['5.4']
    if ch==15 and sec=='15.4' and nums!=14:topicids=['7.5']
    if ch==15 and nums in [61,62,63,64,65,66,72]:topicids=['7.5']
    if topicids:
        e['ap_topic']=topicids;e['ap_unit']=int(topicids[0].split('.')[0]);e['visibility']='visible'
        for tid in topicids:next(t for t in topics if t['topic_id']==tid)['exercise_refs'].append(e['exercise_id'])
    if ch==15 and nums in [61,62,63,64,65,66,72]:e['source_section']='15.4';e['scope_review']='manual: simple/physical pendulum; 64/65 also use collisions'

# Answer key references are detected by chapter/category/number, never by odd-number guesses.
answer_ch=None;answer_type=None
for p in pages:
    if p['pdf_page']<876:continue
    for line in p['text'].splitlines():
        line=line.strip();m=re.fullmatch(r'Chapter (\d+)',line)
        if m:answer_ch=int(m[1]);answer_type=None
        elif line in TYPES:answer_type=line
        elif answer_ch and answer_type:
            m=re.match(r'^(\d+)\s*\.(?:\s|$)',line)
            if m:
                e=next((x for x in exercises if x['source_chapter']==answer_ch and x['source_number']==int(m[1]) and x['exercise_type']==answer_type),None)
                if e:e['answer_ref']={'source_ref':'source/university-physics-v1.pdf','pdf_page':p['pdf_page'],'printed_page':p['printed_page'],'chapter':answer_ch,'number':e['source_number'],'category':answer_type}

# Figure index for all AP-linked source sections. Preserve caption and credits verbatim.
figures=json.loads((ROOT/'data/figures.json').read_text(encoding='utf8')) if '--reuse-figure-index' in sys.argv else []
currentsection=None;usedsections={r.replace('os-section-','') for t in topics for r in t['source_refs']}|{'2.4'}
for p in ([] if '--reuse-figure-index' in sys.argv else pages[5:]):
    pp=p['printed_page'];text=p['text']
    for m in re.finditer(r'FIGURE\s+(\d+\.\d+)\s+(.+?)(?=\n\s*\n|$)',text,re.S):
        number=m[1];ch=int(number.split('.')[0]);c=next((c for c in chapters if c['chapter']==ch),None)
        if not c or pp is None:continue
        possible=[s for s in sections if s['chapter']==ch and s['printed_start']<=pp]
        s=max(possible,key=lambda s:s['printed_start']) if possible else None
        if not s or (s['section'] not in usedsections and pp<c['review_start']):continue
        caption=m[2].strip()
        # Captions use smaller type than body text. Read their actual PDF character runs.
        pg=pl.pages[p['pdf_page']-1];ls=pg.extract_text_lines(return_chars=True)
        found=next((i for i,l in enumerate(ls) if re.match(r'FIGURE\s+'+re.escape(number)+r'\b',l['text'])),None)
        if found is not None:
            caplines=[ls[found]['text']]
            for line in ls[found+1:]:
                if max((c['size'] for c in line['chars']),default=0)>8 or line['text'].startswith('FIGURE'):break
                caplines.append(line['text'])
            caption=re.sub(r'^FIGURE\s+'+re.escape(number)+r'\s*','',' '.join(caplines))
        credits=re.findall(r'\(credit[^:)]*:\s*(?:[^()]|\([^()]*\))*\)',caption,re.I|re.S)
        relevant=[r for r in readings if r['pdf_page']==p['pdf_page'] and re.search(r'FIGURE\s+'+re.escape(number)+r'\b',r['text_for_search'])]
        figures.append({'figure_id':'os-figure-'+number,'figure_number':number,'caption':caption,'individual_credit':credits,
            'source_section':s['section'] if pp<c['review_start'] else None,'printed_page':pp,'pdf_page':p['pdf_page'],
            'source_attribution':{'book':ATTR['book'],'license':ATTR['license'],'individual_license':'not assumed'},
            'asset_id':pageasset(pp) if relevant else None,'reading_refs':[r['content_id'] for r in relevant],
            'retention_status':'preserved_in_original_reading_region' if relevant else 'indexed_pending_batch',
            'caption_text_status':'PDF text extraction; original caption region is authoritative'})
for f in figures:f['individual_credit']=re.findall(r'\(credit[^:)]*:\s*(?:[^()]|\([^()]*\))*\)',f['caption'],re.I|re.S)
dump('data/figures.json',figures);dump('data/reading-content.json',readings);dump('data/reading-objects.json',objects)
for e in exercises:
    e['dependency_refs']=[]
    for num in re.findall(r'Figure\s+(\d+\.\d+)',e['question_text']):
        f=next((f for f in figures if f['figure_number']==num),None)
        if f:e['dependency_refs'].append({'kind':'figure','figure_number':num,'pdf_page':f['pdf_page'],'printed_page':f['printed_page']})
    if re.search(r'previous (problem|question)',e['question_text'],re.I):
        previous=next((x for x in exercises if x['source_chapter']==e['source_chapter'] and x['source_number']==e['source_number']-1),None)
        if previous:e['dependency_refs'].append({'kind':'exercise','exercise_id':previous['exercise_id'],'source_number':previous['source_number']})
dump('data/exercises.json',exercises);dump('data/assets.json',list(assets.values()));dump('data/supplements.json',supplements)
reviews=[]
for ch in sorted({int(r.replace('os-section-','').split('.')[0]) for t in topics for r in t['source_refs']}):
    reviews.append({'chapter':ch,'title':f'Chapter {ch} · 本章课后习题','status':'representative_extraction' if ch in [5,6,10,15] else 'pending_batch',
        'categories':{kind:[e['exercise_id'] for e in exercises if e['source_chapter']==ch and e['exercise_type']==kind and e['visibility']=='visible'] for kind in TYPES}})
dump('data/chapter-reviews.json',reviews)
course={'course_id':'ap-physics-c-mechanics-2026-27','framework':'user-frozen 2026–27 / May 2027','units':units,'topics':topics,
        'hidden_source_sections':['8.5','9.7','12.3','12.4','11.4','13.6','13.7','15.5','15.6'],
        'math_tool_refs':['os-section-2.4'],'validation_stage':'three representative topics; stop for user acceptance'}
dump('data/course.json',course)
payload={'course':course,'readings':readings,'objects':objects,'exercises':exercises,'assets':list(assets.values()),'supplements':supplements,'reviews':reviews,'figures':figures,'source':ATTR}
(ROOT/'data/textbook.js').write_text('window.PathlineTextbook = '+json.dumps(payload,ensure_ascii=False)+';\n',encoding='utf8')
print('topics',len(topics),'readings',len(readings),'figures',len(figures),'assets',len(assets),'exercises',len(exercises),flush=True)
