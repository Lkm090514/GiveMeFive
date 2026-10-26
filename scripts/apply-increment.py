"""Apply a verified source increment to an unpacked Fusion baseline. Stop the app first."""
from __future__ import annotations
import argparse,hashlib,json,os,shutil,sqlite3,tempfile
from datetime import datetime,timezone
from pathlib import Path,PurePosixPath

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
def below(root,rel):
    p=PurePosixPath(rel)
    if p.is_absolute() or '..' in p.parts:raise ValueError('Unsafe manifest path')
    path=(root/rel).resolve()
    if not path.is_relative_to(root):raise ValueError('Path leaves target project')
    return path

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('target',type=Path);p.add_argument('--bundle',type=Path,default=Path(__file__).resolve().parent)
    args=p.parse_args();root=args.target.resolve();bundle=args.bundle.resolve();m=json.loads((bundle/'increment-manifest.json').read_text())
    if not (root/'backend/app.py').is_file() or not (root/'dist/data/course.json').is_file():raise ValueError('Target must be the existing complete Fusion project')
    conflicts=[];changes=[]
    for f in m['files']:
        target=below(root,f['path']);actual=sha(target)
        if actual==f['after_sha256']:continue
        if actual!=f['before_sha256']:conflicts.append({'path':f['path'],'expected':f['before_sha256'],'actual':actual});continue
        if f['after_sha256'] and sha(below(bundle/'payload',f['path']))!=f['after_sha256']:raise ValueError('Patch payload hash mismatch: '+f['path'])
        changes.append(f)
    if conflicts:
        print(json.dumps({'status':'conflict','files':conflicts},ensure_ascii=False,indent=2));raise SystemExit(2)
    if not changes:print('Already applied; no files or databases changed.');return
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');backup=root.parent/'GMF-update-backups'/stamp;backup.mkdir(parents=True)
    for f in changes:
        src=below(root,f['path']);dst=below(backup/'files',f['path'])
        if src.is_file():dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
    databases=[]
    for src in (root/'runtime').rglob('*.sqlite3'):
        rel=src.relative_to(root).as_posix();dst=backup/'databases'/rel;dst.parent.mkdir(parents=True,exist_ok=True)
        with sqlite3.connect(src) as source,sqlite3.connect(dst) as target:source.backup(target)
        databases.append(rel)
    receipt={'baseline_commit':m['baseline_commit'],'target_commit':m['target_commit'],'target':str(root),'files':changes,'database_backups':databases}
    (backup/'receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf8')
    written=[]
    try:
        for f in changes:
            dest=below(root,f['path']);dest.parent.mkdir(parents=True,exist_ok=True)
            if not f['after_sha256']:dest.unlink();written.append(f);continue
            fd,partial=tempfile.mkstemp(prefix='gmf-update-',dir=dest.parent)
            with os.fdopen(fd,'wb') as out:out.write(below(bundle/'payload',f['path']).read_bytes());out.flush();os.fsync(out.fileno())
            os.replace(partial,dest);written.append(f)
    except BaseException:
        for f in reversed(written):
            dest=below(root,f['path']);old=below(backup/'files',f['path'])
            if old.is_file():shutil.copy2(old,dest)
            elif dest.is_file() and sha(dest)==f['after_sha256']:dest.unlink()
        raise
    print(json.dumps({'status':'applied','files':len(changes),'backup':str(backup),'target_commit':m['target_commit']},ensure_ascii=False))

if __name__=='__main__':main()
