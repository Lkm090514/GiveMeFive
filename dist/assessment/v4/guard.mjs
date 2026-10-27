// One shared MF exam lock across Fusion tabs; backend owns the authoritative deadline.
import {request,ensureIdentity} from './api.mjs?v=4.1-auth2';
import {transition} from '../../mind-flow/v3/core/session.mjs';
import {empty} from '../../mind-flow/v3/host.mjs';
const KEY='mf-v3',channel=typeof BroadcastChannel!=='undefined'?new BroadcastChannel('gmf-mf-v3'):null;
let polling=false,known=null,pendingUntil=0,authRetryAt=0;
export async function setExamLock(id){
 await LearningStore.open();if(id?.startsWith('pending:'))pendingUntil=Date.now()+10000;else pendingUntil=0;const value=id?'v4:'+id:null;
 await LearningStore.atomicModule(KEY,previous=>{
  const row={...empty(),...previous},prior=row.exam_ids||[],other=prior.filter(x=>!x.startsWith('v4:'));
  if(value&&!prior.includes(value)&&row.current){const anchor=row.current.anchor;row.current=transition(row.current,{type:'exam_start'},{wall_ms:Date.now(),mono_ms:anchor?.mono_ms??performance.now(),runtime_id:anchor?.runtime_id||'as-v4-guard'});}
  row.exam_ids=value?[...other,value]:other;return {value:row};
 });
 document.documentElement.classList.toggle('gmf-exam-active',!!id);known=id;
 if(id){let notice=document.getElementById('gmf-exam-guard');if(!notice&&!location.pathname.includes('/assessment/')){notice=document.createElement('div');notice.id='gmf-exam-guard';notice.className='gmf-exam-guard';document.body.prepend(notice);}if(notice){notice.replaceChildren(document.createTextNode('正式考试进行中，心流已暂停。 '));const a=document.createElement('a');a.href='/assessment/#session/'+encodeURIComponent(id);a.textContent='返回考试';notice.append(a);}}
 else document.getElementById('gmf-exam-guard')?.remove();
 channel?.postMessage('changed');document.dispatchEvent(new CustomEvent('gmf-exam-lock',{detail:{id}}));
}
export async function reconcile(){if(polling||Date.now()<authRetryAt)return;polling=true;try{await ensureIdentity();const data=await request('/sessions');if(data.exam_lock||Date.now()>pendingUntil)await setExamLock(data.exam_lock);return data;}catch(e){LearningStore.setIdentity?.(null);authRetryAt=Date.now()+30000;if(e.status!==401){document.dispatchEvent(new CustomEvent('gmf-api-warning',{detail:e.message}));}return null;}finally{polling=false;}}
function backLink(){const value=new URLSearchParams(location.search).get('return_to');if(!value||document.getElementById('as-return-link')||location.pathname.includes('/assessment/'))return;try{const u=new URL(value,location.href);if(u.origin!==location.origin||!u.pathname.includes('/assessment/'))return;const a=document.createElement('a');a.id='as-return-link';a.className='as-return-link';a.href=u.href;a.textContent='← 返回原练习';document.querySelector('.gmf-global')?.insertAdjacentElement('afterend',a);}catch{}}
if(typeof document!=='undefined'){
 const style=document.createElement('style');style.textContent='.gmf-exam-active #mf-mini,.gmf-exam-active .mf-mini,.gmf-exam-active [data-mf-notice],.gmf-exam-active [data-mf="resume"],.gmf-exam-active [data-mf="start"],.gmf-exam-active [data-mf="rest"]{display:none!important}.gmf-exam-guard{padding:12px 24px;background:var(--gmf-s2);color:var(--gmf-text);font:14px system-ui}.gmf-exam-guard a,.as-return-link{color:var(--gmf-blue)}.as-return-link{display:block;margin:12px 32px;font:14px system-ui}';document.head.append(style);
 // Preserve an existing persisted lock while the server is temporarily unreachable.
 LearningStore.getModule(KEY).then(r=>{if(r?.exam_ids?.length)document.documentElement.classList.add('gmf-exam-active');}).catch(()=>{});
 setInterval(()=>{backLink();if(!document.hidden)reconcile();},1500);document.addEventListener('visibilitychange',()=>{if(!document.hidden)reconcile();});reconcile();
}

// A deliberate internal navigation can hand off focus to the next Fusion page.
document.addEventListener('click',async e=>{const a=e.target.closest('a');if(!a||e.defaultPrevented||e.metaKey||e.ctrlKey||a.target==='_blank')return;let u;try{u=new URL(a.href,location.href);}catch{return;}if(u.origin!==location.origin||u.pathname===location.pathname)return;
 e.preventDefault();try{const row=await LearningStore.getModule('mf-v3');if(row?.current?.state==='Focusing'&&!row.exam_ids.length){if(!u.pathname.endsWith('/mind-flow/review.html'))sessionStorage.setItem('gmf-mf-handoff',JSON.stringify({id:row.current.session_id,at:Date.now()}));await LearningStore.atomicModule('mf-v3',r=>{if(r.current?.state==='Focusing'){const a=r.current.anchor;r.current=transition(r.current,{type:'suspend'},{wall_ms:Date.now(),mono_ms:a.mono_ms,runtime_id:a.runtime_id});}return {value:r};});}}finally{location.assign(u.href);}
},true);

if(document.body.dataset.module==='mf-review')LearningStore.atomicModule(KEY,previous=>{const row={...empty(),...previous};if(row.current?.anchor){const a=row.current.anchor;row.current=transition(row.current,{type:'suspend'},{wall_ms:Date.now(),mono_ms:a.mono_ms,runtime_id:'mf-review-entry'});}return {value:row};}).then(()=>channel?.postMessage('changed')).catch(console.error);
