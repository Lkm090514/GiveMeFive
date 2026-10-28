"""Fill one frozen Unit from the supplied PDF. Source text/images are never rewritten."""
import argparse,json,re,hashlib,sys
from pathlib import Path
import pdfplumber
import pypdfium2 as pdfium
sys.stdout.reconfigure(encoding='utf-8')
R=Path(__file__).resolve().parents[1]
load=lambda name:json.loads((R/'data'/name).read_text(encoding='utf-8'))
dump=lambda name,value:(R/'data'/name).write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
parser=argparse.ArgumentParser();parser.add_argument('--unit',type=int,required=True,choices=range(1,8));args=parser.parse_args()
course=load('course.json');structure=load('source-structure.json');meta=load('source-metadata.json')
assert hashlib.sha256((R/meta['source_file']).read_bytes()).hexdigest()==meta['sha256'],'Source PDF changed'
page_map=load('page-map.json');byprint={p['printed_page']:p['pdf_page'] for p in page_map if p['printed_page'] is not None}
assert all(p not in byprint for p in range(863,875))
sections={s['section']:s for s in structure['sections']};chapters={c['chapter']:c for c in structure['chapters']}
topics={t['topic_id']:t for t in course['topics']};baseline=json.loads((R/'scripts/content-baseline.json').read_text(encoding='utf-8'))
assets={a['asset_id']:a for a in load('assets.json')};readings={r['content_id']:r for r in load('reading-content.json')}
objects={o['object_id']:o for o in load('reading-objects.json')};exercises={e['exercise_id']:e for e in load('exercises.json')};figures=load('figures.json')
pdf=pdfplumber.open(R/meta['source_file']);renderer=pdfium.PdfDocument(R/meta['source_file'])
TYPES=['Conceptual Questions','Problems','Additional Problems','Challenge Problems']
BASE={'2.5','5.4','7.5'}
def page(pp):return pdf.pages[byprint[pp]-1]
def lines(pp):return page(pp).extract_text_lines()
def mark(pp,phrase,last=False):
    matches=[l for l in lines(pp) if 52<l['top']<746 and phrase.casefold() in l['text'].casefold()]
    if not matches:raise ValueError(f'Missing boundary: printed {pp} / {phrase}')
    return round(matches[-1 if last else 0]['top']-3,2)
def heading(pp,section):
    matches=[l for l in lines(pp) if 52<l['top']<746 and re.match(r'^'+re.escape(section)+r'\s',l['text'])]
    if not matches:raise ValueError(f'Missing section heading: {pp} / {section}')
    return round(matches[-1]['top']-3,2)
def asset(pp):
    number=byprint[pp];aid=f'os-pdf-page-{number:04d}';path=f'assets/pages/{number:04d}.png'
    if aid not in assets:
        if not (R/path).exists():
            pg=renderer[number-1];pg.render(scale=2).to_pil().save(R/path);pg.close()
        assets[aid]={'asset_id':aid,'path':path,'printed_page':pp,'pdf_page':number,'width':612,'height':792,'source_ref':meta['source_file']}
    return aid
