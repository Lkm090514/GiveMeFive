"""Owner-scoped, answer-free resource inventory for personal PDF caching."""
import hashlib
import json
from fastapi import HTTPException
from .local_auth import data_instance


def private_document(bank, owner, did):
    source = bank.store.source(did)
    if source.scope != 'exam_private' or source.owner_id != owner:
        raise HTTPException(404)
    return source


def inventory(bank, owner):
    with bank.store.connect() as c:
        documents = [json.loads(r[0]) for r in c.execute(
            'SELECT payload FROM documents WHERE scope=? AND owner_id=?', ('exam_private', owner))]
    libraries = []
    for source in documents:
        did = source['document_id']
        rows = [r for r in bank.store.list_questions(scope='exam_private', owner_id=owner, limit=None)
                if r[0].document_id == did]
        if not rows:
            continue
        assets = set()
        for _, v, _, _ in rows:
            m = bank.meta(v.version_id)
            assets.update([*m.get('safe_assets', []), *m.get('shared_assets', [])])
        resources = []
        for aid in sorted(assets):
            a = bank.store.asset(aid)
            path = bank.assets / a.relative_path
            resources.append({'url': '/api/v4/assets/' + aid, 'sha256': a.sha256, 'bytes': path.stat().st_size if path.is_file() else -1})
        original = bank.assets / did / 'original.pdf'
        if original.is_file():
            resources.append({'url': '/api/v4/library/' + did + '/original', 'sha256': source['sha256'], 'bytes': original.stat().st_size})
        version = hashlib.sha256(json.dumps(resources, sort_keys=True).encode()).hexdigest()[:24]
        libraries.append({'document_id': did, 'title': source['filename'], 'question_count': len(rows),
                          'classified': sum(bool(bank.meta(v.version_id).get('core')) for _, v, _, _ in rows),
                          'version': version, 'resources': resources})
    namespace = hashlib.sha256((data_instance(bank.root) + ':' + owner).encode()).hexdigest()[:24]
    return {'namespace': namespace, 'owner_id': owner, 'libraries': libraries}
