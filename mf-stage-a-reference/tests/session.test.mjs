import test from 'node:test';
import assert from 'node:assert/strict';
import {createSession,transition,totals,timerView,validateSession} from '../src/session.mjs';
import {SessionCoordinator} from '../src/coordinator.mjs';
import {AtomicTestPort} from './atomic-port.mjs';
import {writeFileSync,readFileSync,mkdtempSync,rmSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {spawnSync} from 'node:child_process';
const base=Date.UTC(2026,9,21), at=(t,r='owner')=>({wall_ms:base+t,mono_ms:t,runtime_id:r});
const ready=(options={})=>createSession({session_id:'s1',...options},at(0));
const start=(options={})=>transition(ready(options),{type:'start'},at(0));
const step=(s,t,type,extra={})=>transition(s,{type,...extra},at(t));

test('T01/T08 free start with no task; no fake percentage',()=>{
  const s=step(start(),7000,'tick');assert.equal(totals(s).focus_ms,7000);
  assert.equal(s.task_id,null);assert.equal(timerView(s).progress,null);
});
test('T02 pomodoro defaults and configurable durations',()=>{
  const s=start({mode:'pomodoro'});assert.equal(s.focus_ms,1500000);assert.equal(s.rest_ms,300000);
  assert.equal(timerView(start({mode:'pomodoro',focus_ms:1000})).remaining_ms,1000);
});
test('T03 pause excludes all elapsed paused time; phase continues on resume',()=>{
  let s=step(start(),4000,'pause');s=step(s,100000,'tick');assert.equal(totals(s).focus_ms,4000);
  s=step(s,100000,'resume');s=step(s,103000,'tick');assert.equal(totals(s).focus_ms,7000);assert.equal(s.phase,1);
});
test('T04 rest separately counted and not attributed to task',()=>{
  let s=step(start({task_id:'A'}),3000,'rest');s=step(s,7000,'resume');s=step(s,8000,'end');
  assert.equal(totals(s).focus_ms,4000);assert.equal(totals(s).rest_ms,4000);assert.equal(totals(s).tasks.A,4000);
  assert.equal(s.phase,3);
});
test('T05 focus expiry is nonblocking, one notice, overtime counted',()=>{
  let s=step(start({mode:'pomodoro',focus_ms:5000}),7000,'tick');s=step(s,9000,'tick');
  assert.equal(s.state,'Focusing');assert.equal(s.notices.length,1);assert.equal(totals(s).focus_ms,9000);
  assert.equal(timerView(s).overtime_ms,4000);
});
test('T06 rest expiry never starts focus',()=>{
  let s=step(start({rest_ms:2000}),1000,'rest');s=step(s,5000,'tick');s=step(s,6000,'tick');
  assert.equal(s.state,'Resting');assert.equal(s.notices.length,1);assert.equal(totals(s).focus_ms,1000);assert.equal(totals(s).rest_ms,5000);
});
test('T07 switch closes task allocation with no overlap',()=>{
  let s=step(start({task_id:'A'}),4000,'switch_task',{task_id:'B'});s=step(s,7000,'switch_task',{task_id:null});s=step(s,9000,'end');
  assert.deepEqual({...totals(s).tasks},{A:4000,B:3000});assert.equal(totals(s).focus_ms,9000);
  assert.equal(s.segments.length,3);
});
test('T11 refresh recovery preserves confirmed time and original identity',()=>{
  let s=step(start(),5000,'tick');s=transition(JSON.parse(JSON.stringify(s)),{type:'recover'},at(900000,'new'));
  assert.equal(s.session_id,'s1');assert.equal(s.state,'Paused');assert.equal(totals(s).focus_ms,5000);
  s=transition(JSON.parse(JSON.stringify(s)),{type:'recover'},at(1900000,'third'));
  assert.equal(totals(s).focus_ms,5000);assert.equal(s.state,'Paused');
});
test('T12 serialized checkpoint survives a separate process; offline gap excluded (not browser test)',()=>{
  const dir=mkdtempSync(join(tmpdir(),'mf-v3-'));
  try {
    const path=join(dir,'snapshot.json');writeFileSync(path,JSON.stringify(step(start(),4000,'tick')));
    const moduleUrl=new URL('../src/session.mjs',import.meta.url).href;
    const code=`import fs from 'node:fs';import {transition} from ${JSON.stringify(moduleUrl)};const p=process.argv[1];const s=transition(JSON.parse(fs.readFileSync(p)),{type:'recover'},${JSON.stringify(at(86400000,'new-process'))});fs.writeFileSync(p,JSON.stringify(s));`;
    const r=spawnSync(process.execPath,['--input-type=module','-e',code,path],{encoding:'utf8'});assert.equal(r.status,0,r.stderr);
    const s=JSON.parse(readFileSync(path));assert.equal(s.state,'Paused');assert.equal(totals(s).focus_ms,4000);
  } finally {rmSync(dir,{recursive:true,force:true});}
});
test('uncertain scheduler gap, wall rollback and wall/monotonic divergence fail closed',()=>{
  for(const stamp of [at(60000),{...at(2000),wall_ms:base-10},{...at(4000),mono_ms:1000}]) {
    const s=transition(step(start(),1000,'tick'),{type:'tick'},stamp);
    assert.equal(s.state,'Paused');assert.equal(totals(s).focus_ms,1000);
  }
});
test('old writer heartbeat is ignored; explicit foreign control pauses without unknown credit',()=>{
  const s=step(start(),3000,'tick');assert.deepEqual(transition(s,{type:'tick'},at(7000,'follower')),s);
  const p=transition(s,{type:'pause'},at(7000,'follower'));assert.equal(totals(p).focus_ms,3000);assert.equal(p.state,'Paused');
});
test('ended time is frozen; stale controls cannot reopen it',()=>{
  const s=step(start(),1000,'end');assert.deepEqual(step(s,900000,'tick'),s);assert.deepEqual(step(s,900000,'end'),s);
  assert.throws(()=>step(s,900000,'resume'),/ended/);
});
test('duplicate start never resets or silently resumes',()=>{
  let s=step(start(),1000,'start');assert.equal(totals(s).focus_ms,1000);
  s=step(s,2000,'pause');s=step(s,5000,'start');assert.equal(s.state,'Paused');assert.equal(totals(s).focus_ms,2000);
});
test('invalid transitions/NaN/unknown schema rejected without mutating input',()=>{
  const r=ready(), snapshot=JSON.stringify(r);assert.throws(()=>step(r,0,'rest'));assert.throws(()=>step(r,0,'resume'));
  assert.throws(()=>transition(r,{type:'start'},at(NaN)));assert.throws(()=>validateSession({...r,schema:'future'}));
  assert.throws(()=>ready({focus_ms:Infinity}));assert.equal(JSON.stringify(r),snapshot);
});
test('clock rollback cannot overlap history after resume',()=>{
  let s=step(start(),5000,'pause');s=step(s,4000,'resume');assert.equal(s.state,'Paused');
  s=step(s,6000,'resume');s=step(s,7000,'tick');assert.equal(totals(s).focus_ms,6000);
});
test('T13 100 concurrent starts from simulated tabs create one session',async()=>{
  const port=new AtomicTestPort(), tabs=Array.from({length:100},()=>new SessionCoordinator(port,'user'));
  const all=await Promise.all(tabs.map((c,i)=>c.start({session_id:'s'+i},at(0,'tab'+i))));
  assert.equal(new Set(all.map(r=>r.current.session_id)).size,1);assert.equal(port.archives.size,0);
});
test('revision conflict prevents double credit and stale overwrite',async()=>{
  const port=new AtomicTestPort(), c=new SessionCoordinator(port,'user');const row=await c.start({session_id:'s'},at(0));
  const outcomes=await Promise.allSettled(Array.from({length:50},()=>c.dispatch('s',row.current.revision,{type:'tick'},at(1000))));
  assert.equal(outcomes.filter(o=>o.status==='fulfilled').length,1);assert.equal(totals((await c.read()).current).focus_ms,1000);
});
test('durable commit failure rolls back and does not report success',async()=>{
  const port=new AtomicTestPort(), c=new SessionCoordinator(port,'user');const r=await c.start({session_id:'s'},at(0));
  port.failNext=true;await assert.rejects(c.dispatch('s',r.current.revision,{type:'tick'},at(5000)),/commit failure/);
  assert.deepEqual(await c.read(),r);
  const retried=await c.dispatch('s',r.current.revision,{type:'tick'},at(15000));assert.equal(retried.current.state,'Paused');assert.equal(totals(retried.current).focus_ms,0);
});
test('T17 formal exam pauses and prevents restart until every exam lock is released',async()=>{
  const c=new SessionCoordinator(new AtomicTestPort(),'user');await c.start({session_id:'s'},at(0));
  let r=await c.examStart('exam1',at(3000));await c.examStart('exam2',at(4000));r=await c.examEnd('exam1');
  assert.equal(r.current.state,'Paused');await assert.rejects(c.dispatch('s',r.current.revision,{type:'resume'},at(5000)),/exam/);
  r=await c.examEnd('exam2');assert.equal(r.current.state,'Paused');assert.equal(totals(r.current).focus_ms,3000);
  r=await c.dispatch('s',r.current.revision,{type:'resume'},at(3600000));assert.equal(totals(r.current).focus_ms,3000);
});
test('formal exam can lock before any MF session exists',async()=>{
  const c=new SessionCoordinator(new AtomicTestPort(),'user');await c.examStart('e',at(0));
  await assert.rejects(c.start({session_id:'s'},at(1000)),/exam/);
  await c.examEnd('e');assert.equal((await c.start({session_id:'s'},at(2000))).current.state,'Focusing');
});
test('T25 shared engine snapshots agree across simulated views',async()=>{
  const p=new AtomicTestPort(), a=new SessionCoordinator(p,'user'),b=new SessionCoordinator(p,'user');
  let r=await a.start({session_id:'s'},at(0));r=await b.dispatch('s',r.current.revision,{type:'rest'},at(2000));
  assert.deepEqual(timerView((await a.read()).current),timerView((await b.read()).current));
});
test('ended session archived before next; stale commands and ID reuse rejected',async()=>{
  const p=new AtomicTestPort(),c=new SessionCoordinator(p,'u');let r=await c.start({session_id:'a'},at(0));
  await c.dispatch('a',r.current.revision,{type:'end'},at(1000));r=await c.start({session_id:'b'},at(2000));
  assert.equal(p.archives.size,1);await assert.rejects(c.dispatch('a',r.current.revision,{type:'pause'},at(3000)),/identity/);
  await c.dispatch('b',r.current.revision,{type:'end'},at(3000));await assert.rejects(c.start({session_id:'a'},at(4000)),/reused/);
  await assert.rejects(c.start({session_id:'b'},at(4000)),/reused/);
});
test('persisted corrupt anchors, phases and notices are rejected',()=>{
  const s=step(start(),4000,'tick');
  assert.throws(()=>validateSession({...s,anchor:at(2000)}),/Anchor/);
  assert.throws(()=>validateSession({...s,phase_kind:'rest'}),/mismatch/);
  assert.throws(()=>validateSession({...s,notices:[{id:'bad',kind:'fake',phase:1}]}),/notice/);
});
test('independent scopes cannot overwrite one another',async()=>{
  const p=new AtomicTestPort(),a=new SessionCoordinator(p,'u1'),b=new SessionCoordinator(p,'u2');
  await a.start({session_id:'a'},at(0));await b.start({session_id:'b'},at(0));assert.equal((await a.read()).current.session_id,'a');
});
test('model-based random actions preserve time allocation and non-overlap',()=>{
  let seed=719, now=0,s=start(), focus=0,rest=0,state='Focusing';
  const rnd=()=>{seed=(Math.imul(seed,1664525)+1013904223)>>>0;return seed;};
  for(let i=0;i<1500;i++) {
    const delta=rnd()%3000;now+=delta;
    if(state==='Focusing')focus+=delta;if(state==='Resting')rest+=delta;
    const pick=rnd()%4;
    const type=state==='Paused'?(pick===0?'resume':'tick'):state==='Resting'?(pick===0?'resume':'tick'):pick===0?'pause':pick===1?'rest':pick===2?'switch_task':'tick';
    s=step(s,now,type,type==='switch_task'?{task_id:rnd()%2?'A':'B'}:{});state=s.state;
    assert.equal(totals(s).focus_ms,focus);assert.equal(totals(s).rest_ms,rest);
    assert.ok(Object.values(totals(s).tasks).reduce((a,b)=>a+b,0)<=focus);validateSession(s);
  }
});
