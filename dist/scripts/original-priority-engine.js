
window.PathlineEngine = (() => {
  const DAY = 86400000;
  const clamp=(n,a,b)=>Math.max(a,Math.min(b,n));
  const now=()=>Date.now();
  const daysBetween=(a,b)=>Math.max(0,(b-a)/DAY);
  function initialTopicState(){return {mastery:22, attempts:0, correct:0, confidence:0.5, lastStudied:null, dueAt:null, intervalDays:0, ease:2.3, streak:0};}
  function ensureCourseProgress(course, existing={}){
    const out={...existing};
    course.units.forEach(u=>u.topics.forEach(t=>{ if(!out[t.id]) out[t.id]=initialTopicState(); }));
    return out;
  }
  function prerequisiteReadiness(topic, progress){
    if(!topic.prereq?.length) return 1;
    return topic.prereq.reduce((sum,id)=>sum+(progress[id]?.mastery??20)/100,0)/topic.prereq.length;
  }
  function downstreamLeverage(topic, course, progress){
    if(!course) return 0;
    const dependents=[];
    course.units.forEach(u=>u.topics.forEach(t=>{ if(t.prereq?.includes(topic.id)) dependents.push(t); }));
    if(!dependents.length) return 0;
    const weakness=dependents.reduce((sum,t)=>sum+(100-(progress[t.id]?.mastery??20))/100,0)/dependents.length;
    return clamp(weakness*(0.7+0.15*Math.min(2,dependents.length)),0,1);
  }
  function forgettingRisk(state){
    if(!state.lastStudied) return .45;
    const elapsed=daysBetween(state.lastStudied, now());
    const interval=Math.max(.5,state.intervalDays||1);
    return clamp(elapsed/interval,0,1.6)/1.6;
  }
  function examPressure(examDate){
    if(!examDate) return .35;
    const t=new Date(examDate).getTime(); if(!Number.isFinite(t)) return .35;
    const d=Math.max(0,(t-now())/DAY);
    return clamp(1-d/180,0.1,1);
  }
  function priority(topic,state,progress,examDate,course){
    const weakness=(100-state.mastery)/100;
    const forget=forgettingRisk(state);
    const prereqReady=prerequisiteReadiness(topic,progress);
    const leverage=downstreamLeverage(topic,course,progress);
    const confidenceGap=1-(state.confidence??.5);
    const overdue=state.attempts>0 && state.dueAt && state.dueAt<=now()?1:0;
    const pressure=examPressure(examDate);
    const blockPenalty=topic.prereq?.length ? (prereqReady<.45?.18:prereqReady<.65?.08:0) : 0;
    const raw=.36*weakness+.20*forget+.12*leverage+.08*confidenceGap+.12*overdue+.07*pressure-blockPenalty;
    const score=100*clamp(raw,0,1);
    const reasons=[];
    if(weakness>.55) reasons.push('low mastery');
    if(overdue) reasons.push('review due');
    if(state.attempts>0 && forget>.55) reasons.push('memory decay');
    if(leverage>.35) reasons.push('unlocks later topics');
    if(confidenceGap>.55) reasons.push('low confidence');
    if(prereqReady<.6 && topic.prereq?.length) reasons.push('prerequisites not ready');
    if(reasons.length===0) reasons.push('best next gain');
    return {score:Math.round(score),reasons,prereqReady,leverage};
  }
  function recordAnswer(state, correct, confidence=.65){
    const s={...state};
    s.attempts=(s.attempts||0)+1; s.correct=(s.correct||0)+(correct?1:0);
    s.confidence=clamp((s.confidence??.5)*.65+confidence*.35,0,1);
    const quality=correct ? (confidence>.75?5:confidence>.45?4:3) : (confidence>.7?1:2);
    if(correct){
      s.streak=(s.streak||0)+1;
      s.ease=clamp((s.ease||2.3)+(quality===5?.12:.04),1.3,3.0);
      if(s.streak===1) s.intervalDays=1;
      else if(s.streak===2) s.intervalDays=3;
      else s.intervalDays=Math.max(1,Math.round((s.intervalDays||3)*s.ease));
      const gain=7 + (1-s.mastery/100)*10 + (confidence>.7?2:0);
      s.mastery=clamp(Math.round(s.mastery+gain),0,100);
    } else {
      s.streak=0; s.ease=clamp((s.ease||2.3)-.18,1.3,3.0); s.intervalDays=.35;
      const penalty=confidence>.7?9:5; s.mastery=clamp(Math.round(s.mastery-penalty),0,100);
    }
    s.lastStudied=now(); s.dueAt=now()+s.intervalDays*DAY;
    return s;
  }
  function courseReadiness(course,progress){
    let total=0,weight=0;
    course.units.forEach(u=>u.topics.forEach(t=>{const s=progress[t.id]||initialTopicState(); const w=1+((parseInt(u.weight)||15)/30); total+=s.mastery*w;weight+=w;}));
    return weight?Math.round(total/weight):0;
  }
  function rankedTopics(course,progress,examDate){
    const rows=[]; course.units.forEach(u=>u.topics.forEach(t=>{ const st=progress[t.id]||initialTopicState(); rows.push({unit:u,topic:t,state:st,...priority(t,st,progress,examDate,course)}); }));
    return rows.sort((a,b)=>b.score-a.score);
  }
  function dueTopics(course,progress){
    const rows=[]; course.units.forEach(u=>u.topics.forEach(t=>{const s=progress[t.id]; if(s&&s.attempts>0&&s.dueAt&&s.dueAt<=now()) rows.push({unit:u,topic:t,state:s});}));
    return rows.sort((a,b)=>a.state.dueAt-b.state.dueAt);
  }
  return {initialTopicState,ensureCourseProgress,priority,recordAnswer,courseReadiness,rankedTopics,dueTopics,forgettingRisk,prerequisiteReadiness,downstreamLeverage};
})();

