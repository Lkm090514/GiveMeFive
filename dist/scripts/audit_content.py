"""Compute completeness from the delivered dataset, source PDF and UI evidence."""
import json,hashlib,re,sys
from pathlib import Path
from collections import Counter
import pdfplumber
from PIL import Image
sys.stdout.reconfigure(encoding='utf-8')
R=Path(__file__).resolve().parents[1]
read=lambda n:json.loads((R/'data'/n).read_text(encoding='utf-8'))
c=read('course.json');rs=read('reading-content.json');es=read('exercises.json');fs=read('figures.json');os=read('reading-objects.json');assets=read('assets.json');reviews=read('chapter-reviews.json');meta=read('source-metadata.json')
base=json.loads((R/'scripts/content-baseline.json').read_text(encoding='utf-8'))
regions={r['content_id']:r for r in rs};exercise={e['exercise_id']:e for e in es}
asset_ids={a['asset_id'] for a in assets}
all_refs=[*rs,*[ref for e in es for ref in e['render_refs']]]
broken_asset_references=sum(ref['asset_id'] not in asset_ids for ref in all_refs)+sum(f.get('asset_id') is not None and f['asset_id'] not in asset_ids for f in fs)
missing_images=sum(not (R/a['path']).is_file() for a in assets)
legal_sources={s['source_id'] for s in read('source-structure.json')['sections']}
assert broken_asset_references==missing_images==0
used_readings={ref for t in c['topics'] for ref in t['reading_refs']};used_exercises={ref for t in c['topics'] for ref in t['exercise_refs']}
catalogue={ref for rev in reviews for ref in rev['source_exercise_refs']}
assert catalogue==set(exercise),'Orphan/source catalogue exercise mismatch'
assert sum(len(rev['source_exercise_refs']) for rev in reviews)==len(exercise)
ui=json.loads((R/'qa/content-page-checks.json').read_text(encoding='utf-8'))
assert len(ui)==41 and {x['tid'] for x in ui}=={t['topic_id'] for t in c['topics']}
for t in c['topics']:
    check=next(x for x in ui if x['tid']==t['topic_id'])
    assert check['readingRegions']==len(t['reading_refs']) and check['exercises']==len(t['exercise_refs']),t['topic_id']
    assert check['completed']=='false' and check['chapterEntries']==len({r.split('-')[-1].split('.')[0] for r in t['source_refs']})
for a in assets:
    with Image.open(R/a['path']) as im:
        assert im.size==(1224,1584),a['path'];im.verify()
assert len({a['pdf_page'] for a in assets})==len(assets)
assert len({hashlib.sha256((R/a['path']).read_bytes()).hexdigest() for a in assets})==len(assets),'Duplicate binary source page'
pdf=pdfplumber.open(R/meta['source_file'])
illustrated=[];clipped=[]
for e in es:
    images=set()
    for r in e['render_refs']:
        x0,y0,x1,y1=r['bbox']
        for i in pdf.pages[r['pdf_page']-1].images:
            # Original PDF embeds diagrams/photos as image objects; formulas remain
            # authoritative page regions, and are not counted as illustrations.
            if i['width']<25 or i['height']<20:continue
            ix=max(0,min(i['x1'],x1)-max(i['x0'],x0));iy=max(0,min(i['bottom'],y1)-max(i['top'],y0))
            if ix*iy>25:
                images.add((r['pdf_page'],i['x0'],i['top'],i['x1'],i['bottom']))
                if ix*iy < .98*i['width']*i['height']:
                    clipped.append({'exercise_id':e['exercise_id'],'printed_page':r['printed_page'],'image_bbox':[i['x0'],i['top'],i['x1'],i['bottom']],'region_bbox':r['bbox'],'visible':e['visibility']=='visible'})
    if images:illustrated.append(e['exercise_id'])
    assert '•' not in e['question_text'] and not any(re.match(r'^\d+\s*\.\s',line) for line in e['question_text'].splitlines()[1:]),e['exercise_id']
    assert re.match(r'^'+str(e['source_number'])+r'\s*\.',e['question_text']),e['exercise_id']
    for n in set(re.findall(r'Figure\s+(\d+\.\d+)',e['question_text'])):
        assert any(f['figure_number']==n for f in fs) and any(d.get('figure_number')==n for d in e['dependency_refs']),e['exercise_id']
