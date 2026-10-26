"""Rebuild the offline resource inventory after changing the existing frontend."""
from pathlib import Path
import hashlib,json
root=Path(__file__).resolve().parents[1]/'dist'
p=root/'data/runtime-manifest.json'
m=json.loads(p.read_text(encoding='utf-8'))
# Preserve existing Topic/Unit mappings, update only the shell and byte-level inventory.
m['shell']=sorted(x.relative_to(root).as_posix() for x in root.rglob('*') if x.is_file() and x.suffix in {'.js','.mjs','.css','.html','.svg','.webmanifest','.png','.ico'} and not any(k in x.relative_to(root).parts for k in ['source','data','pages','qa']) and not x.name.startswith('qa') and x.name!='legacy.html')
paths=set(m['shell']+m['pdf']+['data/course.json','data/source-metadata.json'])
for t in m['topics'].values():paths.update([t['path'],*t['assets']])
m['resources']={}
for name in sorted(paths):
 data=(root/name).read_bytes();m['resources'][name]={'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
m['resource_version']=hashlib.sha256(json.dumps(m['resources'],sort_keys=True).encode()).hexdigest()[:20]
m['license']={'source':'data/source-metadata.json','scope':'existing-course-only','public_distribution_added':False}
p.write_text(json.dumps(m,ensure_ascii=False,indent=2),encoding='utf-8',newline='\n')
print(json.dumps({'resource_version':m['resource_version'],'resources':len(paths),'bytes':sum(r['bytes'] for r in m['resources'].values())}))
