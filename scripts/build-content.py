"""Derive runtime Topic bundles from preserved canonical course resources. No textbook edits."""
import json, hashlib
from pathlib import Path
root=Path(__file__).resolve().parents[1]/'dist'; data=root/'data'
def read(n):return json.loads((data/(n+'.json')).read_text())
files={'readings':'reading-content','exercises':'exercises','assets':'assets','supplements':'supplements','reviews':'chapter-reviews','objects':'reading-objects','figures':'figures'}
D={k:read(v) for k,v in files.items()}; c=read('course');version='2026-10-21-'+hashlib.sha256(json.dumps(D,sort_keys=True).encode()).hexdigest()[:10];c['content_version']=version;(data/'course.json').write_text(json.dumps(c,ensure_ascii=False,separators=(',',':')))
folder=data/'topics'/version;folder.mkdir(parents=True,exist_ok=True);manifest={'content_version':version,'course_id':c['course_id'],'topics':{},'units':{},'pdf':[]}
for t in c['topics']:
 chapters={int(s.removeprefix('os-section-').split('.')[0]) for s in t['source_refs']};rids=set(t['reading_refs']);exids=set(t['exercise_refs']);reviews=[r for r in D['reviews'] if r['chapter'] in chapters]
 for r in reviews:
  for ids in r['categories'].values():exids.update(ids)
 # Include stable dependencies referenced by another question, not a copied bank.
 for e in D['exercises']:
  if e['exercise_id'] in exids:exids.update(d['exercise_id'] for d in e.get('dependency_refs',[]) if d['kind']=='exercise')
 out={'readings':[r for r in D['readings'] if r['content_id'] in rids],'exercises':[e for e in D['exercises'] if e['exercise_id'] in exids],'reviews':reviews,'supplements':[s for s in D['supplements'] if s['supplement_id'] in t['supplement_refs']],'objects':[o for o in D['objects'] if set([o.get('content_ref')]+o.get('content_refs',[]))&rids],'figures':[f for f in D['figures'] if set(f.get('reading_refs',[]))&rids]}
 aids={r['asset_id'] for r in out['readings']};aids.update(r['asset_id'] for e in out['exercises'] for r in e['render_refs']);out['assets']=[a for a in D['assets'] if a['asset_id'] in aids]
 path=folder/(t['topic_id']+'.json');path.write_text(json.dumps(out,ensure_ascii=False,separators=(',',':')));manifest['topics'][t['topic_id']]={'path':path.relative_to(root).as_posix(),'assets':[a['path'] for a in out['assets']]}
for u in c['units']:manifest['units'][str(u['unit_id'])]=u['topic_refs']
manifest['shell']=[p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file() and p.suffix in ['.js','.mjs','.css','.html','.svg','.webmanifest','.png','.ico'] and not any(x in p.parts for x in ['source','data','pages']) and not p.name.startswith('qa') and p.name!='legacy.html']+['data/course.json','data/runtime-manifest.json']
manifest['pdf']=[p.relative_to(root).as_posix() for p in (root/'source').rglob('*') if p.is_file()]
(data/'runtime-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
print(json.dumps({'version':version,'units':len(c['units']),'topics':len(c['topics']),'exercises':len(D['exercises']),'supplements':len(D['supplements']),'chapter_reviews':len(D['reviews']),'assets':len(D['assets'])}))

# Keep byte-level offline inventory aligned with rebuilt Topic bundles.
exec((Path(__file__).with_name("build-offline-manifest.py")).read_text(encoding="utf-8"))
