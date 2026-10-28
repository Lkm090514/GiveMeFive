import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

SCRIPT=Path(__file__).resolve().parents[1]/'scripts/build-offline-manifest.py'


def fixture(tmp_path):
    (tmp_path/'scripts').mkdir();shutil.copyfile(SCRIPT,tmp_path/'scripts'/SCRIPT.name)
    dist=tmp_path/'dist';(dist/'data').mkdir(parents=True)
    resources={}
    for name in ['course.json','source-metadata.json','reading-content.json','exercises.json','chapter-reviews.json','figures.json','textbook.js']:
        data=b'original canonical content';(dist/'data'/name).write_bytes(data)
        resources['data/'+name]={'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
    (dist/'app.js').write_bytes(b'latest V4.2 source')
    resources['app.js']={'bytes':3,'sha256':hashlib.sha256(b'old').hexdigest()}
    doc={'resources':resources,'topics':{},'units':{},'pdf':[]}
    (dist/'data/runtime-manifest.json').write_text(json.dumps(doc))
    def run(*args):
        return subprocess.run([sys.executable,str(tmp_path/'scripts'/SCRIPT.name),*args],text=True,capture_output=True)
    return dist,doc,run


def test_manifest_refreshes_shell_but_preserves_pinned_canonical_hashes(tmp_path):
    dist,doc,run=fixture(tmp_path)
    assert run().returncode==0
    new=json.loads((dist/'data/runtime-manifest.json').read_text())
    assert new['resources']['app.js']['sha256']==hashlib.sha256(b'latest V4.2 source').hexdigest()
    for name,spec in doc['resources'].items():
        if name!='app.js': assert new['resources'][name]==spec
    (dist/'data/reading-content.json').write_bytes(b'corrupt textbook')
    before=(dist/'data/runtime-manifest.json').read_bytes()
    assert run().returncode!=0
    assert (dist/'data/runtime-manifest.json').read_bytes()==before


def test_missing_content_is_not_rehashed_or_falsely_verified(tmp_path):
    dist,doc,run=fixture(tmp_path)
    (dist/'data/exercises.json').unlink()
    assert run().returncode!=0
    assert run('--allow-missing-content').returncode==0
    new=json.loads((dist/'data/runtime-manifest.json').read_text())
    assert new['resources']['data/exercises.json']==doc['resources']['data/exercises.json']
    assert not (dist/'data/exercises.json').exists()