def region(section,pp,top=55,bottom=746):
    top=round(top,2);bottom=round(bottom,2)
    if bottom-top<2:return None
    bb=[72,top,540,bottom]
    # Reuse an already verified region if its geometry matches exactly.
    existing=next((r for r in readings.values() if r['source_section']==section and r['printed_page']==pp and r['bbox']==bb),None)
    if existing:return existing['content_id']
    key=f'os-content-{section}-p{pp}-{str(top).replace(".","_")}-{str(bottom).replace(".","_")}'
    if key in readings:return key
    text=page(pp).crop(tuple(bb)).extract_text() or ''
    assert text.strip(),f'Empty source crop {key}'
    readings[key]={'content_id':key,'source_section':section,'asset_id':asset(pp),'bbox':bb,'printed_page':pp,'pdf_page':byprint[pp],
        'text_for_search':text,'authoritative_content':'original_page_region; math may not survive PDF text extraction','source_attribution':meta}
    for l in page(pp).crop(tuple(bb)).extract_text_lines():
        m=re.search(r'\b(EXAMPLE|CHECK YOUR UNDERSTANDING)\s+(\d+\.\d+)',l['text'])
        if m:
            oid='os-'+m[1].lower().replace(' ','-')+'-'+m[2]
            if oid in objects:
                o=objects[oid];o['content_refs']=list(dict.fromkeys([o['content_ref'],*o.get('content_refs',[]),key]))
            else:objects[oid]={'object_id':oid,'object_type':'example' if m[1]=='EXAMPLE' else 'check_your_understanding','number':m[2],'content_ref':key,'printed_page':pp,'pdf_page':byprint[pp],'placement':'reading_flow'}
        elif l['text'].strip() in ['Strategy','Solution','Significance']:
            oid=f'{key}-{l["text"].lower()}-{int(l["top"])}'
            objects[oid]={'object_id':oid,'object_type':l['text'].lower(),'content_ref':key,'printed_page':pp,'pdf_page':byprint[pp],'placement':'reading_flow'}
    return key
def span(section,start,end,top=None,bottom=None):
    return [rid for pp in range(start,end+1) if (rid:=region(section,pp,top if pp==start and top is not None else 55,bottom if pp==end and bottom is not None else 746))]
def full(section):
    s=sections[section];start=s['printed_start'];end=s['printed_end_exclusive_boundary']
    later=next((x for x in sections.values() if x['chapter']==s['chapter'] and x['printed_start']==end),None)
    bottom=heading(end,later['section']) if later else mark(end,'Chapter Review')
    return span(section,start,end,heading(start,section),bottom)
def source_goals(section):
    pp=sections[section]['printed_start'];ls=lines(pp);top=heading(pp,section);result=[];current=None
    for l in ls:
        if l['top']<=top:continue
        text=l['text'].strip()
        if text.startswith('•'):
            if current:result.append(current)
            current=text.lstrip('• ').strip()
        elif current and l['x0']>84 and l['top']<740:current+=' '+text
        elif current:
            result.append(current);break
    if current and (not result or result[-1]!=current):result.append(current)
    return result
def selected(tid):
    t=topics[tid]
    if tid=='1.1':return sum([full(s) for s in ['2.1','2.2','2.3','2.4']],[])
    if tid=='1.3':return (span('3.1',100,102,mark(100,'Average Velocity'),heading(102,'3.2'))+full('3.2')+
        span('3.3',110,115,mark(110,'Instantaneous Acceleration'),heading(115,'3.4'))+
        span('3.4',116,117,mark(116,'Displacement and Position from Velocity'),mark(117,'Solving for Final Velocity'))+full('3.6'))
    if tid=='2.1':return span('5.3',202,203,mark(202,'We defined external force'),mark(203,'It seems reasonable'))+full('9.6')
    if tid in ['2.2','2.4']:
        main=sum([full(s.replace('os-section-','')) for s in t['source_refs'] if s!='os-section-6.1'],[])
        return main+span('6.1',249,253,heading(249,'6.1'),mark(253,'Particle Acceleration'))
    if tid=='2.8':return span('5.6',228,229,mark(228,'Spring force'),mark(229,'Real Forces and Inertial Frames'))
    if tid=='4.3':return full('9.3')+span('9.6',431,432,mark(431,'Center of Mass and Conservation of Momentum'),mark(432,'EXAMPLE 9.19'))
    if tid=='6.1':return full('10.4')+span('11.1',521,523,mark(521,'Conservation of Mechanical Energy in Rolling Motion'),heading(523,'11.2'))
    if tid=='6.6':return (full('13.3')+full('13.4')+
        span('13.5',624,625,heading(624,'13.5'),mark(625,'An ellipse has several mathematical forms'))+
        span('13.5',627,627,mark(627,'To determine the velocities for the ellipse'),mark(627,'We end this discussion'))+
        span('13.5',628,630,mark(628,'Kepler’s Second Law'),heading(630,'13.6')))
    if tid=='7.2':return (span('15.1',710,711,mark(710,'Period and Frequency in Oscillations'),mark(711,'Characteristics of Simple Harmonic Motion'))+
        span('15.1',716,716,mark(716,'The Period and Frequency of a Mass on a Spring'))+
        span('15.4',729,730,55,mark(730,'Physical Pendulum')))
    if tid=='7.3':return (span('15.1',712,716,mark(712,'Equations of SHM'),mark(716,'The Period and Frequency of a Mass on a Spring'))+
        span('15.1',717,718,55,heading(718,'15.2'))+full('15.3'))
    return sum([full(ref.replace('os-section-','')) for ref in t['source_refs']],[])

