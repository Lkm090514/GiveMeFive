(function(root){
  'use strict';
  function contextFromHash(hash){
    if(!hash.startsWith('#pathline='))return null;
    try{const c=JSON.parse(decodeURIComponent(hash.slice(10)));if(typeof c.session_id!=='string'||typeof c.course_id!=='string'||typeof c.topic_id!=='string'||typeof c.title!=='string'||!Number.isFinite(Date.parse(c.started_at))||!Array.isArray(c.goals)||c.goals.some(g=>typeof g!=='string'))return null;return c;}catch{return null;}
  }
  function evidence(run){
    const c=run.pathlineContext,log=run.attempt_log||[];
    return {schema_version:1,type:'learning_repair',source:'mind-flow',session_id:c.session_id,course_id:c.course_id,topic_id:c.topic_id,started_at:c.started_at,completed_at:run.date,retrieval_attempts:log.length,successful_retrievals:log.filter(x=>x.self_reported_success).length,retry_count:log.filter(x=>x.retry).length,hint_usage:run.hint_usage||0,repair_steps:run.repair_steps||[],completion:run.steps.every(s=>s.status==='done'),success_basis:'learner_self_check',attempt_log:log,elapsed_ms:run.elapsed};
  }
  const api={contextFromHash,evidence};
  if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.PathlineMFBridge=api;
})(typeof window==='undefined'?globalThis:window);
