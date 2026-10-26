#!/usr/bin/env python3
"""Build or restore a PRIVATE manifest-verified GMF runtime asset ZIP.

Never uploads resources. Check license rights before external distribution.
Only dist/ paths listed in runtime-manifest.json can be included.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat
import tempfile
from zipfile import ZIP_DEFLATED, ZipFile


class AssetError(Exception):
    pass


def verified_manifest(dist):
    doc = json.loads((dist / 'data/runtime-manifest.json').read_text(encoding='utf-8'))
    result = {}
    for rel, spec in doc['resources'].items():
        logical = PurePosixPath(rel)
        if (not rel or '\\' in rel or ':' in rel or logical.is_absolute()
                or '..' in logical.parts or '.' in logical.parts
                or logical.as_posix() != rel):
            raise AssetError(f'Unsafe manifest resource path: {rel!r}')
        if (not isinstance(spec.get('bytes'), int) or spec['bytes'] < 0
                or not isinstance(spec.get('sha256'), str)
                or len(spec['sha256']) != 64
                or any(c not in '0123456789abcdef' for c in spec['sha256'])):
            raise AssetError(f'Invalid asset metadata: {rel}')
        result[rel] = spec
    return result


def target_path(dist, rel):
    path = dist / rel
    if not path.resolve().is_relative_to(dist.resolve()):
        raise AssetError(f'Unsafe destination: {rel}')
    return path


def matches_file(path, spec):
    if not path.is_file() or path.stat().st_size != spec['bytes']:
        return False
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for part in iter(lambda: stream.read(128 * 1024), b''):
            digest.update(part)
    return digest.hexdigest() == spec['sha256']


def pack(dist, archive, resources):
    for rel, spec in resources.items():
        if not matches_file(target_path(dist, rel), spec):
            raise AssetError(f'Cannot package missing or corrupt resource: {rel}')
    archive.parent.mkdir(parents=True, exist_ok=True)
    if archive.exists():
        raise AssetError(f'Refusing to overwrite existing private package: {archive}')
    with ZipFile(archive, 'w', compression=ZIP_DEFLATED, compresslevel=6) as zipfile:
        for rel in sorted(resources):
            zipfile.write(target_path(dist, rel), arcname='dist/' + rel)
    return {'mode': 'pack', 'resources': len(resources), 'package': str(archive)}


def validate_zip(zipfile, resources):
    index = {}
    for info in zipfile.infolist():
        name = info.filename
        if not name.startswith('dist/') or name[5:] not in resources or info.is_dir():
            raise AssetError(f'Unexpected archive member: {name}')
        rel = name[5:]
        if rel in index:
            raise AssetError(f'Duplicate archive member: {rel}')
        if stat.S_ISLNK(info.external_attr >> 16):
            raise AssetError(f'Archive contains symbolic link: {rel}')
        if info.file_size != resources[rel]['bytes']:
            raise AssetError(f'Asset size mismatch in package: {rel}')
        index[rel] = info
    return index


def verify_stream(zipfile, info, spec):
    count = 0
    h = hashlib.sha256()
    with zipfile.open(info) as member:
        for chunk in iter(lambda: member.read(128 * 1024), b''):
            count += len(chunk)
            h.update(chunk)
    return count == spec['bytes'] and h.hexdigest() == spec['sha256']


def restore(dist, archive, resources):
    present = {rel for rel, spec in resources.items() if matches_file(target_path(dist, rel), spec)}
    invalid = [rel for rel in resources if target_path(dist, rel).exists() and rel not in present]
    if invalid:
        raise AssetError(f'Refusing to overwrite existing mismatched resource: {invalid[0]}')
    needed = set(resources) - present
    with ZipFile(archive) as zipfile:
        index = validate_zip(zipfile, resources)
        missing = sorted(needed - index.keys())
        if missing:
            raise AssetError(f'Asset package missing {len(missing)} resources; example: {missing[0]}')
        # Verify all required bytes before writing any destination.
        for rel in sorted(needed):
            if not verify_stream(zipfile, index[rel], resources[rel]):
                raise AssetError(f'Corrupt asset in private package: {rel}')
        for rel in sorted(needed):
            dest = target_path(dist, rel)
            dest.parent.mkdir(parents=True, exist_ok=True)
            fd, tmp = tempfile.mkstemp(prefix='.gmf-asset-', dir=dest.parent)
            try:
                with os.fdopen(fd, 'wb') as out, zipfile.open(index[rel]) as source:
                    for chunk in iter(lambda: source.read(128 * 1024), b''):
                        out.write(chunk)
                os.replace(tmp, dest)
            finally:
                if os.path.exists(tmp):
                    os.unlink(tmp)
    return {'mode': 'restore', 'verified_existing': len(present),
            'restored': len(needed), 'resource_count': len(resources)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['pack', 'restore'])
    parser.add_argument('--dist', type=Path, default=Path(__file__).resolve().parents[1] / 'dist')
    parser.add_argument('--archive', type=Path, required=True)
    args = parser.parse_args()
    try:
        resources = verified_manifest(args.dist.resolve())
        result = (pack(args.dist.resolve(), args.archive, resources)
                  if args.mode == 'pack' else restore(args.dist.resolve(), args.archive, resources))
    except (AssetError, ValueError, OSError, KeyError) as exc:
        parser.exit(1, f'ERROR: {exc}\n')
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