def extract_chapter(ch):
    if any(e['source_chapter']==ch for e in exercises.values()):return
    parsed=[];category_starts={};section_starts=[];etype=None;section=None;current=None
    first_formal=None
    for pp in range(chapters[ch]['review_start'],chapters[ch+1]['printed_start']):
        pg=page(pp)
        if first_formal is None:
            starts=[l['top']-2 for l in pg.extract_text_lines() if l['text'].strip()=='Conceptual Questions']
            if starts:first_formal=(pp,min(starts))
        cutoff=first_formal[1] if first_formal and pp==first_formal[0] else 55
        for left,right in [(72,316.7),(316.8,600)]:
            ls=pg.crop((left,55,right,746)).extract_text_lines();events=[]
            for l in ls:
                txt=l['text'].strip();kind=None;value=None
                if txt in TYPES:kind='type';value=txt
                elif re.match(rf'^{ch}\.\d+\s',txt):kind='section';value=re.match(r'^(\d+\.\d+)',txt)[1]
                else:
                    m=re.match(r'^(\d+)\s*\.\s+(.+)',txt)
                    if m and 0<=l['x0']-left<15:kind='exercise';value=int(m[1])
                if kind and l['top']-2>=cutoff:events.append((round(l['top']-2,2),kind,value))
            events.sort();cursor=cutoff;first=next((v for y,k,v in events if k=='exercise'),None)
            if first:current=next((e for e in parsed if e['source_number']==first-1),None)
            for j,(y,k,v) in enumerate(events):
                following=next((ev[2] for ev in events[j+1:] if ev[1]=='exercise'),None)
                if k=='type' and following is not None:category_starts.setdefault(v,following)
                if k=='section' and j+1<len(events) and events[j+1][1]=='exercise':section_starts.append((following,v))
            def append(end):
                if current is not None and end>cursor+1 and (pg.crop((left,cursor,right,end)).extract_text() or '').strip():
                    current['render_refs'].append({'asset_id':asset(pp),'bbox':[left,cursor,right,end],'printed_page':pp,'pdf_page':byprint[pp]})
            for y,kind,value in events:
                append(y)
                if kind=='type':etype=value;section=None;current=None
                elif kind=='section':section=value;current=None
                elif etype:
                    current={'exercise_id':f'os-ch{ch}-ex{value:03d}','source_chapter':ch,'source_section':section,'source_number':value,'exercise_type':etype,
                        'question_text':'','subparts':[],'image_refs':[],'render_refs':[],'source_page':{'printed_page':pp,'pdf_page':byprint[pp]},
                        'ap_unit':None,'ap_topic':[],'answer_ref':None,'source_attribution':{'book':meta['book'],'license':meta['license']},
                        'visibility':'visible','text_status':'search transcription; original render is authoritative for formulas'}
                    parsed.append(current)
                cursor=y
            append(746)
    assert parsed and sorted(e['source_number'] for e in parsed)==list(range(1,max(e['source_number'] for e in parsed)+1)),f'Noncontiguous chapter {ch}'
    for e in parsed:
        n=e['source_number'];choices=[(start,kind) for kind,start in category_starts.items() if start<=n];e['exercise_type']=max(choices)[1]
        start=category_starts[e['exercise_type']];end=min([s for s in category_starts.values() if s>start]+[100000])
        applicable=[(s,sec) for s,sec in section_starts if start<=s<end and s<=n];e['source_section']=max(applicable)[1] if applicable else None
        e['question_text']='\n'.join(page(r['printed_page']).crop(tuple(r['bbox'])).extract_text() or '' for r in e['render_refs']).strip()
        e['subparts']=list(dict.fromkeys(re.findall(r'\(([a-z])\)',e['question_text'])))
        e['image_refs']=[{'kind':'embedded_original_question_region','render_index':i} for i,r in enumerate(e['render_refs'])]
        assert e['question_text'] and e['render_refs']
        exercises[e['exercise_id']]=e
    print('Parsed Chapter',ch,'unique exercises',len(parsed),flush=True)

