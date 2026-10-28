#!/usr/bin/env python3
"""Read-only public-bank quality gate; refuses drafts, placeholder options and missing assets.

This is an operational check, NOT a copyright license or human content review.
"""
import argparse
import hashlib
import json
import sqlite3
import sys
from pathlib import Path

def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()

def check(db, data_root, minimum):
    problems = []
    report = {"minimum_published": minimum, "published": 0, "verified_answer_keys": 0,
              "checked_assets": 0, "passed": False, "errors": problems}
    if not db.is_file():
        problems.append("Persistent database missing; do not deploy an empty public bank")
        return report
    covered_topics = set()
    try:
        with sqlite3.connect(f"file:{db.resolve()}?mode=ro", uri=True) as con:
            con.row_factory = sqlite3.Row
            rows = con.execute("""SELECT q.question_id,q.document_id,q.current_version_id,
                              q.payload AS question,v.payload AS version,m.payload AS metadata,
                              d.payload AS document
                              FROM questions q
                              LEFT JOIN question_versions v ON v.version_id=q.current_version_id
                              LEFT JOIN v4_meta m ON m.version_id=q.current_version_id
                              LEFT JOIN documents d ON d.document_id=q.document_id
                              WHERE q.scope='bank' AND q.publication='approved'""").fetchall()
            report["published"] = len(rows)
            if len(rows) < minimum:
                problems.append(f"Only {len(rows)} published bank questions; minimum {minimum}")
            for row in rows:
                qid = row["question_id"]
                try:
                    question = json.loads(row["question"])
                    version = json.loads(row["version"])
                    metadata = json.loads(row["metadata"])
                    document = json.loads(row["document"])
                    if question.get("publication") != "approved":
                        raise ValueError("publication payload inconsistent")
                    if not document.get("reuse_confirmed"):
                        raise ValueError("source reuse permission unconfirmed")
                    covered_topics.update(metadata.get("core") or [])
                    if not metadata.get("published_at") or not metadata.get("published_by"):
                        raise ValueError("missing publication audit")
                    if not version.get("stem", "").strip():
                        raise ValueError("blank stem")
                    options = version.get("options") or []
                    if len(options) < 2 or len({o.get("label") for o in options}) != len(options):
                        raise ValueError("invalid options")
                    for option in options:
                        value = option.get("text", "").strip()
                        if not value or "visual option" in value.casefold() or "inspect original" in value.casefold():
                            raise ValueError("placeholder/blank option")
                    assets = metadata.get("safe_assets") or []
                    if not assets:
                        raise ValueError("missing answer-safe question image")
                    for asset_id in assets:
                        item = con.execute("SELECT payload FROM assets WHERE asset_id=?", (asset_id,)).fetchone()
                        if not item:
                            raise ValueError("missing question asset record")
                        spec = json.loads(item[0])
                        rel = Path(spec.get("relative_path", ""))
                        if rel.is_absolute() or ".." in rel.parts or not rel.parts:
                            raise ValueError("unsafe asset path")
                        asset = (data_root / "assets" / rel).resolve()
                        if not asset.is_relative_to((data_root / "assets").resolve()) or not asset.is_file():
                            raise ValueError("missing question image")
                        if sha256(asset) != spec.get("sha256"):
                            raise ValueError("question image hash mismatch")
                        report["checked_assets"] += 1
                    answer = con.execute("SELECT payload FROM answer_keys WHERE version_id=? ORDER BY revision DESC LIMIT 1",
                                         (row["current_version_id"],)).fetchone()
                    key = json.loads(answer[0]) if answer else {}
                    if key.get("status") != "Verified" or key.get("label") not in {o["label"] for o in options}:
                        raise ValueError("missing verified answer key")
                    report["verified_answer_keys"] += 1
                except (ValueError, TypeError, KeyError, json.JSONDecodeError) as error:
                    problems.append(f"{qid}: {error}")
                if len(problems) >= 30:
                    problems.append("Error list truncated after 30; repair and re-run")
                    break
    except (sqlite3.Error, OSError, ValueError) as error:
        problems.append(f"Database read error: {error}")
    if minimum >= 369:
        try:
            course = json.loads((Path(__file__).resolve().parents[1] / "dist/data/course.json").read_text())
            required_topics = {t["topic_id"] for t in course["topics"]}
            report["covered_topics"] = len(required_topics & covered_topics)
            missing_topics = sorted(required_topics - covered_topics)
            if missing_topics:
                problems.append(f"Public bank has no reviewed questions for {len(missing_topics)} topics: {missing_topics[:8]}")
        except (OSError, ValueError, KeyError, TypeError) as error:
            problems.append(f"Cannot verify 41-topic public bank coverage: {error}")
    report["passed"] = not problems
    return report

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--min-published", type=int, default=369)
    args = parser.parse_args()
    if args.min_published < 1:
        parser.error("--min-published must be positive")
    report = check(args.db, args.data_root, args.min_published)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["passed"] else 2

if __name__ == "__main__":
    sys.exit(main())
