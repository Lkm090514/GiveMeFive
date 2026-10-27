import hashlib
import importlib.util
import io
import json
from pathlib import Path
import urllib.error
import pytest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/fetch-private-course-tree.py'
spec = importlib.util.spec_from_file_location('private_tree', SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def fixture(tmp_path):
    dist = tmp_path / 'dist'
    (dist / 'data').mkdir(parents=True)
    data = {'data/topic.json': b'original textbook', 'app.js': b'new V4.2 code'}
    resources = {r: {'bytes': len(b), 'sha256': hashlib.sha256(b).hexdigest()} for r,b in data.items()}
    (dist / 'data/runtime-manifest.json').write_text(json.dumps({'resources':resources}))
    (dist / 'app.js').write_bytes(data['app.js'])
    class FakeResponse(io.BytesIO):
        status = 200
    class FakeOpener:
        requests = []
        def open(self, req, timeout):
            self.requests.append(req)
            return FakeResponse(data['data/topic.json'])
    return dist, data, FakeOpener()


def test_authenticated_tree_verifies_before_install_and_preserves_new_code(tmp_path):
    dist, data, opener = fixture(tmp_path)
    result = module.restore_tree(dist, 'https://example.test', 'service-test-only', opener=opener)
    assert result['restored'] == 1
    assert (dist/'app.js').read_bytes() == data['app.js']
    assert (dist/'data/topic.json').read_bytes() == data['data/topic.json']
    assert opener.requests[0].get_header('Oai-sites-authorization') == 'Bearer service-test-only'
    assert module.restore_tree(dist, 'https://example.test', 'service-test-only', opener=opener)['restored'] == 0
    assert len(opener.requests) == 1


def test_tree_rejects_hash_mismatch_without_install(tmp_path):
    dist, data, opener = fixture(tmp_path)
    data['data/topic.json'] = b'corrupt textbook!'
    with pytest.raises(module.assets.AssetError, match='hash mismatch'):
        module.restore_tree(dist, 'https://example.test', 'test', opener=opener)
    assert not (dist/'data/topic.json').exists()


@pytest.mark.parametrize('base,token', [('http://example.test','test'),('https://example.test?token=x','test'),('https://u:p@example.test','test'),('https://example.test',''),('https://example.test','x\r\nInjected: x')])
def test_tree_rejects_unsafe_origin_or_anonymous_access(tmp_path,base,token):
    dist, _, opener = fixture(tmp_path)
    with pytest.raises(module.assets.AssetError):
        module.restore_tree(dist,base,token,opener=opener)
    assert not opener.requests


def test_tree_never_overwrites_edited_checkout_or_follows_redirects(tmp_path):
    dist, _, opener = fixture(tmp_path)
    (dist/'app.js').write_bytes(b'user changed code')
    with pytest.raises(module.assets.AssetError, match='mismatched resource'):
        module.restore_tree(dist,'https://example.test','test',opener=opener)
    assert not opener.requests
    assert module.NoRedirect().redirect_request(None,None,302,'',{},'https://elsewhere.test') is None
