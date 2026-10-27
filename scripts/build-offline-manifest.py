"""Rebuild the offline resource inventory after changing the existing frontend."""
from pathlib import Path
import argparse
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument("--allow-missing-content",action="store_true",help="Update shell hashes before private resource restoration; preserve all content hashes")
args=parser.parse_args()
import hashlib,json
root=Path(__file__).resolve().parents[1]/'dist'
p=root/'data/runtime-manifest.json'
m=json.loads(p.read_text(encoding='utf-8'))
# Preserve existing Topic/Unit mappings, update only the shell and byte-level inventory.
m['shell']=sorted(x.relative_to(root).as_posix() for x in root.rglob('*') if x.is_file() and x.suffix in {'.js','.mjs','.css','.html','.svg','.webmanifest','.png','.ico'} and not any(k in x.relative_to(root).parts for k in ['source','data','pages','qa']) and not x.name.startswith('qa') and x.name!='legacy.html')
canonical=['data/course.json','data/source-metadata.json','data/reading-content.json','data/exercises.json','data/chapter-reviews.json','data/figures.json','data/textbook.js']
paths=set(m['shell']+m['pdf']+canonical)
for t in m['topics'].values():paths.update([t['path'],*t['assets']])
old=m.get('resources',{}); updated={}
for name in sorted(paths):
 file=root/name
 if name in m['shell']:
  data=file.read_bytes();updated[name]={'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
 else:
  spec=old.get(name)
  if spec is None:
   data=file.read_bytes();spec={'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
  if file.is_file():
   data=file.read_bytes()
   if len(data)!=spec['bytes'] or hashlib.sha256(data).hexdigest()!=spec['sha256']:
    raise SystemExit('Content differs from pinned baseline: '+name)
  elif not args.allow_missing_content:
   raise SystemExit('Content missing: '+name)
  updated[name]=spec
m['resources']=updated
m['resource_version']=hashlib.sha256(json.dumps(m['resources'],sort_keys=True).encode()).hexdigest()[:20]
m['license']={'source':'data/source-metadata.json','scope':'existing-course-only','public_distribution_added':False}
p.write_text(json.dumps(m,ensure_ascii=False,indent=2),encoding='utf-8',newline='\n')
print(json.dumps({'resource_version':m['resource_version'],'resources':len(paths),'bytes':sum(r['bytes'] for r in m['resources'].values())}))
