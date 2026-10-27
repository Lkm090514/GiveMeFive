(function(root){
  'use strict';
  const databaseName=document.currentScript?.dataset.database||'givemefive-learning-v1';
  let db,opening,queue=Promise.resolve();
  let userScope=!!root.location&&!['localhost','127.0.0.1','[::1]'].includes(root.location.hostname),owner=null;
  function setIdentity(p){const enabled=p?p.auth_mode==='password':userScope,next=enabled?p?.owner_id||null:null;if(enabled===userScope&&next===owner)return;userScope=enabled;owner=next;root.dispatchEvent?.(new CustomEvent('gmf-identity-change'));}
  function visible(e){return !userScope||!(buckets[e.type]==='assessment'||['Assessment','assessment','givemefive'].includes(e.source)||e.mode==='assessment')||!!owner&&e.user_id===owner;}
  const buckets={EXPOSURE:'exposure',PRACTICE:'practice',MF_SESSION_COMPLETED:'learning_repair',LEARNING_REPAIR:'learning_repair',ASSESSMENT:'assessment',ASSESSMENT_ITEM_RESULT:'assessment'};
  function open(){if(db)return Promise.resolve();if(opening)return opening;return opening=new Promise((resolve,reject)=>{const req=indexedDB.open(databaseName,1);req.onupgradeneeded=()=>{for(const [name,key] of [['state','key'],['ledger','event_id'],['sessions','session_id'],['pending_sync','key']])req.result.createObjectStore(name,{keyPath:key});};req.onsuccess=()=>{db=req.result;db.onversionchange=()=>db.close();resolve();};req.onerror=()=>reject(req.error);req.onblocked=()=>reject(new Error('Close the older GiveMeFive tab and reload.'));});}
  function request(req){return new Promise((resolve,reject)=>{req.onsuccess=()=>resolve(req.result);req.onerror=()=>reject(req.error);});}
  function transaction(names,work){return new Promise((resolve,reject)=>{const tx=db.transaction(names,'readwrite');tx.oncomplete=()=>resolve(true);tx.onerror=tx.onabort=()=>reject(tx.error||new Error('Local database transaction failed'));try{work(tx);}catch(e){tx.abort();reject(e);}});}
  function canonical(e,bucket,course){const tid=e.topic_id??null,unit=e.unit_id??course?.units.find(u=>u.topic_refs.includes(tid))?.unit_id??null;return {...e,event_id:e.event_id||e.session_id||'legacy-'+bucket+'-'+e.course_id+'-'+tid+'-'+(e.occurred_at||e.at||e.completed_at),course_id:e.course_id,unit_id:unit,topic_id:tid,exercise_id:e.exercise_id??null,source:e.source==='pathline'?'PL':e.source==='mind-flow'?'MF':e.source==='givemefive'?'Assessment':e.source,type:e.schema_version>=4&&buckets[e.type]?e.type:e.type==='MF_SESSION_COMPLETED'?e.type:({exposure:'EXPOSURE',practice:'PRACTICE',learning_repair:'LEARNING_REPAIR',assessment:'ASSESSMENT'})[bucket],occurred_at:e.occurred_at||e.at||e.completed_at};}
  const legacyType={EXPOSURE:'exposure',PRACTICE:'practice',LEARNING_REPAIR:'learning_repair',ASSESSMENT:'assessment'};
  function assessmentRevisionKey(e){return e.schema_version>=4&&e.source==='Assessment'&&e.session_id&&buckets[e.type]==='assessment'?e.session_id+'|'+(e.exercise_id?'item:'+e.exercise_id:'summary'):null;}
  function projection(events){
    events=events.filter(visible);
    const highest=new Map();for(const e of events){const key=assessmentRevisionKey(e),revision=e.payload?.grading_revision||1;if(key&&Number.isInteger(revision)&&revision>0)highest.set(key,Math.max(highest.get(key)||1,revision));}
    const evidence={exposure:[],practice:[],learning_repair:[],assessment:[]};
    for(const e of [...events].sort((a,b)=>Date.parse(a.occurred_at)-Date.parse(b.occurred_at))){const key=assessmentRevisionKey(e);if(key&&(e.payload?.grading_revision||1)<highest.get(key))continue;const bucket=buckets[e.type];if(bucket)evidence[bucket].push(e.schema_version>=2?e:{...e,type:legacyType[e.type]||e.type,source:e.source==='MF'?'mind-flow':e.source==='PL'?'pathline':e.source});}
    return evidence;
  }
  async function restore(legacy,course){const tx=db.transaction(['state','ledger','sessions']);const [saved,events,sessions]=await Promise.all([request(tx.objectStore('state').get('current')),request(tx.objectStore('ledger').getAll()),request(tx.objectStore('sessions').getAll())]);for(const e of events)known.set(e.event_id,JSON.stringify(e));for(const session of sessions)knownSessions.set(session.session_id,JSON.stringify(session));if(saved)return {...legacy,...saved.value,evidence:projection(events),sessions:sessions.filter(visible)};await save(legacy,course);return {...legacy,evidence:projection(events.length?events:Object.entries(legacy.evidence).flatMap(([bucket,list])=>list.map(e=>canonical(e,bucket,course)))),sessions:legacy.sessions.filter(visible)};}
  const known=new Map(),knownSessions=new Map();
  function save(state,course){const snapshot=structuredClone(state);queue=queue.catch(()=>{}).then(async()=>{const metadata={...snapshot};delete metadata.evidence;delete metadata.sessions;const events=Object.entries(snapshot.evidence).flatMap(([bucket,list])=>list.map(e=>canonical(e,bucket,course)));const changes=events.filter(e=>known.get(e.event_id)!==JSON.stringify(e)),sessionChanges=snapshot.sessions.filter(s=>knownSessions.get(s.session_id)!==JSON.stringify(s));await transaction(['state','ledger','sessions','pending_sync'],tx=>{tx.objectStore('state').put({key:'current',value:metadata});for(const e of changes){tx.objectStore('ledger').put(e);tx.objectStore('pending_sync').put({key:'event:'+e.event_id,kind:'event',event_id:e.event_id,status:'pending',queued_at:new Date().toISOString()});}for(const s of sessionChanges){tx.objectStore('sessions').put(s);tx.objectStore('pending_sync').put({key:'session:'+s.session_id,kind:'study_session',session_id:s.session_id,status:'pending',queued_at:new Date().toISOString()});}});for(const e of changes)known.set(e.event_id,JSON.stringify(e));for(const s of sessionChanges)knownSessions.set(s.session_id,JSON.stringify(s));return true;});return queue;}
  async function reset(){await queue.catch(()=>{});await transaction(['state','ledger','sessions','pending_sync'],tx=>{for(const n of ['state','ledger','sessions','pending_sync'])tx.objectStore(n).clear();});known.clear();knownSessions.clear();}
  async function getModule(key){await open();return (await request(db.transaction('state').objectStore('state').get(key)))?.value;}
  function commit(key,value,event,session){const snapshot=structuredClone(value),fact=event?structuredClone(event):null,time= session?structuredClone(session):null;event=fact;session=time;queue=queue.catch(()=>{}).then(()=>transaction(['state','ledger','sessions','pending_sync'],tx=>{
    if(key)tx.objectStore('state').put({key,value:snapshot});
    if(event){if(!event.event_id||!buckets[event.type]||!Number.isFinite(Date.parse(event.occurred_at)))throw new Error('Invalid ledger event');const ledger=tx.objectStore('ledger'),req=ledger.get(event.event_id);req.onsuccess=()=>{if(!req.result){ledger.put(event);tx.objectStore('pending_sync').put({key:'event:'+event.event_id,kind:'event',event_id:event.event_id,status:'pending',queued_at:new Date().toISOString()});}};}
    if(session){if(!session.session_id||!Number.isFinite(session.active_seconds)||session.active_seconds<0)throw new Error('Invalid study session');tx.objectStore('sessions').put(session);tx.objectStore('pending_sync').put({key:'session:'+session.session_id,kind:'study_session',session_id:session.session_id,status:'pending',queued_at:new Date().toISOString()});}
  }));return queue;}
  function patchCurrent(patch){queue=queue.catch(()=>{}).then(()=>transaction(['state'],tx=>{const st=tx.objectStore('state'),r=st.get('current');r.onsuccess=()=>st.put({key:'current',value:{...(r.result?.value||{}),...patch}});}));return queue;}
  // One native read/write transaction serializes all tabs. Reducers MUST be synchronous.
  async function atomicModule(key,reducer){await open();return new Promise((resolve,reject)=>{
    const tx=db.transaction(['state','ledger','sessions','pending_sync'],'readwrite');let value,error;
    tx.oncomplete=()=>resolve(value);tx.onerror=tx.onabort=()=>reject(error||tx.error||new Error('Transaction aborted'));
    const st=tx.objectStore('state'),req=st.get(key);req.onsuccess=()=>{try{
      const result=reducer(structuredClone(req.result?.value));
      if(result?.then)throw new Error('Async reducer is not atomic');
      value=result.value;st.put({key,value});
      for(const s of result.sessions||[]){tx.objectStore('sessions').put(s);tx.objectStore('pending_sync').put({key:'session:'+s.session_id,kind:'study_session',session_id:s.session_id,status:'pending'});}
      for(const e of result.events||[]){tx.objectStore('ledger').put(e);tx.objectStore('pending_sync').put({key:'event:'+e.event_id,kind:'event',event_id:e.event_id,status:'pending'});}
    }catch(e){error=e;tx.abort();}};
  });}
  async function exportAll(){await open();const names=['state','ledger','sessions','pending_sync'],tx=db.transaction(names);const values=await Promise.all(names.map(n=>request(tx.objectStore(n).getAll())));return {schema:'gmf-backup/1',created_at:new Date().toISOString(),stores:Object.fromEntries(names.map((n,i)=>[n,values[i]]))};}
  async function restoreBackup(backup){
    if(backup?.schema!=='gmf-backup/1'||!backup.stores)throw Error('不是完整 GiveMeFive 备份');
    const keys={state:'key',ledger:'event_id',sessions:'session_id',pending_sync:'key'};
    for(const [name,key] of Object.entries(keys))if(!Array.isArray(backup.stores[name])||backup.stores[name].some(x=>!x||typeof x[key]!=='string'))throw Error('备份结构不完整');
    await open();let inserted=0,kept=0;
    // Import is additive. Existing IDs win; conflicting originals are retained in an import archive.
    const archiveKey='backup-import:'+crypto.randomUUID();
    await transaction(Object.keys(keys),tx=>{
      tx.objectStore('state').put({key:archiveKey,value:structuredClone(backup)});
      for(const [name,key] of Object.entries(keys))for(const item of backup.stores[name]){
        const st=tx.objectStore(name),req=st.get(item[key]);req.onsuccess=()=>{if(req.result){kept++;return;}const imported=structuredClone(item);if(name==='state'&&item.key==='mf-v3'&&imported.value?.current?.schema==='gmf.mf.session.candidate/1'&&imported.value.current.state!=='Ended'){imported.value.current.state='Paused';imported.value.current.anchor=null;imported.value.current.pause_reason='recovered';imported.value.current.revision++;}st.put(imported);inserted++;};
      }
    });return {inserted,kept,archiveKey};
  }
  // Multi-module transaction: exam, MF ownership and evidence commit or roll back together.
  async function atomicModules(keys,reducer){await open();return new Promise((resolve,reject)=>{
    const tx=db.transaction(['state','ledger','sessions','pending_sync'],'readwrite');let output,error;const values={};let left=keys.length;
    tx.oncomplete=()=>resolve(output);tx.onerror=tx.onabort=()=>reject(error||tx.error||new Error('Transaction aborted'));
    const st=tx.objectStore('state');
    for(const key of keys){const req=st.get(key);req.onsuccess=()=>{values[key]=structuredClone(req.result?.value);if(--left)return;
      try{const result=reducer(values);if(result?.then)throw Error('Async reducer is not atomic');output=result.value;
        for(const [key,value] of Object.entries(result.modules||{})){if(!keys.includes(key))throw Error('Undeclared module');st.put({key,value});}
        for(const event of result.events||[]){if(!event.event_id||!buckets[event.type]||!Number.isFinite(Date.parse(event.occurred_at)))throw Error('Invalid ledger event');const ledger=tx.objectStore('ledger'),r=ledger.get(event.event_id);r.onsuccess=()=>{if(!r.result){ledger.put(event);tx.objectStore('pending_sync').put({key:'event:'+event.event_id,kind:'event',event_id:event.event_id,status:'pending'});}};}
        for(const session of result.sessions||[]){if(!session.session_id||!Number.isFinite(session.active_seconds)||session.active_seconds<0)throw Error('Invalid study session');tx.objectStore('sessions').put(session);tx.objectStore('pending_sync').put({key:'session:'+session.session_id,kind:'study_session',session_id:session.session_id,status:'pending'});}
      }catch(e){error=e;tx.abort();}
    };}
  });}
  root.LearningStore={setIdentity,open,atomicModules,restore,save,reset,canonical,projection,getModule,atomicModule,exportAll,restoreBackup,putModule:(key,value)=>commit(key,value),commit,patchCurrent,flush:()=>queue};
})(window);

