const assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),crypto=require('node:crypto');
const root=path.resolve(__dirname,'..');
const F=require('../fusion-core.js'),B=require('../mind-flow/pathline-bridge.js'),MF=require('../mind-flow/app.js');
const read=name=>JSON.parse(fs.readFileSync(path.join(root,'data',name),'utf8'));
const context={window:{},Date,console};vm.createContext(context);vm.runInContext(fs.readFileSync(path.join(root,'pathline-core.js'),'utf8'),context);
const E=context.window.PathlineEngine;
class FixedDate extends Date{static now(){return 1791300000000;}}
const before={window:{},Date:FixedDate},after={window:{},Date:FixedDate};vm.createContext(before);vm.createContext(after);vm.runInContext(fs.readFileSync(path.join(__dirname,'original-priority-engine.js'),'utf8'),before);vm.runInContext(fs.readFileSync(path.join(root,'pathline-core.js'),'utf8'),after);
const generic={units:[{topics:[{id:'a',prereq:[]},{id:'b',prereq:['a']},{id:'c',prereq:['a','b']}]}]};
for(const mastery of [22,55,90])for(const attempts of [0,1,4]){const states=Object.fromEntries(['a','b','c'].map((id,i)=>[id,{...E.initialTopicState(),mastery:mastery-i*5,attempts,confidence:.35+i*.2,lastStudied:attempts?FixedDate.now()-3*86400000:null,intervalDays:1,dueAt:attempts?FixedDate.now()-86400000:null}]));for(const topic of generic.units[0].topics)assert.deepEqual(JSON.parse(JSON.stringify(after.window.PathlineEngine.priority(topic,states[topic.id],states,'2027-05-01',generic))),JSON.parse(JSON.stringify(before.window.PathlineEngine.priority(topic,states[topic.id],states,'2027-05-01',generic))));}
const data={course:read('course.json')},course=F.makeCourse(data),progress=E.ensureCourseProgress(course),store=F.emptyEvidence();
assert.equal(course.units.length,7);assert.equal(course.units.flatMap(u=>u.topics).length,41);
assert.deepEqual(course.units.flatMap(u=>u.topics).map(t=>t.id),data.course.topics.map(t=>t.topic_id));
assert.equal(F.availableRanked(E,course,progress,'').length,41);
assert.ok(data.course.topics.every(t=>t.status==='validated'));
const mastery=progress['2.5'].mastery;
F.recordExposure(store,progress,{event_id:'reading-1',course_id:course.id,topic_id:'2.5',action:'reading_completed'});
assert.equal(progress['2.5'].mastery,mastery);assert.ok(progress['2.5'].dueAt>Date.now());
assert.equal(F.recordExposure(store,progress,{event_id:'reading-1',topic_id:'2.5'}),false);
const ctx={session_id:'real-mf-check',course_id:course.id,topic_id:'2.5',started_at:new Date(Date.now()-2000).toISOString()};
const run=MF.createRun('Newton',['闭卷回忆','应用','修正'],'free',25);
run.pathlineContext=ctx;run.attempt_log=[{step_id:1,response:'合力等于质量乘加速度',self_reported_success:false,retry:false},{step_id:1,response:'ΣF = ma，沿所选坐标分解',self_reported_success:true,retry:true}];run.hint_usage=1;run.repair_steps=[{kind:'hint',text:'先写一个有用的关系'}];
MF.completeStep(run);MF.completeStep(run);MF.completeStep(run);run.date=new Date().toISOString();
const evidence=B.evidence(run);assert.equal(evidence.completion,true);assert.equal(evidence.retrieval_attempts,2);assert.equal(evidence.retry_count,1);
assert.equal(F.acceptLearning(store,progress,evidence,ctx),true);assert.equal(F.acceptLearning(store,progress,evidence,ctx),false);
assert.equal(progress['2.5'].mastery,mastery);assert.equal(progress['2.5'].attempts,0);assert.equal(progress['2.5'].confidence,.5);
assert.equal(progress['2.5'].intervalDays,.35);assert.ok(progress['2.5'].lastEvidenceReason.includes('提示或修正'));
assert.notEqual(F.availableRanked(E,course,progress,'')[0].topic.id,'2.5');
const future={...evidence,completed_at:new Date(Date.now()+3600000).toISOString()};
assert.throws(()=>F.validateLearning(future,ctx));assert.throws(()=>F.validateLearning({...evidence,successful_retrievals:3},ctx));assert.throws(()=>F.validateLearning({...evidence,course_id:'other'},ctx));assert.throws(()=>F.validateLearning({...evidence,retry_count:-1},ctx));assert.throws(()=>F.validateLearning({...evidence,attempt_log:[]},ctx));
const priorDue=progress['2.5'].dueAt,emptyCtx={...ctx,session_id:'completion-only'},emptyRun=MF.createRun('empty',['done'],'free',25);emptyRun.pathlineContext=emptyCtx;emptyRun.steps[0].status='done';emptyRun.date=new Date().toISOString();
assert.equal(F.acceptLearning(store,progress,B.evidence(emptyRun),emptyCtx),true);assert.equal(progress['2.5'].mastery,mastery);assert.equal(progress['2.5'].dueAt,priorDue);
progress['2.5'].dueAt=Date.now()-100;assert.equal(E.dueTopics(course,progress)[0].topic.id,'2.5');assert.ok(E.priority(course.units[1].topics[4],progress['2.5'],progress,'',course).reasons.includes('review due'));
assert.equal(store.assessment.length,0);
assert.equal(F.targetScore(course,''),'5');assert.equal(F.targetScore(course,'6'),'5');assert.equal(F.targetScore(course,'2'),'2');
assert.equal(F.targetScore({title:'AP Statistics',targetDefault:'A'},'A'),'5');assert.equal(F.targetScore({title:'My Course',targetDefault:'A'},'90%'),'90%');
assert.equal(F.weightedReadiness(E,course,E.ensureCourseProgress(course),F.emptyEvidence()).score,null);
const weightedCourse={id:'weighted',units:[{weight:'30%',topics:[{id:'a'}]},{weight:'60%',topics:[{id:'b'}]}]},weightedProgress={a:{mastery:80,attempts:1},b:{mastery:22,attempts:0}};
assert.equal(F.weightedReadiness(E,weightedCourse,weightedProgress,F.emptyEvidence()).score,32);
const toggles=F.emptyEvidence(),tp=E.ensureCourseProgress(course),attemptEvent={event_id:'toggle',course_id:course.id,topic_id:'2.5',exercise_id:'exercise-one'};
const baseTime=Date.now()-100000;
assert.equal(F.toggleExercise(toggles,tp,attemptEvent,baseTime),true);assert.equal(F.exerciseRecorded(toggles,course.id,'2.5','exercise-one'),true);
assert.equal(F.toggleExercise(toggles,tp,attemptEvent),false);assert.equal(toggles.exposure.length,0);assert.equal(tp['2.5'].dueAt,null);assert.equal(tp['2.5'].mastery,22);
F.recordExposure(toggles,tp,{...attemptEvent,event_id:'keep-reading',action:'reading_completed'},baseTime);
F.acceptLearning(toggles,tp,evidence,ctx);const repairDue=tp['2.5'].dueAt;
F.toggleExercise(toggles,tp,attemptEvent,Date.now());F.toggleExercise(toggles,tp,attemptEvent);
assert.equal(tp['2.5'].dueAt,repairDue);assert.equal(tp['2.5'].intervalDays,.35);assert.equal(toggles.learning_repair.length,1);assert.equal(tp['2.5'].mastery,22);
console.log('PASS: AP 1–5 targets, original weighted readiness without default mastery, exercise toggle and cancellation preserves MF/reading evidence.');
assert.equal(B.contextFromHash('#pathline='+encodeURIComponent(JSON.stringify({...ctx,title:'Newton',goals:[]}))).topic_id,'2.5');assert.equal(B.contextFromHash('#pathline=bad'),null);
const contentBaseline=JSON.parse(fs.readFileSync(path.join(__dirname,'content-baseline.json'),'utf8'));
const protectedFiles={...contentBaseline.protected,...contentBaseline.assets};
// Only integration modules intentionally changed by MF V1 are exempt from the old UI byte hashes.
const changedIntegration=new Set(['app.js','fusion-core.js','fusion.css','ui-text.js','review-contract.js','mind-flow/app.js','mind-flow/index.html']);
for(const [name,hash] of Object.entries(protectedFiles))if(!changedIntegration.has(name))assert.equal(crypto.createHash('sha256').update(fs.readFileSync(path.join(root,name))).digest('hex'),hash,`Textbook file changed: ${name}`);
const baselineMF=require('node:child_process').execFileSync('git',['-c','safe.directory='+root.replaceAll('\\','/'),'show','5ae27ba:mind-flow/app.js'],{cwd:root,encoding:'utf8'});const coreText=value=>value.replaceAll('\r','').split('  const $ =')[0].replace('(async () => {','(() => {');assert.equal(coreText(fs.readFileSync(path.join(root,'mind-flow/app.js'),'utf8')),coreText(baselineMF),'Original MF task core changed');
const contentContext={window:{PathlineTextbook:{course:read('course.json'),readings:read('reading-content.json'),exercises:read('exercises.json'),assets:read('assets.json'),supplements:read('supplements.json'),reviews:read('chapter-reviews.json'),objects:read('reading-objects.json'),figures:read('figures.json')},PathlineFusion:F}};
vm.createContext(contentContext);vm.runInContext(fs.readFileSync(path.join(root,'topic-content.js'),'utf8'),contentContext);
for(const id of ['2.5','5.4','7.5']){const html=contentContext.window.PathlineContent.topic(id);for(const expected of ['learning-goals','textbook-reading','exercises','source-info','Example','Figure','Check Your Understanding'])assert.ok(html.includes(expected),`${id}: ${expected}`);const topic=data.course.topics.find(t=>t.topic_id===id);for(const ref of topic.exercise_refs)assert.ok(html.includes(`data-exercise-id="${ref}"`));}
for(const t of data.course.topics){const html=contentContext.window.PathlineContent.topic(t.topic_id);assert.ok(!html.includes('正式内容待完成'));assert.ok(html.includes('page-region'));assert.ok(html.includes('source-info'));for(const ref of t.exercise_refs)assert.ok(html.includes(`data-exercise-id="${ref}"`));}
const engineText=fs.readFileSync(path.join(root,'pathline-core.js'),'utf8');assert.ok(engineText.includes('.36*weakness+.20*forget+.12*leverage+.08*confidenceGap+.12*overdue+.07*pressure-blockPenalty'));
console.log('PASS: 7/41 frozen map, all 41 content renderers, three baseline Topics and protected UI/source, MF evidence validation/idempotency, completion ≠ mastery, review/priority recomputation, unchanged priority weights.');
async function checkTextImport(){const parser=context.window.PathlineParsers;await assert.rejects(parser.parseFile({name:'empty.txt',size:0}),/empty/);await assert.rejects(parser.parseFile({name:'large.txt',size:31*1024*1024}),/30 MB/);const result=await parser.parseFile({name:'course.txt',size:12,text:async()=> 'Unit One\nTopic One\nA real imported paragraph explaining a concrete topic in enough detail to study.'});assert.ok(result.text.includes('real imported'));const custom=parser.buildCustomCourse('A local course',result.text);assert.equal(custom.title,'A local course');assert.ok(custom.units[0].topics.length);console.log('PASS: original text import, custom course construction, empty/oversized file guards.');}
checkTextImport().catch(error=>{console.error(error);process.exitCode=1;});
