(function(root){
  'use strict';
  const B=typeof module!=='undefined'&&module.exports?require('./blueprints.js'):root.MFBlueprints;
  const Core=typeof module!=='undefined'&&module.exports?require('./flow-core.js'):root.MindFlowCore;
  const text=(value,lang)=>value[lang==='en'?'en':'zh'];
  const key=c=>c.course_id+'|'+c.topic_id;
  function create(context){
    if(!B[context.topic_id]||!context.unit_id||!context.course_id)throw new Error('Unsupported MF context');
    const run=Core.createRun(context.title,['Recall','Explain / Apply','Repair','Recheck'],'free',25);
    return {...run,context:{...context},stage:'recall',response:'',attempt_log:[],hint_levels_used:[],repair_sources_used:[],repair_used:false,source_open:false,checked:false,final_state:null,active_seconds:0,daily_seconds:{}};
  }
  function prompt(run){const b=B[run.context.topic_id];return run.stage==='recall'?b.recall_prompts[0]:b.application_prompts[run.stage==='application'?0:run.repair_used?2:1];}
  function judge(tid,p,response){
    const s=response.trim().toLowerCase().replace(/²/g,'^2').replace(/[−–]/g,'-');
    if(!s||s.length>4000)return false;
    if(p.kind==='number')return /^[+-]?(?:\d+(?:\.\d*)?|\.\d+)$/.test(s)&&Math.abs(Number(s)-p.value)<1e-6;
    // ponytail: explicit local rubric, not an AI semantic grader. Unrecognised wording goes to repair.
    return Array.isArray(p.required)&&p.required.length>0&&p.required.every(group=>group.some(pattern=>new RegExp(pattern,'i').test(s)))&&!(p.reject||[]).some(pattern=>new RegExp(pattern,'i').test(s));
  }
  function advance(run,step){run.current=step;Core.completeStep(run);}
  function submit(run,response,now=Date.now()){
    if(run.final_state||!['recall','application','recheck'].includes(run.stage)||run.paused)throw new Error('MF is not accepting an answer');
    if(typeof response!=='string'||!response.trim()||response.length>4000)throw new Error('Empty or oversized response');
    const p=prompt(run),success=judge(run.context.topic_id,p,response);
    run.attempt_log.push({prompt_id:p.id,stage:run.stage,response:response.trim(),success,at:new Date(now).toISOString()});
    run.response='';run.checked=false;
    if(run.stage==='recall'){run.initial_retrieval=success?'independent_success':'incomplete';advance(run,1);run.stage=success?'application':'repair';}
    else if(run.stage==='application'){run.explanation_or_application_result=success?'success':'incomplete';advance(run,2);run.stage=success?'recheck':'repair';}
    else if(success){advance(run,4);run.final_state=run.repair_used?'repaired_success':'independent_success';run.stage='finished';run.completed_at=new Date(now).toISOString();}
    else if(run.repair_used){run.final_state='unresolved';run.stage='finished';run.completed_at=new Date(now).toISOString();}
    else run.stage='repair';
    if(run.stage==='repair')run.repair_used=true;
    return success;
  }
  function hint(run){if(run.stage!=='repair'||run.hint_levels_used.length>=2)return false;run.hint_levels_used.push(run.hint_levels_used.length+1);return true;}
  function openSource(run){if(run.stage!=='repair'||run.hint_levels_used.length!==2)throw new Error('Use the hint ladder first');run.source_open=true;run.repair_sources_used=B[run.context.topic_id].repair_sources.map(s=>s.ref);}
  function recheck(run){if(run.stage!=='repair'||!run.hint_levels_used.length)throw new Error('Repair not started');advance(run,3);run.source_open=false;run.stage='recheck';run.response='';}
  function evidence(run){
    if(!run.final_state||run.stage!=='finished')throw new Error('Incomplete MF session has no completed evidence');
    const c=run.context;
    return {schema_version:2,event_id:c.session_id,session_id:c.session_id,course_id:c.course_id,unit_id:c.unit_id,topic_id:c.topic_id,exercise_id:null,source:'MF',type:'MF_SESSION_COMPLETED',occurred_at:run.completed_at,started_at:c.started_at,completed_at:run.completed_at,
      payload:{initial_retrieval:run.initial_retrieval,explanation_or_application_result:run.explanation_or_application_result||'not_attempted',hint_levels_used:[...run.hint_levels_used],repair_used:run.repair_used,repair_sources_used:[...run.repair_sources_used],post_repair_retrieval:run.attempt_log.filter(a=>a.stage==='recheck').at(-1)?.success?'success':'failed',final_state:run.final_state,active_seconds:run.active_seconds,attempt_log:run.attempt_log.map(a=>({...a})),success_basis:'blueprint_local_rubric_v1'}};
  }
  function derived(store,cid,tid,progress){const items=store.learning_repair.filter(e=>e.course_id===cid&&e.topic_id===tid&&e.payload?.mode!=='focus'),latest=items.at(-1);return {latest_mf_result:latest?.payload?.final_state||null,mf_session_count:items.length,last_review_at:latest?.occurred_at||latest?.completed_at||null,next_review_at:progress?.dueAt?new Date(progress.dueAt).toISOString():null};}
  const api={blueprints:B,text,key,create,prompt,judge,submit,hint,openSource,recheck,evidence,derived};
  if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.MindFlowV1=api;
})(typeof window==='undefined'?globalThis:window);
