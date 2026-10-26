"""Build one lean, complete ZIP. No required textbook/source resources are omitted."""
from pathlib import Path
import json,zipfile,subprocess,os,tempfile,shutil
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT.parent/'outputs';OUT.mkdir(exist_ok=True)
archive=OUT/'GiveMeFive-Fusion-AS-V4-Source-Lite.zip'
exclude={'.git','node_modules','.venv','preview-runtime-python','.sites-runtime','.sites-checkout','runtime','__pycache__','.pytest_cache'}
stage=Path(tempfile.mkdtemp(prefix='gmf-v4-package-'))/'complete.zip'
items=[]
for p in sorted(ROOT.rglob('*')):
 rel=p.relative_to(ROOT)
 if not p.is_file() or any(x in exclude for x in rel.parts) or p.suffix in {'.pyc','.log'}:continue
 if p.name.startswith('.openai-download-') or p.name in {'local-access.json','last-launch.json'} or p.suffix in {'.sqlite3','.db','.sqlite'} or p.name.endswith(('-wal','-shm')):continue
 items.append((p,rel))
with zipfile.ZipFile(stage,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
 z.writestr('GiveMeFive-Fusion-AS-V4/RELEASE-GIT.txt',subprocess.run(['git','log','-1','--format=%H%n%D%n%s'],cwd=ROOT,capture_output=True,text=True,check=True).stdout)
 for p,rel in items:z.write(p,Path('GiveMeFive-Fusion-AS-V4')/rel)
with stage.open('rb') as file:os.fsync(file.fileno())
partial=archive.with_suffix('.complete-part')
shutil.copyfile(stage,partial)
with partial.open('rb') as file:os.fsync(file.fileno())
os.replace(partial,archive)
print(json.dumps({'archive':str(archive),'files':len(items),'size_bytes':archive.stat().st_size,'uncompressed_bytes':sum(p.stat().st_size for p,_ in items)}))
with zipfile.ZipFile(archive) as z:
 bad=z.testzip()
 if bad:raise RuntimeError('Archive checksum failed: '+bad)
 required=['Start-GiveMeFive.cmd','scripts/run-v4.py','backend/app.py','backend/migrations/003_assessment_v4.sql','as-v3-reference/gmf_v3/migrations/001_initial.sql','dist/data/course.json','dist/assessment/v4/ui.mjs','docs/as-v4/DELIVERY-REPORT.md']
 for name in required:assert 'GiveMeFive-Fusion-AS-V4/'+name in z.namelist(),name
 assert len([n for n in z.namelist() if '/dist/assets/pages/' in n])==len(list((ROOT/'dist/assets/pages').glob('*')))
print('Archive CRC and required-resource checks passed.')
