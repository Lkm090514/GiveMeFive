"""Regression checks for the standalone, read-only runtime asset auditor."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path


AUDITOR = Path(__file__).resolve().parents[1] / 'scripts' / 'audit-runtime-assets.py'


def run_audit(tmp_path, resource_bytes=b'course content'):
    dist = tmp_path / 'dist'
    (dist / 'data').mkdir(parents=True)
    (dist / 'topics').mkdir()
    asset = dist / 'topics' / 'lesson.json'
    asset.write_bytes(resource_bytes)
    manifest = {
        'course_id': 'test-course', 'content_version': 'v1',
        'units': {'1': {}}, 'topics': {'1.1': {}},
        'resources': {'topics/lesson.json': {
            'bytes': len(resource_bytes),
            'sha256': hashlib.sha256(resource_bytes).hexdigest(),
        }},
    }
    (dist / 'data' / 'runtime-manifest.json').write_text(json.dumps(manifest), encoding='utf-8')
    def execute():
        p = subprocess.run([sys.executable, str(AUDITOR), '--dist', str(dist)], capture_output=True, text=True)
        return p.returncode, json.loads(p.stdout)
    return asset, execute


def test_auditor_accepts_valid_assets(tmp_path):
    _, execute = run_audit(tmp_path)
    code, report = execute()
    assert code == 0
    assert report['complete'] and report['verified'] == 1


def test_auditor_detects_missing_asset(tmp_path):
    asset, execute = run_audit(tmp_path)
    asset.unlink()
    code, report = execute()
    assert code == 1
    assert report['failures'][0]['issue'] == 'missing'


def test_auditor_detects_same_size_corruption(tmp_path):
    asset, execute = run_audit(tmp_path)
    asset.write_bytes(b'course contEnt')
    code, report = execute()
    assert code == 1
    assert report['failures'][0]['issue'] == 'sha256'


def test_auditor_detects_truncated_asset(tmp_path):
    asset, execute = run_audit(tmp_path)
    asset.write_bytes(b'course')
    code, report = execute()
    assert code == 1
    assert report['failures'][0]['issue'] == 'size'
