import test from 'node:test';
import assert from 'node:assert/strict';
import {createTask,editTask,upsertBlocker,editBlocker,routeIntent,planClearMFHistory} from '../src/entities.mjs';
import {createSession,transition,totals} from '../src/session.mjs';
import {recordsSummary,utcCalendar} from '../src/records.mjs';
import {projectLegacyRun,appendMigration} from '../src/legacy.mjs';
const base=Date.UTC(2026,9,20,23,59,58),at=t=>({wall_ms:base+t,mono_ms:t,runtime_id:'owner'});
const start=()=>transition(createSession({session_id:'s'},at(0)),{type:'start'},at(0));
const context={source:'PL',course_id:'ap-physics-c-mechanics-2026-27',unit_id:'2',topic_id:'2.5',return_to:'../index.html#topic/2.5/reading'};
const ref={namespace:'as.modules/1.1',question_id:'question-1',version_id:'v1'};
test('Tasks only require title; manual single level, edits and reopen',()=>{
  const a=createTask({task_id:'a',title:'力学练习'}), b=createTask({task_id:'b',title:'第1题',parent_id:'a'},[a]);
  assert.equal(a.context.course_id,null);assert.equal(a.estimated_ms,null);
  assert.throws(()=>createTask({task_id:'c',title:'嵌套',parent_id:'b'},[a,b]),/one subtask/);
  assert.equal(editTask(editTask(a,{completed:true}),{completed:false}).completed,false);
  assert.equal(editTask(a,{title:'新任务',important:true,estimated_ms:60000}).title,'新任务');
  assert.throws(()=>editTask(a,{deadline:'tomorrow'}));
});
test('T09/T10 blockers survive session end and never change timer or auto-resolve',()=>{
  let s=start();const original=JSON.stringify(s);
  const b=upsertBlocker([],{blocker_id:'b',title:'符号不懂',session_id:s.session_id,context}).blocker;
  assert.equal(JSON.stringify(s),original);s=transition(s,{type:'end'},at(5000));assert.equal(totals(s).focus_ms,5000);
  assert.equal(b.resolved,false);assert.equal(editBlocker(editBlocker(b,{resolved:true}),{resolved:false}).resolved,false);
});
test('T14/T15 PL context retained; route intent is data only, not forced navigation',()=>{
  const s=createSession({session_id:'s',context},at(0));assert.deepEqual(s.context,{...context,exercise_id:null});
  const b=upsertBlocker([],{blocker_id:'b',title:'问题',context:s.context}).blocker;
  assert.equal(routeIntent(b,'PL').topic_id,'2.5');assert.equal(routeIntent(b,'PL').return_to,context.return_to);
  assert.throws(()=>routeIntent(b,'AS'),/No confirmed/);
});
test('T16 AS dedupe uses namespace + stable question ID without copying question/answer',()=>{
  let b=upsertBlocker([],{blocker_id:'b',title:'问题',question_ref:ref,session_id:'s1',answer:'secret'}).blocker;
  b=editBlocker(b,{notes:'原始笔记',resolved:true});
  const again=upsertBlocker([b],{blocker_id:'b2',title:'new',question_ref:{...ref,version_id:'v2'},session_id:'s2'});
  assert.equal(again.created,false);assert.equal(again.blocker.blocker_id,'b');assert.equal(again.blocker.notes,'原始笔记');
  assert.equal(again.blocker.resolved,true);assert.deepEqual(again.blocker.session_ids,['s1','s2']);
  assert.deepEqual(again.blocker.seen_version_ids,['v1','v2']);assert.equal(again.blocker.question_ref.version_id,'v1');
  assert.equal('answer' in again.blocker,false);assert.equal(again.blocker.context.exercise_id,null);
  assert.equal(upsertBlocker([b],{blocker_id:'x',title:'问题',question_ref:{...ref,namespace:'other'}}).created,true);
  assert.equal(routeIntent(b,'AS').question_id,'question-1');
});
test('T18 latest session revision only; midnight splits; weekly sum is requested days',()=>{
  const earlier=transition(start(),{type:'tick'},at(1000)), latest=transition(earlier,{type:'end'},at(5000));
  const summary=recordsSummary([earlier,latest,latest],['2026-10-20','2026-10-21']);
  assert.equal(summary.session_count,1);assert.equal(summary.focus_ms,5000);
  assert.equal(summary.days['2026-10-20'].focus_ms,2000);assert.equal(summary.days['2026-10-21'].focus_ms,3000);
  assert.equal(summary.selected_days_focus_ms,5000);
  assert.throws(()=>recordsSummary([latest,{...latest,task_id:'conflict'}],[]),/Conflicting/);
});
test('calendar injection supports Shanghai day boundary and does not assume host timezone',()=>{
  const offset=8*3600000, calendar={dayKey:ms=>utcCalendar.dayKey(ms+offset),nextDayStart:ms=>utcCalendar.nextDayStart(ms+offset)-offset};
  const s=transition(start(),{type:'end'},at(5000)),summary=recordsSummary([s],['2026-10-21'],calendar);
  assert.equal(summary.days['2026-10-21'].focus_ms,5000);
});
test('T19 observed legacy run projection preserves raw, tasks, blockers, and idempotency',()=>{
  const raw=JSON.stringify({goal:'物理',mode:'free',elapsed:10000,steps:[{id:1,title:'第一题',status:'done',smallDone:['检查']},{id:2,title:'第二题',status:'skipped',micro:'读题',smallDone:[]}],notes:[{taskId:2,title:'第二题',text:'没懂'}],custom:'preserve me'});
  const p=projectLegacyRun(raw,'mindflow.session.v1:export1');assert.equal(p.raw_json,raw);assert.equal(p.tasks.length,3);
  assert.equal(p.tasks[1].completed,true);assert.equal(p.tasks[2].completed,false);assert.equal(p.blockers[0].title,'没懂');
  assert.equal(p.legacy_session.trusted_v3_focus_ms,null);assert.equal(p.legacy_session.legacy_elapsed_ms,10000);
  assert.equal(appendMigration(appendMigration([],p),p).length,1);
  assert.throws(()=>appendMigration([p],{...p,raw_json:'changed'}),/Source changed/);
});
test('Review & Repair and unknown legacy shapes remain preserved, not misconverted',()=>{
  const raw=JSON.stringify({stage:'recall',response:'initial answer',attempts:[{response:'changed'}]});
  const p=projectLegacyRun(raw,'review-export');assert.equal(p.status,'UNSUPPORTED_PRESERVED');assert.equal(p.raw_json,raw);
});
test('T20 deletion requires two confirmations and only targets ended MF sessions',()=>{
  const ended=transition(start(),{type:'end'},at(5000)), active={...start(),session_id:'active'};
  const blocker=upsertBlocker([],{blocker_id:'b',title:'问题',session_id:'s'}).blocker;
  const source={sessions:[ended,active,{schema:'AS',session_id:'exam',state:'Ended'}],blockers:[blocker],ledger:[{id:'PL'}]};
  const before=JSON.stringify(source);assert.throws(()=>planClearMFHistory(source,{confirmed:true,confirmedAgain:false}));
  const p=planClearMFHistory(source,{confirmed:true,confirmedAgain:true});assert.deepEqual(p.delete_session_ids,['s']);
  assert.deepEqual(p.blockers[0].removed_session_ids,['s']);assert.equal(p.preserve_tasks,true);assert.equal(JSON.stringify(source),before);
  assert.equal('ledger' in p,false);
});
