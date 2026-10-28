"""Native PDF layout + MCQ extraction. Original visuals remain the source of truth."""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import tempfile
import traceback
from dataclasses import dataclass
from pathlib import Path

import pdfplumber
from pypdf import PdfReader

from .contracts import (Option, ParsedQuestion, ParseResult, QuestionAsset,
                        QuestionVersion, SourceRecord, SourceSpan)
from .openassess_adapter import compact_answer_pairs

STRICT_QUESTION = re.compile(r"^\s*(?:Question\s+|Q\s*|第\s*)?(\d{1,3})\s*(?:[.)．、](?!\d)|题)\s*(.*)$", re.I)
QUESTION = re.compile(r"^\s*(?:Question\s+|Q\s*|第\s*)?(\d{1,3})(?:\s*(?:[.)．、](?!\d)|题)\s*|\s+(?=[A-Za-z\u3400-\u9fff]))(.*)$", re.I)
OPTION = re.compile(r"(?:^|\s+)(?:\(([A-Ha-h])\)|([A-Ha-h])[.)])\s*")
BARE_OPTION = re.compile(r"^\s*([A-H])()(?=\s|$)\s*")
BARE_INLINE = re.compile(r"(?<!\S)([A-H])()(?=\s|$)")
SHARED_START = re.compile(r"^(?:shared\s+(?:stimulus|material)\b|(?:questions?|题目)\s*\d+\s*(?:[-–—]|and|through|to|至)\s*\d+)",re.I)
ANSWER = re.compile(r"\b(?:correct\s+answer|answer|ans|答案)\s*[:：=]\s*\(?([A-H])\)?\b", re.I)
KEY_HEADER = re.compile(r"^(?:(?:multiple.choice\s+)?answer\s*key\b.*|answers\s*[:：]?|答案(?:表|汇总)?\s*[:：]?)$", re.I)
PAIR = re.compile(r"(?:^|\s)(\d{1,3})\s*[.):\-]?\s*\(?([A-H])\)?(?=\s|$)", re.I)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def question_start(line, margins):
    match = QUESTION.match(line.text)
    # Bare numbers must be at the column's text margin, not in a graph or formula.
    return match if match and (STRICT_QUESTION.match(line.text) or line.x0 <= margins[(line.page,line.col)] + 12) else None


def bare_option_rows(lines):
    """Accept a geometrically aligned A, B, ... sequence, not prose starting 'A'."""
    if any(OPTION.search(l.text) for l in lines[1:]):
        return {}
    chain, best = [], []
    for ix, line in enumerate(lines[1:], 1):
        matches=list(BARE_INLINE.finditer(line.text)) if BARE_OPTION.match(line.text) else []
        if not matches:
            continue
        offsets=[];offset=0
        for token in line.tokens or []:
            offsets.append((offset,token));offset+=len(token['text'])+1
        for match in matches:
            token_ix=next((i for i,(pos,t) in enumerate(offsets) if pos==match.start(1)),None)
            # An inline second column needs real spacing, not an A/B variable in prose.
            if match.start(1)>0 and (token_ix is None or not token_ix or offsets[token_ix][1]['x0']-offsets[token_ix-1][1]['x1']<18):continue
            if match[1] == 'A':
                chain = [(ix, match)]
            elif chain and len(chain)<8 and match[1] == 'ABCDEFGH'[len(chain)] and abs(line.x0-lines[chain[0][0]].x0) <= 12:
                chain.append((ix,match))
            if len(chain) >= max(2,len(best)):
                best = list(chain)
    rows={}
    for ix,match in best:rows.setdefault(ix,[]).append(match)
    return rows


def visual_top(layout, left, top, right):
    """Include a numerator above its native option label, bounded by preceding text."""
    prior=[l['bottom']+2 for l in layout['lines'] if l['bottom']<=top and l['x0']<right and l['x1']>left]
    floor=max(0,top-18,max(prior,default=0))
    candidates=[g['top']-3 for g in layout.get('geometry',[]) if g.get('x0',0)<right and g.get('x1',right)>left and floor<=g.get('top',0)<top and g.get('bottom',0)>=floor]
    return max(floor,min([top,*candidates]))


def fingerprints(stem: str, options: list[Option], visuals: list[str] = ()) -> tuple[str, str]:
    # Preserve values, punctuation and option order: 2m and 3m must never deduplicate.
    text = json.dumps([re.sub(r"\s+", " ", stem).strip(), [(o.label, re.sub(r"\s+", " ", o.text).strip()) for o in options]], ensure_ascii=False)
    t = digest(text.encode())
    return t, digest((t + "|" + "|".join(visuals)).encode())


