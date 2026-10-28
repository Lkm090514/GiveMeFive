"""Source-bound, quarantine-only provisional calculations; never certifies or publishes."""
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'as-v3-reference')]
import sympy as s
from backend.bank import Bank
from gmf_v3.contracts import AnswerEvidence,AnswerStatus,now
SHA='5b0c3224ab846610ea82029e9661f00083c5b94aec0489b623c4bdd0503e45f1'
def calculations():
    t=s.symbols('t',positive=True);d=s.Symbol('d');u=s.Symbol('u');ge,gm=s.symbols('ge gm',positive=True)
    return {
      4:('C',s.sqrt((t-6)**2+(4*t-5)**2).subs(t,2),s.Integer(5),'At t=2 acceleration=(-4,3), norm=5 m/s².'),
      5:('D',s.sqrt((2*t-2)**2+(t-7)**2).subs(t,3),4*s.sqrt(2),'Velocity=(4,-4), 45° clockwise, magnitude 4sqrt(2) m/s.'),
      6:('C',s.sqrt((-8-3)**2+(15-4)**2),11*s.sqrt(2),'Subtract velocities first: (-11,11); magnitude rounds to 15.6 m/s.'),
      10:('C',((5*t**2-t**3).subs(t,3)-(5*t**2-t**3).subs(t,1))/2,s.Integer(7),'Average velocity=(18-4)/2=7 m/s.'),
      11:('B',s.diff(t**3/2+2,t,2).subs(t,3),s.Integer(9),'Second derivative of position at t=3, units m/s².'),
      12:('B',s.diff(10*t**s.Rational(3,2)+t,t).subs(t,4),s.Integer(31),'Derivative evaluated at t=4; original units cm/s.'),
      15:('A',s.sqrt(6**2+5**2)-s.sqrt(10**2+(-3)**2),s.sqrt(61)-s.sqrt(109),'Differentiate vector velocities: first acceleration magnitude is smaller.'),
      18:('A',abs(s.Rational(1,2)-s.Rational(2,3)),s.Rational(1,6),'Return time tf=2u/g, speed at 2tf/3 is gtf/6.'),
      19:('A',s.solve(s.Eq(d,u*t/2),u)[0],2*d/t,'Constant slowing to rest: mean velocity=u/2, so u=2Δx/t.'),
      21:('C',s.Integer(2)**2/s.Integer(2),s.Integer(2),'From rest v²=2aΔx; doubled speed and distance imply twice a.'),
      22:('C',s.sqrt(s.Integer(16)),s.Integer(4),'Same drop height, time proportional to 1/sqrt(g).'),
      23:('C',s.Rational(1,3),s.Rational(1,3),'Same final speed from rest: distance inversely proportional to acceleration.'),
      40:('D',s.Integer(2)**2,s.Integer(4),'Same angle/gravity, maximum height proportional to speed squared.'),
      42:('A',s.sqrt(1/ge)/s.sqrt(1/gm),s.sqrt(gm/ge),'Horizontal launch, same height/speed: range proportional to 1/sqrt(g).')}
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--runtime',type=Path,required=True);p.add_argument('--index',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();b=Bank(a.runtime)
    if a.runtime.resolve().is_relative_to(ROOT/'runtime'):raise ValueError('Use quarantine outside normal data')
    idx=json.loads(a.index.read_text());directory={(str(q['unit']),str(q['question_number_in_unit'])):q['pl_canonical_topic_id'] for q in idx['questions']};answers=[];tags=[];calc=calculations()
    for q,v,_,_ in b.store.list_questions(scope='bank',include_drafts=True,limit=None):
        src=b.store.source(q.document_id)
        if src.owner_id!='isolated-workbook-audit' or src.sha256!=SHA or src.reuse_confirmed:continue
        m=b.meta(v.version_id);candidate={'directory_topic_id':directory.get((v.source_section,q.source_number)),'core':[],'related':[],'reviewer_kind':'ai_visual','confirmed':False}
        if v.source_section=='1':
            n=int(q.source_number)
            if n<=9:core=['1.1'];method='vector_components';structure='vector_system';reason='Vector components, addition or magnitude required.'
            elif n in [13,14,20,24,25,26,27]:core=['1.3'];method='graph_slope_area';structure='motion_graph';reason='Interpret slope, curvature, area or motion data.'
            elif n<=27:core=['1.2'];method='calculus_kinematics' if n in [11,12,15,16,17] else 'kinematic_equations';structure='particle_motion';reason='Position/velocity/acceleration relations with initial conditions.'
            elif n<=37:core=['1.4'];method='relative_velocity';structure='reference_frame';reason='Transform observed motion between reference frames.'
            else:core=['1.5'];method='projectile_motion';structure='projectile';reason='Resolve planar motion into horizontal and vertical components.'
            if n==43:core=['1.1','1.3'];method='vector_components';structure='motion_graph';reason='Magnitude of acceleration from both component graphs; not projectile motion.'
            if n==44:core=['1.4','1.5'];method='relative_velocity';structure='reference_frame';reason='Relative velocity sets crossing component and travel time.'
            b.validate_tags(b.catalog['course_id'],core,[]);candidate.update(core=core,methods=[method],structures=[structure],reason=reason)
        if m.get('classification_candidate')!=candidate:
            m.setdefault('classification_candidate_history',[]).append({'at':now(),'before':m.get('classification_candidate'),'after':candidate});m['classification_candidate']=candidate;b.save_meta(v.version_id,m)
        tags.append({'question_id':q.question_id,'version_id':v.version_id,'unit':v.source_section,'number':q.source_number,**candidate})
        if v.source_section=='1' and int(q.source_number) in calc:
            label,lhs,rhs,reason=calc[int(q.source_number)]
            if s.simplify(lhs-rhs)!=0:raise ValueError('Symbolic check failed')
            record={'question_id':q.question_id,'version_id':v.version_id,'unit':'1','number':q.source_number,'pages':[p.page for p in v.spans],'candidate':label,'status':'Provisional','calculation':str(lhs),'expected':str(rhs),'reason':reason,'source_sha256':SHA,'reviewer_kind':'ai_visual_with_symbolic_calculation','physical_mapping_requires_independent_review':True}
            old=b.store.latest_answer(v.version_id)
            if not any(e.producer=='workbook-symbolic-candidate/1' for e in b.store.evidence(v.version_id)):
                if old and old.status==AnswerStatus.VERIFIED:raise ValueError('Do not overwrite Verified answers')
                ev=AnswerEvidence(version_id=v.version_id,kind='math_check',producer='workbook-symbolic-candidate/1',details=record)
                b.store.append_answer(v.version_id,label=label,status=AnswerStatus.PROVISIONAL,evidence=[ev],explanation=reason,expected_revision=old.revision if old else 0)
            answers.append(record)
    a.output.mkdir(parents=True,exist_ok=True);(a.output/'answer-candidates.json').write_text(json.dumps(answers,ensure_ascii=False,indent=2));(a.output/'classification-candidates.json').write_text(json.dumps(tags,ensure_ascii=False,indent=2));print(json.dumps({'provisional':len(answers),'verified':0,'classification_candidates':sum(bool(r['core']) for r in tags)}))
if __name__=='__main__':main()
