(function(root){
  'use strict';
  const IDLE_MS=120000;
  const dayKey=timestamp=>{const d=new Date(timestamp);return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;};
  function credit(session,from,to,lastInput,visible){
    if(!session||!visible||to<=from)return 0;
    const end=Math.min(to,lastInput+IDLE_MS);if(end<=from)return 0;
    let cursor=from;session.daily_seconds=session.daily_seconds||{};
    while(cursor<end){const d=new Date(cursor),next=new Date(d.getFullYear(),d.getMonth(),d.getDate()+1).getTime(),stop=Math.min(end,next),seconds=(stop-cursor)/1000,key=dayKey(cursor);session.daily_seconds[key]=(session.daily_seconds[key]||0)+seconds;cursor=stop;}
    const seconds=(end-from)/1000;session.active_seconds=(session.active_seconds||0)+seconds;session.ended_at=new Date(to).toISOString();return seconds;
  }
  function week(sessions,timestamp=Date.now()){
    const today=new Date(timestamp),monday=new Date(today.getFullYear(),today.getMonth(),today.getDate()-((today.getDay()+6)%7));
    return Array.from({length:7},(_,i)=>{const date=new Date(monday.getFullYear(),monday.getMonth(),monday.getDate()+i),key=dayKey(+date),courses={};
      for(const s of sessions){const seconds=s.daily_seconds?.[key]||0;if(!Number.isFinite(seconds)||seconds<=0)continue;const c=courses[s.course_id]||(courses[s.course_id]={total:0,learn:0,review:0,assessment:0});c.total+=seconds;c[s.mode]=(c[s.mode]||0)+seconds;}
      return {key,date:+date,courses,total:Object.values(courses).reduce((n,c)=>n+c.total,0)};
    });
  }
  const api={IDLE_MS,credit,week,dayKey};if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.PathlineSessions=api;
})(typeof window==='undefined'?globalThis:window);
