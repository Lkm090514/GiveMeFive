#!/usr/bin/env python3
"""Fail-closed V4.3 Pathline resource and nonempty-topic audit (read only)."""
import argparse
import hashlib
import json
import sys
from pathlib import Path

def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def verify(dist):
    problems = []
    report = {"verified_resources": 0, "required_resources": 0, "units": 0, "topics": 0,
              "nonempty_topics": 0, "passed": False, "errors": problems}
    try:
        manifest = json.loads((dist / "data/runtime-manifest.json").read_text(encoding="utf-8"))
        resources = manifest["resources"]
        report["required_resources"] = len(resources)
        if len(resources) != 1228:
            problems.append(f"Expected 1228 resources, manifest has {len(resources)}")
        for name, spec in resources.items():
            rel = Path(name)
            if (rel.is_absolute() or ".." in rel.parts or "\\" in name or ":" in name
                    or not rel.parts or not isinstance(spec.get("bytes"), int)):
                problems.append(f"Unsafe manifest entry: {name}")
                continue
            path = dist / rel
            if not path.is_file() or path.is_symlink() or path.stat().st_size != spec["bytes"] or sha256(path) != spec["sha256"]:
                problems.append(f"Missing or mismatched resource: {name}")
            else:
                report["verified_resources"] += 1
        pdfjs = dist / "source/pdfjs"
        for name in ("pdf.mjs", "pdf.worker.mjs"):
            if not (pdfjs / name).is_file() or (pdfjs / name).stat().st_size < 100000:
                problems.append("Missing PDF.js runtime: " + name)
        if len([p for p in (pdfjs / "cmaps").glob("*.bcmap") if p.stat().st_size > 0]) < 168:
            problems.append("PDF.js CMap collection incomplete")
        if len([p for p in (pdfjs / "wasm").glob("*.wasm") if p.stat().st_size > 1000]) < 3:
            problems.append("PDF.js WASM decoders incomplete")
        required_fonts = ("FoxitDingbats.pfb", "FoxitFixed.pfb", "FoxitFixedBold.pfb",
                          "FoxitFixedBoldItalic.pfb", "FoxitFixedItalic.pfb",
                          "FoxitSerif.pfb", "FoxitSerifBold.pfb", "FoxitSerifBoldItalic.pfb",
                          "FoxitSerifItalic.pfb", "FoxitSymbol.pfb",
                          "LiberationSans-Bold.ttf", "LiberationSans-BoldItalic.ttf",
                          "LiberationSans-Italic.ttf", "LiberationSans-Regular.ttf")
        for font in required_fonts:
            if not (pdfjs / "standard_fonts" / font).is_file() or (pdfjs / "standard_fonts" / font).stat().st_size == 0:
                problems.append("Missing PDF.js font: " + font)
        course = json.loads((dist / "data/course.json").read_text(encoding="utf-8"))
        report["units"] = len(course.get("units", []))
        topics = sorted((dist / "data/topics").rglob("*.json"))
        report["topics"] = len(topics)
        for topic in topics:
            data = json.loads(topic.read_text(encoding="utf-8"))
            if all(data.get(field) for field in ("readings", "exercises", "assets")):
                report["nonempty_topics"] += 1
            else:
                problems.append(f"Empty topic content: {topic.relative_to(dist)}")
        if report["units"] != 7 or report["topics"] != 41 or report["nonempty_topics"] != 41:
            problems.append("Course must contain 7 units and 41 nonempty topics")
    except (OSError, ValueError, KeyError, TypeError) as error:
        problems.append(f"Course audit failed: {error}")
    report["passed"] = not problems
    return report

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dist", type=Path, required=True)
    parser.add_argument("--mode", choices=["assets-only"], default="assets-only")
    args = parser.parse_args()
    report = verify(args.dist.resolve())
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["passed"] else 2

if __name__ == "__main__":
    sys.exit(main())