@dataclass
class Line:
    text: str
    page: int
    x0: float
    top: float
    x1: float
    bottom: float
    col: int = 0
    extraction: str = "native"
    tokens: list[dict] | None = None


def _native_lines(page, number: int, mode: str) -> tuple[list[Line], bool]:
    words = page.extract_words(x_tolerance=2, y_tolerance=3, keep_blank_chars=False)
    def make(words, col):
        rows = []
        for w in sorted(words, key=lambda w: (round(w["top"] / 3), w["x0"])):
            if rows and abs(rows[-1][0]["top"] - w["top"]) < 3:
                rows[-1].append(w)
            else:
                rows.append([w])
        return [Line(" ".join(w["text"] for w in sorted(row, key=lambda w:w["x0"])), number,
                     min(w["x0"] for w in row), min(w["top"] for w in row),
                     max(w["x1"] for w in row), max(w["bottom"] for w in row), col,
                     tokens=[{k:w[k] for k in ['text','x0','x1','top','bottom']} for w in sorted(row,key=lambda w:w['x0'])]) for row in rows]
    single = make(words, 0)
    half = float(page.width) / 2
    starts = [l for l in single if QUESTION.match(l.text)]
    # Inspect individual leading number words; an entire row can contain two questions.
    left_start = any(re.fullmatch(r"\d{1,3}[.)]", w["text"]) and w["x0"] < half-25 for w in words)
    right_start = any(re.fullmatch(r"\d{1,3}[.)]", w["text"]) and w["x0"] > half+5 for w in words)
    two = mode == "two-column" or (mode == "auto" and left_start and right_start)
    if two:
        return make([w for w in words if w["x0"] < half], 0) + make([w for w in words if w["x0"] >= half], 1), True
    return single, False


def _ocr_lines(image: Path, page: int, width: float, height: float) -> list[Line]:
    from PIL import Image
    with Image.open(image) as im:
        sx, sy = width / im.width, height / im.height
    result = subprocess.run(["tesseract", str(image), "stdout", "--psm", "3", "tsv"], capture_output=True, text=True, timeout=90, check=True)
    import csv, io
    groups = {}
    for w in csv.DictReader(io.StringIO(result.stdout), delimiter="\t", quoting=csv.QUOTE_NONE):
        if w.get("text", "").strip() and float(w.get("conf", -1)) >= 0:
            groups.setdefault((w["block_num"], w["par_num"], w["line_num"]), []).append(w)
    lines = []
    for row in groups.values():
        lines.append(Line(" ".join(w["text"] for w in row), page,
            min(int(w["left"]) for w in row)*sx, min(int(w["top"]) for w in row)*sy,
            max(int(w["left"])+int(w["width"]) for w in row)*sx,
            max(int(w["top"])+int(w["height"]) for w in row)*sy, extraction="ocr"))
    return sorted(lines, key=lambda x: (x.top, x.x0))


