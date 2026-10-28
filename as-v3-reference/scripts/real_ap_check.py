"""Downloads an official public PDF for local QA only; does not add it to a shared bank.

College Board retains rights. PDF and extracted question text are not distributed
in this module package. The report contains identifiers and extraction checks only.
"""
from pathlib import Path
import hashlib,json,urllib.request,argparse
from gmf_v3.service import Modules

URL="https://apcentral.collegeboard.org/media/pdf/ap-physics-c-mechanics-course-and-exam-description.pdf"
EXPECTED=dict(zip(map(str,range(1,16)),"DCBDBBBCBDDADCC"))


def run(pdf,output,data_dir):
    m=Modules(data_dir)
    batch=m.import_pdfs([pdf],scope="exam_private",owner_id="qa-official-ap",auto_solve=False,page_range=(177,193))
    rows=[]
    for qid in batch.files[0].get("question_ids",[]):
        q=m.store.question(qid);v=m.store.version(q.current_version_id);a=m.store.latest_answer(v.version_id)
        inp=m.answers.solver_input(v.version_id)
        rows.append({"number":q.source_number,"option_count":len(v.options),"extracted_answer":a.label if a else None,
            "expected_answer":EXPECTED.get(q.source_number),"answer_status":a.status.value if a else None,
            "has_visual":v.has_visual,"pages":[s.page for s in v.spans],"warnings":v.warnings,
            "original_and_page_image_preserved":all(any(m.store.asset(x).kind==kind for x in v.asset_ids) for kind in ["original_pdf","page_image","question_crop"]),
            "answer_payload_excludes_student_response":"student_answer" not in inp.model_dump()})
    ok=len(rows)==15 and all(r["extracted_answer"]==r["expected_answer"] and r["option_count"]==4 and r["original_and_page_image_preserved"] for r in rows)
    report={"source_url":URL,"source_sha256":hashlib.sha256(Path(pdf).read_bytes()).hexdigest(),"page_range":[177,193],
        "expected_mcq":15,"extracted_mcq":len(rows),"passed":ok,"questions":rows,
        "limitations":["Source answers remain Provisional pending accountable review","Formula transcription and visual association require review","No live AI request made","Not an AP syllabus or full exam conformance test"]}
    Path(output).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf8")
    print(json.dumps({"passed":ok,"extracted_mcq":len(rows),"answer_mappings_matched":sum(r["extracted_answer"]==r["expected_answer"] for r in rows)},indent=2))
    return ok


if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--pdf");p.add_argument("--download",action="store_true");p.add_argument("--output",default="docs/real-ap-validation.json");p.add_argument("--data",default="runtime/real-ap-check")
    args=p.parse_args();pdf=Path(args.pdf or "runtime/external/ap-mechanics-ced.pdf")
    if args.download:
        pdf.parent.mkdir(parents=True,exist_ok=True)
        req=urllib.request.Request(URL,headers={"User-Agent":"Mozilla/5.0"})
        pdf.write_bytes(urllib.request.urlopen(req,timeout=60).read())
    if not pdf.is_file():p.error("Provide --pdf or --download")
    raise SystemExit(0 if run(pdf,args.output,args.data) else 1)