def repair_review_boundaries():
    # Prince lays the first question row below summaries across both columns.
    # Earlier extraction accidentally attached the opposite column's summary to a question.
    suspect={e['source_chapter'] for e in exercises.values() if '•' in e['question_text']}
    baseline_ids={e['exercise_id'] for e in baseline['exercises']}
    for ch in suspect:
        first=None
        for pp in range(chapters[ch]['review_start'],chapters[ch+1]['printed_start']):
            matches=[l for l in lines(pp) if l['text'].strip()=='Conceptual Questions']
            if matches:first=(pp,min(l['top']-2 for l in matches));break
        if not first:continue
        pp,cutoff=first;starts=[]
        for left,right in [(72,316.7),(316.8,600)]:
            ls=[l for l in page(pp).crop((left,cutoff,right,746)).extract_text_lines()]
            for i,l in enumerate(ls):
                m=re.match(rf'^({ch}\.\d+)\s',l['text'])
                if m:
                    nextnumber=next((int(n[1]) for ll in ls[i+1:] if (n:=re.match(r'^(\d+)\s*\.\s',ll['text']))),None)
                    if nextnumber:starts.append((nextnumber,m[1]))
        for e in exercises.values():
            if e['source_chapter']!=ch or e['exercise_type']!='Conceptual Questions' or e['exercise_id'] in baseline_ids:continue
            refs=[]
            for ref in e['render_refs']:
                ref=dict(ref);ref['bbox']=list(ref['bbox'])
                if ref['printed_page']==pp:ref['bbox'][1]=max(ref['bbox'][1],round(cutoff,2))
                if ref['bbox'][1]<ref['bbox'][3] and (page(ref['printed_page']).crop(tuple(ref['bbox'])).extract_text() or '').strip():refs.append(ref)
            e['render_refs']=refs
            e['question_text']='\n'.join(page(r['printed_page']).crop(tuple(r['bbox'])).extract_text() or '' for r in refs).strip()
            e['image_refs']=[{'kind':'embedded_original_question_region','render_index':i} for i in range(len(refs))]
            if e['source_page']['printed_page']==pp:
                valid=[(n,sec) for n,sec in starts if n<=e['source_number']]
                if valid:e['source_section']=max(valid)[1]
    # Printed p747 has an Additional Problems row that spans both columns.
    e55=exercises.get('os-ch15-ex055');e56=exercises.get('os-ch15-ex056')
    if e55 and e56:
        boundary=mark(747,'Additional Problems')
        for ref in e55['render_refs']:
            if ref['printed_page']==747:ref['bbox'][3]=min(ref['bbox'][3],boundary)
        extra={'asset_id':asset(747),'bbox':[316.8,mark(747,'spring without the mass attached'),600,746],'printed_page':747,'pdf_page':byprint[747]}
        if extra not in e56['render_refs']:e56['render_refs'].insert(1,extra)
        for e in [e55,e56]:
            e['question_text']='\n'.join(page(r['printed_page']).crop(tuple(r['bbox'])).extract_text() or '' for r in e['render_refs']).strip()
            e['subparts']=list(dict.fromkeys(re.findall(r'\(([a-z])\)',e['question_text'])))
            e['image_refs']=[{'kind':'embedded_original_question_region','render_index':i} for i in range(len(e['render_refs']))]