class PDFProcessingCore:
    PARSER_VERSION = "native-segments/9-ocr-error-evidence"

    def __init__(self, asset_root: Path | str, *, max_pages=2000, max_bytes=50*1024*1024, segment_pages=12):
        self.asset_root = Path(asset_root).resolve()
        self.asset_root.mkdir(parents=True, exist_ok=True)
        self.max_pages, self.max_bytes = max_pages, max_bytes
        self.segment_pages = max(1, min(50, segment_pages))

    def parse(self, pdf_path: Path | str, *, scope: str, owner_id: str,
              source_url: str | None = None, license_name: str | None = None,
              reuse_confirmed=False, layout="auto", ocr=True, page_range: tuple[int,int] | None = None,
              checkpoint=None, diagnostics=None) -> ParseResult:
        with tempfile.TemporaryDirectory(prefix="parse-",dir=self.asset_root) as scratch:
            return self._parse_impl(pdf_path,scope=scope,owner_id=owner_id,source_url=source_url,
                license_name=license_name,reuse_confirmed=reuse_confirmed,layout=layout,ocr=ocr,
                page_range=page_range,work_folder=Path(scratch),checkpoint=checkpoint,diagnostics=diagnostics)

    def _parse_impl(self,pdf_path,*,scope,owner_id,source_url,license_name,reuse_confirmed,layout,ocr,page_range,work_folder,checkpoint,diagnostics=None):
        report = diagnostics if diagnostics is not None else {}
        report.update(stage='pdf_read', pages=[], candidates=[])
        if scope not in {"bank", "exam_private"} or not owner_id:
            raise ValueError("scope and owner_id required")
        if layout not in {"auto", "single", "two-column"}:
            raise ValueError("unknown layout")
        path = Path(pdf_path)
        if path.stat().st_size > self.max_bytes:
            raise ValueError("PDF exceeds byte limit")
        data = path.read_bytes()
        if not data.startswith(b"%PDF-"):
            raise ValueError("not a PDF")
        sha = digest(data)
        doc_id = "doc_" + digest(f"{scope}|{owner_id}|{sha}".encode())[:32]
        folder = self.asset_root / doc_id
        folder.mkdir(exist_ok=True)
        original = folder / "original.pdf"
        if original.exists():
            if digest(original.read_bytes())!=sha:raise ValueError("stored original PDF hash mismatch")
        else:original.write_bytes(data)
        assets, warnings, all_lines, page_meta = [], [], [], []
        reader = PdfReader(original)
        if reader.is_encrypted and not reader.decrypt(""):
            raise ValueError("password-protected PDF requires an unlocked local copy")
        n = len(reader.pages)
        report['pdf_read']={'pages':n,'success':True}
        report['stage']='text_extraction'
        if n > self.max_pages and page_range is None:
            raise ValueError("PDF exceeds safety page limit; select an explicit page_range")
        first, last = page_range or (1, n)
        if not 1 <= first <= last <= n or last-first+1 > self.max_pages:
            raise ValueError("invalid or excessive page_range")

        def asset(file, kind, page=None, bbox=None, safe=False):
            file_sha=digest(file.read_bytes())
            if kind!="original_pdf":
                destination=folder/f"{file.stem}-{file_sha}.{file.suffix.lstrip('.')}"
                if destination.exists():
                    if digest(destination.read_bytes())!=file_sha:raise ValueError("immutable asset hash mismatch")
                else:destination.write_bytes(file.read_bytes())
                file=destination
            a = QuestionAsset(asset_id="asset_" + digest(f"{doc_id}|{kind}|{file_sha}|{page}|{bbox}".encode())[:32],
                document_id=doc_id, kind=kind, relative_path=file.relative_to(self.asset_root).as_posix(),
                sha256=file_sha, media_type="application/pdf" if file.suffix==".pdf" else "application/json" if file.suffix==".json" else "image/png",
                page=page, bbox=bbox, exam_safe=False, solver_usable=safe)
            assets.append(a)
            return a

        original_asset = asset(original, "original_pdf")
        page_cache = {}
        with pdfplumber.open(original) as pdf:
            def extract_page(pn):
                page = pdf.pages[pn-1]
                image = page.to_image(resolution=144, antialias=True).original.convert("RGB")
                image_path = work_folder / f"page-{pn:04}.png"
                image.save(image_path)
                lines, two = _native_lines(page, pn, layout)
                native_characters=sum(len(l.text) for l in lines)
                page_warnings=[];ocr_error=None
                if sum(len(l.text) for l in lines) < 15:
                    page_warnings.append(f"page:{pn}:native_text_missing")
                    if ocr:
                        try:
                            lines = _ocr_lines(image_path, pn, float(page.width), float(page.height))
                            page_warnings.append(f"page:{pn}:ocr_used_requires_review")
                        except (OSError, subprocess.SubprocessError) as exc:
                            page_warnings.append(f"page:{pn}:ocr_unavailable_or_failed")
                            ocr_error={'stage':'text_extraction','type':type(exc).__name__,'message':str(exc),'traceback':traceback.format_exc()}
                # Full-page context prevents a preceding diagram being lost at a question boundary.
                # It is solver input only when no answer/solution text is detected on that page.
                context_safe=bool(lines) and all(l.extraction=="native" for l in lines) and not any(ANSWER.search(l.text) or KEY_HEADER.match(l.text.strip()) or re.search(r"\bsolutions?\b|\bexplanation\b",l.text,re.I) for l in lines)
                a = asset(image_path, "page_image", pn, safe=context_safe)
                label = reader.page_labels[pn-1] if reader.page_labels else str(pn)
                # Save positions, raster locations and vector geometry counts; visual evidence is also in page PNG.
                meta=dict(page=pn, label=label, width=float(page.width), height=float(page.height),
                    native_characters=native_characters,
                    ocr_error=ocr_error,
                    key_tokens=page.extract_words(x_tolerance=2,y_tolerance=3) if any(KEY_HEADER.match(l.text.strip()) for l in lines) and native_characters else [],
                    columns=2 if two else 1, image_count=len(page.images), vector_count=len(page.curves)+len(page.lines)+len(page.rects),
                    images=[{k:v for k,v in im.items() if k in {"x0","x1","top","bottom","width","height"}} for im in page.images],
                    geometry=[{k:g.get(k) for k in ["x0","x1","top","bottom"]} for g in [*page.images,*page.curves,*page.lines,*page.rects]],
                    lines=[vars(l) for l in lines])
                image.close();page.close()
                return {"meta":meta,"asset":a.model_dump(),"warnings":page_warnings}

            cache_key=digest(json.dumps([self.PARSER_VERSION,sha,doc_id,layout,ocr,first,last,self.segment_pages]).encode())
            ranges=[(start,min(last,start+self.segment_pages-1)) for start in range(first,last+1,self.segment_pages)]
            if checkpoint:checkpoint.prepare(cache_key,ranges)
            for start,end in ranges:
                entries=checkpoint.load(cache_key,start,end) if checkpoint else None
                if entries is None:
                    if checkpoint:checkpoint.begin(cache_key,start,end)
                    before=len(assets)
                    try:
                        entries=[extract_page(pn) for pn in range(start,end+1)]
                        if checkpoint:checkpoint.complete(cache_key,start,end,entries)
                    except Exception as exc:
                        if checkpoint:checkpoint.fail(cache_key,start,end,exc)
                        raise
                    # Use exactly the same restoration path for fresh and recovered segments.
                    del assets[before:]
                for entry in entries:
                    meta=entry['meta'];pn=meta['page'];a=QuestionAsset.model_validate(entry['asset'])
                    assets.append(a);warnings.extend(entry['warnings']);page_meta.append(meta)
                    page_cache[pn]=(self.asset_root/a.relative_path,meta['width'],meta['height'],meta['columns']==2,meta['label'],a)
                    for raw in meta['lines']:
                        line=Line(**raw)
                        if re.match(r"^Unit\s+\d+\s*:",line.text,re.I) or re.fullmatch(r"(?:AP PHYSICS C: MECHANICS\s+)?Test Booklet",line.text,re.I):continue
                        if line.top>meta['height']-65 and (re.search(r"Course and Exam Description|Return to Table|College Board|Exam.Information|AP Physics|Page\s+\d+\s+of",line.text,re.I) or re.fullmatch(r"\d+",line.text)):continue
                        line.text=re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]"," ",line.text)
                        all_lines.append(line)
            report['pages']=[{'page':p['page'],'native_characters':p.get('native_characters',sum(len(l['text']) for l in p['lines'] if l['extraction']=='native')),'extracted_characters':sum(len(l['text']) for l in p['lines']),'lines':len(p['lines']),'columns':p['columns']} for p in page_meta]
            report['text_extraction']={'native_characters':sum(p['native_characters'] for p in report['pages']),'extracted_characters':sum(p['extracted_characters'] for p in report['pages']),'ocr_unavailable_pages':sum('ocr_unavailable_or_failed' in w for w in warnings)}
            report['ocr_errors']=[{'page':p['page'],**p['ocr_error']} for p in page_meta if p.get('ocr_error')]
            report['stage']='question_detection'
            margins={}
            for line in all_lines:
                key=(line.page,line.col);margins[key]=min(margins.get(key,line.x0),line.x0)
            # Remove repeated running headers/footers, never question/option markers.
            repeated={}
            def running_key(line):return re.sub(r'\d+','#',line.text.strip())
            for line in all_lines:
                page=page_meta[line.page-first]
                if (line.top<45 or line.top>page['height']-45) and not QUESTION.match(line.text) and not BARE_OPTION.match(line.text):repeated.setdefault(running_key(line),set()).add(line.page)
            all_lines=[l for l in all_lines if not ((l.top<45 or l.top>page_meta[l.page-first]['height']-45) and len(repeated.get(running_key(l),()))>=max(2,(last-first+2)//2))]
            keys, chunks, current, in_key = {}, [], None, False
            detailed_key=False;key_row=None;key_matches=0
            sections={p['page']:next((m[1] for l in p['lines'] if (m:=re.match(r'^Unit\s+(\d+)\s*:',l['text'],re.I))),None) for p in page_meta}
            multiple_sections=len(set(sections.values())-{None})>1
            first_question={}
            for l in all_lines:
                if question_start(l,margins):first_question.setdefault(l.page,l)
            non_mcq=False;active_section=None
            for line in all_lines:
                section=sections.get(line.page)
                if section and active_section and section!=active_section:in_key=False;non_mcq=False
                if section:active_section=section
                if SHARED_START.match(line.text):
                    if current:
                        current['stop']=line;chunks.append(current);current=None
                    continue
                if re.match(r'^(?:Section\s+I\b.*(?:Multiple|MCQ)|Multiple[\s-]*Choice(?:\s+(?:Questions?|Section))?\s*$)',line.text,re.I):
                    non_mcq=False;in_key=False
                    continue
                if KEY_HEADER.match(line.text.strip()):
                    in_key = True
                    if current:
                        current["stop"] = line
                        chunks.append(current)
                        current = None
                    continue
                if in_key:
                    # A native answer table may put question numbers and answers in
                    # separate aligned rows. Require equal counts and matching columns.
                    number_tokens=re.findall(r'(?:Q\s*)?(\d{1,3})',line.text,re.I)
                    if re.fullmatch(r'(?:Q?\d{1,3}\s*){2,}',line.text,re.I) and len(set(number_tokens))==len(number_tokens):
                        key_row=(line,number_tokens);continue
                    if key_row and re.fullmatch(r'[A-H](?:\s+[A-H])+',line.text,re.I):
                        prior,numbers=key_row;labels=line.text.upper().split();page=page_meta[line.page-first]
                        row_tokens=lambda top:sorted([w for w in page.get('key_tokens',[]) if abs(w['top']-top)<3],key=lambda w:w['x0'])
                        heads,answers=row_tokens(prior.top),row_tokens(line.top)
                        aligned=prior.page==line.page and 0<line.top-prior.top<60 and len(heads)==len(answers)==len(numbers)==len(labels) and all(abs(a['x0']-h['x0'])<=8 or abs((a['x0']+a['x1']-h['x0']-h['x1'])/2)<=8 for h,a in zip(heads,answers))
                        if aligned:
                            for num,label in zip(numbers,labels):keys.setdefault((sections.get(line.page),str(int(num))),[]).append(label)
                            key_matches+=len(labels)
                        key_row=None;continue
                    key_row=None
                    if re.search(r"Skill|Objective|Knowledge|Alignment",line.text,re.I):detailed_key=True
                    pairs=compact_answer_pairs(line.text) or PAIR.findall(line.text)
                    if detailed_key:pairs=pairs[:1] if re.match(r"^\s*\d+\s+[A-H]\b",line.text,re.I) else []
                    for num, label in pairs:
                        keys.setdefault((sections.get(line.page),str(int(num))), []).append(label.upper())
                        key_matches+=1
                    continue
                if re.search(r"Section\s+(?:II|2).*Free.?Response|Free[\s-]*Response|自由作答",line.text,re.I):
                    non_mcq=True
                    if current:
                        current["stop"]=line;chunks.append(current);current=None
                    continue
                if non_mcq: continue
                # Keep the complete continuation, including wrapped option text after its label.
                # The next question's crop independently retains any figure preceding its number.
                m = question_start(line,margins)
                if m:
                    if current:
                        current["stop"] = line
                        chunks.append(current)
                    current = dict(number=str(int(m[1])), section=sections.get(line.page), lines=[line], first_text=m[2],page_first=first_question.get(line.page) is line)
                elif current:
                    current["lines"].append(line)
            if current:
                chunks.append(current)
            report['question_detection']={'candidates':len(chunks),'per_page':{str(p['page']):sum(question_start(l,margins) is not None for l in all_lines if l.page==p['page']) for p in page_meta}}
            report['stage']='option_split'
            parsed = []
            seen_numbers = set()
            for chunk in chunks:
                num = chunk["number"]
                lines = chunk["lines"]
                source_key=keys.get((chunk['section'],num),[])
                if not source_key and not multiple_sections:source_key=keys.get((None,num),[])
                stem, opts, source_answers, blocked = [], {}, list(source_key), False
                bare_rows=bare_option_rows(lines)
                cutoffs = {}
                for ix, line in enumerate(lines):
                    text = chunk["first_text"] if ix == 0 else line.text
                    am = ANSWER.search(text)
                    if am:
                        source_answers.append(am[1].upper())
                        cutoffs[(line.page,line.col)] = min(cutoffs.get((line.page,line.col),line.top),line.top)
                        text = text[:am.start()].rstrip()
                        blocked = True
                    if re.match(r"^(solution|explanation|解析|解答)\s*[:：]", text, re.I):
                        cutoffs[(line.page,line.col)] = line.top
                        blocked = True
                        continue
                    if blocked and not am:
                        continue
                    matches = list(OPTION.finditer(text)) or bare_rows.get(ix,[])
                    if matches:
                        before = text[:matches[0].start()].strip()
                        if before and not opts:
                            stem.append(before)
                        for j, m in enumerate(matches):
                            label = (m[1] or m[2]).upper()
                            value = text[m.end():matches[j+1].start() if j+1<len(matches) else len(text)].strip()
                            if label in opts:
                                opts[label] += " " + value
                            else:
                                opts[label] = value
                    elif text.strip():
                        if opts:
                            opts[next(reversed(opts))] += " " + text.strip()
                        else:
                            stem.append(text.strip())
                # A malformed candidate is reported, never silently counted as a complete question.
                candidate={'number':num,'page':lines[0].page,'pages':sorted({l.page for l in lines}),'stem_characters':len(' '.join(stem)),'labels':list(opts),'source_answer_labels':list(source_answers)}
                report['candidates'].append(candidate)
                if len(opts) < 2 or not stem:
                    candidate.update(status='rejected',reason='missing_stem' if not stem else 'fewer_than_two_options')
                    warnings.append(f"candidate:{num}:not_complete_mcq")
                    continue
                candidate.update(status='parsed',reason=None)
                q_warnings = []
                if page_range and last<n and not chunk.get('stop'):
                    q_warnings.append('page_range_boundary_requires_review')
                if not all(opts.values()):
                    q_warnings.append("visual_option_requires_review")
                    opts={k:(value or f"[Visual option {k}; inspect original question crop]") for k,value in opts.items()}
                identity=(chunk['section'],num)
                if identity in seen_numbers:
                    q_warnings.append("duplicate_source_number")
                seen_numbers.add(identity)
                if list(opts) != list("ABCDEFGH"[:len(opts)]):
                    q_warnings.append("nonsequential_options")
                if any(l.extraction == "ocr" for l in lines):
                    q_warnings.append("ocr_requires_review")
                if any("(cid:" in t or "\ufffd" in t for t in [*stem,*opts.values()]):
                    q_warnings.append("text_encoding_requires_visual_review")
                spans, q_assets, visual_hashes, has_visual = [], [original_asset.asset_id], [], False
                groups = {}
                for l in lines:
                    groups.setdefault((l.page,l.col), []).append(l)
                for index, ((pn,col), glines) in enumerate(groups.items()):
                    image_path, width, height, two, label, pa = page_cache[pn]
                    left = width/2 if two and col else 0
                    right = width/2 if two and not col else width
                    y0 = max(0, min(l.top for l in glines)-4)
                    y0 = visual_top(next(p for p in page_meta if p['page']==pn),left,y0,right)
                    if chunk.get("page_first") and pn==lines[0].page:
                        prefix=[l for l in all_lines if l.page==pn and l.col==col and l.top<lines[0].top]
                        # Do not expose the preceding question's continued options in the next crop.
                        if prefix and not any(OPTION.search(l.text) or BARE_OPTION.match(l.text) or SHARED_START.match(l.text) for l in prefix):y0=max(0,min(l.top for l in prefix)-4)
                    stop = chunk.get("stop")
                    y1 = min(height-20, stop.top-3) if stop and stop.page==pn and stop.col==col else height-20
                    if (pn,col) in cutoffs:
                        y1 = min(y1,cutoffs[(pn,col)]-2)
                    y1 = max(y0+2,y1)
                    bbox = (left,y0,right,min(height,y1))
                    span = SourceSpan(page=pn,page_label=label,bbox=bbox,extraction=glines[0].extraction)
                    spans.append(span)
                    crop_path = work_folder / f"q-{len(parsed)+1:04}-{index}.png"
                    from PIL import Image
                    with Image.open(image_path) as image:
                        crop = image.crop((round(left/width*image.width),round(y0/height*image.height),round(right/width*image.width),round(y1/height*image.height)))
                        crop.save(crop_path);crop.close()
                    # Source overlays can contain checkmarks/colored answers even without textual markers.
                    # All crops require a review before exposure in an exam; only answer-free native crops feed the solver.
                    safe = not source_answers and not any(l.extraction=="ocr" for l in glines)
                    ca = asset(crop_path,"question_crop",pn,bbox,safe)
                    q_assets.extend([pa.asset_id,ca.asset_id])
                    geometry = next(p['geometry'] for p in page_meta if p['page']==pn)
                    visual = any(g.get("x0",0)<right and g.get("x1",width)>left and g.get("top",0)<y1 and g.get("bottom",height)>y0 for g in geometry)
                    if visual:
                        has_visual = True
                        visual_hashes.append(ca.sha256)
                text = " ".join(stem)
                options = [Option(label=k,text=v.strip()) for k,v in opts.items()]
                tf, fp = fingerprints(text,options,visual_hashes)
                # A rejected preceding candidate must not change every subsequent Question ID.
                anchor=f"{chunk['section'] or ''}|{num}|{lines[0].page}|{round(lines[0].top,1)}|{lines[0].col}"
                qid = "q_" + digest(f"{doc_id}|anchor-v2|{anchor}".encode())[:32]
                vid = qid.replace("q_","qv_",1) + "_1"
                formulas = [l.text for l in lines if re.search(r"[=∫√∑²³^]|\b[mk]g?/?s[2²]?\b",l.text) and not ANSWER.search(l.text)]
                if has_visual:
                    q_warnings.append("visual_and_formula_transcription_requires_review")
                v = QuestionVersion(version_id=vid,question_id=qid,version=1,stem=text,options=options,
                    spans=spans,asset_ids=list(dict.fromkeys(q_assets)),formula_fragments=formulas,
                    raw_text="\n".join(l.text for l in lines),text_fingerprint=tf,fingerprint=fp,
                    warnings=q_warnings,has_visual=has_visual,source_section=chunk['section'])
                parsed.append(ParsedQuestion(number=num,version=v,source_answers=source_answers))
        layout_path = work_folder / "layout.json"
        layout_path.write_text(json.dumps(page_meta,ensure_ascii=False,indent=2),encoding="utf8")
        asset(layout_path,"layout_json")
        if not parsed:
            warnings.append("no_complete_mcq_detected_manual_review_required")
        source = SourceRecord(document_id=doc_id,sha256=sha,filename=path.name,scope=scope,owner_id=owner_id,
            source_url=source_url,license_name=license_name,reuse_confirmed=reuse_confirmed,page_count=n,warnings=warnings)
        report['option_split']={'passed':len(parsed),'rejected':len(chunks)-len(parsed)}
        report['answer_key']={'explicit_matches':key_matches,'unique_question_numbers':len(keys)}
        report['stage']='parsed'
        return ParseResult(source=source,assets=assets,questions=parsed,warnings=warnings,diagnostics=report)

    def enrich_docling(self, document_id: str) -> QuestionAsset:
        """Optional expensive path. Never removes native extraction or original images."""
        if not re.fullmatch(r"doc_[0-9a-f]{32}",document_id):
            raise ValueError("invalid document id")
        try:
            from docling.document_converter import DocumentConverter, PdfFormatOption
            from docling.datamodel.base_models import InputFormat
            from docling.datamodel.pipeline_options import PdfPipelineOptions
        except ImportError as exc:
            raise RuntimeError("Docling is optional and is not installed; pip install '.[docling]'") from exc
        options = PdfPipelineOptions(do_ocr=True, do_formula_enrichment=True, document_timeout=120)
        options.enable_remote_services = False
        converter = DocumentConverter(allowed_formats=[InputFormat.PDF],format_options={InputFormat.PDF:PdfFormatOption(pipeline_options=options)})
        folder = self.asset_root/document_id
        result = converter.convert(folder/"original.pdf")
        data=json.dumps(result.document.export_to_dict(),ensure_ascii=False).encode("utf8")
        sha=digest(data);out=folder/f"docling-{sha}.json"
        if not out.exists():out.write_bytes(data)
        return QuestionAsset(asset_id="asset_"+digest(f"{document_id}|docling_json|{sha}".encode())[:32],document_id=document_id,
            kind="docling_json",relative_path=out.relative_to(self.asset_root).as_posix(),sha256=sha,media_type="application/json")
