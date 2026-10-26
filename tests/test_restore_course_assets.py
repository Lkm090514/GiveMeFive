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
