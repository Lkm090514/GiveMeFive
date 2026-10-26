/* PL Fusion V0.1: evidence compatibility; original priority weights stay in PathlineEngine. */
(function (root) {
  'use strict';
  const DAY = 86400000;
  const goals = {
    '2.5': ['用合力与质量解释加速度：ΣF = ma。', '选择研究对象，画受力图，并按坐标分解牛顿第二定律。', '区分作用在同一物体上的合力与不同物体间的作用反作用力。'],
    '5.4': ['解释转动惯量与质量相对转轴分布的关系。', '使用 I = Σmr²、I = ∫r²dm 和平行轴定理。', '区分改变质量分布与改变转轴对转动惯量的影响。'],
    '7.5': ['解释小角近似下单摆周期与摆长、重力加速度的关系。', '用转动惯量与重心到转轴的距离描述物理摆。', '识别周期公式的适用条件。']
  };
  function makeCourse(data) {
    const topics = new Map(data.course.topics.map(t => [t.topic_id, t]));
    return {id:data.course.course_id, title:'AP Physics C: Mechanics', subtitle:'2026–27 / May 2027 · 7 Units / 41 Topics', accent:'blue', targetDefault:'5', contentKind:'openstax', units:data.course.units.map(u => ({id:String(u.unit_id), title:u.title, weight:'', topics:u.topic_refs.map(id => ({id, title:`${id} ${topics.get(id).title}`, minutes:null, prereq:[], summary:'', objectives:goals[id] || [], questions:[], contentStatus:topics.get(id).status}))}))};
  }
  const emptyEvidence = () => ({exposure:[], practice:[], learning_repair:[], assessment:[]});
  const mcqWeights={'1':'10–15%','2':'20–25%','3':'15–25%','4':'10–20%','5':'10–15%','6':'10–15%','7':'10–15%'};
  function normalizeEvidence(store) {
    store.practice=Array.isArray(store.practice)?store.practice:[];
    for(const e of store.exposure)e.occurred_at=e.occurred_at||e.at;
    for(const e of store.learning_repair)e.occurred_at=e.occurred_at||e.completed_at;
    for(const e of store.assessment)e.occurred_at=e.occurred_at||e.completed_at||e.at;
    // Keep legacy history; migrate the old exercise marker once, by course + exercise.
    const groups=new Map();
    for(const e of store.exposure.filter(e=>e.action==='exercise_attempted'&&e.exercise_id))groups.set(e.course_id+'|'+e.exercise_id,e);
    for(const e of groups.values())if(!store.practice.some(p=>p.course_id===e.course_id&&p.exercise_id===e.exercise_id))store.practice.push({...e,event_id:'migrated-'+e.event_id,type:'practice',action:'exercise_attempted',occurred_at:e.occurred_at});
    return store;
  }
  function completed(store,cid,tid) {
    const e=store.exposure.filter(e=>e.course_id===cid&&e.topic_id===tid&&['reading_completed','reading_cancelled'].includes(e.action)).at(-1);
    return e?.action==='reading_completed';
  }
  function unitProgress(store,cid,unit) {
    const count=unit.topics.filter(t=>completed(store,cid,t.id)).length,total=unit.topics.length;
    return {count,total,percent:total?Math.round(count/total*100):0};
  }
  function practiceComplete(store,cid,id) {
    return store.practice.filter(e=>e.course_id===cid&&e.exercise_id===id).at(-1)?.action==='exercise_completed';
  }
  function courseCompletion(store,course) {return unitProgress(store,course.id,{topics:course.units.flatMap(u=>u.topics)});}
  function exerciseProgress(store,cid,ids) {
    const unique=[...new Set(ids)],count=unique.filter(id=>practiceComplete(store,cid,id)).length;
    return {count,total:unique.length,percent:unique.length?Math.round(count/unique.length*100):0};
  }
  function rebuildSchedule(store,progress,cid,tid) {
    const s=progress[tid];if(!s)return;
    if(!(s.attempts>0)){s.lastStudied=null;s.dueAt=null;s.intervalDays=0;delete s.lastInteraction;delete s.lastEvidenceReason;}
    const events=[...store.exposure.filter(e=>e.course_id===cid&&e.topic_id===tid&&e.action==='topic_opened'),
      ...store.exposure.filter(e=>e.course_id===cid&&e.topic_id===tid&&e.action==='reading_completed'&&completed(store,cid,tid)).slice(-1),
      ...store.practice.filter(e=>e.course_id===cid&&e.topic_id===tid&&(e.action==='exercise_attempted'||e.action==='exercise_completed'&&practiceComplete(store,cid,e.exercise_id))),
      ...store.learning_repair.filter(e=>e.course_id===cid&&e.topic_id===tid&&e.payload?.mode!=='focus')]
      .sort((a,b)=>Date.parse(a.occurred_at||a.at||a.completed_at)-Date.parse(b.occurred_at||b.at||b.completed_at));
    for(const e of events){if(e.type==='learning_repair'||e.type==='MF_SESSION_COMPLETED')applyLearningSchedule(s,e);else recordExposure(emptyEvidence(),progress,{...e,action:e.type==='practice'?'exercise_attempted':e.action},Date.parse(e.occurred_at||e.at));}
    s.naturalDueAt=s.dueAt;s.naturalIntervalDays=s.intervalDays;
  }
  function toggleCompletion(store,progress,event,timestamp=Date.now()) {
    const active=!completed(store,event.course_id,event.topic_id);
    store.exposure.push({...event,type:'exposure',source:'pathline',action:active?'reading_completed':'reading_cancelled',at:new Date(timestamp).toISOString(),occurred_at:new Date(timestamp).toISOString()});
    rebuildSchedule(store,progress,event.course_id,event.topic_id);return active;
  }
  function togglePractice(store,progress,event,timestamp=Date.now()) {
    const active=!practiceComplete(store,event.course_id,event.exercise_id);
    store.practice.push({...event,type:'practice',source:'pathline',action:active?'exercise_completed':'exercise_cancelled',occurred_at:new Date(timestamp).toISOString()});
    const tids=new Set(store.practice.filter(e=>e.course_id===event.course_id&&e.exercise_id===event.exercise_id).map(e=>e.topic_id));
    for(const tid of tids)rebuildSchedule(store,progress,event.course_id,tid);
    return active;
  }
  function dayKey(timestamp=Date.now()) {const d=new Date(timestamp);return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;}
  function localDate(value) {if(!/^\d{4}-\d{2}-\d{2}$/.test(value||''))return null;const d=new Date(value+'T00:00:00');return Number.isFinite(+d)&&dayKey(+d)===value?d:null;}
  function examInfo(value,timestamp=Date.now()) {
    const date=localDate(value);if(!date)return {state:'unset'};
    const today=localDate(dayKey(timestamp));
    const days=Math.round((Date.UTC(date.getFullYear(),date.getMonth(),date.getDate())-Date.UTC(today.getFullYear(),today.getMonth(),today.getDate()))/86400000);
    return {state:days<0?'ended':days===0?'today':'upcoming',days,date:+date,deadline:new Date(date.getFullYear(),date.getMonth(),date.getDate(),23,59,59,999).getTime(),maxIntervalDays:Math.max(1,Math.min(30,Math.ceil(Math.max(0,days)/6)))};
  }
  function capReview(progress,date,timestamp=Date.now()) {
    const exam=examInfo(date,timestamp);
    for(const s of Object.values(progress))if(s.dueAt){
      if(!s.naturalDueAt){s.naturalDueAt=s.dueAt;s.naturalIntervalDays=s.intervalDays;}
      const origin=s.lastStudied||timestamp,limited=exam.state==='upcoming'||exam.state==='today';
      s.dueAt=limited?Math.min(s.naturalDueAt,origin+exam.maxIntervalDays*DAY,exam.deadline):s.naturalDueAt;
      s.intervalDays=limited?Math.min(s.naturalIntervalDays,Math.max(0,(s.dueAt-origin)/DAY)):s.naturalIntervalDays;
      if(s.last_review_at)s.next_review_at=new Date(s.dueAt).toISOString();
    }
    return exam;
  }
  const isReady = topic => topic.contentStatus === 'validated' || topic.contentKind === 'imported';
  const isAP = course => /^AP(?:\s|$)/i.test(course?.title||'');
  function targetScore(course, value) {
    return isAP(course) ? (/^[1-5]$/.test(String(value)) ? String(value) : '5') : String(value || course.targetDefault || 'A');
  }
  function weightedReadiness(engine, course, progress, store) {
    let measured=0;
    const states=Object.fromEntries(course.units.flatMap(u=>u.topics).map(t=>{
      const s=progress[t.id]||{}, known=(s.attempts||0)>0 || store.assessment.some(e=>e.course_id===course.id&&e.topic_id===t.id);
      if(known)measured++;
      return [t.id,{mastery:known?(s.mastery||0):0}];
    }));
    return {score:measured?engine.courseReadiness(course,states):null,measured};
  }
  function exerciseRecorded(store, courseId, topicId, exerciseId) {
    return store.exposure.some(e=>e.course_id===courseId&&e.topic_id===topicId&&e.action==='exercise_attempted'&&e.exercise_id===exerciseId);
  }
  function toggleExercise(store, progress, event, timestamp=Date.now()) {
    if(!exerciseRecorded(store,event.course_id,event.topic_id,event.exercise_id)) {
      recordExposure(store,progress,{...event,action:'exercise_attempted'},timestamp);return true;
    }
    store.exposure=store.exposure.filter(e=>!(e.course_id===event.course_id&&e.topic_id===event.topic_id&&e.action==='exercise_attempted'&&e.exercise_id===event.exercise_id));
    const s=progress[event.topic_id];
    if(s && !(s.attempts>0)) {
      s.lastStudied=null;s.dueAt=null;s.intervalDays=0;delete s.lastInteraction;delete s.lastEvidenceReason;
      const events=[...store.exposure.filter(e=>e.course_id===event.course_id&&e.topic_id===event.topic_id),...store.learning_repair.filter(e=>e.course_id===event.course_id&&e.topic_id===event.topic_id)]
        .sort((a,b)=>Date.parse(a.at||a.completed_at)-Date.parse(b.at||b.completed_at));
      for(const e of events) {
        if(e.type==='learning_repair'||e.type==='MF_SESSION_COMPLETED')applyLearningSchedule(s,e);
        else recordExposure(emptyEvidence(),progress,e,Date.parse(e.at));
      }
    }
    return false;
  }
  function availableRanked(engine, course, progress, date) {
    capReview(progress,date);
    return engine.rankedTopics(course, progress, '', course).filter(r => isReady(r.topic));
  }
  function validateLearning(e, context) {
    if(e?.schema_version===2){
      const MF=typeof module!=='undefined'&&module.exports?require('./mind-flow/v1.js'):root.MindFlowV1;
      if(e.source!=='MF'||e.type!=='MF_SESSION_COMPLETED'||e.event_id!==context.session_id||e.session_id!==context.session_id||e.course_id!==context.course_id||e.unit_id!==context.unit_id||e.topic_id!==context.topic_id||e.started_at!==context.started_at)throw new Error('MF evidence identity mismatch');
      const start=Date.parse(e.started_at),end=Date.parse(e.completed_at),p=e.payload;
      if(!Number.isFinite(start)||!Number.isFinite(end)||end<start||end>Date.now()+60000||e.occurred_at!==e.completed_at||!p||!Number.isFinite(p.active_seconds)||p.active_seconds<0||p.active_seconds>(end-start)/1000+1)throw new Error('Invalid MF time');
      if(!Array.isArray(p.attempt_log)||!p.attempt_log.length||p.attempt_log.length>4||!Array.isArray(p.hint_levels_used)||!Array.isArray(p.repair_sources_used)||typeof p.repair_used!=='boolean'||p.success_basis!=='blueprint_local_rubric_v1')throw new Error('Invalid MF payload');
      const replay=MF.create(context);for(const a of p.attempt_log){
        if(replay.stage==='repair'){for(const level of p.hint_levels_used){if(level!==replay.hint_levels_used.length+1||!MF.hint(replay))throw new Error('Invalid hint order');}if(p.repair_sources_used.length)MF.openSource(replay);MF.recheck(replay);}
        if(a.stage!==replay.stage||a.prompt_id!==MF.prompt(replay).id||typeof a.response!=='string'||typeof a.success!=='boolean'||!Number.isFinite(Date.parse(a.at))||Date.parse(a.at)<start||Date.parse(a.at)>end)throw new Error('Invalid MF attempt');
        if(MF.submit(replay,a.response,Date.parse(a.at))!==a.success)throw new Error('MF rubric mismatch');
      }
      const check=MF.evidence(replay).payload;
      for(const field of ['initial_retrieval','explanation_or_application_result','post_repair_retrieval','final_state','repair_used'])if(p[field]!==check[field])throw new Error('MF outcome mismatch');
      for(const field of ['hint_levels_used','repair_sources_used'])if(JSON.stringify(p[field])!==JSON.stringify(check[field]))throw new Error('MF repair mismatch');
      return e;
    }
    if (!e || e.type !== 'learning_repair' || e.source !== 'mind-flow' || e.schema_version !== 1 || e.session_id !== context.session_id || e.topic_id !== context.topic_id || e.course_id !== context.course_id) throw new Error('MF evidence identity mismatch');
    const start = Date.parse(e.started_at), end = Date.parse(e.completed_at);
    if (!Number.isFinite(start) || !Number.isFinite(end) || end < start || end > Date.now()+60000 || e.started_at !== context.started_at) throw new Error('Invalid evidence time');
    for (const field of ['retrieval_attempts','successful_retrievals','retry_count','hint_usage']) if (!Number.isSafeInteger(e[field]) || e[field] < 0 || e[field] > 10000) throw new Error('Invalid evidence count');
    if (e.successful_retrievals > e.retrieval_attempts || e.retry_count > e.retrieval_attempts || typeof e.completion !== 'boolean' || !Array.isArray(e.repair_steps) || !Array.isArray(e.attempt_log)) throw new Error('Invalid evidence structure');
    if (e.attempt_log.length !== e.retrieval_attempts || e.attempt_log.filter(a => a.self_reported_success === true).length !== e.successful_retrievals || e.attempt_log.filter(a => a.retry === true).length !== e.retry_count) throw new Error('Attempt counters disagree');
    if (e.success_basis !== 'learner_self_check' || !Number.isFinite(e.elapsed_ms) || e.elapsed_ms < 0) throw new Error('Invalid evidence provenance');
    for (const a of e.attempt_log) if (typeof a.response !== 'string' || !a.response.trim() || a.response.length > 4000 || typeof a.self_reported_success !== 'boolean' || typeof a.retry !== 'boolean') throw new Error('Invalid retrieval response');
    for (const step of e.repair_steps) if (!step || typeof step.kind !== 'string' || typeof step.text !== 'string' || step.text.length > 4000) throw new Error('Invalid repair step');
    return e;
  }
  function recordExposure(store, progress, e, timestamp = Date.now()) {
    if (store.exposure.some(x => x.event_id === e.event_id)) return false;
    store.exposure.push({...e,type:'exposure',source:'pathline',at:new Date(timestamp).toISOString(),occurred_at:new Date(timestamp).toISOString()});
    const s = progress[e.topic_id];
    if (s) {
      s.lastInteraction = timestamp;
      if (e.action !== 'topic_opened') {
        s.lastStudied = timestamp;
        s.intervalDays = s.intervalDays || 1;
        s.dueAt = timestamp + s.intervalDays * DAY;
        s.lastEvidenceReason = e.action === 'exercise_attempted' ? '已记录教材练习尝试，等待复习' : '已记录正文学习，等待复习';
        s.naturalDueAt=s.dueAt;s.naturalIntervalDays=s.intervalDays;
      }
    }
    return true;
  }
  function acceptLearning(store, progress, evidence, context) {
    validateLearning(evidence, context);
    if (store.learning_repair.some(e => e.session_id === evidence.session_id)) return false;
    const s = progress[evidence.topic_id];
    if (!s) throw new Error('Topic progress missing');
    store.learning_repair.push({...evidence,occurred_at:evidence.completed_at});
    applyLearningSchedule(s,evidence);
    return true;
  }
  function applyLearningSchedule(s,evidence) {
    if(evidence.payload?.mode==='focus')return;
    if(evidence.schema_version===2){
      const timestamp=Date.parse(evidence.occurred_at);if(timestamp<(s.lastInteraction||0))return;
      const state=evidence.payload.final_state;
      s.lastInteraction=s.lastStudied=timestamp;s.last_review_at=evidence.occurred_at;s.latest_mf_result=state;
      s.intervalDays=state==='independent_success'?2:state==='repaired_success'?.5:.125;
      s.dueAt=timestamp+s.intervalDays*DAY;s.next_review_at=new Date(s.dueAt).toISOString();s.lastEvidenceReason=state;
      s.naturalDueAt=s.dueAt;s.naturalIntervalDays=s.intervalDays;return;
    }
    // Completion and self-checks never call recordAnswer or modify mastery/confidence.
    if (evidence.retrieval_attempts || evidence.hint_usage || evidence.repair_steps.length) {
      const timestamp = Date.parse(evidence.completed_at);
      if (timestamp >= (s.lastInteraction || 0)) {
        const repair = evidence.retrieval_attempts > evidence.successful_retrievals || evidence.hint_usage > 0 || evidence.repair_steps.length > 0;
        s.lastInteraction = s.lastStudied = timestamp;
        s.intervalDays = repair ? .35 : (s.intervalDays || 1);
        s.dueAt = timestamp + s.intervalDays * DAY;
        s.lastEvidenceReason = repair ? 'MF 记录了提示或修正，需要较早复习' : 'MF 记录了提取尝试，已安排下次复习';
        s.naturalDueAt=s.dueAt;s.naturalIntervalDays=s.intervalDays;
      }
    }
  }
  function topicEvidence(store, courseId, topicId) {
    return {exposure:store.exposure.filter(e => e.course_id === courseId && e.topic_id === topicId), learning:store.learning_repair.filter(e => e.course_id === courseId && e.topic_id === topicId), assessment:store.assessment.filter(e => e.course_id === courseId && e.topic_id === topicId)};
  }
  const api = {rebuildSchedule,goals,makeCourse,emptyEvidence,isReady,isAP,targetScore,weightedReadiness,exerciseRecorded,toggleExercise,availableRanked,validateLearning,recordExposure,acceptLearning,topicEvidence,mcqWeights,normalizeEvidence,completed,unitProgress,courseCompletion,practiceComplete,exerciseProgress,toggleCompletion,togglePractice,dayKey,examInfo,capReview};
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.PathlineFusion = api;
})(typeof window === 'undefined' ? globalThis : window);