def applicable(tid,e):
    curated={'2.8':{f'os-ch5-ex{n:03d}' for n in [86,87,88,89,102]}}
    if e['exercise_id'] in curated.get(tid,set()):return True
    sec=e['source_section'];text=e['question_text'].casefold();refs={r.replace('os-section-','') for r in topics[tid]['source_refs']}
    if sec not in refs and not(tid=='1.1' and sec=='2.4'):return False
    if tid=='1.3':return sec=='3.6' or any(x in text for x in ['graph','plot','slope','function','v(t)','x(t)','a(t)'])
    if tid=='2.1' and sec=='5.3':return any(x in text for x in ['system','internal','external'])
    if tid=='2.2' and sec=='6.1':return any(x in text for x in ['free-body','free body','diagram','sketch','draw'])
    if tid=='2.4' and sec=='6.1':return any(x in text for x in ['equilibrium','at rest','stationary','constant speed','constant velocity','hanging','suspended']) and not any(x in text for x in ['accelerat','pulley','barge'])
    if tid=='2.8':return 'spring' in text or 'hooke' in text
    if tid=='4.3' and sec=='9.6':return 'momentum' in text or 'velocity' in text
    if tid=='6.1' and sec=='10.4':return e['source_number'] not in [12,54]
    if tid=='6.1' and sec=='11.1':return any(x in text for x in ['energy','work','height','bottom','hill','incline'])
    if tid=='6.6':return not any(x in text for x in ['hohmann','transfer orbit','eccentricity','conic'])
    if tid=='7.2':return any(x in text for x in ['period','frequency','length','pendulum','spring']) and not any(x in text for x in ['torsion','physical pendulum','damping'])
    if tid=='7.3' and sec=='15.1':return any(x in text for x in ['graph','position','velocity','acceleration','phase','function','equation'])
    return True

unit=next(u for u in course['units'] if u['unit_id']==args.unit)
for ch in sorted({int(r.replace('os-section-','').split('.')[0]) for tid in unit['topic_refs'] for r in topics[tid]['source_refs']}):extract_chapter(ch)
repair_review_boundaries()
for tid in unit['topic_refs']:
    if tid not in BASE:
        topics[tid]['reading_refs']=list(dict.fromkeys(selected(tid)))
        goal_sections={'1.3':['3.2','3.3','3.6'],'2.1':['9.6'],'2.2':['5.1','5.6','5.7'],'2.4':['5.2'],'4.3':['9.3']}.get(tid,[ref.replace('os-section-','') for ref in topics[tid]['source_refs']])
        goals=list(dict.fromkeys(g for sec in goal_sections for g in source_goals(sec)))
        if tid=='7.2':goals=[g for g in goals if 'period' in g.casefold() or 'frequency' in g.casefold()];goals=[g for g in goals if 'physical pendulum' not in g.casefold() and 'torsional' not in g.casefold()]
        topics[tid]['learning_goals']=goals
        topics[tid]['exercise_refs']=[e['exercise_id'] for e in exercises.values() if applicable(tid,e)]
        assert topics[tid]['reading_refs'] and topics[tid]['exercise_refs'],f'Empty Topic {tid}'
    topics[tid]['status']='validated';topics[tid]['content_status']='content_ready';topics[tid]['exercise_status']='exercise_ready'
    for eid in topics[tid]['exercise_refs']:
        e=exercises[eid];e['ap_topic']=list(dict.fromkeys([*e['ap_topic'],tid]));e['ap_unit']=e['ap_unit'] or args.unit;e['visibility']='visible'

