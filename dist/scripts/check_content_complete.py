"""Validate the content batch, frozen scope, baseline, source references and metadata."""
import json,hashlib,argparse,re,sys
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
R=Path(__file__).resolve().parents[1]
read=lambda n:json.loads((R/'data'/n).read_text(encoding='utf-8'))
parser=argparse.ArgumentParser();parser.add_argument('--unit',type=int);args=parser.parse_args()
c=read('course.json');base=json.loads((R/'scripts/content-baseline.json').read_text(encoding='utf-8'))
assert len(c['units'])==7 and len(c['topics'])==41
topics={t['topic_id']:t for t in c['topics']};assets={a['asset_id']:a for a in read('assets.json')};regions={r['content_id']:r for r in read('reading-content.json')};exercises={e['exercise_id']:e for e in read('exercises.json')};objects={o['object_id']:o for o in read('reading-objects.json')};figures={f['figure_id']:f for f in read('figures.json')};reviews=read('chapter-reviews.json')
assert len(assets)==len(read('assets.json')) and len(regions)==len(read('reading-content.json')) and len(exercises)==len(read('exercises.json')) and len(objects)==len(read('reading-objects.json')) and len(figures)==len(read('figures.json'))
for t in base['frozen_mapping']:
    assert all(topics[t['topic_id']][k]==v for k,v in t.items()),f'Frozen mapping changed: {t["topic_id"]}'
for name,value in {**base['protected'],**base['assets']}.items():assert hashlib.sha256((R/name).read_bytes()).hexdigest()==value,f'Protected baseline changed: {name}'
for t in base['topics']:
    for k in ['reading_refs','exercise_refs','supplement_refs']:assert topics[t['topic_id']][k]==t[k],f'Baseline Topic changed: {t["topic_id"]}/{k}'
for r in base['readings']:assert regions[r['content_id']]==r,f'Baseline crop changed: {r["content_id"]}'
for e in base['exercises']:
    assert all(exercises[e['exercise_id']][k]==v for k,v in e.items() if k not in ['ap_topic','ap_unit','visibility']),f'Baseline question changed: {e["exercise_id"]}'
    assert set(e['ap_topic'])<=set(exercises[e['exercise_id']]['ap_topic'])
for o in base['objects']:assert all(objects[o['object_id']][k]==v for k,v in o.items()),f'Baseline object changed: {o["object_id"]}'
for f in base['figures']:
    assert all(figures[f['figure_id']][k]==v for k,v in f.items() if k not in ['reading_refs']),f'Baseline figure changed: {f["figure_id"]}'
    assert set(f['reading_refs'])<=set(figures[f['figure_id']]['reading_refs'])
mapping={p['printed_page']:p['pdf_page'] for p in read('page-map.json') if p['printed_page'] is not None}
assert len(mapping)==929 and not set(range(863,875))&mapping.keys()
assert len({a['path'] for a in assets.values()})==len(assets)
for a in assets.values():assert (R/a['path']).is_file() and mapping[a['printed_page']]==a['pdf_page']
def check_ref(r):
    assert r['asset_id'] in assets and mapping[r['printed_page']]==r['pdf_page']
    assert assets[r['asset_id']]['pdf_page']==r['pdf_page']
    x0,y0,x1,y1=r['bbox'];assert 0<=x0<x1<=612 and 50<=y0<y1<=746,r
for r in regions.values():
    check_ref(r);assert r['text_for_search'].strip() and r['source_attribution']['license']=='CC BY-NC-SA 4.0'
for e in exercises.values():
    assert e['exercise_type'] in ['Conceptual Questions','Problems','Additional Problems','Challenge Problems']
    assert e['question_text'].strip() and e['render_refs'] and not e['question_text'].startswith('EXAMPLE')
    for r in e['render_refs']:check_ref(r)
    for r in e['image_refs']:assert 0<=r['render_index']<len(e['render_refs'])
    if e['answer_ref']:assert mapping[e['answer_ref']['printed_page']]==e['answer_ref']['pdf_page']
    for d in e.get('dependency_refs',[]):
        if d['kind']=='exercise':assert d['exercise_id'] in exercises
        elif d['kind']=='figure':assert mapping[d['printed_page']]==d['pdf_page']
for ch in sorted({e['source_chapter'] for e in exercises.values()}):
    numbers=sorted(e['source_number'] for e in exercises.values() if e['source_chapter']==ch)
    assert numbers==list(range(1,max(numbers)+1)),f'Chapter {ch} has missing/duplicate numbers'
for o in objects.values():
    assert o['placement']=='reading_flow' and o['content_ref'] in regions
    assert all(ref in regions for ref in o.get('content_refs',[]))
for f in figures.values():
    assert mapping[f['printed_page']]==f['pdf_page'] and f['source_attribution']['license']=='CC BY-NC-SA 4.0'
    assert re.findall(r'\(credit[^:)]*:\s*(?:[^()]|\([^()]*\))*\)',f['caption'],re.I|re.S)==f['individual_credit']
    for ref in f.get('reading_refs',[]):assert ref in regions
assert any('OS541/DoD' in credit for credit in figures['os-figure-6.9']['individual_credit'])
assert len(read('supplements.json'))==4
for review in reviews:
    for kind,ids in review['categories'].items():
        assert len(ids)==len(set(ids))
        for eid in ids:assert exercises[eid]['source_chapter']==review['chapter'] and exercises[eid]['exercise_type']==kind and exercises[eid]['visibility']=='visible'
selected=[t for t in c['topics'] if t['ap_unit']==args.unit] if args.unit else [t for t in c['topics'] if t['status']=='validated']
for t in selected:
    assert t['status']=='validated' and t['reading_refs'] and t['exercise_refs'],f'Incomplete Topic {t["topic_id"]}'
    assert len(t['reading_refs'])==len(set(t['reading_refs'])) and len(t['exercise_refs'])==len(set(t['exercise_refs']))
    legal={r.replace('os-section-','') for r in t['source_refs']}|({'2.4'} if t['topic_id']=='1.1' else set())
    for ref in t['reading_refs']:assert ref in regions and regions[ref]['source_section'] in legal
    for eid in t['exercise_refs']:assert eid in exercises and t['topic_id'] in exercises[eid]['ap_topic'] and exercises[eid]['visibility']=='visible'
    assert not any(regions[r]['source_section'] in c['hidden_source_sections'] for r in t['reading_refs'])
print(json.dumps({'result':'passed','unit':args.unit,'checked_topics':[t['topic_id'] for t in selected],'regions':len(regions),'unique_exercises':len(exercises),'source_assets':len(assets),'baseline':'all three representatives and UI/source protected'},ensure_ascii=False))
