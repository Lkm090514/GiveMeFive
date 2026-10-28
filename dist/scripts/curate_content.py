"""Finish source-layout repairs and explicit Topic curation after seven Unit batches."""
import json,re,sys
from pathlib import Path
import pdfplumber
sys.stdout.reconfigure(encoding='utf-8')
R=Path(__file__).resolve().parents[1]
read=lambda n:json.loads((R/'data'/n).read_text(encoding='utf-8'))
write=lambda n,v:(R/'data'/n).write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')
c=read('course.json');es=read('exercises.json');rs=read('reading-content.json');fs=read('figures.json');assets=read('assets.json');reviews=read('chapter-reviews.json');meta=read('source-metadata.json')
base=json.loads((R/'scripts/content-baseline.json').read_text(encoding='utf-8'))
baseline_ids={e['exercise_id'] for e in base['exercises']}
eid={e['exercise_id']:e for e in es};topics={t['topic_id']:t for t in c['topics']}
pdf=pdfplumber.open(R/meta['source_file'])
def transcription(e):
    e['question_text']='\n'.join(pdf.pages[r['pdf_page']-1].crop(tuple(r['bbox'])).extract_text() or '' for r in e['render_refs']).strip()
    e['subparts']=list(dict.fromkeys(re.findall(r'\(([a-z])\)',e['question_text'])))
    e['image_refs']=[{'kind':'embedded_original_question_region','render_index':i} for i in range(len(e['render_refs']))]
# Printed p749 floats the last line of 67 to the opposite column above a shared heading.
extra={'asset_id':'os-pdf-page-0754','bbox':[316.8,55,600,102.43],'printed_page':749,'pdf_page':754}
if extra not in eid['os-ch15-ex067']['render_refs']:eid['os-ch15-ex067']['render_refs'].append(extra)
for ref in eid['os-ch15-ex070']['render_refs']:
    if ref['printed_page']==749 and ref['bbox'][0]==316.8:ref['bbox'][1]=126.91
for e in es:
    if e['exercise_id'] in baseline_ids:continue
    e['render_refs']=[r for r in e['render_refs'] if (pdf.pages[r['pdf_page']-1].crop(tuple(r['bbox'])).extract_text() or '').strip() or any(i['x0']<r['bbox'][2] and i['x1']>r['bbox'][0] and i['top']<r['bbox'][3] and i['bottom']>r['bbox'][1] for i in pdf.pages[r['pdf_page']-1].images)]
    transcription(e)
# Original exercise 14 is about sine/cosine phase, although the book puts it under 15.4.
# Additional Problems below explicitly ask mass-spring period, equations or energy.
curated={'7.1':[56],'7.2':[57,58,59,67],'7.3':[14,60],'7.4':[56,59,67]}
for tid,numbers in curated.items():
    for n in numbers:
        ref=f'os-ch15-ex{n:03d}'
        if ref not in topics[tid]['exercise_refs']:topics[tid]['exercise_refs'].append(ref)
        eid[ref]['scope_review']='manual: original question is phase / ideal mass-spring motion / period / energy; source section label unchanged'
# 15.2 CQ8 explicitly requires damping and a driving mechanism, outside the frozen path.
topics['7.4']['exercise_refs']=[x for x in topics['7.4']['exercise_refs'] if x!='os-ch15-ex008']
used={x for t in c['topics'] for x in t['exercise_refs']}
for e in es:
    e['ap_topic']=[t['topic_id'] for t in c['topics'] if e['exercise_id'] in t['exercise_refs']]
    e['ap_unit']=int(e['ap_topic'][0].split('.')[0]) if e['ap_topic'] else None
# Preserve the whole source catalogue. AP chapter entrances hide the same excluded
# subject matter as the main path; the unmodified PDF remains the complete book.
excluded=re.compile(r'torsion|rocket|gyroscop|precession|damp|resonan|driving mechanism|wind-driven|tidal|general relativity|Einstein|Hohmann|transfer orbit|Young.s modulus|bulk modulus|shear modulus|compressibil|tensile|strain|stress',re.I)
for e in es:
    reason=None
    if e['source_section'] in c['hidden_source_sections']:reason='frozen excluded source section'
    elif excluded.search(e['question_text']):reason='question explicitly uses frozen excluded subject matter'
    if e['exercise_id'] in used:reason=None
    e['visibility']='hidden_excluded_source_scope' if reason else 'visible'
    e['chapter_scope_review']=reason or 'formal source question retained in AP chapter entrance'
for review in reviews:
    chapter=[e for e in es if e['source_chapter']==review['chapter']]
    review['status']='content_ready'
    review['source_exercise_refs']=[e['exercise_id'] for e in chapter]
    review['categories']={kind:[e['exercise_id'] for e in chapter if e['exercise_type']==kind and e['visibility']=='visible'] for kind in ['Conceptual Questions','Problems','Additional Problems','Challenge Problems']}
    review['scope_policy']='All formal source questions catalogued once; frozen excluded material hidden in AP entrance and accessible in original PDF.'
