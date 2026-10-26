#!/usr/bin/env python3
"""Verify local Pathline runtime inventory; never copy or upload assets."""
import argparse
import hashlib
import json
from pathlib import Path


def audit(root: Path):
    manifest_path = root / 'data/runtime-manifest.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    resources = manifest['resources']
    failures = []
    checked = 0
    for rel, expected in sorted(resources.items()):
        path = root / rel
        if not path.is_file():
            failures.append({'path': rel, 'issue': 'missing'})
            continue
        payload = path.read_bytes()
        if len(payload) != expected['bytes']:
            failures.append({'path': rel, 'issue': 'size', 'expected': expected['bytes'], 'actual': len(payload)})
            continue
        digest = hashlib.sha256(payload).hexdigest()
        if digest != expected['sha256']:
            failures.append({'path': rel, 'issue': 'sha256'})
            continue
        checked += 1
    return {'course_id': manifest['course_id'], 'content_version': manifest['content_version'],
            'units': len(manifest['units']), 'topics': len(manifest['topics']),
            'resource_count': len(resources), 'verified': checked, 'failures': failures,
            'complete': not failures}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dist', type=Path, default=Path(__file__).resolve().parents[1] / 'dist')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    result = audit(args.dist.resolve())
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(text + '\n', encoding='utf-8')
    print(text)
    raise SystemExit(0 if result['complete'] else 1)


if __name__ == '__main__':
    main()
