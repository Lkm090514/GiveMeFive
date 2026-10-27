#!/usr/bin/env python3
"""Restore pinned missing assets over authenticated HTTPS, never overwrite checkout code.

Credentials are environment-only. No redirects or cookies are followed. Files are
verified in a temporary directory before any destination is installed.
"""
import concurrent.futures
import importlib.util
import json
import os
from pathlib import Path
import shutil
import tempfile
import threading
import urllib.error
import urllib.parse
import urllib.request

spec = importlib.util.spec_from_file_location('course_assets', Path(__file__).with_name('restore-course-assets.py'))
assets = importlib.util.module_from_spec(spec)
spec.loader.exec_module(assets)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def restore_tree(dist, base, token, auth='sites', workers=8, opener=None):
    url = urllib.parse.urlsplit(base)
    if (url.scheme != 'https' or not url.hostname or url.username or url.password
            or url.query or url.fragment):
        raise assets.AssetError('Resource origin must be a plain HTTPS URL without credentials, query or fragment')
    if not token or any(c in token for c in '\r\n\0'):
        raise assets.AssetError('Missing or invalid GMF_COURSE_ASSETS_TOKEN; anonymous resource downloads are forbidden')
    headers = {'sites': 'OAI-Sites-Authorization', 'bearer': 'Authorization'}
    if auth not in headers:
        raise assets.AssetError('Unknown resource authentication mode')
    resources = assets.verified_manifest(dist)
    present = {r for r, s in resources.items() if assets.matches_file(assets.target_path(dist, r), s)}
    invalid = [r for r in resources if assets.target_path(dist, r).exists() and r not in present]
    if invalid:
        raise assets.AssetError('Checkout contains mismatched resource: ' + invalid[0] + '; rebuild shell manifest, never replace code from a resource host')
    needed = sorted(set(resources) - present)
    opener = opener or urllib.request.build_opener(NoRedirect())
    with tempfile.TemporaryDirectory(prefix='gmf-private-assets-') as tmp:
        stage = Path(tmp)
        stop = threading.Event()
        def fetch_one(rel):
            address = base.rstrip('/') + '/' + urllib.parse.quote(rel, safe='/')
            req = urllib.request.Request(address, headers={headers[auth]: 'Bearer ' + token})
            spec = resources[rel]
            target = stage / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            try:
                with opener.open(req, timeout=90) as response, target.open('wb') as output:
                    if response.status != 200:
                        raise assets.AssetError('Resource server did not return 200: ' + rel)
                    count = 0
                    while chunk := response.read(128 * 1024):
                        count += len(chunk)
                        if count > spec['bytes']:
                            raise assets.AssetError('Resource exceeds pinned size: ' + rel)
                        output.write(chunk)
            except (urllib.error.URLError, TimeoutError, OSError):
                raise assets.AssetError('Private resource fetch failed: ' + rel + '; check service token, origin and access policy') from None
            if not assets.matches_file(target, spec):
                raise assets.AssetError('Resource hash mismatch: ' + rel)
        def download(rel):
            if stop.is_set(): return
            try:
                fetch_one(rel)
            except Exception:
                stop.set()
                raise
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
            list(pool.map(download, needed))
        for rel in needed:
            dest = assets.target_path(dist, rel)
            dest.parent.mkdir(parents=True, exist_ok=True)
            # Recheck immediately before install: never replace concurrent edits.
            if dest.exists():
                raise assets.AssetError('Resource appeared during restore: ' + rel)
            fd, name = tempfile.mkstemp(prefix='.gmf-asset-', dir=dest.parent)
            os.close(fd)
            try:
                shutil.copyfile(stage / rel, name)
                os.replace(name, dest)
            finally:
                if os.path.exists(name): os.unlink(name)
    return {'mode': 'authenticated-tree', 'verified_existing': len(present), 'restored': len(needed), 'resource_count': len(resources)}


def main():
    try:
        dist = Path(os.environ.get('COURSE_ASSETS_DIST', 'dist')).resolve()
        result = restore_tree(dist, os.environ.get('COURSE_ASSETS_URL', ''),
            os.environ.get('COURSE_ASSETS_TOKEN', ''), os.environ.get('COURSE_ASSETS_AUTH', 'sites'))
    except (assets.AssetError, ValueError, OSError) as error:
        raise SystemExit('ERROR: ' + str(error)) from None
    print(json.dumps(result))


if __name__ == '__main__': main()
