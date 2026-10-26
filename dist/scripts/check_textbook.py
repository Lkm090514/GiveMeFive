import json,hashlib
from pathlib import Path
R=Path(__file__).resolve().parents[1]
def read(n):return json.loads((R/'data'/n).read_text(encoding='utf8'))
course=read('course.json');maps=read('page-map.json');assets=read('assets.json');content=read('reading-content.json');ex=read('exercises.json');figs=read('figures.json');objects=read('reading-objects.json');supp=read('supplements.json');reviews=read('chapter-reviews.json')
assert len(course['units'])==7 and len(course['topics'])==41
assert len(maps)==934 and sum(m['printed_page'] is not None for m in maps)==929
printed={m['printed_page']:m['pdf_page'] for m in maps if m['printed_page'] is not None}
assert printed[202]==207 and printed[733]==738 and printed[941]==934
assert not any(p in printed for p in range(863,875))
sections={s['source_id'] for s in read('source-structure.json')['sections']}
for t in course['topics']:assert set(t['source_refs'])<=sections
assert len(supp)==4 and {s['ap_topic'] for s in supp}=={'2.8','5.4','6.2','6.3'}
assert len({e['exercise_id'] for e in ex})==len(ex)
for ch,maxnum in [(5,109),(6,135),(10,125),(15,73)]:
    nums=sorted(e['source_number'] for e in ex if e['source_chapter']==ch)
    assert nums==list(range(1,maxnum+1)),(ch,nums)
    print('PASS chapter',ch,'complete exercise numbers 1..'+str(maxnum))
eid={e['exercise_id']:e for e in ex};aid={a['asset_id']:a for a in assets};rid={r['content_id']:r for r in content}
assert len({a['path'] for a in assets})==len(assets)
for a in assets:assert (R/a['path']).is_file() and printed[a['printed_page']]==a['pdf_page']
for r in content:
    assert r['asset_id'] in aid and r['bbox'][1]<r['bbox'][3]
for e in ex:
    assert e['question_text'] and e['exercise_type'] in ['Conceptual Questions','Problems','Additional Problems','Challenge Problems']
    assert e['render_refs']
    assert not e['question_text'].startswith('EXAMPLE')
    for r in e['render_refs']:
        assert r['asset_id'] in aid and r['bbox'][1]<r['bbox'][3]
    if e['answer_ref']:assert printed[e['answer_ref']['printed_page']]==e['answer_ref']['pdf_page']
for t in course['topics']:
    assert all(r in rid for r in t['reading_refs'])
    for id in t['exercise_refs']:assert eid[id]['visibility']=='visible' and t['topic_id'] in eid[id]['ap_topic']
for c in reviews:
    for cat,ids in c['categories'].items():
        for id in ids:assert eid[id]['source_chapter']==c['chapter'] and eid[id]['exercise_type']==cat and eid[id]['visibility']=='visible'
t75=next(t for t in course['topics'] if t['topic_id']=='7.5')
assert len(t75['reading_refs'])==6
assert all('Torsional Pendulum' not in rid[r]['text_for_search'] for r in t75['reading_refs'])
assert any('Significance' in rid[r]['text_for_search'] for r in t75['reading_refs'] if rid[r]['printed_page']==733)
assert {'15.3','15.4'}<={o.get('number') for o in objects if o['object_type']=='example'}
assert '10.8' in {o.get('number') for o in objects if o['object_type']=='example'}
e27=eid['os-ch5-ex027'];assert len(e27['render_refs'])==2 and [r['printed_page'] for r in e27['render_refs']]==[238,239]
assert eid['os-ch10-ex118']['exercise_type']=='Additional Problems'
assert eid['os-ch10-ex123']['exercise_type']=='Challenge Problems'
assert eid['os-ch6-ex022']['visibility']=='visible' and '2.9' in eid['os-ch6-ex022']['ap_topic']
assert eid['os-ch6-ex027']['render_refs'][-1]['bbox'][1]==275
assert eid['os-ch15-ex014']['visibility']=='visible' and '7.3' in eid['os-ch15-ex014']['ap_topic'] and '7.5' not in eid['os-ch15-ex014']['ap_topic']
assert all(r['bbox'][1]>=50 for r in content)
assert len({f['figure_id'] for f in figs})==len(figs)
assert 'OS541/DoD' in next(f for f in figs if f['figure_number']=='6.9')['individual_credit'][0]
assert all(t['status']=='validated' and t['reading_refs'] and t['exercise_refs'] for t in course['topics'])
assert {t['topic_id']:len(t['exercise_refs']) for t in course['topics'] if t['topic_id'] in ['2.5','5.4','7.5']}=={'2.5':41,'5.4':14,'7.5':18}
meta=read('source-metadata.json');assert hashlib.sha256((R/meta['source_file']).read_bytes()).hexdigest()==meta['sha256']
summary={'status':'passed','units':7,'topics':41,'mapped_pages':929,'pdf_pages':934,'source_sections':len(sections),'exercises':len(ex),'figures_indexed':len(figs),'figures_preserved_in_reading':sum(f['retention_status']=='preserved_in_original_reading_region' for f in figs),'unique_page_assets':len(assets),'supplements':4,
    'representatives':{t['topic_id']:{'reading_regions':len(t['reading_refs']),'exercises':len(t['exercise_refs']),'answer_refs':sum(eid[id]['answer_ref'] is not None for id in t['exercise_refs'])} for t in course['topics'] if t['status']=='validated'}}
(R/'validation-results.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf8');print(json.dumps(summary,ensure_ascii=False,indent=2))
