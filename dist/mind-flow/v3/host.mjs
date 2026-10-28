import {SessionCoordinator} from './core/coordinator.mjs';
import {transition,totals,requireId} from './core/session.mjs';
import {projectLegacyRun} from './core/legacy.mjs';
export const KEY='mf-v3';
// Limit the visible list without changing historical totals or shared learning evidence.
export function recentSessions(sessions){return sessions.slice().reverse().sort((a,b)=>b.created_at-a.created_at).slice(0,5);}
export const calendar={dayKey(ms){const d=new Date(ms);return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;},nextDayStart(ms){const d=new Date(ms);return +new Date(d.getFullYear(),d.getMonth(),d.getDate()+1);}};
export const empty=()=>({version:1,current:null,exam_ids:[],history:[],tasks:[],blockers:[],migrations:[],hidden_ids:[]});
export function studyProjection(s){
 const daily_seconds={};for(const p of s.segments.filter(p=>p.kind==='focus')){let cursor=p.start_ms;while(cursor<p.end_ms){const end=Math.min(p.end_ms,calendar.nextDayStart(cursor)),key=calendar.dayKey(cursor);daily_seconds[key]=(daily_seconds[key]||0)+p.duration_ms*(end-cursor)/(p.end_ms-p.start_ms)/1000;cursor=end;}}
 const t=totals(s);return {session_id:s.session_id,...s.context,source:'MF',mode:'focus',started_at:new Date(s.created_at).toISOString(),ended_at:new Date(s.ended_at??s.created_at).toISOString(),active_seconds:t.focus_ms/1000,rest_seconds:t.rest_ms/1000,daily_seconds};
}
export function prepareCommit(previous,next){
 const before=previous||empty();next={...empty(),...next};
 if(before.current&&before.current.session_id!==next.current?.session_id){if(before.current.state!=='Ended')throw Error('Cannot replace active session');if(!next.history.some(s=>s.session_id===before.current.session_id))next.history.push(before.current);if(next.history.some(s=>s.session_id===next.current?.session_id))throw Error('Archived session ID reused');}
 const result={value:next,sessions:[],events:[]};
 next.ledger_ids=next.ledger_ids||[];
 for(const ended of [...next.history,...(next.current?[next.current]:[])].filter(s=>s.state==='Ended'&&!next.ledger_ids.includes(s.session_id))){
 const s=studyProjection(ended);result.sessions.push(s);result.events.push({schema_version:3,event_id:s.session_id,session_id:s.session_id,course_id:s.course_id,unit_id:s.unit_id,topic_id:s.topic_id,exercise_id:null,source:'MF',type:'MF_SESSION_COMPLETED',occurred_at:s.ended_at,payload:{mode:'focus',active_seconds:s.active_seconds,rest_seconds:s.rest_seconds,timer_mode:ended.mode}});next.ledger_ids.push(s.session_id);}
 return result;
}
export function makePort(store){return {read:async scope=>(await store.getModule(scope))||empty(),transact:(scope,reducer)=>store.atomicModule(scope,prior=>prepareCommit(prior,reducer(structuredClone(prior||empty()))))};}
export async function migrateLegacy(store){
 const raw=await store.getModule('mf-focus')||{};for(const k of ['mindflow.session.v1','mindflow.history.v1'])if(raw[k]===undefined){try{raw[k]=JSON.parse(localStorage.getItem(k)||'null');}catch{}}
 const review=await store.getModule('mf-review');
 return store.atomicModule(KEY,prior=>{if(prior?.legacy_backup)return {value:prior};const row={...empty(),...prior,legacy_backup:{focus:raw,review:review||null,created_at:new Date().toISOString()}};
 const records=[...(Array.isArray(raw['mindflow.history.v1'])?raw['mindflow.history.v1']:[]),...(raw['mindflow.session.v1']?[raw['mindflow.session.v1']]:[])];
 records.forEach((r,i)=>{try{const p=projectLegacyRun(JSON.stringify(r),'fusion-v2-export:'+i);row.migrations.push(p);row.tasks.push(...p.tasks);row.blockers.push(...p.blockers);}catch(e){row.migrations.push({migration_id:'raw:'+i,raw_json:JSON.stringify(r),status:'UNSUPPORTED_PRESERVED',reason:e.message});}});
 return {value:row};});
}
export function createHost(store,{runtime_id,tab_id,stamp,onChange=()=>{}}){
 const port=makePort(store),coordinator=new SessionCoordinator(port,KEY);let row=empty();
 async function refresh(){row=await port.read(KEY);onChange(row);return row;}
 async function mutate(reducer){row=await port.transact(KEY,reducer);onChange(row);return row;}
 async function command(type,extra={}){return mutate(r=>{if(!r.current)return r;if(r.exam_ids.length&&['start','resume','rest'].includes(type))throw Error('考试进行中，请先结束考试。');r.current=transition(r.current,{type,...extra},stamp());if(r.current.anchor?.runtime_id===runtime_id)r.owner_tab=tab_id;return r;});}
 async function start(options={}){row=await coordinator.start({session_id:crypto.randomUUID(),...options},stamp());if(row.current.anchor?.runtime_id===runtime_id)await mutate(r=>{if(r.current.anchor?.runtime_id===runtime_id)r.owner_tab=tab_id;return r;});onChange(row);return row;}
 async function recover(force=false){return mutate(r=>{const s=r.current;if(s?.anchor&&(force&&r.owner_tab===tab_id||Date.now()-s.anchor.wall_ms>10000)){r.current=transition(s,{type:'recover'},stamp());}return r;});}
 async function heartbeat(){await refresh();if(row.current?.anchor?.runtime_id===runtime_id)return command('tick');if(row.current?.anchor&&Date.now()-row.current.anchor.wall_ms>10000)return recover();return row;}
 return {get row(){return row;},coordinator,refresh,mutate,command,start,recover,heartbeat};
}

export function associateBlockerTask(blocker,task_id){const out=structuredClone(blocker);if(task_id!=null){requireId(task_id);out.task_ids=[...new Set([...(out.task_ids||[]),task_id])];}return out;}
