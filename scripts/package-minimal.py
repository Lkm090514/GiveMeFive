"""Package the current runnable source without identities, student data or old app copies."""
from pathlib import Path
import hashlib
import json
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    if subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT).strip():
        raise SystemExit('Commit the reviewed source before packaging.')
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT).decode().strip()
    paths = subprocess.check_output(['git', 'ls-files', '-z'], cwd=ROOT).decode().split('\0')
    excluded = {'assessment-source', 'legacy-source', '_archive-notes', '.openai', 'runtime', '.git', '.venv', 'node_modules', '__pycache__'}
    files = []
    for name in filter(None, paths):
        path = Path(name)
        if excluded.intersection(path.parts) or path.suffix in {'.pyc', '.log', '.sqlite3', '.sqlite', '.db'} or path.name in {'local-access.json', 'last-launch.json', 'RELEASE-GIT.txt', '开始使用.txt'} or path.name.endswith(('-wal', '-shm')):
            continue
        if path.parts[0] == 'as-v3-reference' and path.parts[1] not in {'gmf_v3', 'requirements.txt', 'start.cmd', 'scripts'}:
            continue
        if path.parts[:2] == ('dist', 'qa'):
            continue
        files.append(name)
    out = ROOT.parent / 'outputs' / ('GiveMeFive-AS-V4.1-Minimal-' + head[:7] + '.zip')
    out.parent.mkdir(exist_ok=True)
    prefix = 'GiveMeFive-AS-V4.1/'
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        archive.writestr(prefix + 'RELEASE-GIT.txt', head + '\n')
        archive.writestr(prefix + '开始使用.txt', '解压到独立目录，双击 Start-GiveMeFive.cmd。首次运行会安装依赖，需联网。\n此包保留网站及原教材必需资源，省略旧网站副本、虚拟环境、Git 历史、私人数据库和登录身份。\n本机已导入的私人练习册不随源码分发；在另一台电脑使用“模考 → 我的试卷”重新导入原 PDF，目录分类将自动恢复。\n不要用空白运行数据覆盖旧项目 runtime。\n'.encode('utf-8'))
        for name in files:
            archive.write(ROOT / name, prefix + name)
    with zipfile.ZipFile(out) as archive:
        assert archive.testzip() is None
        names = set(archive.namelist())
        assert len(names) == len(archive.namelist()), 'Duplicate ZIP entry'
        for required in ['Start-GiveMeFive.cmd', 'scripts/run-v4.py', 'backend/local_auth.py', 'backend/library.py', 'dist/practice-library.mjs', 'dist/data/runtime-manifest.json', 'as-v3-reference/gmf_v3/migrations/001_initial.sql']:
            assert prefix + required in names, required
        manifest = json.loads((ROOT / 'dist/data/runtime-manifest.json').read_text(encoding='utf-8'))
        for name in manifest['resources']:
            assert prefix + 'dist/' + name in names, name
    print(json.dumps({'archive': str(out), 'files': len(files), 'bytes': out.stat().st_size, 'sha256': hashlib.sha256(out.read_bytes()).hexdigest(), 'commit': head}, ensure_ascii=False))


if __name__ == '__main__':
    main()
