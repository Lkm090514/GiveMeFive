"""Package a file-hash guarded increment for the 15b0e4d release tree."""
from pathlib import Path
import hashlib,json,subprocess,zipfile
ROOT=Path(__file__).resolve().parents[1]
def git(*a):return subprocess.check_output(['git',*a],cwd=ROOT,stderr=subprocess.DEVNULL)
if git('status','--porcelain'):raise SystemExit('Commit before packaging')
base=git('rev-parse','quality-baseline-15b0e4d').decode().strip();head=git('rev-parse','HEAD').decode().strip();files=[]
for path in git('diff','--name-only',base,head).decode().splitlines():
    try:before=git('show',base+':'+path)
    except subprocess.CalledProcessError:before=None
    after=(ROOT/path).read_bytes() if (ROOT/path).is_file() else None
    files.append({'path':path,'before_sha256':hashlib.sha256(before).hexdigest() if before is not None else None,'after_sha256':hashlib.sha256(after).hexdigest() if after is not None else None})
manifest={'baseline_commit':'15b0e4dc9ea23e42417ed492535a32848de92a23','baseline_reconstruction_commit':base,'target_commit':head,'files':files}
out=ROOT.parent/'outputs/GiveMeFive-AS-V4-Quality-Increment-20261023.zip'
with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
    z.writestr('increment-manifest.json',json.dumps(manifest,ensure_ascii=False,indent=2));z.write(ROOT/'scripts/apply-increment.py','Apply-Patch.py')
    z.writestr('changes.patch',git('diff','--binary',base,head));z.writestr('rollback.patch',git('diff','--binary',head,base))
    z.writestr('README.txt','Baseline release: '+manifest['baseline_commit']+'\nStop GiveMeFive. Unzip this bundle separately.\nWindows: py -3 Apply-Patch.py "C:\\path\\to\\GiveMeFive-Fusion-AS-V4"\nConflicts stop before mutation. Files and SQLite are backed up. Reapply is a no-op.\nNo schema changes. See docs/as-v4/quality-20261023/REPORT.md in the updated project.\n')
    for f in files:
        if f['after_sha256']:z.write(ROOT/f['path'],'payload/'+f['path'])
with zipfile.ZipFile(out) as z:assert z.testzip() is None
print(json.dumps({'archive':str(out),'files':len(files),'target':head}))