# Index a source dependency even though its tidal-force question stays hidden.
missing={n for e in es for n in re.findall(r'Figure\s+(\d+\.\d+)',e['question_text']) if not any(f['figure_number']==n for f in fs)}
page_text=json.loads((R/'source/page-text.json').read_text(encoding='utf-8'))
structure=read('source-structure.json')
# PDF text-stream line breaks omitted some same-page captions in the old index.
# Discover their actual caption markers in original reading regions as well.
missing|={n for r in rs for n in re.findall(r'FIGURE\s+(\d+\.\d+)',r['text_for_search']) if not any(f['figure_number']==n for f in fs)}
for number in sorted(missing):
    source=next((p for p in page_text if re.search(r'FIGURE\s+'+re.escape(number)+r'\b',p['text'])),None)
    if source is None:
        r=next(r for r in rs if re.search(r'FIGURE\s+'+re.escape(number)+r'\b',r['text_for_search']))
        source={'printed_page':r['printed_page'],'pdf_page':r['pdf_page']}
    pg=pdf.pages[source['pdf_page']-1]
    marker=pg.search(r'FIGURE\s+'+re.escape(number)+r'\b')[0]
    neighbours=[m for m in pg.search(r'FIGURE\s+\d+\.\d+\b') if abs(m['top']-marker['top'])<3 and m['x0']>marker['x0']+10]
    right=min(m['x0'] for m in neighbours)-4 if neighbours else 600
    ls=pg.crop((marker['x0']-1,marker['top']-1,right,746)).extract_text_lines(return_chars=True)
    at=next(i for i,l in enumerate(ls) if re.match(r'FIGURE\s+'+re.escape(number)+r'\b',l['text']))
    cap=[ls[at]['text']]
    for line in ls[at+1:]:
        if max((ch['size'] for ch in line['chars']),default=0)>8 or line['text'].startswith('FIGURE'):break
        cap.append(line['text'])
    caption=re.sub(r'^FIGURE\s+'+re.escape(number)+r'\s*','',' '.join(cap))
    section=max((s for s in structure['sections'] if s['chapter']==int(number.split('.')[0]) and s['printed_start']<=source['printed_page']),key=lambda s:s['printed_start'])['section']
    actual=[r['content_id'] for r in rs if r['pdf_page']==source['pdf_page'] and re.search(r'FIGURE\s+'+re.escape(number)+r'\b',r['text_for_search'])]
    fs.append({'figure_id':'os-figure-'+number,'figure_number':number,'caption':caption,'individual_credit':re.findall(r'\(credit[^:)]*:\s*(?:[^()]|\([^()]*\))*\)',caption,re.I|re.S),'source_section':section,'printed_page':source['printed_page'],'pdf_page':source['pdf_page'],'source_attribution':{'book':meta['book'],'license':meta['license'],'individual_license':'not assumed'},'asset_id':next((a['asset_id'] for a in assets if a['pdf_page']==source['pdf_page']),None) if actual else None,'reading_refs':actual,'retention_status':'preserved_in_original_reading_region' if actual else 'indexed_excluded_source_dependency','caption_text_status':'PDF text extraction; original caption region is authoritative'})
for e in es:
    if e['exercise_id'] in baseline_ids:continue
    e['dependency_refs']=[]
    for n in dict.fromkeys(re.findall(r'Figure\s+(\d+\.\d+)',e['question_text'])):
        f=next(f for f in fs if f['figure_number']==n)
        e['dependency_refs'].append({'kind':'figure','figure_number':n,'pdf_page':f['pdf_page'],'printed_page':f['printed_page']})
    if re.search(r'previous (problem|question)',e['question_text'],re.I):
        prev=eid.get(f'os-ch{e["source_chapter"]}-ex{e["source_number"]-1:03d}')
        if prev:e['dependency_refs'].append({'kind':'exercise','exercise_id':prev['exercise_id'],'source_number':prev['source_number']})
fs.sort(key=lambda f:tuple(int(part) for part in f['figure_number'].split('.')))
for t in c['topics']:assert t['reading_refs'] and t['exercise_refs'] and all(eid[x]['visibility']=='visible' for x in t['exercise_refs'])
for name,value in [('course.json',c),('exercises.json',es),('figures.json',fs),('chapter-reviews.json',reviews)]:write(name,value)
payload={'course':c,'readings':rs,'objects':read('reading-objects.json'),'exercises':es,'assets':assets,'supplements':read('supplements.json'),'reviews':reviews,'figures':fs,'source':meta}
(R/'data/textbook.js').write_text('window.PathlineTextbook = '+json.dumps(payload,ensure_ascii=False)+';\n',encoding='utf-8')
print(json.dumps({'result':'curated','unique_exercises':len(es),'visible_chapter_exercises':sum(e['visibility']=='visible' for e in es),'unique_topic_exercises':len(used),'source_catalogue':sum(len(r['source_exercise_refs']) for r in reviews)}))
