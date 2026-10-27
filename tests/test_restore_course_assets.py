"""Check secure resource package restore without uploading or overwriting files."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from zipfile import ZipFile

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'restore-course-assets.py'


def fixture(tmp_path):
    dist = tmp_path / 'dist'
    (dist / 'data/topics').mkdir(parents=True)
    resource = dist / 'data/topics/1.1.json'
    body = b'{"readings": []}'
    resource.write_bytes(body)
    manifest = {'resources': {'data/topics/1.1.json': {
        'bytes': len(body), 'sha256': hashlib.sha256(body).hexdigest()}}}
    (dist / 'data/runtime-manifest.json').write_text(json.dumps(manifest))
    archive = tmp_path / 'private-assets.zip'
    def run(mode):
        return subprocess.run([sys.executable, str(SCRIPT), mode, '--dist', str(dist),
                               '--archive', str(archive)], capture_output=True, text=True)
    return resource, body, archive, run


def test_private_package_restore_and_idempotency(tmp_path):
    resource, body, archive, run = fixture(tmp_path)
    assert run('pack').returncode == 0
    with ZipFile(archive) as z:
        assert z.namelist() == ['dist/data/topics/1.1.json']
    resource.unlink()
    r = run('restore')
    assert r.returncode == 0, r.stderr
    assert resource.read_bytes() == body
    assert json.loads(run('restore').stdout)['restored'] == 0


def test_restore_rejects_corrupt_archive_before_writing(tmp_path):
    resource, _, archive, run = fixture(tmp_path)
    resource.unlink()
    with ZipFile(archive, 'w') as z:
        z.writestr('dist/data/topics/1.1.json', b'{"readings": XX}')
    assert run('restore').returncode != 0
    assert not resource.exists()


def test_restore_never_overwrites_changed_local_resource(tmp_path):
    resource, _, _, run = fixture(tmp_path)
    assert run('pack').returncode == 0
    resource.write_bytes(b'user edited file')
    assert run('restore').returncode != 0
    assert resource.read_bytes() == b'user edited file'


def test_restore_rejects_unexpected_files(tmp_path):
    resource, _, archive, run = fixture(tmp_path)
    resource.unlink()
    with ZipFile(archive, 'w') as z:
        z.writestr('dist/data/topics/1.1.json', b'{"readings": []}')
        z.writestr('dist/private/student.db', b'private')
    assert run('restore').returncode != 0
    assert not resource.exists()


def test_pack_fails_if_manifest_does_not_match_disk(tmp_path):
    resource, _, _, run = fixture(tmp_path)
    resource.unlink()
    assert run('pack').returncode != 0

def test_restore_keeps_verified_new_shell_and_reuses_old_private_content(tmp_path):
 resource,body,archive,run=fixture(tmp_path);dist=resource.parents[2];shell=dist/'app.js';shell.write_bytes(b'old shell');manifest=json.loads((dist/'data/runtime-manifest.json').read_text());manifest['resources']['app.js']={'bytes':9,'sha256':hashlib.sha256(b'old shell').hexdigest()};(dist/'data/runtime-manifest.json').write_text(json.dumps(manifest));assert run('pack').returncode==0
 shell.write_bytes(b'new verified shell');manifest['resources']['app.js']={'bytes':shell.stat().st_size,'sha256':hashlib.sha256(shell.read_bytes()).hexdigest()};(dist/'data/runtime-manifest.json').write_text(json.dumps(manifest));resource.unlink();result=run('restore');assert result.returncode==0,result.stderr;assert resource.read_bytes()==body;assert shell.read_bytes()==b'new verified shell'


def test_original_source_zip_restores_only_manifest_assets(tmp_path):
    resource, body, archive, run = fixture(tmp_path)
    resource.unlink()
    with ZipFile(archive, 'w') as z:
        z.writestr('GiveMeFive-AS-V4.1/dist/data/topics/1.1.json',body)
        z.writestr('GiveMeFive-AS-V4.1/dist/app.js',b'old code must not be extracted')
        z.writestr('GiveMeFive-AS-V4.1/backend/app.py',b'old backend')
    result=subprocess.run([sys.executable,str(SCRIPT),'restore','--dist',str(resource.parents[2]),'--archive',str(archive),'--source-root','GiveMeFive-AS-V4.1'],capture_output=True,text=True)
    assert result.returncode==0,result.stderr
    assert resource.read_bytes()==body
    assert not (resource.parents[2]/'app.js').exists()


def test_original_source_zip_rejects_traversal(tmp_path):
    resource, body, archive, run = fixture(tmp_path)
    resource.unlink()
    with ZipFile(archive,'w') as z:
        z.writestr('GiveMeFive-AS-V4.1/dist/data/topics/1.1.json',body)
        z.writestr('../outside',b'untrusted')
    result=subprocess.run([sys.executable,str(SCRIPT),'restore','--dist',str(resource.parents[2]),'--archive',str(archive),'--source-root','GiveMeFive-AS-V4.1'],capture_output=True,text=True)
    assert result.returncode!=0
    assert not resource.exists()
