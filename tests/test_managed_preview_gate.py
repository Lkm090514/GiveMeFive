"""Prevent accidentally publishing the complete private textbook through preview."""
import runpy,sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.preview_auth import require_password, matches

def test_preview_password_must_be_configured():
    for secret in (None,'','short',' '*20):
        with pytest.raises(RuntimeError):require_password(secret)
    assert require_password('a-long-secret-that-is-private')=='a-long-secret-that-is-private'
    assert matches('a-long-secret-that-is-private','a-long-secret-that-is-private')
    assert not matches('wrong','a-long-secret-that-is-private')
    assert not matches(None,'a-long-secret-that-is-private')

def test_preview_password_gates_everything(monkeypatch):
    monkeypatch.setenv('SITES_MANAGED_LINUX_CONTAINER','1')
    monkeypatch.setenv('GMF_PREVIEW_PASSWORD','safe-test-password-abcdef-123')
    monkeypatch.setattr(sys,'argv',['managed-preview.py','--port','4173'])
    import uvicorn
    captured={}
    monkeypatch.setattr(uvicorn,'run',lambda app,**kwargs:captured.setdefault('app',app))
    runpy.run_path(str(ROOT/'scripts/managed-preview.py'),run_name='__main__')
    client=TestClient(captured['app'],base_url='https://preview.example.test',follow_redirects=False)
    for path in ('/','/data/runtime-manifest.json','/data/reading-content.json','/content-runtime.js','/api/v4/me'):
        res=client.get(path,headers={'accept':'application/json'})
        assert res.status_code==401,(path,res.status_code)
    assert client.get('/qa-preview').status_code==200
    assert client.post('/qa-preview',data={'password':'wrong'}).status_code==403
    assert client.post('/qa-preview',data={}).status_code==403
    good=client.post('/qa-preview',data={'password':'safe-test-password-abcdef-123'})
    assert good.status_code==303
    assert 'httponly' in good.headers['set-cookie'].lower()
    assert 'secure' in good.headers['set-cookie'].lower()
    assert 'samesite=strict' in good.headers['set-cookie'].lower()
    assert client.get('/').status_code==200
    assert client.get('/data/runtime-manifest.json').status_code==200
    assert client.get('/api/v4/me').status_code==200
