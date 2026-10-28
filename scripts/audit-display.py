"""Read-only display quality audit for an isolated real-workbook bank."""
import argparse,json,csv,sys
from pathlib import Path
from collections import Counter
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'as-v3-reference')]
from backend.bank import Bank
from backend.quality import inspect_display,attach_visual_review,repair_display_rasters
from PIL import Image,ImageDraw

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--runtime',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--reviews',type=Path);p.add_argument('--repair-raster',action='store_true');p.add_argument('--sheets',action='store_true');a=p.parse_args()
    if a.runtime.resolve().is_relative_to(ROOT/'runtime'):raise ValueError('Use an isolated runtime outside normal user data')
    b=Bank(a.runtime);out=a.output;out.mkdir(parents=True,exist_ok=True)
    questions=[(q,v) for q,v,_,_ in b.store.list_questions(scope='bank',include_drafts=True,limit=None) if b.store.source(q.document_id).owner_id=='isolated-workbook-audit']
    if a.repair_raster:(out/'repair.json').write_text(json.dumps([repair_display_rasters(b,d) for d in sorted({q.document_id for q,v in questions})],indent=2))
    rows=sorted([inspect_display(b,q,v) for q,v in questions],key=lambda r:(int(r['unit']),int(r['source_number'])))
    reviews=json.loads(a.reviews.read_text()) if a.reviews else {}
    rows=[attach_visual_review(r,reviews[r['question_id']]) if r['question_id'] in reviews else r for r in rows]
    (out/'questions.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2))
    with (out/'questions.csv').open('w',newline='') as f:
        w=csv.writer(f);w.writerow(['unit','number','question_id','version_id','pages','state','reviewer_kind','faults','warnings'])
        for r in rows:w.writerow([r['unit'],r['source_number'],r['question_id'],r['version_id'],str(r['pages']),r['quality_state'],r['visual_review']['reviewer_kind'] if r['visual_review'] else '',','.join(r['automated_faults']),','.join(r['parser_warnings'])])
    if a.sheets:
        unit=[r for r in rows if r['unit']=='1']
        for start in range(0,len(unit),3):
            images=[]
            for r in unit[start:start+3]:
                banner=Image.new('RGB',(1000,35),'#e5eef5');ImageDraw.Draw(banner).text((12,10),'Unit 1 Q'+r['source_number']+' PDF '+str(r['pages']),fill='black');images.append(banner)
                for asset in r['assets']:
                    with Image.open(b.assets/asset['relative_path']) as im:images.append(im.convert('RGB').resize((1000,round(im.height*1000/im.width))))
            sheet=Image.new('RGB',(1000,sum(im.height for im in images)),'white');y=0
            for im in images:sheet.paste(im,(0,y));y+=im.height
            sheet.save(out/f'unit1-{start+1:02}-{start+3:02}.png')
    summary={'total':len(rows),'states':dict(Counter(r['quality_state'] for r in rows)),'units':[{'unit':u,'total':sum(r['unit']==str(u) for r in rows),'states':dict(Counter(r['quality_state'] for r in rows if r['unit']==str(u)))} for u in range(1,8)]}
    (out/'summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary))
if __name__=='__main__':main()