# Index actual figure appearances without changing original captions or credits.
for f in figures:
    actual=[r['content_id'] for r in readings.values() if r['pdf_page']==f['pdf_page'] and re.search(r'FIGURE\s+'+re.escape(f['figure_number'])+r'\b',r['text_for_search'])]
    if actual:f['asset_id']=asset(f['printed_page']);f['reading_refs']=list(dict.fromkeys([*f.get('reading_refs',[]),*actual]));f['retention_status']='preserved_in_original_reading_region'

# Answer references use the existing per-page map, not an assumed offset/odd-number rule.
page_text=json.loads((R/'source/page-text.json').read_text(encoding='utf-8'));answer_ch=None;answer_type=None
for p in page_text:
    if p['pdf_page']<876:continue
    for line in p['text'].splitlines():
        line=line.strip();m=re.fullmatch(r'Chapter (\d+)',line)
        if m:answer_ch=int(m[1]);answer_type=None
        elif line in TYPES:answer_type=line
        elif answer_ch and answer_type:
            m=re.match(r'^(\d+)\s*\.(?:\s|$)',line)
            if m:
                e=exercises.get(f'os-ch{answer_ch}-ex{int(m[1]):03d}')
                if e and e['exercise_type']==answer_type and not e['answer_ref']:
                    e['answer_ref']={'source_ref':meta['source_file'],'pdf_page':p['pdf_page'],'printed_page':p['printed_page'],'chapter':answer_ch,'number':e['source_number'],'category':answer_type}
for e in exercises.values():
    if 'dependency_refs' not in e:
        e['dependency_refs']=[]
        for n in re.findall(r'Figure\s+(\d+\.\d+)',e['question_text']):
            f=next((f for f in figures if f['figure_number']==n),None)
            if f:e['dependency_refs'].append({'kind':'figure','figure_number':n,'pdf_page':f['pdf_page'],'printed_page':f['printed_page']})
        if re.search(r'previous (problem|question)',e['question_text'],re.I):
            previous=exercises.get(f'os-ch{e["source_chapter"]}-ex{e["source_number"]-1:03d}')
            if previous:e['dependency_refs'].append({'kind':'exercise','exercise_id':previous['exercise_id'],'source_number':previous['source_number']})
    for r in e['render_refs']:assert r['asset_id'] in assets and byprint[r['printed_page']]==r['pdf_page']

reviews=load('chapter-reviews.json')
for review in reviews:
    ch=review['chapter'];available=[e for e in exercises.values() if e['source_chapter']==ch]
    if available:review['status']='content_ready';review['categories']={kind:[e['exercise_id'] for e in available if e['exercise_type']==kind and e['visibility']=='visible'] for kind in TYPES}
for t in course['topics']:
    if t['status']=='validated':assert all(ref in readings for ref in t['reading_refs']) and all(ref in exercises for ref in t['exercise_refs'])
course['validation_stage']='unit-by-unit content completion'
dump('course.json',course);dump('reading-content.json',list(readings.values()));dump('reading-objects.json',list(objects.values()));dump('assets.json',list(assets.values()));dump('exercises.json',list(exercises.values()));dump('figures.json',figures);dump('chapter-reviews.json',reviews)
payload={'course':course,'readings':list(readings.values()),'objects':list(objects.values()),'exercises':list(exercises.values()),'assets':list(assets.values()),'supplements':load('supplements.json'),'reviews':reviews,'figures':figures,'source':meta}
(R/'data/textbook.js').write_text('window.PathlineTextbook = '+json.dumps(payload,ensure_ascii=False)+';\n',encoding='utf-8')
print(json.dumps({'unit':args.unit,'topics':[{ 'id':tid,'regions':len(topics[tid]['reading_refs']),'exercises':len(topics[tid]['exercise_refs'])} for tid in unit['topic_refs']],'assets':len(assets),'unique_exercises':len(exercises)},ensure_ascii=False),flush=True)