active_objects=[o for o in os if used_readings & {o['content_ref'],*o.get('content_refs',[])}]
active_figures=[f for f in fs if used_readings & set(f.get('reading_refs',[]))]
new_assets=[a for a in assets if a['path'] not in base['assets']]
chapter_stats=[{'chapter':rev['chapter'],'source_exercises':len(rev['source_exercise_refs']),'visible_exercises':sum(len(ids) for ids in rev['categories'].values()),'topic_exercises':len(used_exercises & set(rev['source_exercise_refs']))} for rev in reviews]
summary={'status':'source_and_UI_audited','course':{'units':len(c['units']),'topics':len(c['topics']),'content_ready_topics':sum(t['content_status'] in ['content_ready','verified'] for t in c['topics']),'verified_topics':sum(t.get('content_status')=='verified' for t in c['topics'])},
 'content':{'unique_source_sections':len({regions[x]['source_section'] for x in used_readings}),'unique_reading_regions':len(used_readings),'indexed_reading_regions':len(rs),'figures_in_reading':len(active_figures),'indexed_figures':len(fs),'examples':sum(o['object_type']=='example' for o in active_objects),'check_your_understanding':sum(o['object_type']=='check_your_understanding' for o in active_objects),'supplements':len(read('supplements.json'))},
 'exercises':{'unique_formal_source_exercises':len(es),'visible_chapter_exercises':sum(e['visibility']=='visible' for e in es),'unique_topic_exercises':len(used_exercises),'illustrated_source_exercises':len(illustrated),'illustrated_visible_exercises':sum(exercise[x]['visibility']=='visible' for x in illustrated),'illustrated_topic_exercises':len(used_exercises & set(illustrated)),'image_count_method':'Original PDF embedded image >=25pt wide and >=20pt high intersects question region; page regions retain vector formulas as well.','chapters':chapter_stats},
 'topics':[{'topic_id':t['topic_id'],'reading_regions':len(t['reading_refs']),'source_sections':sorted({regions[x]['source_section'] for x in t['reading_refs']}),'exercises':len(t['exercise_refs']),'figures':sum(bool(set(t['reading_refs']) & set(f.get('reading_refs',[]))) for f in fs),'examples':sum(o['object_type']=='example' and bool(set(t['reading_refs']) & {o['content_ref'],*o.get('content_refs',[])}) for o in os),'checks':sum(o['object_type']=='check_your_understanding' and bool(set(t['reading_refs']) & {o['content_ref'],*o.get('content_refs',[])}) for o in os)} for t in c['topics']],
 'sources':{'unique_page_assets':len(assets),'new_page_assets':len(new_assets),'reused_baseline_page_assets':len(base['assets']),'new_asset_references':sum(len(t['reading_refs']) for t in c['topics'])+sum(len(e['render_refs']) for e in es),'pdf_pages':len(read('page-map.json')),'mapped_printed_pages':sum(p['printed_page'] is not None for p in read('page-map.json')),'missing_printed_pages':meta['omitted_printed_pages'],'license':meta['license'],'source_sha256':meta['sha256'],'figure_credit_entries':sum(bool(f['individual_credit']) for f in fs),'figure_6_9_credit':next(f['individual_credit'] for f in fs if f['figure_number']=='6.9'),'attribution_completeness':{'reading_regions':sum(r['source_attribution'].get('license')==meta['license'] for r in rs),'figures':sum(f['source_attribution'].get('license')==meta['license'] for f in fs),'exercises':sum(e['source_attribution'].get('license')==meta['license'] for e in es)}},
 'validation':{'all_topic_UI_pages':len(ui),'PNG_files_decoded':len(assets),'broken_asset_references':broken_asset_references,'duplicate_exercise_ids':len(es)-len(exercise),'duplicate_source_assets':len(assets)-len({a['pdf_page'] for a in assets}),'missing_images':missing_images,'orphan_exercises':len(set(exercise)-catalogue),'topics_without_reading':sum(not t['reading_refs'] for t in c['topics']),'topics_without_frozen_mapping':sum(not t['source_refs'] or not set(t['source_refs'])<=legal_sources for t in c['topics']),'protected_UI_source_files':len(base['protected']),'baseline_original_regions':len(base['readings']),'baseline_original_exercises':len(base['exercises']),'clipped_image_candidates':clipped}}
(R/'content-completeness.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in summary.items() if k not in ['topics']},ensure_ascii=False))
