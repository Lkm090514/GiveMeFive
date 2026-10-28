"""Create a small, hash-guarded increment for the explicit 2026-10-23 V4 baseline."""
from pathlib import Path
import hashlib,json,subprocess,zipfile

ROOT=Path(__file__).resolve().parents[1]
BASE='5acb7d2714c0213e2579960cbbe9904b0e395c62'
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT,stderr=subprocess.DEVNULL)
if git('status','--porcelain','--untracked-files=normal'):raise SystemExit('Commit the reviewed increment before packaging')
head=git('rev-parse','HEAD').decode().strip();files=[]
for path in git('diff','--name-only',BASE,head).decode().splitlines():
    try:before=git('show',BASE+':'+path)
    except subprocess.CalledProcessError:before=None
    after=(ROOT/path).read_bytes() if (ROOT/path).is_file() else None
    files.append({'path':path,'before_sha256':hashlib.sha256(before).hexdigest() if before is not None else None,'after_sha256':hashlib.sha256(after).hexdigest() if after is not None else None})
manifest={'baseline_commit':BASE,'target_commit':head,'files':files}
out=ROOT.parent/'outputs/GiveMeFive-AS-V4-Increment-20261023.zip';out.parent.mkdir(exist_ok=True)
with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    z.writestr('increment-manifest.json',json.dumps(manifest,ensure_ascii=False,indent=2))
    z.write(ROOT/'scripts/apply-increment.py','Apply-Patch.py')
    z.writestr('changes.patch',git('diff','--binary',BASE,head))
    z.writestr('rollback.patch',git('diff','--binary',head,BASE))
    z.writestr('README.txt','Baseline: '+BASE+'\nTarget: '+head+'\nStop GiveMeFive first. Unzip this bundle into a separate folder.\nWindows: py -3 Apply-Patch.py "C:\\path\\to\\GiveMeFive-Fusion-AS-V4"\nConflicts stop before any mutation. The updater backs up changed files and runtime SQLite databases.\nRepeat application is a no-op. See payload/docs/as-v4/INCREMENT-20261023.md for migration and rollback details.\n')
    for f in files:
        if f['after_sha256']:z.write(ROOT/f['path'],'payload/'+f['path'])
with zipfile.ZipFile(out) as z:
    if z.testzip():raise RuntimeError('ZIP CRC failed')
print(json.dumps({'archive':str(out),'size_bytes':out.stat().st_size,'changed_files':len(files),'baseline':BASE,'target':head}))
